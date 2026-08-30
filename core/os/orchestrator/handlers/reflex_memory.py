"""
JKAI AI OS — Reflex Memory Handler
T-0.3: Tra cứu bộ nhớ phản xạ nơ-ron từ Cognitive Memory.
"""

from __future__ import annotations

import logging
from core.os.orchestrator.handlers.base import BaseHandler
from core.os.orchestrator.types import OSRequestPlan, OrchestratorContext, HandlerResult, log_telemetry

logger = logging.getLogger("jkai.os.orchestrator.reflex")


class ReflexMemoryHandler(BaseHandler):
    """Tra cứu bộ nhớ phản xạ nhanh từ Redis/Qdrant."""

    async def process(self, plan: OSRequestPlan, ctx: OrchestratorContext) -> HandlerResult:
        if not ctx.check_reflex:
            return HandlerResult(early_exit=False)

        try:
            from core.utils.cognitive_memory import cognitive_memory
            reflex = await cognitive_memory.check_reflex(plan.goal, ctx.task_id)
            if reflex and reflex.get("answer"):
                log_telemetry(plan, "ZENITH", "⚡ [REFLEX-MEMORY]: Phản xạ nơ-ron — trả lời từ bộ nhớ chung.")
                plan.early_response = {
                    "answer": reflex["answer"],
                    "task_id": ctx.task_id,
                    "cached": True,
                    "pipeline": "fast",
                    "mode": "fast"
                }
                return HandlerResult(early_exit=True)
        except Exception as e:
            logger.debug("[REFLEX-LOOKUP-SKIP] %s", e)

        return HandlerResult(early_exit=False)
