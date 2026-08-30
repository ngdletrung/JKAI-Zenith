"""
JKAI AI OS — Request Orchestrator
Một điểm vào duy nhất: Phân loại ý định, làm giàu goal, chọn pipeline, gắn ràng buộc.
Kiến trúc Pipeline / Chain of Responsibility Pattern hướng module hóa, tốc độ cao.
"""

from __future__ import annotations

import time
import logging
from typing import Any, List, Optional

from core.os.orchestrator.types import OSRequestPlan, OrchestratorContext, log_telemetry
from core.os.orchestrator.handlers import get_default_pipeline_handlers
from core.utils.engine import engine

logger = logging.getLogger("jkai.os.orchestrator")

# Backward-compatible alias
_log = log_telemetry


async def orchestrate_request(
    goal: str,
    task_id: str = "system",
    history: Optional[List] = None,
    *,
    check_reflex: bool = True,
    container: Any = None,
    **kwargs,
) -> OSRequestPlan:
    """
    Chuẩn bị mọi yêu cầu Master trước khi Receptionist / TaskManager thực thi.
    Điểm vào duy nhất chạy qua chuỗi Pipeline Handlers tối ưu.
    """
    t0 = time.perf_counter()
    engine._increment_stat("total")

    plan = OSRequestPlan(goal=(goal or "").strip())
    ctx = OrchestratorContext(
        task_id=task_id,
        history=history,
        check_reflex=check_reflex,
        container=container,
        kwargs=dict(kwargs or {}),
        start_time=t0,
        trace_id=kwargs.get("trace_id") or task_id
    )

    handlers = get_default_pipeline_handlers()
    for handler in handlers:
        result = await handler.execute(plan, ctx)
        if result.early_exit:
            logger.info("[ORCHESTRATOR-EARLY-EXIT] %s kích hoạt phản xạ sớm trong %.2fms", handler.name, (time.perf_counter() - t0) * 1000)
            return plan

    total_lat_ms = round((time.perf_counter() - t0) * 1000, 2)
    logger.info("[ORCHESTRATOR-COMPLETE] Task '%s' qua toàn bộ 8 handlers trong %.2fms (Pipeline: %s)", task_id, total_lat_ms, plan.pipeline)
    return plan


__all__ = [
    "orchestrate_request",
    "OSRequestPlan",
    "OrchestratorContext",
    "log_telemetry",
    "_log"
]
