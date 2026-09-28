# -*- coding: utf-8 -*-
"""Tests for internal-vocabulary output gate (Red Team: live log 21:58 27/09)."""
from core.governance.internal_vocabulary import (
    find_internal_terms,
    gate_user_text,
)


class TestFindInternalTerms:
    def test_live_log_sentence_is_flagged(self):
        text = ("Hiện tại, tôi đang trong chế độ Rửa mặt và chào đón "
                "(tương ứng với trạng thái stage: ACTIVE của hệ thống). "
                "Kiểm tra tình hình: Xác nhận trạng thái thế giới (world_version).")
        hits = find_internal_terms(text)
        assert "world_version" in hits

    def test_stage_enum_is_flagged(self):
        assert find_internal_terms("kết quả STAGE_4_1_DETERMINISTIC xong") != []

    def test_trace_and_task_ids_flagged(self):
        hits = find_internal_terms("xem trace_abc123 trong mission ZENITH_2709-2158_d3a4ca")
        assert any("trace_abc123" in h for h in hits)
        assert any("ZENITH_2709" in h for h in hits)

    def test_clean_master_facing_text_passes(self):
        text = "Chào Master, ngày hôm nay là Chủ nhật. Bạn cần tôi hỗ trợ gì?"
        assert find_internal_terms(text) == []

    def test_role_words_not_flagged(self):
        # Vai trò/pipeline là từ Master vẫn đọc — cấm che nhầm.
        assert find_internal_terms("Receptionist đã nhận yêu cầu preflight xong") == []


class TestGateUserText:
    def test_clean_text_untouched(self):
        text = "Chào Master, ngày hôm nay là Chủ nhật."
        cleaned, hits = gate_user_text(text)
        assert cleaned == text
        assert hits == []

    def test_internal_term_redacted(self):
        cleaned, hits = gate_user_text("xác nhận world_version hiện tại")
        assert hits != []
        assert "world_version" not in cleaned.lower()
        assert "xác nhận" in cleaned  # phần lành giữ nguyên

    def test_empty_input(self):
        assert gate_user_text("") == ("", [])
