"""
JKAI ZENITH — MISSION LAYER: MISSION BUILDER (v2.1)
File: core/mission/mission_builder.py

Chuyển đổi CognitiveRequest thành MissionDefinition - Nguồn Sự Thật Duy Nhất (Single Source of Truth).
Không ai (Planner, LLM, Executor, Verifier) được tự ý sửa đổi objective gốc của Mission.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, Optional

from core.contracts.cognitive_contract import (
    CognitiveRequest,
    MissionDefinition,
    DeliverableSpec,
)

logger = logging.getLogger("jkai.mission.builder")


class MissionBuilder:
    """Bộ Xây Dựng Nhiệm Vụ Tác Chiến (Mission Builder)."""

    @classmethod
    def build_mission(cls, request: CognitiveRequest) -> MissionDefinition:
        """
        Chuyển đổi CognitiveRequest thành MissionDefinition bất biến.
        """
        mission = MissionDefinition(
            identity=request.identity,
            objective=request.goal,
            constraints=tuple(request.constraints),
            resources_required=tuple(request.entities),
            expected_output=request.deliverable,
            verification_criteria=tuple(request.success_criteria),
            authorization_scope=tuple(request.authority_required),
            risk_policy="STRICT_DENY_FIRST" if request.risk_level in ("HIGH", "CRITICAL") else "STANDARD"
        )
        logger.info(f"🚩 [MISSION-BUILDER]: Built Mission ID={mission.identity.mission_id}, Objective='{mission.objective[:40]}...'")
        return mission
