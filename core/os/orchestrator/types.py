"""
JKAI AI OS — Request Orchestrator Types
Định nghĩa cấu trúc dữ liệu, kết quả thực thi và context của Ingress Pipeline.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

from core.os.mission_state import MissionState

logger = logging.getLogger("jkai.os.orchestrator")


@dataclass
class OSRequestPlan:
    """Kế hoạch thực thi do AI OS kernel sinh ra."""

    goal: str
    pipeline: str = "fast"
    execution_mode: str = "fast"
    is_deep: bool = False
    is_fast: bool = True
    use_deep_full: bool = False
    use_cursor_agent: bool = False
    os_intent: str = "general"
    team_pattern: str = "pipeline"
    capability_tags: List[str] = field(default_factory=list)
    kwargs_patch: Dict[str, Any] = field(default_factory=dict)
    log_messages: List[Tuple[str, str, bool]] = field(default_factory=list)
    early_response: Optional[Dict[str, Any]] = None
    mission_state: Optional[MissionState] = None
    steps: List[Any] = field(default_factory=list)
    
    # Metadata mở rộng từ TaskProfiler & CentralIntentRouter v4.0
    task_profile: Optional[Any] = None
    execution_policy: Optional[Any] = None
    route_decision: Optional[Any] = None

    def merge_into_kwargs(self, kwargs: dict) -> dict:
        out = dict(kwargs or {})
        out.update(self.kwargs_patch)
        return out


@dataclass
class OrchestratorContext:
    """Context vận hành xuyên suốt qua các handler của pipeline."""

    task_id: str = "system"
    history: Optional[List[Dict[str, Any]]] = None
    check_reflex: bool = True
    container: Any = None
    kwargs: Dict[str, Any] = field(default_factory=dict)
    start_time: float = 0.0
    trace_id: str = "sys"


@dataclass
class HandlerResult:
    """Kết quả trả về của từng handler trong pipeline."""

    early_exit: bool = False
    error: Optional[str] = None


def log_telemetry(plan: OSRequestPlan, tag: str, msg: str, stealth: bool = False) -> None:
    """Ghi nhận log vào plan và xuất Machine Telemetry Log có cấu trúc."""
    plan.log_messages.append((tag, msg, stealth))
    try:
        import json, datetime
        telemetry_event = {
            "timestamp": datetime.datetime.now(datetime.timezone.utc).astimezone().isoformat(),
            "component": "ingress_orchestrator",
            "event": f"orchestration.{tag.lower()}",
            "goal": plan.goal,
            "pipeline": plan.pipeline,
            "os_intent": plan.os_intent,
            "stealth": stealth,
            "message": msg
        }
        logger.info(json.dumps(telemetry_event, ensure_ascii=False))
    except Exception:
        pass
