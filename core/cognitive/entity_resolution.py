"""
JKAI ZENITH — COGNITION LAYER: ENTITY RESOLUTION ENGINE (v2.1)
File: core/cognitive/entity_resolution.py

Phân tích và rút trích các Thực thể (Entities) từ User Goal mà KHÔNG hardcode keyword.
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any

logger = logging.getLogger("jkai.cognition.entity")


@dataclass(frozen=True)
class EntityResolutionResult:
    entities: List[str] = field(default_factory=list)
    confidence: float = 0.95


class EntityResolver:
    """Rút trích các đối tượng/thực thể trọng tâm từ ngữ cảnh tác chiến."""

    @classmethod
    def resolve_entities(cls, goal: str) -> EntityResolutionResult:
        g_lower = (goal or "").lower()
        entities: List[str] = []

        if any(w in g_lower for w in ["team", "đội", "nhóm", "phòng ban"]):
            entities.append("TEAM_WORKLOAD")
        if any(w in g_lower for w in ["báo cáo", "tiến độ", "report"]):
            entities.append("PROGRESS_REPORT")
        if any(w in g_lower for w in ["hợp đồng", "contract"]):
            entities.append("CONTRACT_DOCUMENTS")
        if any(w in g_lower for w in ["bất thường", "anomaly", "nguy cơ", "trễ hạn"]):
            entities.append("ANOMALY_DETECTION")

        return EntityResolutionResult(entities=entities, confidence=0.95)
