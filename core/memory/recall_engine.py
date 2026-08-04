"""
JKAI ZENITH — MEMORY PACKAGE: RECALL ENGINE (v2.1)
File: core/memory/recall_engine.py

Truy xuất trải nghiệm quá khứ (Recall) trước khi thực thi để nâng cao hiệu suất (Attempts 2 -> 1).
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List, Optional

from core.memory.experience_store import ExperienceStore

logger = logging.getLogger("jkai.memory.recall")


class RecallEngine:
    """Bộ Truy Xuất Trải Nghiệm (Recall Engine)."""

    @classmethod
    def recall_prior_experience(cls, task_signature: str) -> Dict[str, Any]:
        """
        Truy xuất bài học và chiến lược ưu tiên từ Engram v2.
        """
        negative_lessons = ExperienceStore.get_negative_lessons(task_signature)
        best_strategy = ExperienceStore.get_successful_strategy(task_signature)

        logger.info(f"🔮 [ENGRAM-RECALL]: Recalled for signature='{task_signature}' -> BestStrategy={best_strategy}, NegativeLessons={len(negative_lessons)}")
        return {
            "best_strategy": best_strategy,
            "negative_lessons": negative_lessons,
            "has_prior_knowledge": best_strategy is not None or len(negative_lessons) > 0
        }
