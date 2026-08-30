# -*- coding: utf-8 -*-
"""
Unit test suite cho 5 Trụ Cột Tầng Nhận Thức & Tiến Hóa (Trụ Cột 12 -> 16)
"""

import pytest
from core.evolution.auto_patcher import auto_patcher
from core.kernel.meta_cognition import meta_cognition
from core.cognitive.emotional_intelligence import emotional_intelligence, MasterEmotionalState
from core.kernel.world_model import ScenarioSimulator, ProactiveTrendPredictor
from core.security.multi_user_manager import multi_user_manager, UserAccessLevel


class TestConsciousnessAndEvolutionPillars:
    """Kiểm tra độ chính xác của 5 Trụ Cột Tầng Nhận Thức & Tiến Hóa (12 -> 16)."""

    # ── TRỤ CỘT 14: GOVERNED SELF-EVOLVING CODEBASE ──
    def test_auto_patcher_diagnoses_traceback(self):
        tb_sample = (
            'Traceback (most recent call last):\n'
            '  File "core/utils/engine.py", line 45, in execute_task\n'
            '    result = 1 / 0\n'
            'ZeroDivisionError: division by zero'
        )
        report = auto_patcher.diagnose_traceback(tb_sample)
        assert report.target_file == "core/utils/engine.py"
        assert report.line_number == 45
        assert "ZeroDivisionError" in report.error_message

    def test_auto_patcher_governed_commit_requires_master(self):
        orig_code = "def calc(a, b):\n    return a / b\n"
        patched_code = "def calc(a, b):\n    if b == 0:\n        return 0\n    return a / b\n"
        patch = auto_patcher.create_candidate_patch("core/utils/calc.py", orig_code, patched_code)
        assert patch.syntax_valid is True

        # Từ chối commit nếu chưa có phê duyệt của Master
        unauth_res = auto_patcher.apply_governed_patch(patch.patch_id, is_master_approved=False)
        assert unauth_res["success"] is False

        # Thành công khi Master phê duyệt
        auth_res = auto_patcher.apply_governed_patch(patch.patch_id, is_master_approved=True)
        assert auth_res["success"] is True

    # ── TRỤ CỘT 12: META-COGNITION & CONFIDENCE CALIBRATION ──
    def test_meta_cognition_calibration_and_reflection(self):
        # Có dữ liệu tri thức và code -> Confidence cao
        assessment_high = meta_cognition.assess_response_confidence(
            goal="Tính tổng", kb_context="Dữ liệu tài chính tháng 8", generated_answer="Kết quả: 500 triệu"
        )
        assert assessment_high.confidence_score >= 0.80
        assert assessment_high.has_sufficient_data is True

        # Thiếu context -> Confidence thấp, có câu hỏi làm rõ
        assessment_low = meta_cognition.assess_response_confidence(
            goal="Hỏi chuyện phiếm", kb_context="", generated_answer="Tôi nghĩ là vậy."
        )
        assert assessment_low.confidence_score <= 0.70
        assert len(assessment_low.clarification_questions) >= 1

        # Ghi nhận suy ngẫm ngầm
        entry = meta_cognition.record_post_hoc_reflection("task_test_99")
        assert entry.task_id == "task_test_99"

    # ── TRỤ CỘT 15: EMOTIONAL & MOTIVATIONAL INTELLIGENCE ──
    def test_emotional_intelligence_tone_adaptation(self):
        # Phát hiện khi Master bực bội / hối thúc
        frustrated_res = emotional_intelligence.analyze_master_input("sao lại lỗi thế này, sửa nhanh lên")
        assert frustrated_res.detected_state == MasterEmotionalState.FRUSTRATED
        assert frustrated_res.recommended_tone == "CONCISE_ACTION_ORIENTED"

        # Phát hiện khi Master tò mò nghiên cứu
        curious_res = emotional_intelligence.analyze_master_input("Hãy phân tích sâu nguyên lý hoạt động của RRF")
        assert curious_res.detected_state == MasterEmotionalState.CURIOUS

    # ── TRỤ CỘT 13: PREDICTIVE WORLD MODEL & SCENARIO SIMULATOR ──
    def test_scenario_simulator_what_if_analysis(self):
        outcome = ScenarioSimulator.simulate_what_if("Nâng cấp thêm 32GB RAM và Xeon v4")
        assert outcome.predicted_state == "HIGH_PERFORMANCE"
        assert "cpu_throughput" in outcome.estimated_impact

        trend = ProactiveTrendPredictor.predict_proactive_offer(["nghiên cứu ai", "deep learning"])
        assert trend is not None
        assert "AI" in trend

    # ── TRỤ CỘT 16: MULTI-USER SOVEREIGNTY & FEDERATED IDENTITY ──
    def test_multi_user_access_control_and_isolation(self):
        # Master Root có toàn quyền
        assert multi_user_manager.verify_user_session_access("master_root", "session_100") is True

        # Mời cộng tác viên mới vào dự án 'Project_Alpha'
        collab_res = multi_user_manager.register_collaborator(
            user_id="dev_an",
            display_name="Kỹ sư An",
            project_id="Project_Alpha",
            invited_by="master_root"
        )
        assert collab_res["success"] is True
        assert collab_res["namespace"] == "ns_dev_an"

        # Người lạ không có quyền
        assert multi_user_manager.verify_user_session_access("stranger_99", "session_100") is False
