import asyncio
import json
import logging
import time
import httpx
from dataclasses import dataclass
from typing import Any
from core.utils.engine import engine

logger = logging.getLogger("JKAI.ExecutorGateway")

# Top-level ExecutionResult and DecisionOutcome with fail-safe fallback
try:
    from core.kernel.execution_integrity import ExecutionResult, DecisionOutcome
except ImportError:
    from enum import Enum
    class DecisionOutcome(str, Enum):
        ALLOW = "ALLOW"
        DENY = "DENY"
        REQUIRE_APPROVAL = "REQUIRE_APPROVAL"

    class ExecutionResult:
        def __init__(self, outcome, tool_executed, result=None, reason="", interrupt_id=None, action=""):
            self.outcome = outcome
            self.tool_executed = tool_executed
            self.result = result
            self.reason = reason
            self.interrupt_id = interrupt_id
            self.action = action

        def __str__(self):
            if self.outcome == DecisionOutcome.ALLOW:
                return str(self.result) if self.result is not None else ""
            if self.outcome == DecisionOutcome.REQUIRE_APPROVAL:
                return f"[APPROVAL-REQUIRED]: Tool '{self.action}' requires approval. InterruptID={self.interrupt_id}. Reason: {self.reason}"
            return f"[EXECUTION-DENIED]: {self.reason}"

_EVIDENCE_GUARD = None


def _get_evidence_guard():
    global _EVIDENCE_GUARD
    if _EVIDENCE_GUARD is None:
        try:
            from core.kernel.evidence_gate import EvidenceGuard
            _EVIDENCE_GUARD = EvidenceGuard()
        except ImportError as e:
            logger.debug("[EVIDENCE-GUARD] EvidenceGuard not available: %s", e)
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
            import os
            from core.config import IS_DOCKER
            r_host = os.getenv("REDIS_HOST", "redis-ai")
            # If on Windows host and host is default docker name "redis-ai", skip blocking connection
            if not IS_DOCKER and r_host == "redis-ai":
                return None
            from core.redis_client import get_redis_client
            return get_redis_client()
        except Exception as e:
            logger.debug("[HEALTH-CACHE] Redis client acquisition skipped: %s", e)
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
            except Exception as e:
                logger.debug("[HEALTH-CACHE] Redis read failed: %s", e)

        return None

    def update(self, name: str, healthy: bool) -> None:
        self._cache[name] = (healthy, time.monotonic())
        # Sync to Redis for multi-worker processes
        r = self._get_redis()
        if r is not None:
            try:
                val = "1" if healthy else "0"
                r.setex(f"{self.REDIS_KEY_PREFIX}{name}", int(self.CACHE_TTL), val)
            except Exception as e:
                logger.debug("[HEALTH-CACHE] Redis write failed: %s", e)

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

