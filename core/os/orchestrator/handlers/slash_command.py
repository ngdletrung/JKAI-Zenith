"""
JKAI AI OS — Slash Command Handler
T-0.1: Bắt và điều phối các lệnh tắt (/research, /code, /status, /help).
"""

from __future__ import annotations

from core.os.orchestrator.handlers.base import BaseHandler
from core.os.orchestrator.types import OSRequestPlan, OrchestratorContext, HandlerResult
from core.os.orchestrator.slash_registry import SlashCommandRegistry


class SlashCommandHandler(BaseHandler):
    """Xử lý lệnh tắt Slash Commands từ người dùng."""

    async def process(self, plan: OSRequestPlan, ctx: OrchestratorContext) -> HandlerResult:
        intercepted = SlashCommandRegistry.intercept(plan.goal, plan, ctx)
        if intercepted and plan.early_response is not None:
            return HandlerResult(early_exit=True)
        return HandlerResult(early_exit=False)
