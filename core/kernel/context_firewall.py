# -*- coding: utf-8 -*-
"""
🏛️ CONTEXT FIREWALL POLICY ENFORCEMENT ENGINE (P0-1 & P0-2)
Bảo vệ tính toàn vẹn và cô lập ngữ cảnh giữa các Mission/Task trong hệ điều hành AI OS.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class ContextPolicy(str, Enum):
    ISOLATED = "ISOLATED"
    CONTINUOUS = "CONTINUOUS"


class SourceType(str, Enum):
    PREVIOUS_MISSION = "PREVIOUS_MISSION"
    USER_INPUT = "USER_INPUT"
    SYSTEM_MEMORY = "SYSTEM_MEMORY"
    TOOL_OUTPUT = "TOOL_OUTPUT"


class ActorType(str, Enum):
    MODEL = "MODEL"
    USER = "USER"
    SYSTEM = "SYSTEM"
    EXECUTOR = "EXECUTOR"


class DerivationType(str, Enum):
    DIRECT = "DIRECT"
    DERIVED = "DERIVED"
    SUMMARIZED = "SUMMARIZED"


class AdmissionDecision(str, Enum):
    ADMITTED = "ADMITTED"
    QUARANTINED = "QUARANTINED"
    DROPPED = "DROPPED"


@dataclass
class ContextFragment:
    content: str
    source: str
    source_type: SourceType = SourceType.USER_INPUT
    mission_id: str = "default"
    task_id: str = "default"
    actor: ActorType = ActorType.USER
    provenance: str = ""
    is_quarantined: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)


class ContextFirewall:
    """Tường lửa kiểm soát và cách ly ngữ cảnh."""

    def filter_and_admit(
        self,
        raw_fragments: List[ContextFragment],
        mission_policy: ContextPolicy = ContextPolicy.ISOLATED,
        current_mission_id: str = "default"
    ) -> Tuple[List[ContextFragment], List[ContextFragment]]:
        """
        Lọc và phân bổ ContextFragment thành: (admitted_fragments, quarantined_fragments)
        """
        admitted: List[ContextFragment] = []
        quarantined: List[ContextFragment] = []

        for frag in raw_fragments:
            if mission_policy == ContextPolicy.ISOLATED:
                # Nếu chính sách là ISOLATED, cách ly toàn bộ mảnh vỡ từ mission khác
                if frag.mission_id != current_mission_id and frag.source_type == SourceType.PREVIOUS_MISSION:
                    frag.is_quarantined = True
                    quarantined.append(frag)
                    continue
            
            admitted.append(frag)

        return admitted, quarantined


context_firewall = ContextFirewall()
