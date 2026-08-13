"""
core/os/cognition/escl/requirement_compiler.py
E0 — Semantic Requirement Compiler.

Compiles canonical goal text into structured SemanticRequirement objects
and initializes the SemanticContinuityLedger.
"""

from __future__ import annotations
import re
from typing import List
from core.os.cognition.escl.contracts import (
    RequirementCategory,
    SemanticRequirement,
)
from core.os.cognition.escl.continuity_ledger import SemanticContinuityLedger


class SemanticRequirementCompiler:
    """Compiles raw user intent into formal semantic requirements."""

    def compile(self, goal_text: str, mission_id: str = "default") -> SemanticContinuityLedger:
        ledger = SemanticContinuityLedger(mission_id=mission_id, canonical_goal_text=goal_text)
        g_low = goal_text.lower()

        # 1. Format Detection
        if any(k in g_low for k in ["excel", "xlsx", "bảng tính", "sheet"]):
            ledger.add_requirement(
                RequirementCategory.ARTIFACT_FORMAT, "Định dạng bảng tính Excel XLSX", ".xlsx", is_mandatory=True
            )
        elif any(k in g_low for k in ["word", "docx", "văn bản", "hợp đồng", "biên bản"]):
            ledger.add_requirement(
                RequirementCategory.ARTIFACT_FORMAT, "Định dạng tài liệu Word DOCX", ".docx", is_mandatory=True
            )
        elif any(k in g_low for k in ["pdf"]):
            ledger.add_requirement(
                RequirementCategory.ARTIFACT_FORMAT, "Định dạng tài liệu PDF", ".pdf", is_mandatory=True
            )

        # 2. Entity Count Detection (e.g. "5 người", "10 nhân viên", "12 tháng")
        count_match = re.search(r"\b(\d+)\s*(?:người|nhân sự|nhân viên|chuyên viên|tháng|phòng|mục|task)\b", g_low)
        if count_match:
            count = int(count_match.group(1))
            ledger.add_requirement(
                RequirementCategory.ENTITY_COUNT, f"Dữ liệu quản lý cho {count} đối tượng", count, is_mandatory=True
            )

        # 3. Visualization / Chart Detection
        if any(k in g_low for k in ["biểu đồ", "bieu do", "chart", "đồ thị", "visual"]):
            ledger.add_requirement(
                RequirementCategory.VISUALIZATION, "Có biểu đồ trực quan (Bar/Line/Pie Chart)", True, is_mandatory=True
            )

        # 4. Formula & Computation Detection
        if any(k in g_low for k in ["tiến độ", "tien do", "công thức", "tổng", "kpi", "tính toán", "phần trăm"]):
            ledger.add_requirement(
                RequirementCategory.FORMULA, "Tự động tính toán công thức tiến độ/KPI", True, is_mandatory=True
            )

        # 5. Styling Detection
        if any(k in g_low for k in ["văn phòng", "van phong", "chuyên nghiệp", "executive", "đẹp"]):
            ledger.add_requirement(
                RequirementCategory.STYLING, "Phong cách định dạng văn phòng Executive chuyên nghiệp", True, is_mandatory=False
            )

        return ledger


requirement_compiler = SemanticRequirementCompiler()
