"""
core/os/cognition/knowledge_fabric/knowledge_need_planner.py
Knowledge Need Planner — Pre-Retrieval Epistemic Need Formulation.

Transforms retrieval from Question -> Blind Search into:
Mission -> Knowledge Need Compiler -> Required Evidence Types -> Source Strategy -> EASG -> Retrieval.
"""

from __future__ import annotations
import datetime
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec


class KnowledgeDomain(str, Enum):
    INTERNAL_REGULATION = "INTERNAL_REGULATION"   # Quy chế nội bộ
    INTERNAL_ACCOUNT = "INTERNAL_ACCOUNT"         # Thông tin tài khoản / bảo mật
    OFFICIAL_DOCS = "OFFICIAL_DOCS"               # Tài liệu chính thức (Microsoft, Python, GCP)
    LEGAL_STATUTE = "LEGAL_STATUTE"               # Văn bản pháp luật chính thức
    TECHNICAL_BENCHMARK = "TECHNICAL_BENCHMARK"   # Báo cáo kỹ thuật / release note mới
    COMMUNITY_DISCUSSION = "COMMUNITY_DISCUSSION" # Diễn đàn / ý kiến cộng đồng
    BRAINSTORM_CREATIVE = "BRAINSTORM_CREATIVE"   # Sáng tạo / tri thức nội tại LLM


@dataclass
class KnowledgeNeed:
    """Explicit declaration of what information is needed, why, and what to ignore."""
    mission_id: str
    target_domain: KnowledgeDomain
    required_topics: List[str]
    prohibited_noise: List[str]                   # e.g. ["generic blog", "unverified SEO spam"]
    temporal_validity_year: int = field(default_factory=lambda: datetime.datetime.now().year)
    requires_internal_authority: bool = False
    requires_external_official: bool = False


class KnowledgeNeedPlanner:
    """Compiles structured KnowledgeNeeds from Canonical Missions."""

    def plan_needs(self, mission: CanonicalMissionSpec) -> KnowledgeNeed:
        goal_lower = mission.raw_goal.lower()
        
        # 1. Internal HR / Company Regulation
        if any(kw in goal_lower for kw in ["quy chế", "nghỉ phép", "nội bộ", "phòng ban", "lương", "thưởng", "quy trình"]):
            return KnowledgeNeed(
                mission_id=mission.mission_id,
                target_domain=KnowledgeDomain.INTERNAL_REGULATION,
                required_topics=["Current internal department regulation", "Approval hierarchy", "Valid policies"],
                prohibited_noise=["Generic Internet HR blogs", "Foreign company policies"],
                requires_internal_authority=True,
                requires_external_official=False
            )

        # 2. Official Technical / API Documentation
        if any(kw in goal_lower for kw in ["api", "microsoft", "python", "docker", "fastapi", "linux", "git", "openpyxl"]):
            return KnowledgeNeed(
                mission_id=mission.mission_id,
                target_domain=KnowledgeDomain.OFFICIAL_DOCS,
                required_topics=["Official API specifications", "Current package release"],
                prohibited_noise=["Outdated tutorials from prior major versions", "Unverified forums"],
                requires_internal_authority=False,
                requires_external_official=True
            )

        # 3. Legal / Statute
        if any(kw in goal_lower for kw in ["luật", "nghị định", "thông tư", "pháp luật", "thuế"]):
            return KnowledgeNeed(
                mission_id=mission.mission_id,
                target_domain=KnowledgeDomain.LEGAL_STATUTE,
                required_topics=["Official gazette publication", "Current effective statute"],
                prohibited_noise=["Informal legal forum summaries"],
                requires_internal_authority=False,
                requires_external_official=True
            )

        # Default: General Technical / Modern Knowledge
        return KnowledgeNeed(
            mission_id=mission.mission_id,
            target_domain=KnowledgeDomain.TECHNICAL_BENCHMARK,
            required_topics=["Current accurate facts", "Operational requirements"],
            prohibited_noise=["SEO farm articles"],
            requires_internal_authority=False,
            requires_external_official=False
        )


knowledge_need_planner = KnowledgeNeedPlanner()
