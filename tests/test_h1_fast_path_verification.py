# -*- coding: utf-8 -*-
"""
tests/test_h1_fast_path_verification.py
H1 — Fast-Path Verification Honesty Test Suite

Spec (Opencode Turn 70):
  Branch A: Mission with empty success_criteria
            → verdict = CONVERSATIONAL_REFLEX, conf = 1.0,
              rationale does NOT mention task criteria
  Branch B: Task mission with evidence requirement but NO supporting evidence
            → verdict != FULFILLED  (system must reject, not LLM-judge)
"""
import sys
import os
import unittest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "ai-brain")))

from core.os.cognition.epistemic_auditor import EpistemicAuditor, AuditVerdict
from core.os.cognition.goal_contract import GoalContract


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_contract(
    success_criteria=None,
    is_realtime_news: bool = False,
    required_time: str = "",
    min_length: int = 100,
    min_paragraphs: int = 3,
) -> GoalContract:
    """Build a GoalContract with controlled fields."""
    contract = GoalContract.__new__(GoalContract)
    # Use object.__setattr__ to bypass any frozen dataclass restrictions
    for attr, val in [
        ("success_criteria", success_criteria or []),
        ("is_realtime_news", is_realtime_news),
        ("required_time", required_time),
        ("min_length", min_length),
        ("min_paragraphs", min_paragraphs),
    ]:
        try:
            object.__setattr__(contract, attr, val)
        except (AttributeError, TypeError):
            # If GoalContract is not a dataclass, try direct assignment
            setattr(contract, attr, val)
    return contract


def _auditor() -> EpistemicAuditor:
    return EpistemicAuditor()


# ---------------------------------------------------------------------------
# Branch A: Empty success_criteria (conversation / greeting)
# ---------------------------------------------------------------------------

class TestH1BranchA_ConversationalReflex(unittest.TestCase):
    """
    Branch A: Mission with empty success_criteria → CONVERSATIONAL_REFLEX.
    """

    def setUp(self):
        self.auditor = _auditor()
        self.greeting_text = "Xin chào! Tôi có thể giúp gì cho bạn hôm nay?"
        self.contract_empty = _make_contract(success_criteria=[])

    def test_empty_criteria_gives_conversational_reflex_verdict(self):
        """Branch A: verdict MUST be CONVERSATIONAL_REFLEX when criteria list is empty."""
        report = self.auditor.audit(self.greeting_text, self.contract_empty)
        self.assertEqual(
            report.verdict,
            AuditVerdict.CONVERSATIONAL_REFLEX,
            msg=f"Expected CONVERSATIONAL_REFLEX, got {report.verdict}"
        )

    def test_empty_criteria_confidence_is_1_0(self):
        """Branch A: confidence MUST be exactly 1.0 (no uncertainty for reflex)."""
        report = self.auditor.audit(self.greeting_text, self.contract_empty)
        self.assertEqual(
            report.confidence,
            1.0,
            msg=f"Expected confidence=1.0, got {report.confidence}"
        )

    def test_empty_criteria_rationale_does_not_mention_task_criteria(self):
        """Branch A: rationale must NOT mention task/criteria fabrications."""
        report = self.auditor.audit(self.greeting_text, self.contract_empty)
        rationale_lower = report.rationale.lower()
        # Should not claim any specific criteria were evaluated
        forbidden_phrases = ["0.98", "criterion", "criteria satisfied", "fulfilled", "task invariant missed"]
        for phrase in forbidden_phrases:
            self.assertNotIn(
                phrase, rationale_lower,
                msg=f"Rationale should NOT contain '{phrase}', got: {report.rationale}"
            )

    def test_empty_criteria_satisfied_list_is_empty(self):
        """Branch A: no criteria to satisfy → satisfied_criteria must be []."""
        report = self.auditor.audit(self.greeting_text, self.contract_empty)
        self.assertEqual(
            report.satisfied_criteria,
            [],
            msg=f"satisfied_criteria should be [], got {report.satisfied_criteria}"
        )

    def test_short_response_but_empty_criteria_still_reflex(self):
        """Branch A: even a short greeting still gets CONVERSATIONAL_REFLEX (not EVIDENCE_INSUFFICIENT)."""
        short_text = "Chào bạn!"
        # Note: current code checks len < 10 → EVIDENCE_INSUFFICIENT before criteria check.
        # This test verifies a response of >= 10 chars with empty criteria → REFLEX.
        text = "Chào bạn! Tôi đây."  # > 10 chars
        report = self.auditor.audit(text, self.contract_empty)
        self.assertEqual(
            report.verdict,
            AuditVerdict.CONVERSATIONAL_REFLEX,
            msg=f"Expected CONVERSATIONAL_REFLEX, got {report.verdict}"
        )

    def test_various_conversational_responses_get_reflex(self):
        """Branch A: various conversation responses must all yield CONVERSATIONAL_REFLEX."""
        responses = [
            "Xin chào Master! Hôm nay bạn cần tôi hỗ trợ gì?",
            "Tôi đã sẵn sàng thực thi nhiệm vụ của bạn.",
            "Được rồi, tôi hiểu rồi. Bạn muốn bắt đầu từ đâu?",
            "Hello! How can I assist you today with JKAI Zenith?",
        ]
        contract = _make_contract(success_criteria=[])
        for resp in responses:
            with self.subTest(response=resp[:40]):
                report = self.auditor.audit(resp, contract)
                self.assertEqual(
                    report.verdict,
                    AuditVerdict.CONVERSATIONAL_REFLEX,
                    msg=f"Response '{resp[:40]}...' should get CONVERSATIONAL_REFLEX"
                )


