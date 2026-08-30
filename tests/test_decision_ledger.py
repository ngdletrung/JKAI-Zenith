# -*- coding: utf-8 -*-
"""
Unit test suite cho ImmutableDecisionLedger
"""

import pytest
from core.kernel.decision_ledger import (
    ImmutableDecisionLedger, decision_ledger, DecisionEntry
)


class TestDecisionLedger:
    """Kiểm tra tính bất biến và toàn vẹn của chuỗi Hash-Chain Decision Ledger."""

    @pytest.fixture(autouse=True)
    def reset_ledger(self):
        decision_ledger.ledger.clear()
        decision_ledger._last_hash = "0" * 64

    def test_record_decision_creates_valid_hash_chain(self):
        e1 = decision_ledger.record_decision(
            decision_type="ROUTING",
            task_id="task_001",
            input_summary="tạo bảng lương",
            output_decision="OFFICE",
            reason="Nhận diện từ khóa excel và bảng lương"
        )
        assert e1.prev_hash == "0" * 64
        assert len(e1.entry_hash) == 64

        e2 = decision_ledger.record_decision(
            decision_type="POLICY",
            task_id="task_001",
            input_summary="ghi file bang_luong.xlsx",
            output_decision="ALLOW",
            reason="Thao tác trong thư mục outputs"
        )
        assert e2.prev_hash == e1.entry_hash

    def test_ledger_integrity_verification_pass(self):
        decision_ledger.record_decision("ROUTING", "task_01", "query 1", "CHAT", "reason 1")
        decision_ledger.record_decision("MODEL", "task_01", "select model", "qwen3.5:4b", "reason 2")
        decision_ledger.record_decision("VERIFY", "task_01", "check output", "PASSED", "reason 3")

        is_valid, bad_idx = decision_ledger.verify_integrity()
        assert is_valid is True
        assert bad_idx is None

    def test_ledger_integrity_mutation_detected(self):
        e1 = decision_ledger.record_decision("ROUTING", "task_02", "query 1", "CHAT", "reason 1")
        e2 = decision_ledger.record_decision("MODEL", "task_02", "select model", "qwen3.5:4b", "reason 2")

        # Cố tình can thiệp sửa đổi nội dung quá khứ
        e1.output_decision = "TAMPERED_DECISION"

        is_valid, bad_idx = decision_ledger.verify_integrity()
        assert is_valid is False
        assert bad_idx == 0

    def test_query_decisions_by_task_id(self):
        decision_ledger.record_decision("ROUTING", "task_A", "qA", "OFFICE", "rA")
        decision_ledger.record_decision("ROUTING", "task_B", "qB", "CODING", "rB")
        decision_ledger.record_decision("VERIFY", "task_A", "vA", "PASSED", "rA2")

        res_a = decision_ledger.query_decisions(task_id="task_A")
        assert len(res_a) == 2
        assert all(e.task_id == "task_A" for e in res_a)
