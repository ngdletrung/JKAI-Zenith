"""
JKAI ZENITH v3 — ADAPTIVE COGNITION LAYER: META-PLANNER (v3.0)
File: core/planning/meta_planner.py

Meta-Planner quyết định Chiến lược Lập kế hoạch (Planning Strategy Selection)
trước khi chuyển cho Cognitive Planner tạo TaskGraph DAG.
"""

from __future__ import annotations
import logging
from enum import Enum
from dataclasses import dataclass
from typing import List, Dict, Any

from core.contracts.cognitive_contract import CognitiveRequest

logger = logging.getLogger("jkai.planning.meta")


class PlanningStrategy(Enum):
    DIRECT_REFLEX = "DIRECT_REFLEX"              # Trả lời hoặc thực thi trực tiếp
    RESEARCH_FIRST = "RESEARCH_FIRST"            # Nghiên cứu / Tìm kiếm trước khi lập kế hoạch
    DECOMPOSE_DAG = "DECOMPOSE_DAG"              # Phân rã DAG đa nhiệm phức tạp
    PARALLEL_ISOLATED = "PARALLEL_ISOLATED"      # Tác chiến song song nhiều nhánh
    DEEP_REASONING = "DEEP_REASONING"            # Lập luận sâu nhiều bước
    HUMAN_APPROVAL_REQUIRED = "HUMAN_APPROVAL"  # Cần phê duyệt hành vi rủi ro cao


@dataclass(frozen=True)
class MetaPlanDecision:
    strategy: PlanningStrategy
    recommended_depth: int
    requires_world_model_lookup: bool
    rationale: str


class MetaPlanner:
    """Bộ Lập Chiến Lược Kế Hoạch (Meta-Planner)."""

    @classmethod
    def select_strategy(cls, request: CognitiveRequest) -> MetaPlanDecision:
        """
        Phân tích CognitiveRequest và chọn chiến lược lập kế hoạch tối ưu.
        """
        g_lower = request.goal.lower()

        # 1. Phê duyệt người dùng nếu rủi ro cao
        if request.risk_level in ("HIGH", "CRITICAL") or "xóa" in g_lower:
            return MetaPlanDecision(
                strategy=PlanningStrategy.HUMAN_APPROVAL_REQUIRED,
                recommended_depth=3,
                requires_world_model_lookup=True,
                rationale="High-risk objective requires human approval gate"
            )

        # 2. Nghiên cứu trước nếu thiếu thông tin
        if any(w in g_lower for w in ["tìm", "nghiên cứu", "khảo sát", "search", "lookup"]):
            return MetaPlanDecision(
                strategy=PlanningStrategy.RESEARCH_FIRST,
                recommended_depth=2,
                requires_world_model_lookup=True,
                rationale="Goal requires initial research & information gathering"
            )

        # 3. Phân rã DAG nếu tạo file / tác vụ đa bước
        if request.deliverable.format != "markdown" or len(g_lower) > 50:
            return MetaPlanDecision(
                strategy=PlanningStrategy.DECOMPOSE_DAG,
                recommended_depth=3,
                requires_world_model_lookup=True,
                rationale="Complex artifact deliverable requires DAG task graph decomposition"
            )

        # 4. Mặc định: Phản xạ trực tiếp
        return MetaPlanDecision(
            strategy=PlanningStrategy.DIRECT_REFLEX,
            recommended_depth=1,
            requires_world_model_lookup=False,
            rationale="Simple query resolved via direct cognitive reflex"
        )
