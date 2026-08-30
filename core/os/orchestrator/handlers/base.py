"""
JKAI AI OS — Base Handler Protocol
Interface cơ sở cho các bước xử lý trong Ingress Pipeline.
"""

from __future__ import annotations

import abc
import time
import logging
from typing import Any

from core.os.orchestrator.types import OSRequestPlan, OrchestratorContext, HandlerResult
from core.os.orchestrator.exception_handler import OrchestratorExceptionHandler

logger = logging.getLogger("jkai.os.orchestrator.handlers")


class BaseHandler(abc.ABC):
    """Interface trừu tượng cho một handler trong chuỗi xử lý Ingress."""

    def __init__(self, name: str = "") -> None:
        self.name = name or self.__class__.__name__

    async def execute(self, plan: OSRequestPlan, ctx: OrchestratorContext) -> HandlerResult:
        """Thực thi handler với đo lường observability và bảo vệ lỗi tập trung."""
        t0 = time.perf_counter()
        try:
            res = await self.process(plan, ctx)
            dur_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.debug("[HANDLER-METRIC] %s hoàn tất trong %.2fms (early_exit=%s)", self.name, dur_ms, res.early_exit)
            return res
        except Exception as e:
            dur_ms = round((time.perf_counter() - t0) * 1000, 2)
            logger.warning("[HANDLER-FAIL] %s thất bại sau %.2fms: %s", self.name, dur_ms, e)
            OrchestratorExceptionHandler.handle(self.name, e, plan, task_id=ctx.task_id)
            return HandlerResult(early_exit=plan.early_response is not None, error=str(e))

    @abc.abstractmethod
    async def process(self, plan: OSRequestPlan, ctx: OrchestratorContext) -> HandlerResult:
        """Hàm xử lý cụ thể của từng handler."""
        raise NotImplementedError
