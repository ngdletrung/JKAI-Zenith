"""
core/os/cognition/escl/canonical_mission.py
Cognitive Brain (WHAT?) — Canonical Mission Representation & Testable Success Criteria.

Transforms unstructured natural language requests into structured, machine-verifiable mission specifications.
"""

from __future__ import annotations
import hashlib
import re
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional


@dataclass
class SuccessCriterion:
    """Atomic verifiable condition for mission success."""
    criterion_id: str
    description: str
    target_attribute: str
    expected_value: Any
    is_mandatory: bool = True
    evaluated: bool = False
    passed: bool = False
    evidence: Optional[str] = None


@dataclass
class CanonicalMissionSpec:
    """
    Canonical Mission Representation (CMR).
    Complete structured breakdown of Master's intent.
    """
    mission_id: str
    raw_goal: str
    objective: str
    artifact_type: str # XLSX, DOCX, PDF, PY, JSON
    entity_count: Optional[int]
    purposes: List[str] = field(default_factory=list) # e.g. ["task_management", "progress_tracking"]
    presentation_style: str = "OFFICE_EXECUTIVE"
    chart_required: bool = False
    chart_types: List[str] = field(default_factory=list) # ["bar", "line", "pie"]
    formulas_required: bool = False
    success_criteria: List[SuccessCriterion] = field(default_factory=list)
    spec_hash: str = ""
    created_at: float = field(default_factory=time.time)

    def add_criterion(self, description: str, target_attr: str, expected_val: Any, is_mandatory: bool = True) -> SuccessCriterion:
        cid = f"CRIT-{len(self.success_criteria)+1:03d}"
        crit = SuccessCriterion(
            criterion_id=cid,
            description=description,
            target_attribute=target_attr,
            expected_value=expected_val,
            is_mandatory=is_mandatory
        )
        self.success_criteria.append(crit)
        return crit

    @classmethod
    def compile_from_text(cls, goal_text: str = "", mission_id: str = "m_default", **kwargs) -> CanonicalMissionSpec:
        """Parses natural language into Canonical Mission Spec."""
        if not goal_text and "goal" in kwargs:
            goal_text = kwargs["goal"]
        if not goal_text and "text" in kwargs:
            goal_text = kwargs["text"]
        g_low = (goal_text or "").lower()
        
        # 1. Artifact Type Detection
        artifact_type = "XLSX"
        if any(k in g_low for k in ["3d", "webgl", "unity", "unreal", "game"]):
            artifact_type = "3D_GAME_ENGINE"
        elif any(k in g_low for k in ["word", "docx", "văn bản", "biên bản"]):
            artifact_type = "DOCX"
        elif any(k in g_low for k in ["pdf"]):
            artifact_type = "PDF"
        elif any(k in g_low for k in ["python", "script", "code"]):
            artifact_type = "PY"

        # 2. Entity Count
        count_match = re.search(r"\b(\d+)\s*(?:người|nhân sự|nhân viên|tháng|mục)\b", g_low)
        entity_count = int(count_match.group(1)) if count_match else None

        # 3. Chart Requirements (handles both biểu đồ and biễu đồ)
        chart_required = any(k in g_low for k in ["biểu đồ", "biễu đồ", "bieu do", "chart", "đồ thị", "visual", "graph"])
        chart_types = ["bar"] if chart_required else []

        # 4. Formulas & Purpose
        formulas_required = any(k in g_low for k in ["tiến độ", "công thức", "tổng", "kpi", "tính toán"])
        
        purposes = []
        if any(k in g_low for k in ["3d", "webgl", "game", "unity"]):
            purposes.append("3d_webgl_game")
        if "công việc" in g_low or "task" in g_low:
            purposes.append("task_management")
        if "tiến độ" in g_low or "progress" in g_low:
            purposes.append("progress_tracking")
        if "doanh thu" in g_low or "tài chính" in g_low:
            purposes.append("financial_reporting")

        spec = cls(
            mission_id=mission_id,
            raw_goal=goal_text,
            objective=f"Generate {artifact_type} for {', '.join(purposes) or 'general purpose'}",
            artifact_type=artifact_type,
            entity_count=entity_count,
            purposes=purposes,
            presentation_style="OFFICE_EXECUTIVE",
            chart_required=chart_required,
            chart_types=chart_types,
            formulas_required=formulas_required
        )

        # 5. Populate Success Criteria
        spec.add_criterion(f"File exists with format {artifact_type}", "file_exists", True)
        if entity_count:
            spec.add_criterion(f"Data rows >= {entity_count} entities", "min_rows", entity_count)
        if formulas_required:
            spec.add_criterion("Dynamic formulas present (COUNTIF/AVERAGEIF/SUM)", "has_formulas", True)
        if chart_required:
            spec.add_criterion("Embedded visual chart present", "has_charts", True)

        spec.spec_hash = hashlib.sha256(f"{mission_id}:{goal_text}".encode()).hexdigest()[:16]
        return spec
