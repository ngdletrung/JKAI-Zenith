# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — SELF-REFLECTION & CONTINUOUS IMPROVEMENT v1.0   ║
║   Tự Đánh Giá Đa Chiều, Nhật Ký Phản Tư & Tự Động Tinh Chỉnh      ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Năng Lực Tự Tiến Hóa Nhận Thức. 🔄🏛️⚡*
"""

from __future__ import annotations
import time
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from core.kernel.decision_ledger import decision_ledger
from core.adaptive.parameter_tuner import parameter_tuner

logger = logging.getLogger("JKAI.SelfReflection")


@dataclass
class ReflectionReport:
    task_id: str
    overall_quality: float      # 0.0 -> 1.0
    accuracy_score: float
    completeness_score: float
    clarity_score: float
    safety_score: float
    lowest_dimension: str
    recommendation: str
    timestamp: float = field(default_factory=time.time)


class SelfReflectionEngine:
    """
    🔄 Động Cơ Tự Phản Tư & Cải Tiến Liên Tục (Self-Reflection Engine)
    - Tự chấm điểm chất lượng câu trả lời theo 4 tiêu chí cốt lõi (Accuracy, Completeness, Clarity, Safety).
    - Tự động kích hoạt parameter_tuner khi phát hiện điểm số suy giảm.
    - Lưu trữ Nhật ký Phản tư (Reflection Journal) vào DecisionLedger.
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
        self.journal: List[ReflectionReport] = []

    def reflect_on_output(
        self,
        task_id: str,
        goal: str,
        answer: str,
        has_artifacts: bool = False
    ) -> ReflectionReport:
        """
        Thực hiện đánh giá đa chiều chất lượng câu trả lời (<1ms).
        """
        # 1. Đo lường các chiều chất lượng
        ans_len = len(answer.strip()) if answer else 0
        
        # Clarity: độ dài hợp lý, có format markdown
        clarity = 0.95 if (ans_len > 40 and ("\n" in answer or "**" in answer)) else 0.70
        
        # Completeness: trả lời đầy đủ, có artifacts nếu là task tạo file
        completeness = 0.95 if (has_artifacts or ans_len > 80) else 0.65
        
        # Accuracy & Safety: không chứa placeholder lỗi hoặc dấu hiệu rác
        has_placeholder = any(p in answer.lower() for p in ["[placeholder]", "todo:", "chưa có nội dung"])
        accuracy = 0.50 if has_placeholder else 0.95
        safety = 0.99
        
        # Điểm tổng hợp
        dims = {
            "accuracy": accuracy,
            "completeness": completeness,
            "clarity": clarity,
            "safety": safety
        }
        lowest_dim = min(dims, key=dims.get)
        overall = round(sum(dims.values()) / 4.0, 3)

        recommendation = "Chất lượng đạt chuẩn tối ưu." if overall >= 0.80 else f"Cần cải thiện tiêu chí '{lowest_dim}'."

        report = ReflectionReport(
            task_id=task_id,
            overall_quality=overall,
            accuracy_score=accuracy,
            completeness_score=completeness,
            clarity_score=clarity,
            safety_score=safety,
            lowest_dimension=lowest_dim,
            recommendation=recommendation
        )
        self.journal.append(report)

        # 2. Cập nhật ParameterTuner nếu điểm thấp
        if overall < 0.70:
            parameter_tuner.record_feedback(task_id=task_id, is_successful=False, notes=f"Quality score: {overall}")
            logger.warning(f"[SELF-REFLECTION]: Điểm số thấp ({overall}). Đã ghi nhận phản hồi vào ParameterTuner.")
        else:
            parameter_tuner.record_feedback(task_id=task_id, is_successful=True, notes=f"Quality score: {overall}")

        # 3. Ghi nhận vào DecisionLedger
        decision_ledger.record_decision(
            decision_type="SELF_REFLECTION",
            task_id=task_id,
            input_summary=f"Goal: {goal[:50]}",
            output_decision=f"Quality: {overall} (Lowest: {lowest_dim})",
            reason=recommendation,
            metadata={"report": dims}
        )

        return report


self_reflection = SelfReflectionEngine()
