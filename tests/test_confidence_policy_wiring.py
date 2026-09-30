# -*- coding: utf-8 -*-
"""
tests/test_confidence_policy_wiring.py
Contract tests verifying ADR 0003 Confidence Policy wiring into TriTierDecisionAdapter.
"""

from __future__ import annotations

import pytest

from core.cognitive_bus.decision_substrate_adapter import (
    DecisionPrimitive,
    ExecutionTier,
    TriTierDecisionAdapter,
)
from core.cognitive_bus.backends.fake_backend import FakeTier2Backend
from core.cognitive_bus.tier2_backend import BackendMetadata
from core.governance.confidence_policy import ActionClass, PolicyVerdict


def _uncal_backend():
    return FakeTier2Backend(metadata=BackendMetadata(
        name="fake-uncal",
        version="1.0",
        is_deterministic=True,
        is_local_only=True,
        supported_languages=("*",),
        calibration_state="uncalibrated",
        ece=None,
    ))


def test_uncalibrated_read_above_threshold_authorizes():
    backend = _uncal_backend()   # confidence default 0.97
    adapter = TriTierDecisionAdapter(
        enable_mock=False,
        record_shadow=False,
        tier2_backend=backend,
    )
    verdict = adapter.evaluate_parallel_batch(
        {"body": "benign"},
        [(DecisionPrimitive.BOOLEAN, "is this safe?", None)],
        action_class=ActionClass.READ,
    )
    # Fake returns 0.97 confidence. θ_read_uncal = 0.85 -> should authorize.
    assert verdict.execution_tier == ExecutionTier.TIER_2_LOCAL


def test_uncalibrated_read_low_conf_falls_through():
    backend = FakeTier2Backend(
        confidence=0.60,
        metadata=BackendMetadata(
            name="fake-uncal",
            version="1.0",
            is_deterministic=True,
            is_local_only=True,
            supported_languages=("*",),
            calibration_state="uncalibrated",
            ece=None,
        ),
    )
    adapter = TriTierDecisionAdapter(
        enable_mock=False,
        record_shadow=False,
        tier2_backend=backend,
    )
    verdict = adapter.evaluate_parallel_batch(
        {"body": "benign"},
        [(DecisionPrimitive.BOOLEAN, "is this safe?", None)],
        action_class=ActionClass.READ,
    )
    # 0.60 < 0.85 -> escalate, do NOT return Tier 2
    assert verdict.execution_tier != ExecutionTier.TIER_2_LOCAL


def test_policy_decisions_returned_per_question():
    backend = _uncal_backend()
    adapter = TriTierDecisionAdapter(
        enable_mock=False,
        record_shadow=False,
        tier2_backend=backend,
    )
    verdict = adapter.evaluate_parallel_batch(
        {"body": "benign"},
        [(DecisionPrimitive.BOOLEAN, "q1", None),
         (DecisionPrimitive.BOOLEAN, "q2", None)],
    )
    decisions = adapter.apply_confidence_policy(
        verdict, ActionClass.READ, "uncalibrated",
    )
    assert set(decisions.keys()) == {"q1", "q2"}
    for d in decisions.values():
        assert d.verdict == PolicyVerdict.AUTHORIZE


def test_mutate_uncalibrated_never_authorizes():
    backend = _uncal_backend()
    adapter = TriTierDecisionAdapter(
        enable_mock=False,
        record_shadow=False,
        tier2_backend=backend,
    )
    verdict = adapter.evaluate_parallel_batch(
        {"body": "benign"},
        [(DecisionPrimitive.BOOLEAN, "is this safe?", None)],
        action_class=ActionClass.MUTATE_IRREVERSIBLE,
    )
    # Even if Tier 2 confidence is 0.97, mutation on uncalibrated backend MUST fall through to Tier 3!
    assert verdict.execution_tier != ExecutionTier.TIER_2_LOCAL
    assert verdict.execution_tier in (ExecutionTier.TIER_3_RULE, ExecutionTier.ESCALATE)
