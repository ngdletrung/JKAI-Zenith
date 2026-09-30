# -*- coding: utf-8 -*-
"""
tests/test_confidence_policy.py
Contract tests for ADR 0003 confidence policy.
"""

from __future__ import annotations

import pytest

from core.cognitive_bus.decision_substrate_adapter import (
    DecisionPrimitive,
    ExecutionTier,
    TypedJudgementPacket,
)
from core.governance.confidence_policy import (
    ActionClass,
    PolicyVerdict,
    THETA_IRREV_FIT_PLACEHOLDER,
    THETA_MUT_FIT_PLACEHOLDER,
    THETA_READ_FIT_PLACEHOLDER,
    THETA_READ_UNCAL_FIT_PLACEHOLDER,
    decide,
)


def _packet(confidence: float) -> TypedJudgementPacket:
    return TypedJudgementPacket(
        primitive=DecisionPrimitive.BOOLEAN,
        question="q",
        result=confidence,
        confidence=confidence,
        distribution={"true": confidence, "false": round(1.0 - confidence, 6)},
        execution_tier=ExecutionTier.TIER_2_LOCAL,
        latency_ms=1.0,
    )


# ---------------------------------------------------------------------------
# READ
# ---------------------------------------------------------------------------

class TestReadPolicy:

    def test_calibrated_above_threshold_authorizes(self):
        d = decide(_packet(0.75), ActionClass.READ, "calibrated")
        assert d.verdict == PolicyVerdict.AUTHORIZE
        assert d.threshold_used == THETA_READ_FIT_PLACEHOLDER

    def test_calibrated_below_threshold_escalates(self):
        d = decide(_packet(0.50), ActionClass.READ, "calibrated")
        assert d.verdict == PolicyVerdict.ESCALATE_TO_TIER3

    def test_uncalibrated_uses_higher_threshold(self):
        d = decide(_packet(0.75), ActionClass.READ, "uncalibrated")
        assert d.verdict == PolicyVerdict.ESCALATE_TO_TIER3
        assert d.threshold_used == THETA_READ_UNCAL_FIT_PLACEHOLDER

    def test_uncalibrated_above_higher_threshold_authorizes(self):
        d = decide(_packet(0.90), ActionClass.READ, "uncalibrated")
        assert d.verdict == PolicyVerdict.AUTHORIZE

    def test_boundary_exactly_at_threshold_authorizes(self):
        d = decide(_packet(THETA_READ_FIT_PLACEHOLDER), ActionClass.READ, "calibrated")
        assert d.verdict == PolicyVerdict.AUTHORIZE


# ---------------------------------------------------------------------------
# MUTATE_REVERSIBLE
# ---------------------------------------------------------------------------

class TestMutateReversiblePolicy:

    def test_uncalibrated_always_escalates(self):
        for conf in [0.50, 0.90, 0.99, 1.0]:
            d = decide(_packet(conf), ActionClass.MUTATE_REVERSIBLE, "uncalibrated")
            assert d.verdict == PolicyVerdict.ESCALATE_TO_TIER3, conf

    def test_calibrated_above_threshold_authorizes(self):
        d = decide(_packet(0.95), ActionClass.MUTATE_REVERSIBLE, "calibrated")
        assert d.verdict == PolicyVerdict.AUTHORIZE

    def test_calibrated_below_threshold_escalates(self):
        d = decide(_packet(0.85), ActionClass.MUTATE_REVERSIBLE, "calibrated")
        assert d.verdict == PolicyVerdict.ESCALATE_TO_TIER3


# ---------------------------------------------------------------------------
# MUTATE_IRREVERSIBLE
# ---------------------------------------------------------------------------

class TestMutateIrreversiblePolicy:

    def test_uncalibrated_always_escalates(self):
        d = decide(_packet(1.0), ActionClass.MUTATE_IRREVERSIBLE, "uncalibrated")
        assert d.verdict == PolicyVerdict.ESCALATE_TO_TIER3

    def test_calibrated_low_confidence_escalates(self):
        d = decide(_packet(0.90), ActionClass.MUTATE_IRREVERSIBLE, "calibrated")
        assert d.verdict == PolicyVerdict.ESCALATE_TO_TIER3

    def test_calibrated_high_confidence_no_tier3_escalates(self):
        d = decide(
            _packet(0.99),
            ActionClass.MUTATE_IRREVERSIBLE,
            "calibrated",
            tier3_concurred=None,
        )
        assert d.verdict == PolicyVerdict.ESCALATE_TO_TIER3
        assert "concurrence" in d.reason

    def test_calibrated_high_confidence_tier3_disagrees_rejects(self):
        d = decide(
            _packet(0.99),
            ActionClass.MUTATE_IRREVERSIBLE,
            "calibrated",
            tier3_concurred=False,
        )
        assert d.verdict == PolicyVerdict.REJECT

    def test_calibrated_high_confidence_tier3_agrees_authorizes(self):
        d = decide(
            _packet(0.99),
            ActionClass.MUTATE_IRREVERSIBLE,
            "calibrated",
            tier3_concurred=True,
        )
        assert d.verdict == PolicyVerdict.AUTHORIZE


# ---------------------------------------------------------------------------
# Invariants
# ---------------------------------------------------------------------------

class TestPolicyInvariants:

    def test_uncalibrated_never_authorizes_mutations(self):
        """Fail-closed invariant: uncalibrated backend cannot authorize mutations."""
        for cls in (ActionClass.MUTATE_REVERSIBLE, ActionClass.MUTATE_IRREVERSIBLE):
            for conf in [0.0, 0.5, 0.9, 0.99, 1.0]:
                d = decide(_packet(conf), cls, "uncalibrated",
                           tier3_concurred=True)
                assert d.verdict != PolicyVerdict.AUTHORIZE, (cls, conf)

    def test_decision_is_deterministic(self):
        args = (_packet(0.92), ActionClass.READ, "uncalibrated")
        d1 = decide(*args)
        d2 = decide(*args)
        assert d1 == d2

    def test_reason_always_present(self):
        for cls in ActionClass:
            for state in ("calibrated", "uncalibrated"):
                d = decide(_packet(0.5), cls, state)
                assert d.reason
