# -*- coding: utf-8 -*-
"""5 core tests for AnswerQualityVerifier (Red Team Q5)."""
from core.os.cognition.answer_quality_verifier import answer_quality_verifier


class TestAnswerQualityCore:
    def test_01_master_standard_answer_passes_all(self):
        text = "Chào Master, ngày hôm nay là Chủ nhật. Bạn cần tôi hỗ trợ gì thêm không?"
        r = answer_quality_verifier.verify(text, goal="hôm nay là thứ mấy")
        assert r.overall_passed is True
        assert r.overall_score == 1.0

    def test_02_internal_leak_fails_dung(self):
        text = "Chào Master, kết quả STAGE_4_1_DETERMINISTIC đã xong ở world_version mới."
        r = answer_quality_verifier.verify(text, goal="kiểm tra trạng thái")
        assert r.dung.passed is False
        assert r.overall_passed is False

    def test_03_direct_answer_passes_du(self):
        """Câu trả lời trực tiếp không cần greeting — AQV không được tự bổ sung."""
        text = ("Báo cáo phân tích của bạn đã hoàn thành đầy đủ với tất cả "
                "các chỉ số được tổng hợp chi tiết theo từng hạng mục yêu cầu.")
        r = answer_quality_verifier.verify(text, goal="báo cáo phân tích")
        # AQV không còn được phép force greeting — corrected_text phải là None
        assert r.corrected_text is None, (
            f"AQV không được tự thêm greeting. corrected_text={r.corrected_text!r}"
        )
        assert r.du.passed is True

    def test_04_verbose_off_goal_fails_trung(self):
        goal = "doanh thu quý 3 theo từng chi nhánh"
        text = ("Nói về thời tiết hôm nay thì trời trong xanh và có nắng nhẹ "
                "trên khắp các khu vực miền Trung với nhiệt độ ổn định " * 8)
        r = answer_quality_verifier.verify(text, goal=goal)
        assert r.trung.passed is False

    def test_05_unsourced_claim_fails_dung(self):
        text = "Chào Master, theo nghiên cứu thì phương pháp này hiệu quả vượt trội."
        r = answer_quality_verifier.verify(text, goal="đánh giá phương pháp")
        assert r.dung.passed is False
        assert r.needs_escalate is True
