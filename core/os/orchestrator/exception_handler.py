"""
JKAI AI OS — Orchestrator Exception Handler
Phân loại và xử lý tập trung mọi lỗi phát sinh trong Ingress Pipeline.
"""

from __future__ import annotations

import logging
from enum import Enum
from typing import Any, Optional

from core.os.orchestrator.types import OSRequestPlan, log_telemetry

logger = logging.getLogger("jkai.os.orchestrator.exceptions")


class ErrorSeverity(str, Enum):
    FATAL = "FATAL"           # Lỗi nghiêm trọng khiến không thể tiếp tục, trả về early_response lỗi
    TRANSIENT = "TRANSIENT"   # Lỗi mạng/timeout tạm thời, fallback sang chế độ an toàn
    IGNORABLE = "IGNORABLE"   # Lỗi nhỏ ở bước phụ (enrichment), ghi log và tiếp tục


class OrchestratorExceptionHandler:
    """Bộ xử lý lỗi tập trung của Ingress Gateway."""

    @staticmethod
    def classify(exc: Exception) -> ErrorSeverity:
        """Phân loại mức độ nghiêm trọng của exception."""
        if isinstance(exc, (KeyboardInterrupt, SystemExit, MemoryError)):
            return ErrorSeverity.FATAL
        if isinstance(exc, (TimeoutError, ConnectionError)):
            return ErrorSeverity.TRANSIENT
        return ErrorSeverity.IGNORABLE

    @classmethod
    def handle(
        cls,
        handler_name: str,
        exc: Exception,
        plan: OSRequestPlan,
        task_id: str = "sys"
    ) -> Optional[ErrorSeverity]:
        """Xử lý ngoại lệ phát sinh từ handler."""
        severity = cls.classify(exc)
        logger.warning("[ORCHESTRATOR-HANDLER-ERR] [%s] (%s): %s", handler_name, severity.value, exc)
        
        if severity == ErrorSeverity.FATAL:
            log_telemetry(plan, "ERROR", f"[FATAL-ERR in {handler_name}]: {exc}")
            plan.early_response = {
                "status": "error",
                "error": f"Lỗi hệ thống nghiêm trọng tại cửa ngõ: {exc}",
                "task_id": task_id,
                "pipeline": "fast",
                "mode": "fast"
            }
        elif severity == ErrorSeverity.TRANSIENT:
            log_telemetry(plan, "WARN", f"[TRANSIENT-ERR in {handler_name}]: Fallback an toàn kích hoạt.")
        else:
            log_telemetry(plan, "TRACE", f"[{handler_name}]: {exc}", stealth=True)

        return severity
