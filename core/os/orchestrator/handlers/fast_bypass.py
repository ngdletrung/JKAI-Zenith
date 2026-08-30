"""
JKAI AI OS — Fast Bypass Handler
T-0.4: Fast-Path Bypass cho các câu chào hỏi / đàm thoại xã giao cực ngắn.
Tích hợp kiểm tra Anaphora qua EntityResolver để tránh bypass nhầm câu hỏi ngữ cảnh.
"""

from __future__ import annotations

from core.os.orchestrator.handlers.base import BaseHandler
from core.os.orchestrator.types import OSRequestPlan, OrchestratorContext, HandlerResult, log_telemetry
from core.os.mission_state import MissionState
from core.os.execution_plan import ExecutionPlan, ExecutionPlanStep
from core.utils.engine import engine

_BYPASS_WHITELIST: frozenset = frozenset([
    "xin chào", "chào", "hello", "hi", "ok", "yes", "2+2", "tạm biệt", "bye", "cảm ơn", "thanks",
    "bạn có thể lập trình không", "bạn có thể lập trình không ?", "bạn có biết lập trình không",
    "bạn có biết lập trình không ?", "can you code", "can you program"
])

_ANAPHORA_WORDS: frozenset = frozenset([
    "nó", "đó", "cái đó", "như trên", "ở trên", "vừa rồi", "trước đó", "còn lại", "tiếp tục", "tiếp theo"
])


class FastBypassHandler(BaseHandler):
    """Bỏ qua 14 tầng phân tích cho câu hỏi đàm thoại xã giao cơ bản."""

    async def process(self, plan: OSRequestPlan, ctx: OrchestratorContext) -> HandlerResult:
        g_clean = plan.goal.lower().strip()
        
        # 1. Kiểm tra nếu nằm trong Whitelist
        if g_clean not in _BYPASS_WHITELIST:
            return HandlerResult(early_exit=False)

        # 2. Kiểm tra Anaphora (tham chiếu lịch sử hội thoại)
        has_history = ctx.history and len(ctx.history) > 1
        has_anaphora = any(w in g_clean.split() for w in _ANAPHORA_WORDS)

        # Nếu có lịch sử và có từ chỉ định tham chiếu -> Không được bypass
        if has_history and has_anaphora:
            return HandlerResult(early_exit=False)

        # 3. Kích hoạt Fast Path Bypass
        plan.pipeline = "fast"
        plan.execution_mode = "fast"
        plan.is_fast = True
        plan.is_deep = False
        plan.os_intent = "social"

        plan.mission_state = MissionState(
            goal=plan.goal,
            original_goal=plan.goal,
            task_id=ctx.task_id,
            os_intent="social",
            pipeline="fast",
            execution_mode="fast",
            is_fast=True,
            is_deep=False,
            trace_id=ctx.trace_id
        )
        plan.mission_state.execution_plan = ExecutionPlan(
            selected_pipeline="fast",
            estimated_cost=1.0,
            steps=[ExecutionPlanStep(step_id="S1_FAST_REACTIVE", description="Phản xạ nhanh bypass", assigned_agent="general")]
        )
        engine._increment_stat("bypass")
        log_telemetry(plan, "ZENITH", "⚡ [FAST-PATH-BYPASS]: Câu hỏi đơn giản. Bỏ qua 14 tầng phân tích Router.")
        return HandlerResult(early_exit=True)
