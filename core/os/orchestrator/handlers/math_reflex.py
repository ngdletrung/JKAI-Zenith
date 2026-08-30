"""
JKAI AI OS — Math Reflex Handler
T-0: Zero-Latency Math Reflex (<1ms) xử lý các phép tính toán học trực tiếp từ Ingress.
"""

from __future__ import annotations

import re
from core.os.orchestrator.handlers.base import BaseHandler
from core.os.orchestrator.types import OSRequestPlan, OrchestratorContext, HandlerResult, log_telemetry
from core.os.routing.intent_router import CentralIntentRouter


class MathReflexHandler(BaseHandler):
    """Xử lý phản xạ toán học siêu tốc dưới 1ms."""

    _IGNORE_WORDS = [
        'tại sao', 'vì sao', 'giải mã', 'kiến trúc', 'code', 'hàm', 'script', 'lỗi', 'python', 'javascript',
        'nội dung', 'bài tập', 'nghỉ lễ', 'lễ', 'thông báo', 'soạn', 'tạo file', 'word', 'docx', 'excel', 'xlsx', 'pdf'
    ]

    async def process(self, plan: OSRequestPlan, ctx: OrchestratorContext) -> HandlerResult:
        g = plan.goal
        g_low = g.lower().strip()

        # Bỏ qua nếu có chứa từ khóa code/văn bản
        if any(kw in g_low for kw in self._IGNORE_WORDS):
            return HandlerResult(early_exit=False)

        # Bỏ qua nếu là chuỗi ngày tháng (VD: 2/9, 30/4/2026)
        is_real_date = bool(
            re.search(r'(?:ngày\s+)?\b\d{1,2}\/\d{1,2}(?:\/\d{2,4})?\b', g_low)
            or re.search(r'ngày\s+\d{1,2}\/\d{1,2}\b', g_low)
        )
        if is_real_date:
            return HandlerResult(early_exit=False)

        math_val = CentralIntentRouter.evaluate_math(g)
        if math_val:
            log_telemetry(plan, "ZENITH", "⚡ [MATH-REFLEX]: Phản xạ tính toán dưới 1ms từ Ingress Root.")
            plan.pipeline = "fast"
            plan.execution_mode = "fast"
            plan.is_fast = True
            plan.is_deep = False
            plan.early_response = {
                "answer": (
                    f"**[MATH-REFLEX (<1ms)]**\n\n"
                    f"{math_val}\n\n"
                    f"*Xử lý qua cổng phản xạ toán học ở chế độ FAST trên JKAI Zenith OS.*"
                ),
                "task_id": ctx.task_id,
                "cached": True,
                "pipeline": "fast",
                "mode": "fast"
            }
            return HandlerResult(early_exit=True)

        return HandlerResult(early_exit=False)
