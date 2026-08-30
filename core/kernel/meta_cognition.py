# -*- coding: utf-8 -*-
"""
🧠 [META-COGNITION ENGINE & CONFIDENCE CALIBRATION v1.0]
File: core/kernel/meta_cognition.py

Hệ Thống Siêu Nhận Thức & Tự Vấn (Trụ Cột 12):
  1. Pre-Response Self-Questioning: Tự vấn về độ đầy đủ của dữ liệu và góc nhìn phản biện.
  2. Confidence Calibration: Đo lường mức độ tự tin thực tế (0.0 - 1.0).
  3. Uncertainty Disclaimer & Clarification: Chủ động nêu rõ giới hạn khi confidence < 0.70.
  4. Post-Hoc Reflection Journal: Tự ngẫm ngầm sau mỗi task để hoàn thiện chính mình.
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("JKAI.MetaCognition")


@dataclass
class MetaCognitiveAssessment:
    has_sufficient_data: bool
    confidence_score: float  # 0.0 -> 1.0
    epistemic_uncertainty: float  # 0.0 -> 1.0 (Độ bất định tri thức)
    missing_aspects: List[str] = field(default_factory=list)
    criticism_angle: str = ""
    clarification_questions: List[str] = field(default_factory=list)
    is_calibrated: bool = True


@dataclass
class ReflectionEntry:
    task_id: str
    strengths: List[str]
    weaknesses: List[str]
    lessons_learned: List[str]
    timestamp: float = field(default_factory=time.time)


class MetaCognitionEngine:
    """
    🧠 Động Cơ Siêu Nhận Thức & Tự Hoàn Thiện
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
        self.reflection_journal: List[ReflectionEntry] = []

    def assess_response_confidence(
        self,
        goal: str,
        kb_context: str,
        generated_answer: str
    ) -> MetaCognitiveAssessment:
        """
        Thực hiện chu trình tự vấn (Self-Questioning) và tính điểm tin cậy đã hiệu chuẩn.
        """
        # 1. Đo lường độ phủ ngữ cảnh tri thức
        has_context = bool(kb_context and len(kb_context.strip()) > 30)
        has_math_or_code = any(k in generated_answer.lower() for k in ["```", "kết quả:", "đáp án", "phép tính"])
        
        # 2. Tính điểm tự tin (Confidence Calibration)
        base_confidence = 0.85 if has_math_or_code else (0.80 if has_context else 0.65)
        
        missing = []
        clarifications = []
        criticism = ""

        if not has_context and not has_math_or_code:
            missing.append("Thiếu tài liệu tham chiếu thực tế từ Knowledge Base.")
            clarifications.append("Master có thể cung cấp thêm ngữ cảnh hoặc tài liệu cụ thể hơn không ạ?")
            criticism = "Câu trả lời dựa trên suy luận thuần túy của mô hình, có thể chưa bao quát đủ các trường hợp ngoại lệ."
            base_confidence = 0.60

        uncertainty = round(1.0 - base_confidence, 2)

        return MetaCognitiveAssessment(
            has_sufficient_data=base_confidence >= 0.70,
            confidence_score=round(base_confidence, 2),
            epistemic_uncertainty=uncertainty,
            missing_aspects=missing,
            criticism_angle=criticism,
            clarification_questions=clarifications
        )

    def record_post_hoc_reflection(
        self,
        task_id: str,
        strengths: Optional[List[str]] = None,
        weaknesses: Optional[List[str]] = None,
        lessons: Optional[List[str]] = None
    ) -> ReflectionEntry:
        """
        Ghi nhận bài học tự suy ngẫm vào nhật ký ngầm.
        """
        entry = ReflectionEntry(
            task_id=task_id,
            strengths=strengths or ["Phản xạ nhanh", "Đúng định dạng"],
            weaknesses=weaknesses or [],
            lessons_learned=lessons or ["Duy trì kỷ luật kiến trúc"]
        )
        self.reflection_journal.append(entry)
        logger.info(f"🧠 [META-REFLECTION]: Recorded self-improvement reflection for task '{task_id}'.")
        return entry


meta_cognition = MetaCognitionEngine()