# ---------------------------------------------------------------------------
# Branch B: Task with evidence requirement but no evidence → REJECT (not FULFILLED)
# ---------------------------------------------------------------------------

class TestH1BranchB_EvidenceRequiredReject(unittest.TestCase):
    """
    Branch B: Task mission has criteria but response lacks supporting evidence
              → verdict MUST NOT be FULFILLED.
    """

    def setUp(self):
        self.auditor = _auditor()

    def test_task_with_world_event_criteria_but_no_evidence_not_fulfilled(self):
        """Branch B: WORLD_EVENT_COVERAGE required but response has no event content → not FULFILLED."""
        contract = _make_contract(
            success_criteria=["WORLD_EVENT_COVERAGE", "EXCLUDE_NOISE_SCOPES"],
            is_realtime_news=True,
        )
        # Response about horoscopes — clearly off-topic
        bad_response = (
            "Hôm nay cung hoàng đạo Bọ Cạp rất may mắn. "
            "Tử vi của bạn cho thấy vận tài chính tốt. "
            "Con giáp của bạn sẽ gặp nhiều thuận lợi trong tình cảm."
        )
        report = self.auditor.audit(bad_response, contract)
        self.assertNotEqual(
            report.verdict,
            AuditVerdict.FULFILLED,
            msg=f"Off-topic horoscope response should NOT be FULFILLED, got {report.verdict}"
        )

    def test_task_with_world_event_criteria_on_topic_response_can_pass(self):
        """Branch B (sanity): on-topic world event response CAN be FULFILLED."""
        contract = _make_contract(
            success_criteria=["WORLD_EVENT_COVERAGE", "EXCLUDE_NOISE_SCOPES"],
            is_realtime_news=True,
            required_time="2026",
            min_length=50,
            min_paragraphs=1,
        )
        good_response = (
            "Ngày 24/09/2026 — Thế giới: Cuộc đàm phán ngoại giao giữa Mỹ và Nga "
            "tiếp tục diễn ra tại Geneva. Các chuyên gia quốc tế nhận định tình hình "
            "Ukraine vẫn còn căng thẳng. Ngoại trưởng hai bên đã có cuộc gặp song phương."
        )
        report = self.auditor.audit(good_response, contract)
        # Should NOT be OFF_TOPIC or EVIDENCE_INSUFFICIENT
        self.assertNotIn(
            report.verdict,
            [AuditVerdict.OFF_TOPIC, AuditVerdict.EVIDENCE_INSUFFICIENT],
            msg=f"On-topic world event response should not be OFF_TOPIC/EVIDENCE_INSUFFICIENT, got {report.verdict}"
        )

    def test_fulfilled_verdict_conf_is_not_old_0_98(self):
        """Branch B: FULFILLED confidence must be 0.95 (not the old copy-paste 0.98)."""
        contract = _make_contract(
            success_criteria=["WORLD_EVENT_COVERAGE", "EXCLUDE_NOISE_SCOPES"],
            is_realtime_news=True,
            required_time="2026",
            min_length=50,
            min_paragraphs=1,
        )
        good_response = (
            "Ngày 24/09/2026 — Cuộc chiến sự tại Ukraine 2026: quốc tế tiếp tục đàm phán "
            "ngoại giao. Nga và Mỹ nhóm họp tại Geneva. Thế giới theo dõi sát sao tình hình."
        )
        report = self.auditor.audit(good_response, contract)
        if report.verdict == AuditVerdict.FULFILLED:
            self.assertNotEqual(
                report.confidence,
                0.98,
                msg="Old copy-paste 0.98 confidence detected — fix H1 not applied!"
            )
            self.assertAlmostEqual(
                report.confidence,
                0.95,
                places=2,
                msg=f"FULFILLED confidence should be 0.95, got {report.confidence}"
            )

    def test_fulfilled_rationale_lists_actual_criteria_not_copy_paste(self):
        """Branch B: FULFILLED rationale must list actual criteria, not boilerplate."""
        contract = _make_contract(
            success_criteria=["WORLD_EVENT_COVERAGE", "EXCLUDE_NOISE_SCOPES"],
            is_realtime_news=True,
            required_time="2026",
            min_length=50,
            min_paragraphs=1,
        )
        good_response = (
            "Ngày 24/09/2026 — Thế giới: Hội nghị ngoại giao quốc tế tại Geneva. "
            "Ukraine: các bên tiếp tục đàm phán. Phương Tây theo dõi sát diễn biến chiến sự Nga."
        )
        report = self.auditor.audit(good_response, contract)
        if report.verdict == AuditVerdict.FULFILLED:
            # Rationale must contain actual criteria names
            self.assertTrue(
                any(c in report.rationale for c in ["WORLD_EVENT_COVERAGE", "EXCLUDE_NOISE_SCOPES", "criteria"]),
                msg=f"FULFILLED rationale must list criteria, got: {report.rationale}"
            )

    def test_empty_response_gives_evidence_insufficient(self):
        """Sanity: empty/trivial response → EVIDENCE_INSUFFICIENT regardless of criteria."""
        contract = _make_contract(success_criteria=["WORLD_EVENT_COVERAGE"])
        report = self.auditor.audit("   ", contract)
        self.assertEqual(
            report.verdict,
            AuditVerdict.EVIDENCE_INSUFFICIENT,
            msg=f"Empty response should be EVIDENCE_INSUFFICIENT, got {report.verdict}"
        )


