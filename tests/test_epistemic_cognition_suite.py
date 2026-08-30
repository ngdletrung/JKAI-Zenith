# -*- coding: utf-8 -*-
"""
tests/test_epistemic_cognition_suite.py
JKAI DEMS v1.0 — Comprehensive Epistemic Cognition & Scope Test Suite.

Verifies:
1. GoalContract compilation (Required topics, exclusions, anchors).
2. ScopeClassifier categorization (Politics, Economy, Tech vs Horoscope).
3. EpistemicAuditor verdicts (FULFILLED vs OFF_TOPIC on Golden Failure Case #001).
4. Raw Trace persistence and 6-Factor arbitration signal.
"""

import pytest
from core.os.cognition.goal_contract import goal_contract_compiler, GoalContract
from core.os.cognition.scope_classifier import scope_classifier, ClassifiedScope
from core.os.cognition.epistemic_auditor import epistemic_auditor, AuditVerdict
from core.governor.claim_ledger import ClaimItem, ClaimScope, ClaimStatus


class TestEpistemicCognitionSuite:

    # ─────────────────────────────────────────────────────────────
    # VECTOR 1: Goal Contract Compiles World News Accurately
    # ─────────────────────────────────────────────────────────────
    def test_01_goal_contract_world_news(self):
        """Vector 1: Goal contract identifies world news and excludes horoscope/entertainment."""
        contract = goal_contract_compiler.compile("Tình hình thế giới hôm nay có gì mới?")
        
        assert "POLITICS" in contract.required_topics
        assert "INTERNATIONAL" in contract.required_topics
        assert "HOROSCOPE" in contract.excluded_scopes
        assert "ENTERTAINMENT" in contract.excluded_scopes
        assert "WORLD_EVENT_COVERAGE" in contract.success_criteria
        assert contract.is_realtime_news is True
        assert contract.required_time is not None

    # ─────────────────────────────────────────────────────────────
    # VECTOR 2: Scope Classifier Distinguishes Real News from Horoscope
    # ─────────────────────────────────────────────────────────────
    def test_02_scope_classifier_categories(self):
        """Vector 2: Accurately classifies Ukraine war, Gold price, and Horoscope."""
        # A. Politics / War
        res_war = scope_classifier.classify("Thời sự quốc tế: Ukraine cáo buộc quân đội Nga tập kích tên lửa quy mô lớn.")
        assert res_war.primary_scope == "POLITICS"
        assert res_war.is_noise is False
        assert res_war.applicability_to_world_news >= 0.90

        # B. Economy / Gold
        res_gold = scope_classifier.classify("Giá vàng hôm nay rơi thẳng đứng do quyết định lãi suất mới từ Fed và tỷ giá USD.")
        assert res_gold.primary_scope == "ECONOMY"
        assert res_gold.is_noise is False
        assert res_gold.applicability_to_world_news >= 0.60

        # C. Horoscope / Noise
        res_horo = scope_classifier.classify("Tử vi 12 con giáp ngày 29/08/2026: Tuổi Tý tài vận hanh thông, công việc phát triển.")
        assert res_horo.primary_scope == "HOROSCOPE"
        assert res_horo.is_noise is True
        assert res_horo.applicability_to_world_news <= 0.05

    # ─────────────────────────────────────────────────────────────
    # VECTOR 3: Epistemic Auditor Rejects Off-Topic Horoscope Answer
    # ─────────────────────────────────────────────────────────────
    def test_03_epistemic_auditor_detects_off_topic(self):
        """Vector 3: Golden Failure Case #001 — Auditor flags horoscope-only answer as OFF_TOPIC."""
        contract = goal_contract_compiler.compile("Tình hình thế giới hôm nay có gì mới?")
        
        bad_response = (
            "[Ngày 29/08/2026] Giá vàng hôm nay giảm mạnh 1.5 triệu đồng.\n"
            "[Ngày 29/08/2026] Tử vi 12 con giáp hôm nay: Tuổi Thân gặp nhiều may mắn."
        )

        audit_report = epistemic_auditor.audit(bad_response, contract)
        assert audit_report.verdict == AuditVerdict.OFF_TOPIC
        assert audit_report.contains_excluded_noise is True
        assert "WORLD_EVENT_COVERAGE" in audit_report.missing_criteria

    # ─────────────────────────────────────────────────────────────
    # VECTOR 4: Epistemic Auditor Confirms Fulfilled World News Answer
    # ─────────────────────────────────────────────────────────────
    def test_04_epistemic_auditor_confirms_fulfilled(self):
        """Vector 4: Golden Success Case — Valid international politics report passes with FULFILLED."""
        contract = goal_contract_compiler.compile("Tình hình thế giới hôm nay có gì mới?")
        
        good_response = (
            "📌 **Chính trị - Quân sự & Địa chính trị Quốc tế:**\n"
            "- [Ngày 29/08/2026] Ukraine cáo buộc Nga tiến hành tập kích xuyên đêm, tình hình căng thẳng leo thang (VOV).\n\n"
            "📌 **Kinh tế - Tài chính:**\n"
            "- [Ngày 29/08/2026] Giá vàng thế giới giảm mạnh 145 USD/ounce do thông điệp mới từ Fed."
        )

        audit_report = epistemic_auditor.audit(good_response, contract)
        assert audit_report.verdict == AuditVerdict.FULFILLED
        assert audit_report.confidence >= 0.95
        assert audit_report.contains_excluded_noise is False
        assert len(audit_report.missing_criteria) == 0

    # ─────────────────────────────────────────────────────────────
    # VECTOR 5: 6-Factor Claim Arbitration with Applicability
    # ─────────────────────────────────────────────────────────────
    def test_05_claim_arbitration_6_factor(self):
        """Vector 5: Verifies 6-Factor score prioritizes high applicability claims."""
        claim_war = ClaimItem(
            claim_id="c_01",
            subject="ukraine_war",
            predicate="status",
            object_val="escalated",
            scope=ClaimScope.GENERAL,
            evidence_refs=["ev_01"],
            authority_level=4, # Runtime Tool
            freshness=1000.0,
            directness=1.0,
            verification_score=1.0,
            applicability=0.98
        )

        claim_horo = ClaimItem(
            claim_id="c_02",
            subject="astrology",
            predicate="daily_fortune",
            object_val="lucky",
            scope=ClaimScope.GENERAL,
            evidence_refs=["ev_02"],
            authority_level=4,
            freshness=1000.0,
            directness=1.0,
            verification_score=1.0,
            applicability=0.01
        )

        score_war = claim_war.calculate_score(current_time=1000.0)
        score_horo = claim_horo.calculate_score(current_time=1000.0)

        assert score_war > 0.90
        assert score_horo < 0.80
        assert score_war > score_horo
