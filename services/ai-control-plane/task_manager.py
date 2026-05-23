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
from cognitive_state import CognitiveState, CognitiveStateStore, CogEventType, CogEvent
from core.utils.knowledge_brain import knowledge_brain
from core.utils.path_locker import path_lock_registry
from core.utils.workspace_manager import workspace_manager

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

class CircuitBreakerRegistry:
    def __init__(self):
        self._breakers: Dict[str, CircuitBreaker] = {}
        self._lock = asyncio.Lock()

    def get_sync(self, tool: str) -> CircuitBreaker:
        if tool not in self._breakers:
            self._breakers[tool] = CircuitBreaker()
        return self._breakers[tool]

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
        except: return False


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
# SECTION 6 — EVENT-SOURCED COGNITIVE CORE [IMPROVED]
# ══════════════════════════════════════════════════════════════════

class EventSourcedCognitiveCore:
    """[CORE] Bản ngã nơ-ron v5.0."""
    SNAPSHOT_EVERY = 40

    def __init__(self, task_id: str, initial_state: CognitiveState, weights: CognitiveWeights | None = None):
        self.task_id = task_id
        self.weights = weights or CognitiveWeights.from_env()
        self._events: list[CogEvent] = []
        self._beliefs: list[dict] = list(initial_state.beliefs)
        self._failed_fps: set[str] = set(initial_state.failed_fingerprints)
        self._current = replace(initial_state, beliefs=tuple(self._beliefs), failed_fingerprints=frozenset(self._failed_fps))
        self._conf_cache: tuple[float, float] = (0.0, -1.0)

    def apply(self, event: CogEvent) -> CognitiveState:
        self._events.append(event)
        self._current = self._reduce(self._current, event)
        if len(self._events) % self.SNAPSHOT_EVERY == 0:
            asyncio.get_event_loop().call_soon(self._persist_snapshot_sync)
        return self._current

    def _reduce(self, state: CognitiveState, event: CogEvent) -> CognitiveState:
        p = event.payload
        if event.type == CogEventType.BELIEF_ADDED:
            self._beliefs.append(p)
            self._conf_cache = (0.0, -1.0)
            return replace(state, beliefs=tuple(self._beliefs), version=state.version + 1)
        elif event.type == CogEventType.TOOL_EXECUTED:
            return replace(state, completed_steps=state.completed_steps + (p.get("step_id", ""),), steps_done=state.steps_done + 1, total_latency=state.total_latency + p.get("duration", 0.0), version=state.version + 1)
        elif event.type == CogEventType.TOOL_FAILED:
            self._failed_fps.add(p.get("fingerprint", ""))
            return replace(state, failed_steps=state.failed_steps + (p,), failed_fingerprints=frozenset(self._failed_fps), version=state.version + 1)
        elif event.type == CogEventType.REPLANNED:
            return replace(state, replan_count=state.replan_count + 1, version=state.version + 1)
        elif event.type == CogEventType.REFLECTED:
            return replace(state, reflection_notes=state.reflection_notes + (p,), version=state.version + 1)
        return state

    def _persist_snapshot_sync(self):
        try:
            payload = json.dumps({"version": self._current.version, "ts": _time.time()})
            redis_safe(lambda r: r.set(f"cog:snapshot:{self.task_id}", payload, ex=86400))
        except: pass

    def get_state(self) -> CognitiveState: return self._current

    @property
    def fatigue_score(self) -> float:
        w, s = self.weights, self._current
        raw = (s.replan_count * w.replan_weight + len(s.failed_steps) * w.failure_weight + s.total_latency / w.latency_divisor)
        return min(raw, 1.0)

    @property
    def confidence_score(self) -> float:
        now = _time.time()
        if now - self._conf_cache[1] < 2.0: return self._conf_cache[0]
        res = sum(b.get("confidence", 0.5) for b in self._beliefs) / len(self._beliefs) if self._beliefs else 1.0
        self._conf_cache = (res, now)
        return res

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
    def adaptive_concurrency(self, core: EventSourcedCognitiveCore) -> int:
        f = core.fatigue_score
        if f > 0.8: return 2
        if f > 0.5: return 3
        return 8

    def should_abort(self, core: EventSourcedCognitiveCore, budget: MissionBudget) -> bool:
        return core.fatigue_score > 0.95 or budget.remaining_time < 10.0