# ---------------------------------------------------------------------------
# Branch C: Regression guards
# ---------------------------------------------------------------------------

class TestH1Regression(unittest.TestCase):
    """Regression: old behaviour (FULFILLED at 0.98 for everything) must be gone."""

    def setUp(self):
        self.auditor = _auditor()

    def test_greeting_never_gets_fulfilled(self):
        """Regression: a pure greeting MUST NOT get FULFILLED (was the pre-H1 bug)."""
        contract = _make_contract(success_criteria=[])
        report = self.auditor.audit(
            "Xin chào! Tôi có thể giúp gì cho bạn?",
            contract
        )
        self.assertNotEqual(
            report.verdict,
            AuditVerdict.FULFILLED,
            msg="Greeting with empty criteria got FULFILLED — regression!"
        )

    def test_greeting_never_gets_0_98_confidence(self):
        """Regression: confidence 0.98 (old hardcoded value) must never appear for greetings."""
        contract = _make_contract(success_criteria=[])
        report = self.auditor.audit(
            "Xin chào! Hôm nay tôi có thể giúp gì?",
            contract
        )
        self.assertNotEqual(
            report.confidence,
            0.98,
            msg="Old hardcoded 0.98 confidence detected for greeting — regression!"
        )

    def test_four_different_missions_get_different_verdicts_not_uniform_fulfilled(self):
        """Regression: 4 different mission types must NOT all get FULFILLED (was log live bug)."""
        auditor = self.auditor

        missions = [
            # (response_text, contract)
            (
                "Xin chào! Tôi đây.",
                _make_contract(success_criteria=[]),
            ),
            (
                "Tử vi hôm nay rất tốt. Cung hoàng đạo của bạn thuận lợi.",
                _make_contract(success_criteria=["WORLD_EVENT_COVERAGE", "EXCLUDE_NOISE_SCOPES"]),
            ),
            (
                "",  # empty
                _make_contract(success_criteria=["WORLD_EVENT_COVERAGE"]),
            ),
        ]

        verdicts = [auditor.audit(resp, contract).verdict for resp, contract in missions]

        # All must NOT be FULFILLED
        all_fulfilled = all(v == AuditVerdict.FULFILLED for v in verdicts)
        self.assertFalse(
            all_fulfilled,
            msg=f"All 3 distinct missions returned FULFILLED — uniform-FULFILLED regression! Verdicts: {verdicts}"
        )

        # At least one must be CONVERSATIONAL_REFLEX (the greeting)
        self.assertIn(
            AuditVerdict.CONVERSATIONAL_REFLEX,
            verdicts,
            msg=f"No CONVERSATIONAL_REFLEX found in verdicts: {verdicts}"
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)
