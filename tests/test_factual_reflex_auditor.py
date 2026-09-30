# -*- coding: utf-8 -*-
"""
Regression test for Red Team finding 27/09 (Master log 21:58):
"hôm nay là thứ mấy" answered "Chào Master, ngày hôm nay Chủ nhật."
was wrongly marked PARTIALLY_FULFILLED (DATE_ANCHOR + COVERAGE).
Master standard: greeting + correct weekday == FULFILLED, no length/coverage gate.
"""
from datetime import datetime

from core.os.cognition.goal_contract import goal_contract_compiler
from core.os.cognition.epistemic_auditor import epistemic_auditor, AuditVerdict


VI_DAYS = ["thứ hai", "thứ ba", "thứ tư", "thứ năm", "thứ sáu", "thứ bảy", "chủ nhật"]


def _today_vi():
    return VI_DAYS[datetime.now().weekday()]


class TestFactualReflexWeekday:
    def test_perfect_answer_per_master_standard_is_fulfilled(self):
        goal = "hôm nay là thứ mấy"
        contract = goal_contract_compiler.compile(goal)
        response = f"Chào Master, ngày hôm nay là {_today_vi()}."
        report = epistemic_auditor.audit(response, contract)
        assert report.verdict == AuditVerdict.FULFILLED
        assert report.missing_criteria == []

    def test_actual_live_log_answer_is_fulfilled(self):
        goal = "hôm nay là thứ mấy"
        contract = goal_contract_compiler.compile(goal)
        response = f"Chào Master, ngày hôm nay {_today_vi()}."
        report = epistemic_auditor.audit(response, contract)
        assert report.verdict == AuditVerdict.FULFILLED

    def test_wrong_weekday_is_not_fulfilled(self):
        goal = "hôm nay là thứ mấy"
        contract = goal_contract_compiler.compile(goal)
        wrong = [d for d in VI_DAYS if d != _today_vi()][0]
        report = epistemic_auditor.audit(f"Hôm nay là {wrong}.", contract)
        assert report.verdict != AuditVerdict.FULFILLED

    def test_heavy_scope_questions_unaffected(self):
        # World-news questions must still go through full criteria, not factual shortcut
        contract = goal_contract_compiler.compile("Tình hình thế giới hôm nay có gì mới?")
        assert "WORLD_EVENT_COVERAGE" in contract.success_criteria
        report = epistemic_auditor.audit("Chào Master, ngày hôm nay Chủ nhật.", contract)
        assert report.verdict != AuditVerdict.FULFILLED or "WORLD_EVENT_COVERAGE" in report.satisfied_criteria