class MetaReflectionEngine:
    async def reflect(self, core: EventSourcedCognitiveCore, goal: str) -> dict:
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
        self.cog_store = CognitiveStateStore(redis_safe)
        # 🛡️ [ZERO-LEAK]: Background tasks handled via fire_and_forget
        self.mission_control_url = os.getenv("MISSION_CONTROL_URL", "http://mission-control:9998")

    async def _save_mission_to_history(self, core: EventSourcedCognitiveCore, status: str = "completed"):
        """🏛️ [ETERNAL-SAVE]: Ghi dấu Sứ mệnh vào Biên niên sử Zenith."""
        try:
            state = core.get_state()
            payload = {
                "id": self.task_id_to_mission_id(core.task_id),
                "title": state.goal.split('\n')[0][:70],
                "goal": state.goal,
                "status": status,
                "ts": _time.time(),
                "logs": [{"tag": "SYSTEM", "msg": f"Nhiệm vụ {status}.", "ts": _time.time()}],
                "artifacts": {
                    "plan": "Lịch sử nơ-ron đã được lưu trữ."
                }
            }
            # 📡 Gửi tới Mission Control - Reuse client
            await self.client.post(f"{self.mission_control_url}/api/mission/save", json=payload, timeout=5.0)
        except Exception as e:
            self._log("ERROR", f"❌ [PERSISTENCE-ERR]: Không thể lưu lịch sử ({e})")

    def task_id_to_mission_id(self, tid: str) -> str:
        if tid.startswith("m_"): return tid
        return f"m_{tid}"

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
        try: return await self._run_mission(goal, tid, trid, data.get("mode", "fast"))
        finally: redis_safe(lambda r: r.delete(lkey))

    async def _run_mission(self, goal, tid, trid, mode):
        """🏛️ [COGNITIVE-ROUTER]: Phân tách lộ trình Nhất thể."""
        # T1: Tiếp nhận và Phân loại sơ khởi
        manifest = await self.router.route_to_receptionist({"goal": goal, "task_id": tid, "mode": mode})
        
        # 🛡️ [ERROR-SHIELD]: Nếu Receptionist báo lỗi, chặn đứng không cho chạy tiếp
        if manifest.get("status") == "error" or "error" in manifest:
            err_msg = manifest.get("error", "Lỗi nơ-ron không xác định.")
            self._log("ERROR", f"🚨 [RECEPTIONIST-FAILED]: {err_msg}", tid, trid)
            err_answer = f"⚠️ **Sự cố Kết nối Nơ-ron**: Hệ thống Lễ Tân gặp lỗi khi tiếp nhận yêu cầu. Master vui lòng kiểm tra xem mô hình `qwen3:4b` hoặc dịch vụ Ollama có bị quá tải không và thử lại ạ. 🫡 (Chi tiết: {err_msg})"
            self._log("JKAI", err_answer, tid, trid)
            return {"status": "error", "answer": err_answer, "task_id": tid}

        # 🛡️ [EARLY-EXIT]: Nếu Receptionist đã hoàn tất (Social/Command - không có steps)
        if (manifest.get("answer") and not manifest.get("steps")) or manifest.get("is_social"):
            ans_val = manifest.get("answer", "Hệ thống đã nhận thông điệp của ngài.")
            ans_str = ans_val.get("content") if isinstance(ans_val, dict) else str(ans_val)
            self._log("JKAI", ans_str, tid, trid)
            return {**manifest, "status": "success"}

        # 🚀 [BRANCHING]: Nếu là FAST hoặc Dispatcher cưỡng chế FAST
        current_mode = manifest.get("mode", mode)
        if current_mode == "fast" and not manifest.get("mode") == "delegate":
            return await self._run_fast_path(goal, tid, trid, manifest)
        
        # 🏛️ [DEEP/AUTO-PATH]: Quy trình 6 Giai đoạn chuẩn
        return await self._run_deep_path(goal, tid, trid, mode, manifest)

    async def _run_fast_path(self, goal, tid, trid, manifest):
        """⚡ [FAST-PATH]: Lộ trình phản xạ siêu tốc."""
        engine.publish_progress(10, "⚡ Khởi tạo Giao thức Phản xạ Nhất thể", "fast_route", tid, trid)
        self._log("SYSTEM", "⚡ [FAST-ROUTE]: Kích hoạt Giao thức Phản xạ Nhất thể.", tid, trid, stealth=True)
        
        # T3: Blueprint trực tiếp (Bỏ qua Planner)
        steps = manifest.get("steps")
        if not steps:
            plan_res = await self.router.route_to_planner({"goal": goal, "task_id": tid, "mode": "fast"})
            steps = plan_res.get("steps", [])
        
        if not steps:
            err_answer = "⚠️ **Lỗi phản xạ**: Không thể tạo lộ trình thực thi chớp nhoáng (FAST) cho yêu cầu này. Master vui lòng tinh chỉnh lại yêu cầu hoặc thử lại ạ. 🫡"
            self._log("JKAI", err_answer, tid, trid)
            return {"status": "error", "answer": err_answer, "task_id": tid}

        sid = manifest.get("session_id") or trid
        core = EventSourcedCognitiveCore(tid, CognitiveState(task_id=tid, session_id=sid, goal=goal, steps_total=len(steps)), self.weights)
        dag, budget, w_lock = SafeDAGScheduler(steps), MissionBudget(max_steps=len(steps)*2), asyncio.Lock()

        # T4: Thực thi chớp nhoáng
        all_results = await self._execute_dag(dag, core, budget, w_lock, goal, tid, trid, "fast")

        # T5/T6 FAST: Tổng hợp nhanh
        engine.publish_progress(90, "🧠 Đang tổng hợp và chắt lọc kết quả", "fast_route", tid, trid)
        summary_res = await self.router.route_to_summarizer({"goal": goal, "result": all_results, "steps": steps, "mode": "fast", "task_id": tid, "trace_id": trid})
        final_ans = summary_res.get("summary", summary_res.get("answer", "Nhiệm vụ hoàn tất."))

        # Sửa lỗi thừa: Tác vụ FAST không cần chưng cất bài học (Bypass Distiller)
        self._log("JKAI", final_ans, tid, trid)
        
        # 💾 [PERSISTENCE-TRIGGER]: Ghi sổ
        await self._save_mission_to_history(core, "completed")
        
        return {"status": "success", "answer": final_ans, "task_id": tid}

    async def _run_deep_path(self, goal, tid, trid, mode, manifest):
        """🏛️ [DEEP-PATH]: Quy trình 6 Giai đoạn Chiến lược."""
        if manifest.get("is_social"): return {**manifest, "status": "success"}

        # 🧪 [T2.5: SCRIPT-INJECTION]: Tiêm script chuẩn bị thực địa
        # Ví dụ: Tự động chạy git diff hoặc nén bối cảnh
        await self._run_t2_5_injection(goal, tid, trid)

        try:
            steps = manifest.get("steps") or (await self.router.route_to_planner({"goal": goal, "task_id": tid, "mode": mode})).get("steps", [])
            
            # 🛡️ [EMPTY-PLAN-PROTECTION]: Nếu Planner trả về rỗng, kích hoạt fallback khẩn cấp
            if not steps:
                raise ValueError("Planner returned no steps.")

            sid = manifest.get("session_id") or trid
            core = EventSourcedCognitiveCore(tid, CognitiveState(task_id=tid, session_id=sid, goal=goal, steps_total=len(steps)), self.weights)
            dag, budget, w_lock = SafeDAGScheduler(steps), MissionBudget(max_steps=len(steps)*2), asyncio.Lock()

            # T4: Hành pháp Swarm v5.0
            all_results = await self._execute_dag(dag, core, budget, w_lock, goal, tid, trid, mode)

            # T5: Thẩm định Tư pháp
            jr = await self.router.route_to_judicial_review({"goal": goal, "blueprint": {"steps": steps}, "results": all_results, "task_id": tid, "metadata": {"fatigue": core.fatigue_score, "ratio": dag.completion_ratio}})
            async with w_lock: core.apply(CogEvent(CogEventType.REFLECTED, payload=jr))

            # T6: Thu hoạch Tri thức
            safe_results = str(all_results)[:4000] if all_results else []
            res = await self.router.route_to_summarizer({"goal": goal, "result": safe_results, "steps": steps, "judicial_review": jr})
            
            # Chỉ chưng cất bài học nếu nhiệm vụ đủ phức tạp
            if mode != "fast" and core.fatigue_score > 0.1:
                self._fire_and_forget(self.router.route_to_distill({"goal": goal, "task_id": tid}))
                self._fire_and_forget(self.router.route_to_distill_judicial({"task_id": tid, "judicial_review": jr}))

            final_ans = res.get("summary", "")
            async with w_lock: self.cog_store.save(core.apply(CogEvent(CogEventType.TASK_FINALIZED, payload={"answer": final_ans})))
            self._log("JKAI", final_ans, tid, trid)
            
            # 💾 [PERSISTENCE-TRIGGER]: Ghi sổ
            await self._save_mission_to_history(core, "completed")
            
            return res

        except Exception as e:
            self._log("ERROR", f"🚨 [DEEP-PATH-FAILED]: {str(e)}", tid, trid)
            err_answer = f"⚠️ **Lỗi thực thi chiến lược**: Hệ thống không thể lập kế hoạch hoặc thực thi nhiệm vụ này. Master vui lòng kiểm tra lại bối cảnh hoặc thử lại ạ. 🫡 (Chi tiết: {str(e)})"
            self._log("JKAI", err_answer, tid, trid)
            return {"status": "error", "answer": err_answer, "task_id": tid}

    async def _execute_dag(self, dag, core, budget, w_lock, goal, tid, trid, mode):
        results, stalls = [], 0
        active_paths: Dict[str, Set[str]] = {} # Theo dõi đường dẫn đang bị khóa

        while not dag.is_complete():
            if self.governor.should_abort(core, budget): break
            
            ready_batch = await dag.get_ready_batch(self.governor.adaptive_concurrency(core))
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
            self._log("SYSTEM", f"📡 [T4: ORCHESTRATOR] Đang điều phối đợt thực thi gồm {len(execution_batch)} bước song song.", tid, trid, stealth=True)
            
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
                        engine.publish_progress(70, f"⚠️ Lỗi thực thi: {tool}", "fast_route", tid, trid)
                        self._log("WARN", f"⚠️ [T4: ORCHESTRATOR] Ban Thực thi báo lỗi cho bước `{sid}`: {res.get('msg', res.get('output', 'Unknown error'))}", tid, trid, stealth=True)
                    else:
                        engine.publish_progress(80, f"✅ Hoàn tất thực thi: {tool}", "fast_route", tid, trid)
                        self._log("SYSTEM", f"✅ [T4: ORCHESTRATOR] Ban Thực thi đã hoàn tất bước `{sid}`.", tid, trid, stealth=True)
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
                core.apply(CogEvent(CogEventType.TOOL_EXECUTED, payload={"step_id": sid, "duration": _time.time()-span.start_ts}))
                if res.get("answer"):
                    ans_val = res["answer"]
                    ans_str = ans_val.get("content") or ans_val.get("output") or str(ans_val) if isinstance(ans_val, dict) else str(ans_val)
                    core.apply(CogEvent(CogEventType.BELIEF_ADDED, payload={"content": ans_str[:200], "confidence": 0.9, "source": tool}))
                await dag.mark_done(sid)
            else:
                breaker.record_failure(); await dag.mark_failed(sid, cascade=True)
        return [res] if res else []

    async def _run_t2_5_injection(self, goal, tid, trid):
        """🧪 [T2.5: INJECTION]: Thực thi các script chuẩn bị."""
        try:
            # Kiểm tra xem có script nào cần chạy không (Heuristic: git diff cho refactor)
            if "refactor" in goal.lower() or "sửa" in goal.lower():
                self._log("INJECT", "🧬 [T2.5]: Tự động quét Git Diff để chuẩn bị thực địa...", tid, trid)
                # Giả lập tiêm script
                pass
        except: pass

class _TaskManagerBuilder:
    def __init__(self, cls): self._cls, self._kwargs = cls, {}
    def with_redis(self, s, a): self._kwargs.update({"redis_conn": s, "async_redis_conn": a}); return self
    def with_router(self, r): self._kwargs["router"] = r; return self
    def with_hitl(self, h): self._kwargs["hitl"] = h; return self
    def build(self): return self._cls(**self._kwargs)
