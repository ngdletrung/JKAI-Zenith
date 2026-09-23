import asyncio
import json
import logging
import time
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


class _HealthCache:
    """
    [N1 / G2.2] Circuit Breaker Health Cache for executor endpoints.
    Multi-worker safe via Redis-backed cache with in-process fast fallback.
    TTL = 30s. Probe timeout = 500ms.
    """
    PROBE_TIMEOUT: float = 0.5     # 500ms max per health probe
    CACHE_TTL: float = 30.0        # seconds before re-probing
    REDIS_KEY_PREFIX: str = "executor:health:"

    def __init__(self, redis_conn=None):
        self._cache: dict[str, tuple[bool, float]] = {}  # local fallback: name -> (is_healthy, last_check_ts)
        self._redis = redis_conn

    def _get_redis(self):
        if self._redis is not None:
            return self._redis
        try:
            from core.redis_client import get_redis_client
            return get_redis_client()
        except Exception:
            return None

    def is_known_healthy(self, name: str) -> bool | None:
        """Return True/False if within TTL, None if expired or unknown."""
        # 1. Fast local memory check
        entry = self._cache.get(name)
        if entry is not None:
            healthy, ts = entry
            if time.monotonic() - ts <= self.CACHE_TTL:
                return healthy

        # 2. Multi-worker shared Redis check (G2.2)
        r = self._get_redis()
        if r is not None:
            try:
                val = r.get(f"{self.REDIS_KEY_PREFIX}{name}")
                if val is not None:
                    # Redis stores '1' (healthy) or '0' (unhealthy)
                    is_h = val in (b"1", "1", 1, True)
                    # Update local fast cache to match
                    self._cache[name] = (is_h, time.monotonic())
                    return is_h
            except Exception:
                pass

        return None

    def update(self, name: str, healthy: bool) -> None:
        self._cache[name] = (healthy, time.monotonic())
        # Sync to Redis for multi-worker processes
        r = self._get_redis()
        if r is not None:
            try:
                val = "1" if healthy else "0"
                r.setex(f"{self.REDIS_KEY_PREFIX}{name}", int(self.CACHE_TTL), val)
            except Exception:
                pass

    def mark_unhealthy(self, name: str) -> None:
        self.update(name, False)