async def probe_executor_health(name: str, executor_url: str, http_client: Any = None) -> bool:
    """
    [N1-v2 / P0-1] Unified health probe: GET /health with 500ms hard timeout.
    Healthy = status_code 2xx AND body field 'status'/'healthy' matches UP/OK/TRUE (JSON-first).
    Fallback to quoted substring only when body is not valid JSON.
    Fail-safe: any exception or ambiguous response -> False.
    """
    cached = _health_cache.is_known_healthy(name)
    if cached is not None:
        return cached
    close_client = False
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=_HealthCache.PROBE_TIMEOUT + 0.5)
        close_client = True
    try:
        resp = await asyncio.wait_for(
            http_client.get(f"{executor_url}/health"),
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
                # Check standard fields: status, health, state
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
    finally:
        if close_client:
            await http_client.aclose()


async def preflight_check_executors(http_client: Any = None) -> tuple[bool, str, list[str]]:
    """
    [P0-1] Preflight check before mission start (Turn 60 Consensus).
    Reuses existing _health_cache and probe_executor_health.
    Fails fast in < 3s if both executor and executor_2 are unreachable.
    Returns: (is_available: bool, reason: str, available_urls: list[str])
    """
    from core.utils.registry import registry
    close_client = False
    if http_client is None:
        http_client = httpx.AsyncClient(timeout=_HealthCache.PROBE_TIMEOUT + 0.5)
        close_client = True
    try:
        available = []
        errors = []
        for name in ("executor", "executor_2"):
            try:
                url = registry.get_service_url(name)
                is_alive = await probe_executor_health(name, url, http_client)
                if is_alive:
                    available.append(url)
                else:
                    errors.append(f"{name} ({url})")
            except Exception as e:
                errors.append(f"{name}: {e}")
        if not available:
            return False, f"All executors DOWN. Details: {'; '.join(errors)}", []
        return True, f"Available executors: {', '.join(available)}", available
    finally:
        if close_client:
            await http_client.aclose()


def _seal_receipt_fail_closed(integrity, tool_name, tool_args, output, decision, task_id):
    """
    [SROS v2 Fail-Closed Receipt Enforcement]
    Mọi hành vi thực thi thành công bắt buộc phải niêm phong được ExecutionReceipt.
    Nếu seal thất bại -> FAIL-CLOSED: coi như execution thất bại hoàn toàn.
    """
    try:
        rcpt = integrity.seal_execution_receipt(
            action=tool_name,
            arguments=dict(tool_args or {}),
            output=output,
            lds_verdict=decision.lds_verdict,
            task_id=task_id
        )
        if not rcpt:
            return False, None, "FAIL-CLOSED: Execution completed on substrate but receipt sealing produced empty receipt."
        return True, rcpt.to_dict(), ""
    except Exception as e:
        return False, None, f"FAIL-CLOSED: Execution completed on substrate but cryptographic receipt sealing failed: {e}"


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
        return await probe_executor_health(name, executor_url, self.http_client)








    async def execute_tool(self, request: ExecutionRequest, task_id: str) -> ExecutionResult:
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
            from core.kernel.execution_integrity import ExecutionIntegrityLayer
            from core.kernel.task_contract_store import (
                get_active_contract,
                get_active_policy,
                get_policy_snapshot,
                get_or_create_default_contract,
                get_or_create_policy_snapshot,
            )

            task_contract = get_active_contract(task_id) or get_or_create_default_contract(task_id)
            policy = get_active_policy(task_id)
            snapshot = get_policy_snapshot(task_id) or get_or_create_policy_snapshot(task_id)

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
            # Bug 1 Fix: Fail-closed without re-importing potentially failing module
            self._log("INTEGRITY", f"[FAIL-CLOSED] ExecutionIntegrityLayer import failed: {e}. Denying tool.", task_id)
            return ExecutionResult(
                outcome=DecisionOutcome.DENY,
                tool_executed=False,
                reason=f"Execution Integrity Layer unavailable — fail-closed. {e}",
                action=request.tool_name
            )
        except Exception as e:
            # Unexpected error in integrity check — fail-closed
            self._log("INTEGRITY", f"[FAIL-CLOSED] Integrity check error: {e}. Denying tool.", task_id)
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
            # Bug 3 Fix: use public is_observation_tool API
            from core.kernel.execution_integrity import ExecutionIntegrityLayer
            eil = ExecutionIntegrityLayer(mission_id=task_id)
            if not eil.is_observation_tool(request.tool_name):
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
            if request.tool_name.upper().startswith("OPENHANDS"):
                from .openhands_provider import openhands_provider
                res = await openhands_provider.execute_mission(request.tool_args.get("query", ""), task_id)
                out_val = res.get("output") or res.get("message")
                rcpt_ok, rcpt_dict, rcpt_err = _seal_receipt_fail_closed(
                    integrity, request.tool_name, request.tool_args, out_val, decision, task_id
                )
                if not rcpt_ok:
                    return ExecutionResult(
                        outcome=DecisionOutcome.DENY,
                        tool_executed=False,
                        result=rcpt_err,
                        reason=rcpt_err,
                        action=request.tool_name,
                        risk_tier=decision.risk_tier,
                        lds_verdict=decision.lds_verdict
                    )
                return ExecutionResult(
                    outcome=DecisionOutcome.ALLOW,
                    tool_executed=True,
                    result=out_val,
                    action=request.tool_name,
                    receipt=rcpt_dict,
                    risk_tier=decision.risk_tier,
                    lds_verdict=decision.lds_verdict
                )

            # 🚀 [P0-2 LOCAL-FIRST DUAL-PATH TOOL EXECUTION]
            # Primitive file & command operations run directly via SYSTEM_CORE_EXECUTOR
            # Eliminates HTTP network hops, container DNS failures, and JSON empty body errors.
            norm_name = request.tool_name.lower().strip()
            # FIX-41310c: canonicalize planner aliases BEFORE local dispatch.
            try:
                from core.kernel.tool_contracts import ToolContractRegistry as _TCR
                _canon = _TCR.get_canonical_name(request.tool_name)
                if _canon:
                    norm_name = _canon
            except ImportError:
                pass
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
                "verify_file": "verify_file",
                "check_file": "verify_file",
                "list_dir": "list_dir",
                "listdir": "list_dir",
                "ls": "list_dir",
                "run_command": "run_command",
                "execute_command": "run_command",
                "cmd": "run_command",
                "run_cmd": "run_command",
                "execute_code": "run_command",
                "grep_search": "grep_search",
                "grep": "grep_search",
                "search_code": "grep_search",
                "search_web": "search_web",
                "web_search": "search_web",
                "search_web_global": "search_web",
                "omni_search_engine": "search_web",
                "code_execution": "run_command",
                "python_execute": "run_command",
                "read_url_content": "read_url_content",
                "query_repo_map": "query_repo_map",
                "repo_map": "query_repo_map",
                "view_file_outline": "view_file_outline",
                "read_stream_window": "read_stream_window",
                "read_stream": "read_stream_window",
                "search_in_stream": "search_in_stream",
                "search_stream": "search_in_stream",
                "browser_action": "browser_action",
                "browser_control": "browser_action",
                "browse": "browser_action",
                "web_browse": "browser_action",
                "crawl": "browser_action",
                "web_read": "web_read",
                "fast_read": "web_read",
                "read_doc": "web_read",
                "browser_observe": "browser_observe",
                "observe_dom": "browser_observe",
                "observe": "browser_observe",
                "browser_act": "browser_act",
                "act_element": "browser_act",
                "act": "browser_act",
                "browser_extract": "browser_extract",
                "extract_data": "browser_extract",
                "extract": "browser_extract",
            }

            if norm_name in LOCAL_PRIMITIVE_MAP:
                local_fn_name = LOCAL_PRIMITIVE_MAP[norm_name]
                try:
                    kwargs = dict(request.tool_args or {})
                    kwargs.pop("task_id", None)
                    kwargs.pop("trace_id", None)

                    if local_fn_name in ("browser_action", "web_read", "browser_observe", "browser_act", "browser_extract"):
                        try:
                            from tools.definitions import browser_interact
                        except ImportError:
                            try:
                                from services.tools.definitions import browser_interact
                            except ImportError:
                                import browser_interact
                        self._log("EXECUTOR", f"🌐 [LOCAL-BROWSER-EXEC] Executing '{request.tool_name}' ({local_fn_name}) via Sovereign Browser Subsystem.", task_id)
                        b_act = kwargs.get("action", "")
                        b_obj = kwargs.get("objective") or kwargs.get("task") or kwargs.get("goal") or ""
                        if local_fn_name == "web_read":
                            b_url = kwargs.get("url") or kwargs.get("target_url") or ""
                            b_filter = kwargs.get("filter") or kwargs.get("filter_keyword")
                            b_outline = kwargs.get("outline", False)
                            b_prefer_llms = kwargs.get("prefer_llms_txt", True)
                            local_res = await asyncio.to_thread(
                                browser_interact.web_read,
                                url=b_url,
                                filter_keyword=b_filter,
                                extract_outline=b_outline,
                                prefer_llms_txt=b_prefer_llms,
                            )
                        elif local_fn_name == "browser_observe":
                            b_url = kwargs.get("url") or kwargs.get("target_url")
                            b_goal = kwargs.get("goal") or kwargs.get("objective")
                            local_res = await asyncio.to_thread(
                                browser_interact.browser_observe,
                                url=b_url,
                                goal=b_goal,
                            )
                        elif local_fn_name == "browser_act":
                            b_ref = kwargs.get("element_ref") or kwargs.get("ref")
                            b_act = kwargs.get("action", "click")
                            b_val = kwargs.get("value")
                            b_confirm = kwargs.get("confirm", False)
                            b_refresh = kwargs.get("force_refresh", False)
                            local_res = await asyncio.to_thread(
                                browser_interact.browser_act,
                                element_ref=b_ref,
                                action=b_act,
                                value=b_val,
                                confirm=b_confirm,
                                force_refresh=b_refresh,
                            )
                        elif local_fn_name == "browser_extract":
                            b_goal = kwargs.get("goal") or kwargs.get("objective") or "Extract structured data"
                            b_schema = kwargs.get("schema_definition") or kwargs.get("schema")
                            local_res = await asyncio.to_thread(
                                browser_interact.browser_extract,
                                goal=b_goal,
                                schema_definition=b_schema,
                            )
                        else:  # browser_action / browser_control
                            b_url = kwargs.get("url") or kwargs.get("target_url") or "https://www.google.com"
                            b_act = kwargs.get("action")
                            b_obj = kwargs.get("objective") or kwargs.get("task") or (f"Action: {b_act}" if b_act else f"Đọc và tổng hợp nội dung từ {b_url}")
                            
                            # Fast-path: Nếu là load_page / read / xem trang, ưu tiên dùng FastWebReader (<100ms, 0MB VRAM)
                            if not any(kw in f"{b_act or ''} {b_obj}".lower() for kw in ("screenshot", "chụp", "visual", "ảnh")) and (b_act in ("load_page", "read", "view", "open") or any(kw in str(b_obj).lower() for kw in ("xem trang", "đọc trang", "tổng hợp"))):
                                fast_res = await asyncio.to_thread(browser_interact.web_read, url=b_url)
                                if fast_res.get("status") == "success" and fast_res.get("content"):
                                    local_res = fast_res
                                else:
                                    local_res = await asyncio.to_thread(browser_interact.browser_action, url=b_url, objective=b_obj)
                            else:
                                local_res = await asyncio.to_thread(browser_interact.browser_action, url=b_url, objective=b_obj)

                        needs_evidence = any(
                            token in f"{b_act or ''} {b_obj}".lower()
                            for token in ("screenshot", "chụp", "visual", "ảnh")
                        )
                        evidence_ok = local_res.get("evidence_complete") is True
                        is_ok = (
                            local_res.get("status") in ("success", "captured")
                            or local_res.get("success") is True
                            or bool(local_res.get("content"))
                            or bool(local_res.get("snapshot"))
                        ) and (not needs_evidence or evidence_ok)
                        if needs_evidence and not evidence_ok:
                            local_res["status"] = "inconclusive"
                            local_res["message"] = "Browser evidence incomplete: screenshot, DOM, hash, or capture time missing."
                        out_msg = (
                            local_res.get("content")
                            or local_res.get("snapshot")
                            or local_res.get("analysis")
                            or local_res.get("markdown")
                            or local_res.get("message")
                            or json.dumps(local_res, ensure_ascii=False)
                        )
                        self._log("EXECUTOR", f"[{request.tool_name}] {'✅ Browser interaction succeeded' if is_ok else '⚠️ Browser status: ' + str(local_res.get('message', ''))}", task_id)
                        if is_ok:
                            rcpt_ok, rcpt_dict, rcpt_err = _seal_receipt_fail_closed(
                                integrity, request.tool_name, request.tool_args, out_msg, decision, task_id
                            )
                            if not rcpt_ok:
                                return ExecutionResult(
                                    outcome=DecisionOutcome.DENY,
                                    tool_executed=False,
                                    result=rcpt_err,
                                    reason=rcpt_err,
                                    action=request.tool_name,
                                    risk_tier=decision.risk_tier,
                                    lds_verdict=decision.lds_verdict
                                )
                        else:
                            rcpt_dict = None
                        return ExecutionResult(
                            outcome=DecisionOutcome.ALLOW,
                            tool_executed=is_ok,
                            result=out_msg,
                            action=request.tool_name,
                            receipt=rcpt_dict,
                            risk_tier=decision.risk_tier,
                            lds_verdict=decision.lds_verdict
                        )

                    import intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR.logic as core_exec
                    fn = getattr(core_exec, local_fn_name, None)
                    if fn and callable(fn):
                        self._log("EXECUTOR", f"⚡ [LOCAL-DIRECT-EXEC] Executing '{request.tool_name}' via sovereign local runtime.", task_id)

                        # Normalize key names for all local primitives
                        if local_fn_name == "list_dir":
                            if "path" not in kwargs:
                                kwargs["path"] = kwargs.get("directory_path") or kwargs.get("DirectoryPath") or kwargs.get("folder") or kwargs.get("dir") or "."
                        elif local_fn_name == "view_file":
                            if "path" not in kwargs:
                                kwargs["path"] = kwargs.get("file_path") or kwargs.get("AbsolutePath") or kwargs.get("TargetFile") or kwargs.get("file") or ""
                        elif local_fn_name == "write_to_file":
                            if "target_path" not in kwargs:
                                kwargs["target_path"] = kwargs.get("file_path") or kwargs.get("path") or kwargs.get("TargetFile") or ""
                            if "target_content" not in kwargs:
                                kwargs["target_content"] = kwargs.get("content") or kwargs.get("CodeContent") or ""
                        elif local_fn_name == "replace_file_content":
                            if "path" not in kwargs:
                                kwargs["path"] = kwargs.get("file_path") or kwargs.get("TargetFile") or kwargs.get("target_path") or ""
                            if "target" not in kwargs:
                                kwargs["target"] = kwargs.get("TargetContent") or kwargs.get("targetContent") or kwargs.get("old_str") or kwargs.get("old_code") or kwargs.get("find") or ""
                            if "replacement" not in kwargs:
                                kwargs["replacement"] = kwargs.get("ReplacementContent") or kwargs.get("replacementContent") or kwargs.get("new_str") or kwargs.get("new_code") or kwargs.get("replace") or ""
                        elif local_fn_name == "delete_file":
                            if "path" not in kwargs:
                                kwargs["path"] = kwargs.get("file_path") or kwargs.get("TargetFile") or kwargs.get("path") or ""
                            kwargs.setdefault("confirm", True)
                        elif local_fn_name == "verify_file":
                            if "path" not in kwargs:
                                kwargs["path"] = kwargs.get("file_path") or kwargs.get("TargetFile") or kwargs.get("path") or ""
                        elif local_fn_name == "grep_search":
                            if "query" not in kwargs:
                                kwargs["query"] = kwargs.get("Query") or kwargs.get("pattern") or kwargs.get("keyword") or kwargs.get("q") or ""
                            if "path" not in kwargs:
                                kwargs["path"] = kwargs.get("SearchPath") or kwargs.get("directory") or kwargs.get("dir") or "."
                        elif local_fn_name == "run_command":
                            if "command" not in kwargs:
                                kwargs["command"] = kwargs.get("CommandLine") or kwargs.get("cmd") or ""
                            if not kwargs["command"] and "code" in kwargs:
                                kwargs["command"] = f"python -c {kwargs['code']!r}"
                            if "cwd" not in kwargs and "Cwd" in kwargs:
                                kwargs["cwd"] = kwargs["Cwd"]
                        elif local_fn_name == "search_web":
                            # FIX-41310c: accept Query/pattern/q/topic fallbacks; never dispatch empty query.
                            if not kwargs.get("query"):
                                kwargs["query"] = (
                                    kwargs.get("Query") or kwargs.get("pattern") or kwargs.get("q")
                                    or kwargs.get("keyword") or kwargs.get("topic") or kwargs.get("input") or ""
                                )
                        
                        local_res = await fn(task_id=task_id, **kwargs)
                        is_ok = local_res.get("status") == "success"
                        out_msg = local_res.get("msg") or local_res.get("content") or local_res.get("stdout") or json.dumps(local_res, ensure_ascii=False)
                        if not is_ok and local_res.get("stderr"):
                            out_msg = f"{out_msg}\nStderr: {local_res.get('stderr')}"

                        err_detail = local_res.get('msg') or local_res.get('stderr') or (str(local_res.get('stdout', ''))[:300] if not is_ok else '')
                        self._log("EXECUTOR", f"[{request.tool_name}] {'✅ Local execution succeeded' if is_ok else '⚠️ Local execution returned error: ' + str(err_detail)}", task_id)
                        if is_ok:
                            rcpt_ok, rcpt_dict, rcpt_err = _seal_receipt_fail_closed(
                                integrity, request.tool_name, request.tool_args, out_msg, decision, task_id
                            )
                            if not rcpt_ok:
                                return ExecutionResult(
                                    outcome=DecisionOutcome.DENY,
                                    tool_executed=False,
                                    result=rcpt_err,
                                    reason=rcpt_err,
                                    action=request.tool_name,
                                    risk_tier=decision.risk_tier,
                                    lds_verdict=decision.lds_verdict
                                )
                        else:
                            rcpt_dict = None
                        return ExecutionResult(
                            outcome=DecisionOutcome.ALLOW,
                            tool_executed=is_ok,
                            result=out_msg,
                            action=request.tool_name,
                            receipt=rcpt_dict,
                            risk_tier=decision.risk_tier,
                            lds_verdict=decision.lds_verdict
                        )
                except Exception as local_err:
                    self._log("WARN", f"[LOCAL-DIRECT-FAIL] Local execution of '{request.tool_name}' failed: {local_err}. Falling back to HTTP executor.", task_id)
                    try:
                        import traceback
                        from core.recovery.error_classifier import ErrorClassifier
                        from core.utils.failure_memory import failure_memory, FailureStage
                        classifier = ErrorClassifier()
                        tb_str = traceback.format_exc()
                        v = classifier.classify(str(local_err), tb_str)
                        coro = failure_memory.record_failure(
                            task_id=task_id,
                            goal=f"Execute {request.tool_name}",
                            task_type="local_primitive",
                            failure_stage=FailureStage.TOOL_EXECUTION,
                            error_detail=f"{v.subclass.value}: {local_err}",
                            failed_tools=[request.tool_name],
                            attempted_fix=v.recommended_action,
                            fix_worked=False
                        )
                        asyncio.create_task(coro)
                    except Exception:
                        pass

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
                        except Exception as rec_err:
                            logger.debug("[RECOVERY-NOTICE] Recovery plan generation skipped: %s", rec_err)
                    # Mark this executor as still healthy since response was received
                    _health_cache.update(name, True)
                    is_success = outcome.is_success
                    if is_success:
                        output = data.get("output", "No output.")
                    else:
                        # [HOTFIX-1410] Lan truyen ly do that bai that thay vi "No output."
                        # de critic/replan thay NGUYEN NHAN (tool khong ton tai? timeout?
                        # loi logic?) thay vi doan mo, tranh replan mu quang.
                        output = (
                            data.get("msg") or data.get("message") or data.get("detail")
                            or data.get("error") or data.get("output") or "No output."
                        )
                    if is_success:
                        rcpt_ok, rcpt_dict, rcpt_err = _seal_receipt_fail_closed(
                            integrity, request.tool_name, request.tool_args, output, decision, task_id
                        )
                        if not rcpt_ok:
                            return ExecutionResult(
                                outcome=DecisionOutcome.DENY,
                                tool_executed=False,
                                result=rcpt_err,
                                reason=rcpt_err,
                                action=request.tool_name,
                                risk_tier=decision.risk_tier,
                                lds_verdict=decision.lds_verdict
                            )
                    else:
                        rcpt_dict = None
                    return ExecutionResult(
                        outcome=DecisionOutcome.ALLOW,
                        tool_executed=is_success,
                        result=output,
                        action=request.tool_name,
                        receipt=rcpt_dict,
                        risk_tier=decision.risk_tier,
                        lds_verdict=decision.lds_verdict
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
                import os
                from core.config import IS_DOCKER
                r_host = os.getenv("REDIS_HOST", "redis-ai")
                if IS_DOCKER or r_host != "redis-ai":
                    from redis_client import get_redis
                    r_conn = get_redis()
                    if r_conn:
                        event_payload = json.dumps({
                            "intent": request.tool_name,
                            "is_success": is_success
                        }, ensure_ascii=False)
                        r_conn.publish("zenith:cognitive_events", event_payload)
            except Exception as publish_err:
                logger.debug("[EXECUTOR-GATEWAY] Cognitive event publish skipped: %s", publish_err)

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
        except Exception as auth_err:
            logger.debug("[SOVEREIGN-AUTH-ERR] %s", auth_err)

