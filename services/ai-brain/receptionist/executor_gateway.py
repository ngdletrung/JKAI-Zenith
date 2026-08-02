import asyncio
import json
from dataclasses import dataclass
from core.utils.engine import engine

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
            enhanced_msg = f"[ZENITH]: {msg}" if tag == "ZENITH" else msg
            engine.publish_mission_log(tag, enhanced_msg, task_id, stealth=stealth)
        except Exception: pass

    async def _post_to_executor(self, url: str, payload: dict, timeout: int) -> dict:
        """Helper: POST to executor and return JSON response."""
        resp = await self.http_client.post(url, json=payload, timeout=timeout)
        return resp.json()

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
            from core.kernel.task_contract_store import get_active_contract, get_active_policy

            task_contract = get_active_contract(task_id)
            policy = get_active_policy(task_id)

            integrity = ExecutionIntegrityLayer(mission_id=task_id)
            decision = integrity.authorize(
                action=request.tool_name,
                arguments=dict(request.tool_args or {}),
                task_contract=task_contract,
                policy=policy,
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
                "token": request.capability_token
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

                    if data.get("status") == "error":
                        is_success = False
                        output = data.get("msg") or data.get("error") or data.get("output") or "Unknown executor error."
                    else:
                        output = data.get("output", "No output.")
                        if isinstance(output, dict) and output.get("status") == "error":
                            is_success = False
                            output = output.get("msg") or output.get("error") or str(output)
                        elif isinstance(output, str) and ("Thất bại sau" in output or "error" in output.lower()):
                            is_success = False
                        else:
                            is_success = True

                    self._log("EXECUTOR", f"Executor {name} success ({len(str(output))} chars)", task_id)
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

