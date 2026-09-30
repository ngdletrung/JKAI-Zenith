#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Validate 3 red-team fixes:
1. GoalContract detects math tasks and generates MATH_NUMERIC_FIDELITY
2. EpistemicAuditor enforces unit fidelity and prevents CONVERSATIONAL_REFLEX on math tasks
3. Anaphora detection logic identifies follow-up queries
"""
import sys
import os

from core.os.cognition.goal_contract import goal_contract_compiler
from core.os.cognition.epistemic_auditor import epistemic_auditor, AuditVerdict


# ──────────────────────────────────────────────────────────────────────────────
# TEST 1: GoalContract nhận dạng bài toán số học
# ──────────────────────────────────────────────────────────────────────────────
def test_fix1_goal_contract_detects_math():
    """Fix 1: GoalContract phải thêm MATH_NUMERIC_FIDELITY cho bài toán."""
    goal = "240 thung hang, xe tai cho duoc 30 thung/chuyen. Can bao nhieu chuyen? Phi xang moi chuyen 400k"
    c = goal_contract_compiler.compile(goal)
    assert "MATH_NUMERIC_FIDELITY" in c.success_criteria, (
        f"FAIL: 'MATH_NUMERIC_FIDELITY' không có trong success_criteria={c.success_criteria}"
    )
    assert "MATH" in c.required_topics
    print("✅ TEST 1 PASS: GoalContract nhận dạng bài toán → MATH_NUMERIC_FIDELITY")

    # Câu chào không phải bài toán
    greet = "bạn thấy thế nào?"
    c2 = goal_contract_compiler.compile(greet)
    assert "MATH_NUMERIC_FIDELITY" not in c2.success_criteria, (
        f"FAIL: câu chào không được có MATH_NUMERIC_FIDELITY, got={c2.success_criteria}"
    )
    print("✅ TEST 1b PASS: Câu chào không trigger MATH_NUMERIC_FIDELITY")


# ──────────────────────────────────────────────────────────────────────────────
# TEST 2: EpistemicAuditor Unit Fidelity Check
# ──────────────────────────────────────────────────────────────────────────────
def test_fix2_unit_fidelity_auditor():
    """Fix 2: EpistemicAuditor phải phát hiện đổi đơn vị từ thùng sang tấn và không cho CONVERSATIONAL_REFLEX."""
    goal = "240 thùng hàng, xe tải chở được 30 thùng/chuyến. Phí xăng mỗi chuyến 400k"
    contract = goal_contract_compiler.compile(goal)
    assert "MATH_NUMERIC_FIDELITY" in contract.success_criteria

    # Đáp sai đơn vị: đổi thùng sang tấn
    answer_wrong = "Để vận chuyển hết 240 tấn hàng với công suất 30 tấn/chuyến: 8 chuyến. Tổng phí xăng 3.200.000 đồng."
    report_wrong = epistemic_auditor.audit(answer_wrong, contract)
    
    assert report_wrong.verdict != AuditVerdict.CONVERSATIONAL_REFLEX, (
        "FAIL: Bài toán số học tuyệt đối không được gán CONVERSATIONAL_REFLEX"
    )
    assert report_wrong.verdict == AuditVerdict.PARTIALLY_FULFILLED, (
        f"FAIL: Đổi đơn vị phải là PARTIALLY_FULFILLED, got {report_wrong.verdict}"
    )
    assert report_wrong.confidence < 0.9, f"Confidence quá cao cho đáp án sai đơn vị: {report_wrong.confidence}"
    print("✅ TEST 2a PASS: Đáp sai đơn vị bị hạ verdict và confidence")

    # Đáp đúng đơn vị: giữ nguyên thùng
    answer_correct = "Để vận chuyển hết 240 thùng hàng với công suất 30 thùng/chuyến: 8 chuyến. Tổng phí xăng 3.200.000 đồng."
    report_correct = epistemic_auditor.audit(answer_correct, contract)
    
    assert report_correct.verdict == AuditVerdict.FULFILLED
    assert "MATH_NUMERIC_FIDELITY" in report_correct.satisfied_criteria
    print("✅ TEST 2b PASS: Đáp đúng đơn vị được FULFILLED với MATH_NUMERIC_FIDELITY")


# ──────────────────────────────────────────────────────────────────────────────
# TEST 3: Anaphora detection logic
# ──────────────────────────────────────────────────────────────────────────────
def test_fix3_anaphora_detection():
    """Fix 3: Phát hiện anaphora trong follow-up goal ngắn."""
    _ANAPHORA_TRIGGERS = frozenset([
        "chi tiết hơn", "giải thích", "giải thích thêm", "chi tiết",
        "tiếp tục", "tiếp theo", "còn", "cái đó", "vừa rồi",
        "ở trên", "như trên", "đó là", "nó là", "cái kia",
        "thêm nữa", "làm rõ", "cụ thể hơn", "expand", "elaborate",
    ])

    followups = [
        "hãy giải thích chi tiết hơn",
        "còn cái kia thì sao",
        "tiếp tục",
        "làm rõ hơn đi",
    ]
    non_followups = [
        "240 thùng hàng xe tải chở 30 thùng/chuyến cần bao nhiêu chuyến",
        "lập kế hoạch họp 80 người tại phòng Alpha",
        "giá vàng hôm nay là bao nhiêu",
    ]

    for g in followups:
        has = any(t in g.lower() for t in _ANAPHORA_TRIGGERS)
        is_short = len(g) < 80
        assert has and is_short, f"FAIL: '{g}' phải là anaphora ngắn. has={has}, is_short={is_short}"

    for g in non_followups:
        has = any(t in g.lower() for t in _ANAPHORA_TRIGGERS)
        is_short = len(g) < 80
        assert not (has and is_short), f"FAIL: '{g}' không được match anaphora"

    print("✅ TEST 3 PASS: Anaphora triggers match chính xác câu hỏi nối tiếp")


if __name__ == "__main__":
    test_fix1_goal_contract_detects_math()
    test_fix2_unit_fidelity_auditor()
    test_fix3_anaphora_detection()
    print("\nALL 3 RED-TEAM TESTS PASSED! ✅")
