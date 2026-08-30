# -*- coding: utf-8 -*-
"""
Unit test suite cho DynamicParameterTuner (Trụ cột 1)
"""

import pytest
from core.adaptive.parameter_tuner import DynamicParameterTuner, AdaptiveConfigProfile


class TestParameterTuner:
    """Kiểm tra chức năng ghi nhận feedback và tự động tối ưu hóa tham số thích ứng."""

    @pytest.fixture(autouse=True)
    def reset_tuner(self):
        tuner = DynamicParameterTuner()
        tuner.profile = AdaptiveConfigProfile()
        tuner.feedback_history.clear()

    def test_record_feedback_and_auto_tune(self):
        tuner = DynamicParameterTuner()
        initial_threshold = tuner.profile.dual_draft_coverage_threshold

        # Giả lập 5 phản hồi thành công liên tiếp (100% success)
        for i in range(5):
            tuner.record_feedback(
                task_id=f"t_{i}",
                is_successful=True,
                task_type="deep_plan",
                user_rating=5.0
            )

        # Ngưỡng coverage phải tự động hạ nhẹ để tăng tỷ lệ early-exit
        assert tuner.profile.dual_draft_coverage_threshold <= initial_threshold
        assert tuner.profile.tuning_iterations >= 1
        assert tuner.profile.feedback_samples_count == 5

    def test_low_success_rate_increases_rigor(self):
        tuner = DynamicParameterTuner()
        # Giả lập 5 phản hồi thất bại (0% success)
        for i in range(5):
            tuner.record_feedback(
                task_id=f"t_fail_{i}",
                is_successful=False,
                task_type="deep_plan"
            )

        # Ngưỡng coverage và top_k phải tự động tăng để yêu cầu độ khắt khe cao hơn
        assert tuner.profile.dual_draft_coverage_threshold >= 0.70
        assert tuner.profile.rag_top_k >= 5
