import asyncio
import json
import logging
from dataclasses import dataclass
from core.utils.engine import engine

logger = logging.getLogger("JKAI.ExecutorGateway")

_EVIDENCE_GUARD = None


def _get_evidence_guard():
    global _EVIDENCE_GUARD
    if _EVIDENCE_GUARD is None:
        from core.kernel.evidence_gate import EvidenceGuard
        _EVIDENCE_GUARD = EvidenceGuard()
    return _EVIDENCE_GUARD

@dataclass(frozen=True)
class ExecutionRequest:
    trace_id: str
    capability_token: dict
    tool_name: str
    tool_args: dict
    timeout: int = 600

class ExecutorGateway:
    """
    JKAI Zenith - Executor Gateway
    Secure execution broker using capability tokens.

    [v26.2] ExecutionIntegrityLayer is wired here as the SINGLE enforcement point.
    All tool calls — from ReAct loop, skill executor, project agent — pass through
    execute_tool(), so enforcing integrity here closes all execution paths simultaneously.
    """
    def __init__(self, http_client):
        self.http_client = http_client

    def _log(self, tag, msg, task_id="manual", stealth=False):
        try:
            engine.publish_mission_log(tag, msg, task_id, stealth=stealth)
        except Exception: pass

    async def _post_to_executor(self, url: str, payload: dict, timeout: int) -> dict:
        """Helper: POST to executor and return JSON response."""
        resp = await self.http_client.post(url, json=payload, timeout=timeout)
        if hasattr(resp, "json"):
            res = resp.json()
            if hasattr(res, "__await__"):
                return await res
            return res
        elif isinstance(resp, dict):
            return resp
        return {}

    async def execute_tool(self, request: ExecutionRequest, task_id: str) -> str:
        """
        [v26.2] Execution entry point with integrated security gate.

        Order of evaluation:
          1. ExecutionIntegrityLayer.authorize() — TaskContract + DecisionAuthority + Risk
          2. If DENY → return denial string immediately (no executor call)
          3. If REQUIRE_APPROVAL → log interrupt, return approval-required string (no executor call)
          4. If ALLOW → proceed to executor HTTP dispatch as before
        """
        # ------------------------------------------------------------------ #
        # [EXECUTION INTEGRITY GATE] — wire before ANY tool dispatch          #
        # ------------------------------------------------------------------ #
        try:
            from core.kernel.execution_integrity import ExecutionIntegrityLayer, DecisionOutcome
            from core.kernel.task_contract_store import get_active_contract, get_active_policy, get_policy_snapshot, get_or_create_policy_snapshot

            task_contract = get_active_contract(task_id)
            policy = get_active_policy(task_id)
            snapshot = get_policy_snapshot(task_id)

            integrity = ExecutionIntegrityLayer(mission_id=task_id)
            decision = integrity.authorize(
                action=request.tool_name,
                arguments=dict(request.tool_args or {}),
                task_contract=task_contract,
                policy=policy,
                snapshot=snapshot,
            )

            if decision.outcome == DecisionOutcome.DENY:
                self._log(
                    "INTEGRITY",
                    f"[HARD-DENY] Tool '{request.tool_name}' blocked. Reason: {decision.reason}",
                    task_id,
                )
                from core.kernel.execution_integrity import ExecutionResult
                return ExecutionResult(
                    outcome=DecisionOutcome.DENY,
                    tool_executed=False,
                    reason=decision.reason,
                    action=request.tool_name
                )

            if decision.outcome == DecisionOutcome.REQUIRE_APPROVAL:
                self._log(
                    "INTEGRITY",
                    f"[APPROVAL-REQUIRED] Tool '{request.tool_name}' halted. "
                    f"InterruptID={decision.interrupt_id}. Reason: {decision.reason}",
                    task_id,
                )
                from core.kernel.execution_integrity import ExecutionResult
                return ExecutionResult(
                    outcome=DecisionOutcome.REQUIRE_APPROVAL,
                    tool_executed=False,
                    reason=decision.reason,
                    interrupt_id=decision.interrupt_id,
                    action=request.tool_name
                )

            # ALLOW — fall through to executor dispatch below
            self._log(
                "INTEGRITY",
                f"[ALLOW] Tool '{request.tool_name}' authorized by ExecutionIntegrityLayer.",
                task_id,
                stealth=True,
            )

        except ImportError as e:
            # Integrity layer unavailable — fail-closed: log and deny
            self._log("INTEGRITY", f"[FAIL-CLOSED] ExecutionIntegrityLayer import failed: {e}. Denying tool.", task_id)
            from core.kernel.execution_integrity import ExecutionResult, DecisionOutcome
            return ExecutionResult(
                outcome=DecisionOutcome.DENY,
                tool_executed=False,
                reason=f"Execution Integrity Layer unavailable — fail-closed. {e}",
                action=request.tool_name
            )
        except Exception as e:
            # Unexpected error in integrity check — fail-closed
            self._log("INTEGRITY", f"[FAIL-CLOSED] Integrity check error: {e}. Denying tool.", task_id)
            from core.kernel.execution_integrity import ExecutionResult, DecisionOutcome
            return ExecutionResult(
                outcome=DecisionOutcome.DENY,
                tool_executed=False,
                reason=f"Integrity check raised an unexpected error — fail-closed. {e}",
                action=request.tool_name
            )

        # ------------------------------------------------------------------ #
        # Authorized — proceed to executor                                     #
        # ------------------------------------------------------------------ #
        # [P0-3 / P0-4]: Evidence Gate — chặn mutation target hallucinated trước khi dispatch
        try:
            from core.kernel.evidence_gate import guard_mutation as _guard_mutation
            guard_inst = _get_evidence_guard()
            if guard_inst:
                ev_decision = _guard_mutation(
                    request.tool_name, dict(request.tool_args or {}),
                    mission_id=task_id, guard=guard_inst,
                )
                if not ev_decision.allowed:
                    self._log("INTEGRITY", f"[EVIDENCE-DENY] {ev_decision.path}: {ev_decision.reason}", task_id)
                    from core.kernel.execution_integrity import ExecutionResult, DecisionOutcome
                    return ExecutionResult(
                        outcome=DecisionOutcome.DENY,
                        tool_executed=False,
                        reason=ev_decision.reason,
                        action=request.tool_name,
                    )
        except ImportError:
            # Evidence gate module not active - handled by ExecutionIntegrityLayer
            pass
        except Exception as eg_err:
            # STRICT FAIL-CLOSED: if Evidence Gate fails for mutation tools, HARD DENY
            from core.kernel.execution_integrity import ExecutionIntegrityLayer, ExecutionResult, DecisionOutcome
            eil = ExecutionIntegrityLayer(mission_id=task_id)
            if not eil._is_observation_tool(request.tool_name):
                self._log("INTEGRITY", f"[EVIDENCE-GATE-ERROR] Evidence gate evaluation failed: {eg_err}", task_id)
                logger.error("[FAIL-CLOSED] Evidence Gate error on mutation tool '%s': %s", request.tool_name, eg_err)
                return ExecutionResult(
                    outcome=DecisionOutcome.DENY,
                    tool_executed=False,
                    reason=f"FAIL-CLOSED: Evidence Gate evaluation encountered an error ({eg_err}). Mutation blocked.",
                    action=request.tool_name,
                )

        # [WAKE-ON-DEMAND]: Tự động đánh thức container công cụ nếu đang ở trạng thái ngủ (Auto-Sleep)
        try:
            from core.kernel.container_idler import container_idler
            await container_idler.ensure_tool_container_ready(request.tool_name)
        except Exception as idler_err:
            logger.debug("[IDLER-WAKE-NOTICE] %s", idler_err)

        self._log("EXECUTOR", f"Safe execution: {request.tool_name}(...) - TraceID: {request.trace_id}", task_id)
        is_success = False
        output = "No output."
        try:
            from core.kernel.execution_integrity import ExecutionResult, DecisionOutcome
            if request.tool_name.upper().startswith("OPENHANDS"):
                from .openhands_provider import openhands_provider
                res = await openhands_provider.execute_mission(request.tool_args.get("query", ""), task_id)
                out_val = res.get("output") or res.get("message")
                return ExecutionResult(
                    outcome=DecisionOutcome.ALLOW,
                    tool_executed=True,
                    result=out_val,
                    action=request.tool_name
                )

            from core.utils.registry import registry
            payload = {
                "name": request.tool_name,
                "args": request.tool_args,
                "task_id": task_id,
                "trace_id": request.trace_id,
                "token": request.capability_token,
                "grant": decision.grant if hasattr(decision, 'grant') else None
            }

            # Retry: primary executor -> fallback executor-2
            executor_names = ["executor", "executor_2"]
            last_exception = None
            for attempt, name in enumerate(executor_names):
                try:
                    executor_url = registry.get_service_url(name)
                    self._log("EXECUTOR", f"Attempt {attempt+1}/{len(executor_names)} -> {name} ({executor_url})", task_id)
                    data = await self._post_to_executor(f"{executor_url}/call_tool", payload, request.timeout)

                    if data.get("status") == "needs_auth":
                        return ExecutionResult(
                            outcome=DecisionOutcome.REQUIRE_APPROVAL,
                            tool_executed=False,
                            reason=f"Action '{request.tool_name}' on restricted area blocked. Master credentials required.",
                            action=request.tool_name
                        )

                    # [P0-2]: Typed ToolOutcome — phân loại trung thực theo content,
                    # log SUCCESS chỉ khi có bằng chứng (I3); UNKNOWN != SUCCESS (I2).
                    from core.kernel.tool_outcome import from_executor_payload
                    outcome = from_executor_payload(data, request.tool_name)
                    self._log("EXECUTOR", outcome.to_log_line(), task_id)
                    if not outcome.is_success:
                        try:
                            from core.kernel.recovery_state_machine import build_recovery_plan
                            plan = build_recovery_plan(
                                request.tool_name, outcome.reason, request.tool_args)
                            self._log("EXECUTOR", f"[RECOVERY] {plan.to_log_line()}", task_id)
                        except Exception:
                            pass
                    is_success = outcome.is_success
                    output = data.get("output", "No output.")
                    return ExecutionResult(
                        outcome=DecisionOutcome.ALLOW,
                        tool_executed=is_success,
                        result=output,
                        action=request.tool_name
                    )

                except Exception as e:
                    last_exception = e
                    self._log("EXECUTOR", f"Executor {name} failed: {e}. {'Falling back...' if attempt < len(executor_names)-1 else 'No more executors.'}", task_id)
                    if attempt < len(executor_names) - 1:
                        await asyncio.sleep(1.0)

            output = f"Error calling executor: {last_exception}"
            is_success = False
            return ExecutionResult(
                outcome=DecisionOutcome.ALLOW,
                tool_executed=False,
                result=output,
                action=request.tool_name
            )

        except Exception as e:
            output = f"Error calling executor: {e}"
            is_success = False
            return ExecutionResult(
                outcome=DecisionOutcome.ALLOW,
                tool_executed=False,
                result=output,
                action=request.tool_name
            )
        finally:
            try:
                from redis_client import get_redis
                r_conn = get_redis()
                if r_conn:
                    event_payload = json.dumps({
                        "intent": request.tool_name,
                        "is_success": is_success
                    }, ensure_ascii=False)
                    r_conn.publish("zenith:cognitive_events", event_payload)
            except Exception as publish_err:
                print(f"[EXECUTOR-GATEWAY-WARN] Failed to publish cognitive event: {publish_err}")

    async def request_sovereign_auth(self, action: str, params: dict, task_id: str):
        payload = {"action": action}
        payload.update(params)
        try:
            from core.utils.registry import registry
            executor_url = registry.get_service_url('executor')
            await self.http_client.post(f"{executor_url}/call_tool", json={
                "name": "request_sovereign_auth",
                "args": payload,
                "task_id": task_id
            })
        except Exception: pass

