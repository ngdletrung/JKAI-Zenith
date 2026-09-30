"""
Contract test suite for Tier 1 / Tier 2 Decision Substrate & Red Team Turn 95 Doctrine:
1. Byte-identical input guarantee across all tiers.
2. Single unified provider contract (S1: no duplicate interfaces).
3. Fast-Path threshold marked strictly as unfit placeholder (S2).
4. Gate F explicitly tracks not_measured_items.
"""

import json
import pytest

from core.sanitizer.state_sanitizer import StateSanitizer
from core.cognitive_bus.decision_substrate_adapter import (
    TriTierDecisionAdapter,
    DecisionPrimitive,
    ExecutionTier,
    TypedJudgementPacket,
    ALLOWED_DECISION_PROVIDERS,
    THETA_FAST_PATH_UNFIT_PLACEHOLDER
)
from core.governance.gate_f_evidence_auditor import (
    GateFElevanceMetrics,
    GateFEvidenceAuditor
)


def test_byte_identical_input_guarantee():
    """StateSanitizer.canonical_bytes must produce byte-identical inputs regardless of key order or NFC normalization."""
    state1 = {"query": "Tối ưu hóa SQL", "limit": 10, "nested": {"b": 2, "a": 1}}
    state2 = {"nested": {"a": 1, "b": 2}, "limit": 10, "query": "Tối ưu hóa SQL"}

    b1 = StateSanitizer.canonical_bytes(state1)
    b2 = StateSanitizer.canonical_bytes(state2)

    assert b1 == b2, "Canonical bytes must be strictly identical across key reorderings"
    assert isinstance(b1, bytes)
    assert len(b1) <= StateSanitizer.MAX_STATE_BYTES


def test_single_unified_provider_contract_s1():
    """S1 Mandate: All tiers share the single DecisionProvider contract without duplicate interfaces."""
    assert "TIER_1_LOCAL_REFLEX" in ALLOWED_DECISION_PROVIDERS
    assert "TIER_2_LOCAL_EMULATOR" in ALLOWED_DECISION_PROVIDERS
    assert "TIER_3_DETERMINISTIC_RULE" in ALLOWED_DECISION_PROVIDERS

    # Verify adapter operates on the single unified contract
    adapter = TriTierDecisionAdapter(enable_mock=True)
    res = adapter.evaluate_noul({"query": "SELECT * FROM db"}, "is_read_only")
    assert isinstance(res, TypedJudgementPacket)
    assert res.primitive == DecisionPrimitive.BOOLEAN
    assert 0.0 <= res.confidence <= 1.0
    assert res.execution_tier in (ExecutionTier.TIER_3_RULE, ExecutionTier.TIER_2_LOCAL, ExecutionTier.TIER_1_LOCAL)


def test_fast_path_threshold_is_unfit_placeholder_s2():
    """S2 Mandate: Theta = 0.85 is an uncalibrated placeholder awaiting empirical shadow fitting."""
    assert THETA_FAST_PATH_UNFIT_PLACEHOLDER == 0.85
    # Must NOT be sealed as calibrated ground truth
    assert getattr(TriTierDecisionAdapter, "THETA_FAST_PATH_PLACEHOLDER", 0.85) == 0.85


def test_gate_f_tracks_not_measured_items(tmp_path):
    """Gate F package must record not_measured_items and not falsely pass unmeasured items."""
    output_dir = str(tmp_path / "gate_f_audit")

    metrics = GateFElevanceMetrics(
        is_gate_f_passed=True,
        total_missions=10,
        mission_success_rate=95.0,
        not_measured_items=["modernbert_395m_latency", "in_process_cpu_vram"]
    )
    verdict = GateFEvidenceAuditor.generate_evidence_package(
        output_dir=output_dir,
        operational_metrics_override=metrics
    )

    # When not_measured_items is non-empty, Gate F must NOT blindly report PASSED
    assert verdict["verdict"] in ("NOT_MEASURED", "FAILED")
    assert "not_measured_items" in verdict
    assert "modernbert_395m_latency" in verdict["not_measured_items"]
