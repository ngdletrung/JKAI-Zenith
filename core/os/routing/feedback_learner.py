# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — RECURSIVE INTENT FEEDBACK LEARNER v1.0          ║
║   Học Tự Động Từ Phản Hồi Sửa Lỗi Của Master & Tinh Chỉnh Ý Định ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Vòng Phản Hồi Ý Định Tự Tiến Hóa. 🧬🏛️⚡*
"""

from __future__ import annotations
import os
import re
import time
import json
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional, Tuple, Set

from core.os.routing.active_learner import active_learner
from core.kernel.decision_ledger import decision_ledger

logger = logging.getLogger("JKAI.FeedbackLearner")


@dataclass
class IntentCorrection:
    correction_id: str
    goal: str
    original_intent: str
    corrected_intent: str
    corrected_tags: List[str] = field(default_factory=list)
    reason: str = ""
    timestamp: float = field(default_factory=time.time)


class RecursiveIntentFeedbackLearner:
    """
    🧬 Bộ Học Phản Hồi Ý Định Đệ Quy (Recursive Intent Feedback Learner)
    - Thu thập phản hồi sửa đổi intent trực tiếp từ Master.
    - Phân tích từ khóa khác biệt và tự động cập nhật vào YAML Lexicons qua ActiveLearner.
    - Ghi nhận audit trail bất biến vào DecisionLedger.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.corrections_history: List[IntentCorrection] = []

    def record_correction(
        self,
        goal: str,
        original_intent: str,
        corrected_intent: str,
        corrected_tags: Optional[List[str]] = None,
        reason: str = "Master explicit correction"
    ) -> IntentCorrection:
        """
        Ghi nhận một phản hồi sửa lỗi từ Master và kích hoạt quy trình tự học.
        """
        import uuid
        correction_id = f"corr_{uuid.uuid4().hex[:12]}"
        tags = corrected_tags or [corrected_intent]
        
        correction = IntentCorrection(
            correction_id=correction_id,
            goal=goal,
            original_intent=original_intent,
            corrected_intent=corrected_intent,
            corrected_tags=tags,
            reason=reason,
            timestamp=time.time()
        )
        self.corrections_history.append(correction)

        # 1. Trích xuất n-gram và cập nhật vào ActiveLearner
        target_mode = corrected_intent.lower()
        if target_mode in {"office", "coding", "realtime", "reasoning", "internal", "social"}:
            active_learner.record_query(goal, target_mode.upper(), 1.0, tags)
            # Học ngay tức thì (immediate reinforce)
            words = [w for w in re.findall(r"\b\w{2,}\b", goal.lower()) if len(w) > 2]
            for w in words:
                active_learner.append_keyword_to_lexicon(target_mode, w)

        # 2. Ghi nhận vào DecisionLedger để truy vết
        decision_ledger.record_decision(
            decision_type="RECURSIVE_INTENT_FEEDBACK",
            task_id=correction_id,
            input_summary=f"Goal: {goal} (Old: {original_intent})",
            output_decision=f"Corrected: {corrected_intent} (Tags: {tags})",
            reason=reason,
            metadata={"correction_id": correction_id, "goal": goal}
        )

        logger.info(f"[FEEDBACK-LEARNER]: Đã học phản hồi sửa lỗi '{original_intent}' -> '{corrected_intent}' cho goal: '{goal}'.")
        return correction

    def get_corrections_count(self) -> int:
        return len(self.corrections_history)


feedback_learner = RecursiveIntentFeedbackLearner()