_health_cache = _HealthCache()



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

    async def _probe_executor_health(self, name: str, executor_url: str) -> bool:
        """
        [N1-v2] Fast health probe: GET /health with 500ms hard timeout.
        Healthy = status_code 2xx AND body field 'status'/'healthy' matches UP/OK/TRUE (JSON-first).
        Fallback to quoted substring only when body is not valid JSON.
        Fail-safe: any exception or ambiguous response -> False.
        """
        cached = _health_cache.is_known_healthy(name)
        if cached is not None:
            return cached
        try:
            resp = await asyncio.wait_for(
                self.http_client.get(f"{executor_url}/health"),
                timeout=_HealthCache.PROBE_TIMEOUT,
            )
            status = getattr(resp, "status_code", None)
            if status is None or not (200 <= status < 300):
                _health_cache.mark_unhealthy(name)
                return False
            # JSON-first: parse body and check known health fields
            try:
                body = resp.json() if hasattr(resp, "json") else None
                if isinstance(body, dict):
                    # Check standard fields: status, healthy, health
                    for field in ("status", "health", "state"):
                        val = body.get(field, "")
                        if isinstance(val, str) and val.strip().lower() in ("up", "ok", "healthy", "running"):
                            _health_cache.update(name, True)
                            return True
                    # Check boolean field 'healthy': true
                    if body.get("healthy") is True:
                        _health_cache.update(name, True)
                        return True
                    # No matching field → unhealthy
                    _health_cache.mark_unhealthy(name)
                    return False
            except Exception:
                body = None
            # Fallback (non-JSON body): quoted substring match only to avoid false positives
            try:
                raw = str(getattr(resp, "text", "") or "").lower()
                _QUOTED_SIGNALS = ('"up"', '"ok"', '"healthy"', '"running"', 'true')
                is_healthy = any(sig in raw for sig in _QUOTED_SIGNALS)
            except Exception:
                is_healthy = False
            _health_cache.update(name, is_healthy)
            return is_healthy
        except Exception as probe_err:
            logger.debug("[HEALTH-PROBE] %s unreachable: %s", name, probe_err)
            _health_cache.mark_unhealthy(name)
            return False



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

            # 🚀 [P0-2 LOCAL-FIRST DUAL-PATH TOOL EXECUTION]
            # Primitive file & command operations run directly via SYSTEM_CORE_EXECUTOR
            # Eliminates HTTP network hops, container DNS failures, and JSON empty body errors.
            norm_name = request.tool_name.lower().strip()
            LOCAL_PRIMITIVE_MAP = {
                "write_to_file": "write_to_file",
                "writefile": "write_to_file",
                "write_file": "write_to_file",
                "create_file": "write_to_file",
                "view_file": "view_file",
                "viewfile": "view_file",
                "read_file": "view_file",
                "replace_file_content": "replace_file_content",
                "edit_file": "replace_file_content",
                "replace_content": "replace_file_content",
                "delete_file": "delete_file",
                "remove_file": "delete_file",
                "list_dir": "list_dir",
                "listdir": "list_dir",
                "ls": "list_dir",
                "run_command": "run_command",
                "execute_command": "run_command",
                "cmd": "run_command",
                "run_cmd": "run_command",
                "execute_code": "run_command",
            }

            if norm_name in LOCAL_PRIMITIVE_MAP:
                local_fn_name = LOCAL_PRIMITIVE_MAP[norm_name]
                try:
                    import intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR.logic as core_exec
                    fn = getattr(core_exec, local_fn_name, None)
                    if fn and callable(fn):
                        self._log("EXECUTOR", f"⚡ [LOCAL-DIRECT-EXEC] Executing '{request.tool_name}' via sovereign local runtime.", task_id)
                        kwargs = dict(request.tool_args or {})
                        # Normalize key names
                        if local_fn_name == "write_to_file":
                            if "target_path" not in kwargs and "file_path" in kwargs:
                                kwargs["target_path"] = kwargs["file_path"]
                            if "target_content" not in kwargs and "content" in kwargs:
                                kwargs["target_content"] = kwargs["content"]
                        if local_fn_name == "run_command":
                            if "command" not in kwargs and "code" in kwargs:
                                kwargs["command"] = f"python -c {kwargs['code']!r}"
                        
                        local_res = await fn(task_id=task_id, **kwargs)
                        is_ok = local_res.get("status") == "success"
                        out_msg = local_res.get("msg") or local_res.get("content") or local_res.get("stdout") or json.dumps(local_res, ensure_ascii=False)
                        if not is_ok and local_res.get("stderr"):
                            out_msg = f"{out_msg}\nStderr: {local_res.get('stderr')}"

                        self._log("EXECUTOR", f"[{request.tool_name}] {'✅ Local execution succeeded' if is_ok else '⚠️ Local execution returned error: ' + str(local_res.get('msg', ''))}", task_id)
                        return ExecutionResult(
                            outcome=DecisionOutcome.ALLOW,
                            tool_executed=is_ok,
                            result=out_msg,
                            action=request.tool_name
                        )
                except Exception as local_err:
                    self._log("WARN", f"[LOCAL-DIRECT-FAIL] Local execution of '{request.tool_name}' failed: {local_err}. Falling back to HTTP executor.", task_id)

            from core.utils.registry import registry
            payload = {
                "name": request.tool_name,
                "args": request.tool_args,
                "task_id": task_id,
                "trace_id": request.trace_id,
                "token": request.capability_token,
                "grant": decision.grant if hasattr(decision, 'grant') else None
            }

            # [N1] Probe-before-dispatch: health check (500ms) before committing request budget.
            # Unhealthy -> immediate failover to executor_2, no 1s sleep penalty.
            # Both dead  -> FAIL_FAST with clear error < 2s total.
            executor_names = ["executor", "executor_2"]
            last_exception = None
            for attempt, name in enumerate(executor_names):
                try:
                    executor_url = registry.get_service_url(name)
                    healthy = await self._probe_executor_health(name, executor_url)
                    if not healthy:
                        msg = f"[HEALTH-GATE] {name} ({executor_url}) is DOWN — skipping."
                        self._log("EXECUTOR", msg, task_id)
                        last_exception = RuntimeError(msg)
                        # Immediately failover, no sleep needed (probe already gave 500ms window)
                        continue

                    self._log("EXECUTOR", f"[HEALTH-OK] {name} is UP — dispatching {request.tool_name}", task_id, stealth=True)
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
                    # Mark this executor as still healthy since response was received
                    _health_cache.update(name, True)
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
                    _health_cache.mark_unhealthy(name)
                    self._log("EXECUTOR", f"Executor {name} failed mid-call: {e}. {'Failing over...' if attempt < len(executor_names)-1 else 'No more executors — FAIL_FAST.'}", task_id)

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

