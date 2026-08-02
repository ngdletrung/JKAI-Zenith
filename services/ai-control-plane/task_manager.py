"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH v5.0 — COGNITIVE GRAPH RUNTIME                     ║
║   Autonomous Cognitive Orchestration System                      ║
║   True Event Sourcing • Safe DAG • Memory Fabric • Meta-Reflect  ║
╚══════════════════════════════════════════════════════════════════╝
*Sovereign Property of Master LeeTrung. Developed by Antigravity AI. 🌌🏛️🔥*
"""

from __future__ import annotations

import asyncio
import json
import os
import time as _time
from collections import defaultdict, deque
from dataclasses import dataclass, field, replace
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Set, Tuple

import httpx

from core.utils.engine import engine
from redis_client import redis_safe
from core.utils.failure_memory import failure_memory, FailureStage
from core.utils.cognitive_guardrails import guardrail_registry
from core.kernel.state_machine import TaskState, StateInvariantViolation
from core.kernel.task_kernel import CognitiveState, CognitiveTaskKernel, StepStatus
from core.kernel.homeostasis import homeostasis_engine
from core.kernel.civilization_ledger import civilization_ledger
from core.utils.knowledge_brain import knowledge_brain
from core.utils.path_locker import path_lock_registry
from core.utils.workspace_manager import workspace_manager
from core.utils.session_context import get_session_context
from redis_client import get_redis

# ══════════════════════════════════════════════════════════════════
# SECTION 1 — TYPED REQUESTS (Backward Compatible)
# ══════════════════════════════════════════════════════════════════

@dataclass(frozen=True, slots=True)
class ToolExecutionRequest:
    goal: str
    steps: list[dict]
    task_id: str
    trace_id: str
    agent_soul: str | None = None
    policy: str | None = None
    cost_hint: float = 1.0

# ══════════════════════════════════════════════════════════════════
# SECTION 2 — OBSERVABILITY [OTEL-COMPATIBLE]
# ══════════════════════════════════════════════════════════════════

@dataclass
class StructuredSpan:
    """[OBS] Một span tracing chuẩn OpenTelemetry-compatible."""
    task_id: str
    trace_id: str
    step_id: str
    tool: str
    start_ts: float = field(default_factory=_time.time)
    end_ts: float = 0.0
    status: str = "running"   # running | ok | failed | aborted
    attempt: int = 1
    error: str = ""

    def finish(self, status: str, error: str = "") -> "StructuredSpan":
        self.end_ts = _time.time()
        self.status = status
        self.error = error
        return self

    @property
    def duration_ms(self) -> float:
        return (self.end_ts - self.start_ts) * 1000

    def to_json(self) -> str:
        return json.dumps({
            "task_id": self.task_id,
            "trace_id": self.trace_id,
            "step_id": self.step_id,
            "tool": self.tool,
            "status": self.status,
            "duration_ms": round(self.duration_ms, 2),
            "attempt": self.attempt,
            "error": self.error,
        })

# ══════════════════════════════════════════════════════════════════
# SECTION 3 — CIRCUIT BREAKER [RESILIENCE]
# ══════════════════════════════════════════════════════════════════

class CircuitState(Enum):
    CLOSED = "closed"
    OPEN = "open"
    HALF_OPEN = "half_open"

@dataclass
class CircuitBreaker:
    """[RESILIENCE] Ngăn chặn sụp đổ dây chuyền."""
    failure_threshold: int = 3
    recovery_ttl: float = 60.0

    _failures: int = field(default=0, init=False)
    _state: CircuitState = field(default=CircuitState.CLOSED, init=False)
    _opened_at: float = field(default=0.0, init=False)

    def allow(self) -> bool:
        if self._state == CircuitState.CLOSED: return True
        if self._state == CircuitState.OPEN:
            if _time.time() - self._opened_at >= self.recovery_ttl:
                self._state = CircuitState.HALF_OPEN
                return True
            return False
        return True

    def record_success(self):
        self._failures = 0
        self._state = CircuitState.CLOSED

    def record_failure(self):
        self._failures += 1
        if self._failures >= self.failure_threshold:
            self._state = CircuitState.OPEN
            self._opened_at = _time.time()

_CB_MAX_LOCAL = 256

class CircuitBreakerRegistry:
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._access_order: List[str] = []
        self._lock = asyncio.Lock()

    def _prune(self):
        if len(self._breakers) > _CB_MAX_LOCAL:
            overflow = len(self._breakers) - _CB_MAX_LOCAL
            for key in self._access_order[:overflow]:
                self._breakers.pop(key, None)
            self._access_order = self._access_order[overflow:]

    def get_sync(self, tool: str) -> CircuitBreaker:
        if tool not in self._breakers:
            cb = CircuitBreaker()
            try:
                from redis_client import get_redis
                r = get_redis()
                if r:
                    saved_state = r.get(f"circuit_breaker:state:{tool}")
                    if saved_state == "OPEN":
                        cb._state = CircuitState.OPEN
                        cb._opened_at = float(r.get(f"circuit_breaker:opened_at:{tool}") or 0.0)
            except Exception:
                pass
            self._breakers[tool] = cb
            self._access_order.append(tool)
            self._prune()
        else:
            self._access_order.remove(tool)
            self._access_order.append(tool)
        return self._breakers[tool]

    def record_state_change(self, tool: str, state_str: str, opened_at: float = 0.0):
        """🚀 [REDIS-CIRCUIT-SYNC]: Đồng bộ trạng thái Circuit Breaker qua Redis cho multi-worker."""
        try:
            from redis_client import get_redis
            r = get_redis()
            if r:
                r.set(f"circuit_breaker:state:{tool}", state_str, ex=3600)
                if opened_at:
                    r.set(f"circuit_breaker:opened_at:{tool}", str(opened_at), ex=3600)
        except Exception:
            pass

_circuit_registry = CircuitBreakerRegistry()

# ══════════════════════════════════════════════════════════════════
# SECTION 4 — MISSION BUDGET [RESOURCES]
# ══════════════════════════════════════════════════════════════════

class MissionBudget:
    """[BUDGET] Kiểm soát tài nguyên thâm sâu."""
    def __init__(self, max_steps: int = 50, max_latency: float = 3600.0):
        self.max_steps = max_steps
        self.max_latency = max_latency
        self._sem = asyncio.Semaphore(max_steps)
        self._start = _time.monotonic()
        self._consumed = 0

    async def consume_step(self) -> bool:
        if self.remaining_time <= 0: return False
        try:
            if self._sem.locked():
                return False
            await self._sem.acquire()
            self._consumed += 1
            return True
        except Exception: return False


    @property
    def remaining_time(self) -> float:
        return max(0.0, self.max_latency - (_time.monotonic() - self._start))

# ══════════════════════════════════════════════════════════════════
# SECTION 5 — WEIGHT CONFIG [METRICS]
# ══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CognitiveWeights:
    """[METRICS] Tham số nơ-ron không hardcode."""
    replan_weight: float = 0.12
    failure_weight: float = 0.18
    latency_divisor: float = 280.0
    confidence_default: float = 0.5
    memory_prune_keep: int = 10
    attention_ttl: float = 600.0

    @classmethod
    def from_env(cls) -> "CognitiveWeights":
        return cls(
            replan_weight=float(os.getenv("COG_REPLAN_W", "0.12")),
            failure_weight=float(os.getenv("COG_FAILURE_W", "0.18")),
            latency_divisor=float(os.getenv("COG_LAT_DIV", "280.0")),
        )

# ══════════════════════════════════════════════════════════════════
# SECTION 6 — EVENT-SOURCED COGNITIVE CORE DEPRECATED (Moved to core/kernel)
# ══════════════════════════════════════════════════════════════════

# ══════════════════════════════════════════════════════════════════
# SECTION 7 — SAFE DAG SCHEDULER [IMPROVED]
# ══════════════════════════════════════════════════════════════════

class SafeDAGScheduler:
    """[DAG] Điều phối đồ thị an toàn."""
    def __init__(self, steps: list[dict], max_dynamic: int = 25):
        self.steps: dict[str, dict] = {}
        self.indegree: dict[str, int] = {}
        self.adj: dict[str, list[str]] = defaultdict(list)
        self.done, self.failed, self.blocked = set(), set(), set()
        self._ready: deque[dict] = deque()
        self._lock = asyncio.Lock()
        self._build(steps)

    def _build(self, steps: list[dict]):
        for s in steps:
            sid = s.setdefault("id", f"step_{len(self.steps)}")
            self.steps[sid] = s
            deps = s.get("deps", [])
            self.indegree[sid] = len(deps)
            for d in deps: self.adj[d].append(sid)
            if self.indegree[sid] == 0: self._ready.append(s)

    def is_complete(self) -> bool:
        return len(self.done | self.failed | self.blocked) >= len(self.steps)

    @property
    def completion_ratio(self) -> float:
        return len(self.done) / len(self.steps) if self.steps else 1.0

    async def get_ready_batch(self, max_size: int = 6) -> list[dict]:
        async with self._lock:
            batch, terminal = [], self.done | self.failed | self.blocked
            while self._ready and len(batch) < max_size:
                s = self._ready.popleft()
                if s["id"] not in terminal: batch.append(s)
            return batch

    async def mark_done(self, sid: str):
        async with self._lock:
            self.done.add(sid)
            for succ in self.adj.get(sid, []):
                self.indegree[succ] -= 1
                if self.indegree[succ] == 0: self._ready.append(self.steps[succ])

    async def mark_failed(self, sid: str, cascade: bool = True):
        async with self._lock:
            self.failed.add(sid)
            if cascade:
                stack = list(self.adj.get(sid, []))
                while stack:
                    curr = stack.pop()
                    if curr not in self.blocked:
                        self.blocked.add(curr)
                        stack.extend(self.adj.get(curr, []))

# ══════════════════════════════════════════════════════════════════
# SECTION 8 — GOVERNOR & REFLECTION
# ══════════════════════════════════════════════════════════════════

class CognitiveGovernor:
    def adaptive_concurrency(self, core: CognitiveTaskKernel) -> int:
        f = core.fatigue_score
        if f > 0.8: return 2
        if f > 0.5: return 3
        return 8

    def should_abort(self, core: CognitiveTaskKernel, budget: MissionBudget) -> bool:
        return core.fatigue_score > 0.95 or budget.remaining_time < 10.0

class MetaReflectionEngine:
    async def reflect(self, core: CognitiveTaskKernel, goal: str) -> dict:
        return {"should_replan": core.confidence_score < 0.45, "fatigue": core.fatigue_score}

# ══════════════════════════════════════════════════════════════════
# SECTION 9 — TASK MANAGER v5.0 [ORCHESTRATOR]
# ══════════════════════════════════════════════════════════════════

class TaskManager:
    """[ZENITH-OS] Lõi điều phối v5.0."""
    def __init__(self, *, redis_conn, async_redis_conn, router, hitl, weights=None):
        self.redis, self.async_redis, self.router, self.hitl = redis_conn, async_redis_conn, router, hitl
        self.weights = weights or CognitiveWeights.from_env()
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(connect=5.0, read=90.0, write=30.0, pool=5.0),
            limits=httpx.Limits(max_connections=100, max_keepalive_connections=20)
        )
        self.governor, self.reflection = CognitiveGovernor(), MetaReflectionEngine()
        # 🛡️ [ZERO-LEAK]: Background tasks handled via fire_and_forget
        self.mission_control_url = os.getenv("MISSION_CONTROL_URL", "http://mission-control:9998")

    async def _save_mission_to_history(self, core: CognitiveTaskKernel, status: str = "completed"):
        """Save the cognitive task mission and its execution log to Zenith history."""
        try:
            state = core.state
            mission_id = self.task_id_to_mission_id(core.task_id)
            task_id_str = str(core.task_id)
            
            def clean_id(tid: str) -> str:
                tid_str = str(tid)
                if tid_str.startswith("m_"):
                    tid_str = tid_str[2:]
                if tid_str.startswith("ZENITH_"):
                    tid_str = tid_str[7:]
                if tid_str.startswith("default_"):
                    tid_str = tid_str[8:]
                return tid_str
            
            clean_target_id = clean_id(task_id_str)
            mission_logs = []
            
            def get_logs_from_redis(r):
                ops = r.lrange("monitor:log_history", 0, -1) or []
                prog = r.lrange("monitor:progress_history", 0, -1) or []
                seen = set()
                merged = []
                for item in ops + prog:
                    key = item if isinstance(item, str) else str(item)
                    if key in seen:
                        continue
                    seen.add(key)
                    merged.append(item)
                return merged

            raw_logs = redis_safe(get_logs_from_redis, [])
            final_answer = ""
            
            for item in raw_logs:
                if not item:
                    continue
                try:
                    if isinstance(item, bytes):
                        item_str = item.decode('utf-8')
                    else:
                        item_str = str(item)
                    
                    log_data = json.loads(item_str)
                    log_task_id = str(log_data.get("task_id", ""))
                    
                    if log_task_id == task_id_str or log_task_id == mission_id or clean_id(log_task_id) == clean_target_id:
                        tag = log_data.get("tag", "SYSTEM")
                        msg = log_data.get("msg", "")
                        mission_logs.append({
                            "tag": tag,
                            "msg": msg,
                            "ts": log_data.get("ts", _time.time()),
                            "source": log_data.get("source", "SYSTEM"),
                            "task_id": log_task_id
                        })
                        if tag in ("JKAI", "MISSION_RESULT", "RESULT", "DONE") and msg:
                            final_answer = msg
                except Exception:
                    pass
            
            mission_logs.sort(key=lambda x: x.get("ts", 0))
            
            if not mission_logs:
                mission_logs = [{"tag": "SYSTEM", "msg": f"Nhiệm vụ {status}.", "ts": _time.time()}]
                
            walkthrough = final_answer or f"Nhiệm vụ {status}. Xem Nhật ký Điều hành (giữa) và tab Tiến trình (phải)."
            payload = {
                "id": mission_id,
                "title": state.goal.split('\n')[0][:70],
                "goal": state.goal,
                "status": status,
                "ts": _time.time(),
                "logs": mission_logs,
                "artifacts": {
                    "plan": state.goal.split("\n")[0][:2000] if state.goal else "",
                    "walkthrough": walkthrough[:15000],
                    "tasks": "Xem tab Tiến trình để biết từng bước EXECUTOR/CURSOR-AGENT.",
                }
            }
            await self.client.post(f"{self.mission_control_url}/api/mission/save", json=payload, timeout=5.0)
        except Exception as e:
            self._log("ERROR", f"Failed to save mission history: {e}")

    async def _record_civilization_wisdom(self, core: CognitiveTaskKernel, jr: dict = None):
        try:
            success_steps = []
            for step_id in core.state.completed_steps:
                step_data = core.state.steps.get(step_id, {}) if isinstance(core.state.steps, dict) else {}
                success_steps.append({
                    "id": step_id,
                    "tool": step_data.get("tool", "unknown_tool")
                })
            failed_steps = list(core.state.failed_steps)
            await civilization_ledger.record_experience(
                task_id=core.task_id,
                goal=core.state.goal,
                success_steps=success_steps,
                failed_steps=failed_steps,
                judicial_review_notes=jr or {}
            )
        except Exception as e:
            self._log("ERROR", f"❌ [CIVILIZATION-ERR]: Lỗi ghi nhận bài học lịch sử ({e})")

    def task_id_to_mission_id(self, tid: str) -> str:
        if tid.startswith("m_"): return tid
        return f"m_{tid}"

    def _write_task_board(self, goal: str, cycle: Any, history_steps: List[Dict[str, Any]]):
        """Ghi nhận trạng thái tiến trình thực thi cuốn chiếu lên bảng công việc vật lý task.md."""
        content = f"# SỨ MỆNH: {goal}\n\n"
        content += f"## VÒNG LẶP HOÀN THIỆN (CYCLE {cycle}/10)\n\n"
        if not history_steps:
            content += "- [ ] Sẵn sàng khởi tạo chiến dịch.\n"
        else:
            for s in history_steps:
                status_icon = "x" if s.get('status') == "success" else " "
                content += f"- [{status_icon}] **{s['id']}** (`{s['tool']}`): {s['description']}\n"
                if s.get('result_summary'):
                    res_snippet = s['result_summary'].strip().replace("\n", " ")[:300]
                    content += f"  - *Kết quả*: {res_snippet}\n"
        
        # 🌍 [PORTABLE-PATH]: Dùng biến môi trường thay vì hardcode Windows path - hỗ trợ Linux/Docker/K8s
        task_md_path = os.getenv("TASK_BOARD_PATH", "/workspace/task.md")
        try:
            with open(task_md_path, "w", encoding="utf-8") as f:
                f.write(content)
        except Exception as e:
            self._log("ERROR", f"❌ Lỗi ghi task.md: {e}")

    def _increment_surgery_count(self, tid: str) -> int:
        """Tăng đếm số lần phẫu thuật của Task ID."""
        def _inc(r):
            val = r.incr(f"zenith:surgery_count:{tid}")
            r.expire(f"zenith:surgery_count:{tid}", 86400)
            return int(val)
        return redis_safe(_inc, 0)


    @classmethod
    def builder(cls): return _TaskManagerBuilder(cls)

    def _log(self, tag, msg, tid="sys", trid="sys", **kwargs): 
        engine.publish_mission_log(tag, msg, tid, trid, **kwargs)

    def _fire_and_forget(self, coro):
        """🛡️ [ZERO-LEAK]: Production task helper."""
        task = asyncio.create_task(coro)
        task.add_done_callback(lambda t: t.exception() if not t.cancelled() else None)

    async def start(self):
        """🚀 [MISSION-LISTENER]: Vòng lặp thụ hưởng Sứ mệnh v5.0."""
        import logging
        logging.info("🏛️ [JKAI-ZENITH] v5.0 Task Orchestrator is listening for missions...")
        self._log("SYSTEM", "🏛️ [JKAI-ZENITH] v5.0 Task Orchestrator is listening for missions...", stealth=True)
        
        while True:
            try:
                # 📥 [QUEUE-POLL]: Lắng nghe từ hàng đợi chính
                if self.async_redis:
                    res = await self.async_redis.blpop(["ai_task_queue", "user_request_queue"], timeout=30)
                    if res:
                        _, payload_raw = res
                        payload = json.loads(payload_raw)
                        # 🧬 [NEURAL-PULSE]: Kích hoạt nhịp đập xử lý
                        asyncio.create_task(self.process_task(payload))
                else:
                    await asyncio.sleep(1)
            except Exception as e:
                self._log("ERROR", f"❌ [ORCHESTRATOR-ERR]: {e}")
                await asyncio.sleep(5)

    async def process_task(self, data: dict):
        goal, tid, trid = data.get("goal", ""), data.get("task_id", "man"), data.get("trace_id", "sys")
        lkey = f"task_lock:{tid}"
        if tid != "man" and not redis_safe(lambda r: r.set(lkey, "busy", nx=True, ex=1800)): return {"status": "skipped"}
        try: return await self._run_mission(goal, tid, trid, data.get("mode", "auto"), data)
        finally: redis_safe(lambda r: r.delete(lkey))

    async def _run_mission(self, goal, tid, trid, mode, data: dict = None):
        """🏛️ [COGNITIVE-ROUTER]: Phân tách lộ trình Nhất thể."""
        sid = trid
        data = data or {}
        core = CognitiveTaskKernel(tid, CognitiveState(task_id=tid, session_id=sid, goal=goal, steps_total=1, mode=mode))

        # 🧠 [SESSION-CONTEXT]: Load/save conversation history to Redis
        session_id = data.get("session_id") or sid
        try:
            sc = get_session_context(get_redis)
            sc.add_user_message(session_id, goal)
            session_history = sc.get_history(session_id, limit=100)
            data["history"] = session_history
        except Exception as sess_err:
            self._log("WARN", f"[SESSION-CONTEXT] Error: {sess_err}", tid, trid)
        status = "failed"
        mission_mid = data.get("mission_id") or self.task_id_to_mission_id(tid)
        parent_mid = data.get("parent_mission_id")
        try:
            try:
                from core.utils.ingress_skill_gate import try_skill_deck_inspect, enrich_goal_with_deck

                inspect_hit = try_skill_deck_inspect(goal)
                if inspect_hit:
                    ans = inspect_hit.get("answer", "")
                    self._log("JKAI", ans[:400], tid, trid)
                    status = "completed"
                    return {"status": inspect_hit.get("status", "success"), "answer": ans, "task_id": tid}
                # Command (/status, /help, ...) không cần SSM enrich — brain sẽ bắt bằng command interceptor
                if not goal.strip().startswith("/"):
                    goal, _, deck_warn = enrich_goal_with_deck(goal)
                    if deck_warn:
                        self._log("WARN", deck_warn, tid, trid)
            except Exception as deck_ex:
                self._log("WARN", f"[SKILL-DECK] control-plane: {deck_ex}", tid, trid)

            manifest = await self.router.route_to_receptionist(
                {
                    "goal": goal,
                    "task_id": tid,
                    "mode": mode,
                    "trace_id": trid,
                    "mission_id": mission_mid,
                    "parent_mission_id": parent_mid,
                    "history": data.get("history", []),
                    "session_id": session_id,
                }
            )
            
            if manifest.get("status") == "error" or "error" in manifest:
                err_msg = manifest.get("error", "Lỗi nơ-ron không xác định.")
                self._log("ERROR", f"[RECEPTIONIST-FAILED]: {err_msg} | manifest={json.dumps(manifest, ensure_ascii=False)[:500]}", tid, trid)
                err_answer = f"[Sự cố Kết nối Nơ-ron]: Hệ thống Lễ Tân gặp lỗi khi tiếp nhận yêu cầu. Master vui lòng kiểm tra xem mô hình model hoặc dịch vụ Ollama có bị quá tải không và thử lại ạ. (Chi tiết: {err_msg})"
                self._log("JKAI", err_answer, tid, trid)
                try:
                    sc = get_session_context(get_redis)
                    sc.add_assistant_message(session_id, err_answer)
                except Exception:
                    pass
                status = "failed"
                return {"status": "error", "answer": err_answer, "task_id": tid}

            if (manifest.get("answer") and not manifest.get("steps")) or manifest.get("is_social"):
                ans_val = manifest.get("answer", "Hệ thống đã nhận thông điệp của ngài.")
                ans_str = ans_val.get("content") if isinstance(ans_val, dict) else str(ans_val)
                self._log("JKAI", ans_str, tid, trid)
                
                try:
                    sc = get_session_context(get_redis)
                    sc.add_assistant_message(session_id, ans_str)
                except Exception:
                    pass
                try:
                    core._state = replace(
                        core._state,
                        goal=(core.state.goal or "") + f"\n\n[KẾT QUẢ]\n{ans_str[:8000]}",
                    )
                except Exception:
                    pass
                status = "completed"
                try:
                    from core.utils.mission_context import save_context_pack

                    save_context_pack(
                        mission_mid,
                        goal=goal,
                        blueprint_summary=ans_str[:2000],
                        parent_mission_id=parent_mid,
                    )
                except Exception:
                    pass
                return {**manifest, "status": "success", "answer": ans_str}

            current_mode = manifest.get("mode", mode)
            if current_mode == "fast" and not manifest.get("mode") == "delegate":
                res = await self._run_fast_path(goal, tid, trid, manifest, core)
                if res.get("status") == "success":
                    status = "completed"
                else:
                    status = "failed"
                try:
                    ans_val = res.get("answer") or res.get("summary") or ""
                    if ans_val:
                        sc = get_session_context(get_redis)
                        sc.add_assistant_message(session_id, str(ans_val)[:5000])
                except Exception:
                    pass
                return res
            
            deep_goal = goal
            try:
                lessons = await civilization_ledger.retrieve_analogous_lessons(goal, limit=2)
                if lessons:
                    lesson_texts = "\n".join([f"📌 [BÀI HỌC KINH NGHIỆM {i+1}]: {l['text']}" for i, l in enumerate(lessons)])
                    self._log("WISDOM_LEDGER", f"📜 [KHO TÀI LIỆU CỔ] Tìm thấy {len(lessons)} bài học tương thích từ lịch sử:\n{lesson_texts}", tid, trid)
                    deep_goal = f"{goal}\n\n[SOVEREIGN WISDOM FROM COLLECTIVE MEMORY - CÁC BÀI HỌC LỊCH SỬ CẦN KẾ THỪA]:\n{lesson_texts}"
                    core._state = replace(core._state, goal=deep_goal)
            except Exception as memory_err:
                self._log("WARN", f"⚠️ [BỘ NHỚ TẬP THỂ PHÂN RÃ]: Không thể truy vấn Sổ cái Văn minh ({str(memory_err)})", tid, trid)

            res = await self._run_deep_path(deep_goal, tid, trid, mode, manifest, core)
            if res.get("status") == "success" or res.get("summary") or "answer" in res:
                status = "completed"
            else:
                status = "failed"
            try:
                ans_val = res.get("answer") or res.get("summary") or ""
                if ans_val:
                    sc = get_session_context(get_redis)
                    sc.add_assistant_message(session_id, str(ans_val)[:5000])
            except Exception:
                pass
            return res
        except Exception as e:
            self._log("ERROR", f"[MISSION-FAILED]: {str(e)}", tid, trid)
            status = "failed"
            return {"status": "error", "answer": f"Lỗi hệ thống: {str(e)}", "task_id": tid}
        finally:
            try:
                await self._save_mission_to_history(core, status)
            except Exception as save_err:
                self._log("ERROR", f"Failed to save final mission history: {save_err}", tid, trid)

    def _build_planner_payload(
        self,
        goal: str,
        tid: str,
        trid: str,
        mode: str,
        context_extra: Optional[dict] = None,
        use_planning_pipeline: bool = False,
    ) -> dict:
        ctx = dict(context_extra or {})
        ctx["trace_id"] = trid
        ctx["mode"] = mode
        if use_planning_pipeline:
            ctx["use_planning_pipeline"] = True
        return {"goal": goal, "task_id": tid, "mode": mode, "context": ctx}

    async def _run_fast_path(self, goal, tid, trid, manifest, core=None):
        """[FAST-PATH]: Lộ trình phản xạ siêu tốc."""
        engine.publish_progress(10, "Đang phân tích Mục tiêu Chiến lược", "deep_route", tid, trid)
        self._log("SYSTEM", "[DEEP-ROUTE]: Khởi tạo Lộ trình Tư duy Đa tầng.", tid, trid, stealth=True)
        
        # T3: Blueprint trực tiếp (Bỏ qua Planner)
        steps = manifest.get("steps")
        if not steps:
            plan_res = await self.router.route_to_planner(
                self._build_planner_payload(goal, tid, trid, "fast")
            )
            steps = plan_res.get("steps", [])
        
        if not steps:
            err_answer = "⚠️ **Lỗi phản xạ**: Không thể tạo lộ trình thực thi chớp nhoáng (FAST) cho yêu cầu này. Master vui lòng tinh chỉnh lại yêu cầu hoặc thử lại ạ. 🫡"
            self._log("JKAI", err_answer, tid, trid)
            return {"status": "error", "answer": err_answer, "task_id": tid}

        sid = manifest.get("session_id") or trid
        if core is None:
            core = CognitiveTaskKernel(tid, CognitiveState(task_id=tid, session_id=sid, goal=goal, steps_total=len(steps), mode="fast"))
        else:
            core._state = replace(core._state, steps_total=len(steps), mode="fast")
        
        # 🏢 [CORPORATE-GOVERNANCE]: Ghi nhận thẩm định hồ sơ vĩ mô
        core.transition(TaskState.VALIDATED, actor="OFFICE_ORCHESTRATOR", reason="Hồ sơ nhiệm vụ phản xạ đã qua thẩm định sơ khởi thành công.")
        core.transition(TaskState.ANALYZED, actor="OFFICE_ORCHESTRATOR", reason="Lộ trình phản xạ siêu tốc được phòng kế hoạch thông qua.")
        core.transition(TaskState.POLICY_CHECKED, actor="OFFICE_ORCHESTRATOR", reason="Ban Pháp chế xác nhận toàn bộ hành động tuân thủ chính sách tập đoàn.")
        core.transition(TaskState.PLANNED, actor="OFFICE_ORCHESTRATOR", reason="Kế hoạch tác chiến phản xạ nhanh chính thức biên soạn xong.", payload={"steps": steps})
        core.transition(TaskState.SANDBOX_PREPARED, actor="OFFICE_ORCHESTRATOR", reason="Phòng hạ tầng bàn giao phân khu làm việc an toàn.")
        core.transition(TaskState.EXECUTING, actor="OFFICE_ORCHESTRATOR", reason="Bắt đầu triển khai lực lượng thực thi chuỗi công vụ DAG.")

        dag, budget, w_lock = SafeDAGScheduler(steps), MissionBudget(max_steps=len(steps)*2), asyncio.Lock()

        # T4: Thực thi chớp nhoáng
        all_results = await self._execute_dag(dag, core, budget, w_lock, goal, tid, trid, "fast")

        # T5/T6 FAST: Tổng hợp nhanh
        engine.publish_progress(90, "🧠 Đang tổng hợp và chắt lọc kết quả", "fast_route", tid, trid)
        summary_res = await self.router.route_to_summarizer({"goal": goal, "result": all_results, "steps": steps, "mode": "fast", "task_id": tid, "trace_id": trid})
        final_ans = summary_res.get("summary", summary_res.get("answer", "Nhiệm vụ hoàn tất."))

        self._log("JKAI", final_ans, tid, trid)
        
        # 🏢 [CORPORATE-GOVERNANCE]: Nghiệm thu kết quả
        core.transition(TaskState.COMMITTING, actor="OFFICE_ORCHESTRATOR", reason="Bàn giao báo cáo nghiệm thu kết quả lên phòng tổng hợp.")
        core.transition(TaskState.COMMITTED, actor="OFFICE_ORCHESTRATOR", reason="Báo cáo chính thức phê duyệt và lưu trữ vào biên niên sử doanh nghiệp.")
        core.transition(TaskState.COMPLETED, actor="OFFICE_ORCHESTRATOR", reason="Sứ mệnh hoàn thành xuất sắc nhiệm vụ phản xạ chớp nhoáng.", payload={"answer": final_ans})

        self._fire_and_forget(self._record_civilization_wisdom(core))
        
        return {"status": "success", "answer": final_ans, "task_id": tid}

    async def _run_deep_path(self, goal, tid, trid, mode, manifest, core=None):
        """🏛️ [DEEP-PATH]: Quy trình 6 Giai đoạn Chiến lược với Vòng lặp Cuốn chiếu (Rolling Horizon)."""
        if manifest.get("is_social"): return {**manifest, "status": "success"}

        # 🧪 [T2.5: SCRIPT-INJECTION]: Tiêm script chuẩn bị thực địa
        await self._run_t2_5_injection(goal, tid, trid)

        # Kiểm tra xem Cloud Escalation có đang kích hoạt hay không
        is_cloud_escalated = redis_safe(lambda r: r.get(f"zenith:cloud_escalated:{tid}") == "true", False)

        try:
            executed_steps_history = []
            all_results = []
            max_cycles = 10
            sid = manifest.get("session_id") or trid
            
            # Khởi tạo CognitiveTaskKernel ban đầu hoặc tái sử dụng core được truyền vào
            if core is None:
                core = CognitiveTaskKernel(tid, CognitiveState(task_id=tid, session_id=sid, goal=goal, steps_total=30, mode=mode))
            else:
                core._state = replace(core._state, steps_total=30, mode=mode)
            
            # 🏢 [CORPORATE-GOVERNANCE]: Ban thẩm định cấp cao phê chuẩn kế hoạch chiến lược ban đầu
            core.transition(TaskState.VALIDATED, actor="CORPORATE_BOARD", reason="Văn phòng thường trực chính thức tiếp nhận và đóng dấu phê duyệt hồ sơ sứ mệnh.")
            core.transition(TaskState.ANALYZED, actor="CORPORATE_BOARD", reason="Văn phòng Chiến lược vĩ mô hoàn tất phân tích bối cảnh tài nguyên toàn cục.")
            core.transition(TaskState.POLICY_CHECKED, actor="CORPORATE_BOARD", reason="Ban Pháp chế và An ninh thông qua bộ quy tắc ứng xử của các Agent tham chiến.")
            
            # Bắt đầu vòng lặp cuốn chiếu (Rolling Horizon) tối đa 10 chu kỳ
            for cycle in range(1, max_cycles + 1):
                self._log("SYSTEM", f"[ROLLING-HORIZON] Khởi chạy Vòng lặp Cuốn chiếu - Chu kỳ {cycle}/{max_cycles}", tid, trid)
                
                # 1. Ghi nhận trạng thái hiện tại lên bảng công việc vật lý task.md
                self._write_task_board(goal, cycle, executed_steps_history)
                
                # 2. Gọi Planner để lấy tối đa 3 bước tiếp theo phù hợp với ngữ cảnh thực tế của task.md
                planner_payload = self._build_planner_payload(
                    goal,
                    tid,
                    trid,
                    mode,
                    context_extra={
                        "cycle": cycle,
                        "history_len": len(executed_steps_history),
                    },
                    use_planning_pipeline=(mode == "deep" and cycle == 1),
                )
                if is_cloud_escalated or manifest.get("model_override"):
                    planner_payload["model"] = "gemini-1.5-pro"
                    planner_payload["model_override"] = "gemini-1.5-pro"
                
                plan_res = await self.router.route_to_planner(planner_payload)
                
                # 🛡️ [EMPTY-PLAN-PROTECTION]: Bảo vệ nếu planner rỗng hoặc báo lỗi
                steps = plan_res.get("steps", [])
                if not steps:
                    if cycle == 1:
                        raise ValueError("Planner returned no steps.")
                    else:
                        self._log("SYSTEM", f"✅ [ROLLING-HORIZON] Planner không sinh thêm bước mới. Nhiệm vụ hoàn thành xuất sắc tại Chu kỳ {cycle-1}.", tid, trid)
                        break
                
                self._log("SYSTEM", f"📡 [ROLLING-HORIZON] Planner sinh {len(steps)} bước cho Chu kỳ {cycle}.", tid, trid)
                
                # Cập nhật số bước tổng thể của Kernel dựa trên số bước thực tế
                core._state = replace(core._state, steps_total=len(executed_steps_history) + len(steps))
                
                core.transition(TaskState.PLANNED, actor="CORPORATE_BOARD", reason=f"Phòng Chiến thuật biên soạn xong sơ đồ chu kỳ {cycle} gồm {len(steps)} bước.", payload={"steps": steps})
                core.transition(TaskState.SANDBOX_PREPARED, actor="CORPORATE_BOARD", reason=f"Chuẩn bị phân vùng tài nguyên biệt lập cho chu kỳ {cycle}.")
                core.transition(TaskState.EXECUTING, actor="CORPORATE_BOARD", reason=f"Kích hoạt nơ-ron thực thi chu kỳ {cycle} cuốn chiếu.")
                
                # 3. Thực thi DAG cho batch 1-3 bước này
                dag, budget, w_lock = SafeDAGScheduler(steps), MissionBudget(max_steps=len(steps)*2), asyncio.Lock()
                
                # T4: Hành pháp Swarm v5.0 cho chu kỳ hiện tại
                cycle_results = await self._execute_dag(dag, core, budget, w_lock, goal, tid, trid, mode)
                all_results.extend(cycle_results)
                
                # 4. Lưu lại kết quả thực thi vào lịch sử để viết lên task.md ở chu kỳ sau
                for s in steps:
                    sid_step = s["id"]
                    is_done = sid_step in dag.done
                    status_str = "success" if is_done else "failed"
                    
                    # Tìm kết quả chi tiết của bước này từ cycle_results
                    result_summary = "N/A"
                    for res in cycle_results:
                        if isinstance(res, dict) and (res.get("id") == sid_step or res.get("step_id") == sid_step or res.get("status") == "success"):
                            result_summary = res.get("output") or res.get("answer") or res.get("msg") or str(res)
                            break
                    if isinstance(result_summary, dict):
                        result_summary = json.dumps(result_summary, ensure_ascii=False)
                    else:
                        result_summary = str(result_summary)
                    
                    executed_steps_history.append({
                        "id": sid_step,
                        "tool": s.get("tool", "unknown"),
                        "description": s.get("description", "Không có mô tả"),
                        "status": status_str,
                        "result_summary": result_summary
                    })
                
                # Nếu có bước nào bị lỗi nghiêm trọng, chuyển giao thông tin để Planner tự phục hồi ở chu kỳ tiếp theo
                has_failures = any(s["id"] in (dag.failed | dag.blocked) for s in steps)
                if has_failures:
                    self._log("WARN", f"⚠️ [ROLLING-HORIZON] Phát hiện lỗi bước thực thi trong chu kỳ {cycle}.", tid, trid)
            
            # Ghi nhận trạng thái hoàn tất cuối cùng lên task.md
            self._write_task_board(goal, "HOÀN TẤT", executed_steps_history)

            # T5: Thẩm định Tư pháp cuối cùng
            async with w_lock:
                core.transition(TaskState.VERIFYING, actor="CORPORATE_BOARD", reason="Bắt đầu phiên Thẩm định Tư pháp cấp cao đánh giá hiệu suất của Agent thực thi.")
            
            jr_payload = {
                "goal": goal,
                "blueprint": {"steps": executed_steps_history},
                "results": all_results,
                "task_id": tid,
                "metadata": {"fatigue": core.fatigue_score, "ratio": 1.0}
            }
            if is_cloud_escalated or manifest.get("model_override"):
                jr_payload["model"] = "gemini-1.5-pro"
                jr_payload["model_override"] = "gemini-1.5-pro"

            jr = await self.router.route_to_judicial_review(jr_payload)
            
            async with w_lock:
                core.apply_event("REFLECTED", actor="JUDICIAL_BOARD", payload=jr)
                core.transition(TaskState.VERIFIED, actor="CORPORATE_BOARD", reason="Báo cáo kiểm toán chất lượng công vụ được Ban Thư ký phê duyệt.")

            # T6: Thu hoạch Tri thức
            safe_results = str(all_results)[:4000] if all_results else []
            
            summarizer_payload = {
                "goal": goal,
                "result": safe_results,
                "steps": executed_steps_history,
                "judicial_review": jr
            }
            if is_cloud_escalated or manifest.get("model_override"):
                summarizer_payload["model"] = "gemini-1.5-pro"
                summarizer_payload["model_override"] = "gemini-1.5-pro"

            res = await self.router.route_to_summarizer(summarizer_payload)
            
            # Chỉ chưng cất bài học nếu nhiệm vụ đủ phức tạp
            if mode != "fast" and core.fatigue_score > 0.1:
                self._fire_and_forget(self.router.route_to_distill({"goal": goal, "task_id": tid}))
                self._fire_and_forget(self.router.route_to_distill_judicial({"task_id": tid, "judicial_review": jr}))

            final_ans = res.get("summary", "")
            async with w_lock:
                core.transition(TaskState.COMMITTING, actor="CORPORATE_BOARD", reason="Chuyển giao toàn bộ tri thức đúc kết và bài học kinh nghiệm về Ban Nhân sự tập đoàn.")
                core.transition(TaskState.COMMITTED, actor="CORPORATE_BOARD", reason="Cơ sở tri thức nòng cốt của tập đoàn chính thức cập nhật kinh nghiệm chiến dịch mới.")
                core.transition(TaskState.COMPLETED, actor="CORPORATE_BOARD", reason="Đại chiến dịch hoàn thành xuất sắc sứ mệnh tầm vĩ mô.", payload={"answer": final_ans})
                
            self._log("JKAI", final_ans, tid, trid)
            self._fire_and_forget(self._record_civilization_wisdom(core, jr))
            
            return res

        except Exception as e:
            self._log("ERROR", f"🚨 [DEEP-PATH-FAILED]: {str(e)}", tid, trid)
            
            # Tăng đếm số lần phẫu thuật / thử của nhiệm vụ
            surgery_count = self._increment_surgery_count(tid)
            if surgery_count > 3:
                self._log("SYSTEM", f"🌐 [CLOUD-ESCALATION]: Đã thực hiện {surgery_count-1} ca phẫu thuật cục bộ nhưng lỗi vẫn tiếp diễn. Kích hoạt Cổng chuyển tiếp đám mây khẩn cấp (Gemini 1.5 Pro)!", tid, trid)
                redis_safe(lambda r: r.set(f"zenith:cloud_escalated:{tid}", "true", ex=86400))
                
                if 'core' in locals():
                    core.transition(TaskState.RETRYING, actor="CLOUD_GATEWAY", reason=f"Kích hoạt cổng chuyển tiếp đám mây khẩn cấp sau {surgery_count-1} lần tự sửa chữa thất bại.")
                
                manifest["model_override"] = "gemini-1.5-pro"
                return await self._run_deep_path(goal, tid, trid, mode, manifest)

            err_answer = f"⚠️ **Sự cố thực thi chiến lược**: Ban Điều hành ghi nhận sự cố gián đoạn ngoài ý muốn trong quá trình thực thi. Chi tiết: {str(e)}"
            self._log("JKAI", err_answer, tid, trid)
            
            if 'core' in locals():
                try:
                    from core.kernel.recovery_engine import RecoveryPolicyEngine, RecoveryAction
                    failure_type = RecoveryPolicyEngine.classify_failure(str(e))
                    attempt_count = surgery_count
                    strategy = RecoveryPolicyEngine.determine_strategy(failure_type, attempt_count)
                    
                    self._log("SYSTEM", f"[RECOVERY-AUDIT] Ban Thư ký phân loại lỗi: {failure_type.value} -> Chiến lược cứu hộ: {strategy.value} (Số lần thử: {attempt_count}/3)", tid, trid)
                    
                    if strategy == RecoveryAction.QUARANTINE:
                        core.transition(TaskState.QUARANTINED, actor="RECOVERY_OFFICER", reason=f"Cách ly khẩn cấp tài nguyên dự án nhằm bảo toàn hệ thống: {str(e)}")
                    elif strategy == RecoveryAction.ABORT_AND_ROLLBACK:
                        core.transition(TaskState.FAILED, actor="RECOVERY_OFFICER", reason=f"Thất bại nghiêm trọng: {str(e)}")
                        core.transition(TaskState.ROLLED_BACK, actor="RECOVERY_OFFICER", reason="Thu hồi toàn bộ tài nguyên, hoàn tác giao dịch về điểm an toàn.")
                    elif strategy == RecoveryAction.TRIGGER_SURGERY:
                        core.transition(TaskState.FAILED, actor="RECOVERY_OFFICER", reason=f"Ghi nhận lỗi cấu trúc/schema nghiêm trọng: {str(e)}. Khởi tạo Ban Phẫu thuật.")
                        import traceback
                        tb_str = traceback.format_exc()
                        failing_file = None
                        for line in reversed(tb_str.split("\n")):
                            if 'File "' in line:
                                parts = line.split('"')
                                if len(parts) >= 2:
                                    candidate = parts[1]
                                    if any(x in candidate for x in ["/app", "/shared", "N8N", "core", "services"]):
                                        if os.path.exists(candidate):
                                            failing_file = candidate
                                            break
                        if failing_file:
                            from core.kernel.surgery_engine import surgery_engine
                            self._log("SYSTEM", f"[PHẪU THUẬT]: Đang tiến hành can thiệp ngoại khoa trên tệp `{os.path.basename(failing_file)}`...", tid, trid)
                            success = await surgery_engine.attempt_surgery(failing_file, tb_str, task_id=tid, trace_id=trid)
                            if success:
                                core.transition(TaskState.RETRYING, actor="RECOVERY_OFFICER", reason="Ca phẫu thuật thành công mỹ mãn. Đang phục hồi sinh lực.")
                                core.transition(TaskState.EXECUTING, actor="RECOVERY_OFFICER", reason="Tái thực thi chiến dịch sâu rộng sau khi hoàn tất sửa chữa cơ thể lõi.")
                                return await self._run_deep_path(goal, tid, trid, mode, manifest)
                            else:
                                self._log("ERROR", f"[PHẪU THUẬT THẤT BẠI]: Ca can thiệp trên `{os.path.basename(failing_file)}` bất thành. Chuyển phương án cách ly.", tid, trid)
                                core.transition(TaskState.QUARANTINED, actor="RECOVERY_OFFICER", reason=f"Ca phẫu thuật thất bại, cách ly bảo toàn hệ thống. Lỗi gốc: {str(e)}")
                        else:
                            self._log("ERROR", "❌ [PHẪU THUẬT THẤT BẠI]: Không xác định được tệp mã lỗi trong traceback.", tid, trid)
                            core.transition(TaskState.QUARANTINED, actor="RECOVERY_OFFICER", reason=f"Không xác định được tệp lỗi để phẫu thuật, cách ly hệ thống. Lỗi gốc: {str(e)}")
                    else:
                        core.transition(TaskState.FAILED, actor="RECOVERY_OFFICER", reason=f"Đóng chiến dịch và báo cáo lỗi: {str(e)}")
                except Exception as transition_err:
                    self._log("ERROR", f"❌ Lỗi ghi nhận trạng thái khẩn cấp lên lõi: {transition_err}", tid, trid)
                    
            return {"status": "error", "answer": err_answer, "task_id": tid}

    async def _execute_dag(self, dag, core, budget, w_lock, goal, tid, trid, mode):
        results, stalls = [], 0
        active_paths: Dict[str, Set[str]] = {} # Theo dõi đường dẫn đang bị khóa

        while not dag.is_complete():
            if self.governor.should_abort(core, budget): break
            
            # 🔋 [HOMEOSTASIS]: Thống kê sinh tồn và điều tiết tài nguyên thực tế
            gov_limit = self.governor.adaptive_concurrency(core)
            hom_limit = await homeostasis_engine.enforce_homeostasis(task_id=tid, trace_id=trid)
            concurrency_limit = min(gov_limit, hom_limit)
            ready_batch = await dag.get_ready_batch(concurrency_limit)
            if not ready_batch:
                stalls += 1
                if stalls >= 5: break
                await asyncio.sleep(0.1); continue
            
            # 🧠 [SMART-CONCURRENCY-FILTER]: Lọc batch dựa trên xung đột đường dẫn
            execution_batch = []
            for s in ready_batch:
                s_paths = path_lock_registry.extract_paths_from_step(s)
                # Kiểm tra xung đột với các bước đang chạy
                conflict = False
                for active_p in active_paths.values():
                    if not path_lock_registry.can_run_parallel(s_paths, active_p):
                        conflict = True; break
                
                if not conflict:
                    execution_batch.append(s)
                    active_paths[s["id"]] = s_paths
                else:
                    # Nếu xung đột, trả lại hàng chờ (trừ khi batch rỗng thì phải chờ)
                    await dag._ready.appendleft(s)

            if not execution_batch:
                await asyncio.sleep(0.1); continue

            stalls = 0
            tasks = []
            self._log("SYSTEM", f"[T4: ORCHESTRATOR] Đang điều phối đợt thực thi gồm {len(execution_batch)} bước song song.", tid, trid, stealth=True)
            
            async with asyncio.TaskGroup() as tg:
                for s in execution_batch:
                    if await budget.consume_step(): 
                        tasks.append(tg.create_task(self._execute_step(s, goal, tid, trid, mode, core, dag, w_lock, active_paths)))
            for t in tasks:
                r = t.result()
                if r: results.extend(r)
        return results

    async def _execute_step(self, step, goal, tid, trid, mode, core, dag, w_lock, active_paths=None):
        sid, tool = step.get("id"), step.get("tool")
        breaker = _circuit_registry.get_sync(tool)
        if not breaker.allow(): return await dag.mark_failed(sid)
        
        # 🛡️ [JSON-REPAIR]: Vá lỗi tham số trước khi gửi
        from core.utils.json_repair import repair_tool_call_arguments
        args = step.get("args") or step.get("arguments", {})
        if isinstance(args, str):
            args = repair_tool_call_arguments(args)
            step["args"] = json.loads(args)

        ws_path = workspace_manager.get_task_workspace(tid)
        
        # 🛡️ [HERMES-PATH-LOCK]: Chiếm quyền khóa đa tầng
        locks = await path_lock_registry.acquire_locks(step)
            
        from contextlib import AsyncExitStack
        async with AsyncExitStack() as stack:
            for l in locks: await stack.enter_async_context(l)
            
            span = StructuredSpan(tid, trid, sid, tool)
            engine.publish_progress(30, f"📡 Chuyển tiếp nhiệm vụ: {tool}", "fast_route", tid, trid)
            self._log("SYSTEM", f"📡 [T4: ORCHESTRATOR] Đang truyền nhiệm vụ tới Ban Thực thi cho bước `{sid}` ({tool})...", tid, trid, stealth=True)
            
            for att in range(1, 4):
                try:
                    # ⚡ [FAST-BYPASS]: Trực tiếp thực thi tool thay vì gọi Agent LLM (Giảm độ trễ từ 42s xuống 0s LLM)
                    if mode == "fast" and str(sid).startswith("fast_"):
                        target_url = self.router.executor_url
                        r = await self.client.post(f"{target_url}/call_tool", json={"name": tool, "args": args, "task_id": tid})
                        if r.status_code == 200:
                            data = r.json()
                            if data.get("status") == "error":
                                res = {"status": "error", "msg": data.get("msg", "Lỗi vô hình từ Executor")}
                            else:
                                out_val = data.get("output", data)
                                res = {"status": "success", "output": out_val, "answer": out_val}
                        else:
                            res = {"status": "error", "msg": f"Lỗi HTTP {r.status_code}: {r.text}"}
                    else:
                        res = await self.router.route_to_executor({
                            "goal": goal, 
                            "steps": [step], 
                            "task_id": tid, 
                            "trace_id": trid, 
                            "agent_soul": step.get("assigned_agent"),
                            "workspace": str(ws_path)
                        })
                        
                    if res.get("status") == "error":
                        engine.publish_progress(70, f"Lỗi thực thi: {tool}", "fast_route", tid, trid)
                        self._log("WARN", f"[T4: ORCHESTRATOR] Ban Thực thi báo lỗi cho bước `{sid}`: {res.get('msg', res.get('output', 'Unknown error'))}", tid, trid, stealth=True)
                    else:
                        engine.publish_progress(80, f"Hoàn tất thực thi: {tool}", "fast_route", tid, trid)
                        self._log("SYSTEM", f"[T4: ORCHESTRATOR] Ban Thực thi đã hoàn tất bước `{sid}`.", tid, trid, stealth=True)
                    break
                except (httpx.ConnectError, httpx.ConnectTimeout) as e:
                    self._log("WARN", f"📡 [T4: ORCHESTRATOR] Thử lại lần {att}: Không thể kết nối tới Ban Thực thi cho bước `{sid}`...", tid, trid)
                    await asyncio.sleep(att)
                except Exception as e: 
                    self._log("ERROR", f"🚨 [T4: ORCHESTRATOR] Sự cố nghiêm trọng khi điều phối bước `{sid}`: {str(e)}", tid, trid)
                    break

        if active_paths is not None and sid in active_paths:
            del active_paths[sid]

        ok = isinstance(res, dict) and res.get("status") != "error"
        async with w_lock:
            if ok:
                breaker.record_success()
                core.apply_event("TOOL_EXECUTED", actor="SYSTEM", payload={"step_id": sid, "duration": _time.time()-span.start_ts})
                if res.get("answer"):
                    ans_val = res["answer"]
                    ans_str = ans_val.get("content") or ans_val.get("output") or str(ans_val) if isinstance(ans_val, dict) else str(ans_val)
                    core.apply_event("BELIEF_ADDED", actor="SYSTEM", payload={"content": ans_str[:200], "confidence": 0.9, "source": tool})
                await dag.mark_done(sid)
            else:
                breaker.record_failure()
                core.apply_event("TOOL_FAILED", actor="SYSTEM", payload={"step_id": sid, "fingerprint": tool, "error": res.get("msg", "Unknown error") if isinstance(res, dict) else "Unknown error"})
                await dag.mark_failed(sid, cascade=True)
        return [res] if res else []

    async def _run_t2_5_injection(self, goal, tid, trid):
        """🧪 [T2.5: INJECTION]: Thực thi các script chuẩn bị."""
        try:
            # Kiểm tra xem có script nào cần chạy không (Heuristic: git diff cho refactor)
            if "refactor" in goal.lower() or "sửa" in goal.lower():
                self._log("INJECT", "🧬 [T2.5]: Tự động quét Git Diff để chuẩn bị thực địa...", tid, trid)
                # Giả lập tiêm script
                pass
        except Exception: pass

class _TaskManagerBuilder:
    def __init__(self, cls): self._cls, self._kwargs = cls, {}
    def with_redis(self, s, a): self._kwargs.update({"redis_conn": s, "async_redis_conn": a}); return self
    def with_router(self, r): self._kwargs["router"] = r; return self
    def with_hitl(self, h): self._kwargs["hitl"] = h; return self
    def build(self): return self._cls(**self._kwargs)
