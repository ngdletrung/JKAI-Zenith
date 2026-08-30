"""
JKAI AI OS — Request Orchestrator (Facade Shim)
Cửa ngõ tương thích ngược 100% cho Ingress Gateway.
Chuyển tiếp trực tiếp sang kiến trúc module hóa: `core.os.orchestrator`.
"""

from __future__ import annotations

from core.os.orchestrator import (
    orchestrate_request,
    OSRequestPlan,
    OrchestratorContext,
    log_telemetry,
    _log,
)
from core.os.orchestrator.handlers.fast_bypass import _BYPASS_WHITELIST

__all__ = [
    "orchestrate_request",
    "OSRequestPlan",
    "OrchestratorContext",
    "log_telemetry",
    "_log",
    "_BYPASS_WHITELIST",
]
