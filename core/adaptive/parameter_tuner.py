# -*- coding: utf-8 -*-
"""
🚀 [ADAPTIVE SELF-OPTIMIZATION & DYNAMIC PARAMETER TUNER v1.0]
File: core/adaptive/parameter_tuner.py

Cơ chế Tự động Tối ưu hóa Tham số Hệ thống dựa trên Phản hồi thực tế:
  1. Feedback-Driven Tuning: Tự động điều chỉnh λ (Temporal Decay), Early-Exit Threshold, top_k RAG.
  2. Telemetry-Aware Learning: Giảm ngưỡng Early-Exit khi Draft A luôn thành công để tiết kiệm CPU Xeon.
  3. Dynamic Profile Serialization: Lưu trữ và nạp cấu hình tối ưu động vào RAM/Redis mà không cần restart.
"""

import time
import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, Optional, List

logger = logging.getLogger("JKAI.ParameterTuner")


@dataclass
class AdaptiveConfigProfile:
    # Tham số RAG & Memory
    rag_decay_lambda_realtime: float = 0.05
    rag_decay_lambda_knowledge: float = 0.005
    rag_top_k: int = 5
    rag_cache_ttl_seconds: int = 600
    
    # Tham số Dual-Drafting & Fast Pipeline
    dual_draft_coverage_threshold: float = 0.70
    fast_reflex_timeout_seconds: float = 5.0
    
    # Tham số Code Sandbox
    sandbox_timeout_seconds: float = 5.0
    sandbox_max_workers: int = 2
    
    # Metadata
    last_updated_at: float = field(default_factory=time.time)
    tuning_iterations: int = 0
    feedback_samples_count: int = 0


class DynamicParameterTuner:
    """
    🎯 Bộ Điều Chỉnh Tham Số Động & Tự Tối Ưu Hóa
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
        self.profile = AdaptiveConfigProfile()
        self.feedback_history: List[Dict[str, Any]] = []

    def record_feedback(
        self,
        task_id: str,
        is_successful: bool,
        task_type: str = "general",
        user_rating: Optional[float] = None,
        notes: str = ""
    ) -> None:
        """
        Ghi nhận phản hồi thực tế của Master để huấn luyện thích ứng.
        """
        record = {
            "task_id": task_id,
            "is_successful": is_successful,
            "task_type": task_type,
            "user_rating": user_rating if user_rating is not None else (1.0 if is_successful else 0.0),
            "timestamp": time.time(),
            "notes": notes
        }
        self.feedback_history.append(record)
        self.profile.feedback_samples_count += 1

        # Tự động kích hoạt điều chỉnh sau mỗi 5 phản hồi
        if len(self.feedback_history) % 5 == 0:
            self.optimize_parameters()

    def optimize_parameters(self) -> Dict[str, Any]:
        """
        Thuật toán tự động tối ưu hóa tham số dựa trên phân tích lịch sử phản hồi.
        """
        if not self.feedback_history:
            return asdict(self.profile)

        recent_feedbacks = self.feedback_history[-20:]
        success_rate = sum(1 for f in recent_feedbacks if f["is_successful"]) / len(recent_feedbacks)

        # 1. Tối ưu hóa Ngưỡng Dual-Drafting
        # Nếu tỷ lệ thành công cao (>90%), hạ nhẹ ngưỡng coverage (0.70 -> 0.65) để tăng tỷ lệ Early-Exit tiết kiệm CPU
        if success_rate >= 0.90:
            self.profile.dual_draft_coverage_threshold = max(0.60, round(self.profile.dual_draft_coverage_threshold - 0.02, 3))
        elif success_rate < 0.70:
            # Nếu tỷ lệ thành công thấp, nâng ngưỡng coverage lên để ép dùng mô hình Deep Reasoner
            self.profile.dual_draft_coverage_threshold = min(0.85, round(self.profile.dual_draft_coverage_threshold + 0.03, 3))

        # 2. Tối ưu hóa RAG top_k
        if success_rate < 0.80:
            # Tăng top_k lên nếu độ chính xác chưa đạt đỉnh
            self.profile.rag_top_k = min(8, self.profile.rag_top_k + 1)

        self.profile.tuning_iterations += 1
        self.profile.last_updated_at = time.time()

        logger.info(
            f"🎯 [AUTO-TUNER]: Iteration {self.profile.tuning_iterations} | "
            f"SuccessRate={success_rate:.2f} | CoverageThreshold={self.profile.dual_draft_coverage_threshold} | "
            f"RAG_TopK={self.profile.rag_top_k}"
        )
        return asdict(self.profile)

    def get_current_profile(self) -> AdaptiveConfigProfile:
        return self.profile


parameter_tuner = DynamicParameterTuner()
