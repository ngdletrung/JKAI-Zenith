# -*- coding: utf-8 -*-
"""
JKAI AI OS — Cloud Discuss Handler.
Intercepts explicit discussion commands from Master and executes
the multi-agent dialectic debate via CloudDiscussOrchestrator.
Zero System 1 / LLMs involved in gating. Non-invasive pass-through for all other tasks.
"""

from __future__ import annotations

import asyncio
import logging

from core.os.orchestrator.handlers.base import BaseHandler
from core.os.orchestrator.types import (
    OSRequestPlan,
    OrchestratorContext,
    HandlerResult,
    log_telemetry,
)
from core.security.trigger_parser import TriggerParser
from core.security.egress_gate import (
    authorize_discuss_mission,
    revoke_discuss_mission,
)
from core.os.cognition.cloud_discuss_orchestrator import CloudDiscussOrchestrator

logger = logging.getLogger("jkai.os.orchestrator.cloud_discuss")


class CloudDiscussHandler(BaseHandler):
    """
    Handler điều phối phiên thảo luận Hội đồng AI (JKAI Discuss Protocol v1.0).
    Chỉ kích hoạt khi câu lệnh của Master chứa yêu cầu thảo luận tường minh
    và nguồn gọi được xác thực là trực tiếp từ Master.
    """

    def __init__(self, name: str = "CloudDiscuss"):
        super().__init__(name)
        self.parser = TriggerParser()
        self.orchestrator = CloudDiscussOrchestrator()

    async def process(self, plan: OSRequestPlan, ctx: OrchestratorContext) -> HandlerResult:
        goal = plan.goal or ""
        # Fail-closed default: caller must explicitly specify a trusted Master source
        source = str(ctx.kwargs.get("source") or "unverified_source").strip()

        # Secondary injection guard: reject if enriched with external skill/web/file markers
        if "<ZENITH_SKILL_ACTIVATED>" in goal or "[WEB-CONTENT]" in goal:
            source = "injected_context"

        # 1. Kiểm tra bộ lọc lệnh xác định (Deterministic Trigger Gate)
        trigger_res = self.parser.parse(goal, source=source)
        if not trigger_res.allowed:
            return HandlerResult(early_exit=False)

        mission_id = ctx.task_id or "mission_discuss"

        # 2. Lệnh hợp lệ -> Ghi nhận telemetry thông báo cho Master
        log_telemetry(
            plan,
            "ZENITH",
            f"🏛️ [CLOUD-DISCUSS]: Kích hoạt Hội đồng Thảo luận AI (Models: {', '.join(trigger_res.models)}).",
        )

        # 3. Cấp quyền theo đúng phạm vi mission_id (không chạm biến môi trường toàn cục)
        # và chạy trên worker thread để không khóa event loop Uvicorn
        authorize_discuss_mission(mission_id)
        try:
            briefing = await asyncio.to_thread(
                self.orchestrator.execute_session,
                user_command=goal,
                source=source,
                mission_id=mission_id,
                allow_cloud=True,
                simulate=bool(ctx.kwargs.get("simulate", False)),
            )

            report_markdown = briefing.render_markdown_report()

            plan.early_response = {
                "answer": report_markdown,
                "task_id": ctx.task_id,
                "pipeline": "discuss",
                "mode": "discuss",
                "status": briefing.status,
                "is_simulated": briefing.is_simulated,
                "cached": False,
            }
            return HandlerResult(early_exit=True)

        except Exception as e:
            logger.error("Lỗi khi thực thi CloudDiscussHandler: %s", e)
            log_telemetry(
                plan,
                "ZENITH",
                f"⚠️ [CLOUD-DISCUSS-ERROR]: Phiên thảo luận gặp lỗi: {e}. Chuyển tiếp an toàn.",
            )
            return HandlerResult(early_exit=False)
        finally:
            revoke_discuss_mission(mission_id)
