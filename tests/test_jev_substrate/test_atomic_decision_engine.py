"""
JKAI Zenith - Unit & Integration Test Suite: Atomic Decision Engine v2.1
Tests Deterministic Controller Anchor, Layered Verification Graph, Multi-Hypothesis Recovery, and Calibration Guard.
Verifies all 6 Red Team conditions from Phiên 21 (Antigravity & OpenCode).
"""

import pytest
from core.cognitive_bus.jev_substrate_adapter import (
    TriTierJevAdapter,
    TypedJudgementPacket,
    JevPrimitive,
    ExecutionTier
)
from core.routing.deterministic_controller import (
    DeterministicRoutingController,
    ExecutionPath
)
from core.verification.layered_verification_graph import (
    LayeredVerificationGraph,
    VerificationLayer
)
from core.recovery.error_classifier import (
    PriorityWeightedRecoveryResolver
)
from core.cognitive_bus.calibration_guard import (
    CalibrationGuard,
    CalibrationHealth
)


# =========================================================================
# 1. DETERMINISTIC CONTROLLER TESTS (Jev Advisor + Circuit Breaker + Seed)
# =========================================================================

def test_deterministic_controller_low_confidence_fallback():
    adapter = TriTierJevAdapter(enable_mock=True)
    # Register mock packet with low confidence
    q = "Determine the optimal cognitive execution path for this task context"
    pkt = TypedJudgementPacket(
        primitive=JevPrimitive.CHOICE,
        question=q,
        result=ExecutionPath.FAST_PATH.value,
        confidence=0.65,  # Below 0.80 floor!
        distribution={ExecutionPath.FAST_PATH.value: 0.90, ExecutionPath.DEEP_PATH.value: 0.10},
        execution_tier=ExecutionTier.TIER_3_RULE,
        latency_ms=1.0
    )
    adapter.register_mock_judgement({"task": "test_low_conf"}, q, pkt)

    controller = DeterministicRoutingController(adapter=adapter)
    decision = controller.route({"task": "test_low_conf"})

    assert decision.selected_path == ExecutionPath.DEEP_PATH
    assert decision.is_fallback is True
    assert "below floor" in decision.reason


def test_deterministic_controller_escalation_safety():
    adapter = TriTierJevAdapter(enable_mock=True)
    q = "Determine the optimal cognitive execution path for this task context"
    pkt = TypedJudgementPacket(
        primitive=JevPrimitive.CHOICE,
        question=q,
        result=ExecutionPath.HUMAN_ESCALATION.value,
        confidence=0.92,
        distribution={
            ExecutionPath.FAST_PATH.value: 0.10,
            ExecutionPath.DEEP_PATH.value: 0.45,
            ExecutionPath.HUMAN_ESCALATION.value: 0.45  # > 0.40 threshold!
        },
        execution_tier=ExecutionTier.TIER_3_RULE,
        latency_ms=1.0
    )
    adapter.register_mock_judgement({"task": "test_escalate"}, q, pkt)

    controller = DeterministicRoutingController(adapter=adapter)
    decision = controller.route({"task": "test_escalate"})

    assert decision.selected_path == ExecutionPath.HUMAN_ESCALATION
    assert decision.is_fallback is False


def test_deterministic_controller_rolling_circuit_breaker():
    adapter = TriTierJevAdapter(enable_mock=True)
    controller = DeterministicRoutingController(adapter=adapter)

    # Feed 10 consecutive low confidence calls (< 0.70)
    for _ in range(10):
        controller.record_confidence(0.50)

    assert controller.is_circuit_disabled is True

    # When circuit is disabled, routing automatically falls back to DEEP_PATH
    decision = controller.route({"task": "any_task"})
    assert decision.selected_path == ExecutionPath.DEEP_PATH
    assert decision.rolling_circuit_status == "OPEN"
    assert decision.is_fallback is True


def test_deterministic_controller_seed_reproducibility():
    adapter = TriTierJevAdapter(enable_mock=True)
    controller = DeterministicRoutingController(adapter=adapter)

    ctx = {"task": "standard_compilation"}
    d1 = controller.route(ctx, random_seed=42)
    d2 = controller.route(ctx, random_seed=42)

    assert d1.selected_path == d2.selected_path
    assert d1.is_fallback == d2.is_fallback


# =========================================================================
# 2. LAYERED VERIFICATION GRAPH TESTS (Dependency Ordering + Short-Circuit)
# =========================================================================

def test_layered_verification_short_circuits_on_l0_failure():
    """
    OpenCode Góp ý A: Layer 0 failure MUST short-circuit.
    Verify that Layer 1 and Layer 2 are skipped completely.
    """
    adapter = TriTierJevAdapter(enable_mock=True)
    
    # Register L0 failure (artifact_exists is False/low probability)
    pkt_fail = TypedJudgementPacket(
        primitive=JevPrimitive.NOUL,
        question="artifact_exists",
        result=0.10,  # FAILED
        confidence=0.99,
        distribution={"true": 0.10, "false": 0.90},
        execution_tier=ExecutionTier.TIER_3_RULE,
        latency_ms=1.0
    )
    adapter.register_mock_judgement({"state": "missing_artifact"}, "artifact_exists", pkt_fail)

    verifier = LayeredVerificationGraph(adapter=adapter)
    result = verifier.verify_observation({"state": "missing_artifact"})

    assert result.overall_passed is False
    assert result.failed_layer == VerificationLayer.LAYER_0_PREREQUISITE
    # Assert Layer 1 and Layer 2 were SKIPPED
    assert VerificationLayer.LAYER_1_INTEGRITY in result.skipped_layers
    assert VerificationLayer.LAYER_2_REALITY in result.skipped_layers
    assert VerificationLayer.LAYER_1_INTEGRITY.value not in result.layer_results
    assert VerificationLayer.LAYER_2_REALITY.value not in result.layer_results


def test_layered_verification_passes_when_all_layers_succeed():
    adapter = TriTierJevAdapter(enable_mock=True)
    verifier = LayeredVerificationGraph(adapter=adapter)

    # Clean valid state
    state = {
        "status": "COMPLETED",
        "output_artifact": "d:\\reports\\summary.json",
        "schema": "v2_valid",
        "side_effects": "none"
    }

    result = verifier.verify_observation(state)
    assert result.overall_passed is True
    assert result.failed_layer is None
    assert len(result.skipped_layers) == 0
    assert result.total_latency_ms < 400.0  # SLA target met!


# =========================================================================
# 3. MULTI-HYPOTHESIS FAILURE DIAGNOSTIC & PRIORITY MATRIX
# =========================================================================

def test_priority_matrix_policy_violation_is_fail_closed():
    resolver = PriorityWeightedRecoveryResolver()
    state = {"error": "unauthorized permission denied IDOR attempt on /admin/keys"}
    
    verdict = resolver.diagnose_and_resolve(state)
    assert verdict.primary_hypothesis == "policy_violation"
    assert verdict.is_fail_closed is True
    assert "STOP_IMMEDIATELY_FAIL_CLOSED" in verdict.resolved_action


def test_priority_matrix_schema_remediation():
    resolver = PriorityWeightedRecoveryResolver()
    state = {"error": "ValidationError: missing_key 'token' in schema response"}
    
    verdict = resolver.diagnose_and_resolve(state)
    assert verdict.primary_hypothesis == "schema_violation"
    assert verdict.is_fail_closed is False
    assert "TASK_SCHEMA_REMEDIATION" in verdict.resolved_action


def test_priority_matrix_circuit_breaker_max_attempts():
    resolver = PriorityWeightedRecoveryResolver()
    state = {"error": "transient timeout connection refused"}
    
    # 4th attempt exceeds MAX_RECOVERY_ATTEMPTS = 3
    verdict = resolver.diagnose_and_resolve(state, current_attempts=4)
    assert verdict.primary_hypothesis == "RECOVERY_EXHAUSTED"
    assert verdict.circuit_status == "EXHAUSTED"
    assert verdict.is_fail_closed is True


# =========================================================================
# 4. CALIBRATION GUARD & 3-TIER DRIFT DEFENSE TESTS
# =========================================================================

def test_calibration_guard_optimal_health():
    guard = CalibrationGuard(baseline_fpr=0.12)
    # Perfectly calibrated synthetic pairs: 90% positive when prob=0.90, 10% positive when prob=0.10
    for _ in range(90):
        guard.record_outcome(predicted_prob=0.90, actual_outcome=1)
    for _ in range(10):
        guard.record_outcome(predicted_prob=0.90, actual_outcome=0)
    for _ in range(90):
        guard.record_outcome(predicted_prob=0.10, actual_outcome=0)
    for _ in range(10):
        guard.record_outcome(predicted_prob=0.10, actual_outcome=1)

    report = guard.evaluate_health()
    assert report.health == CalibrationHealth.OPTIMAL
    assert report.ece <= 0.08
    assert report.autonomous_enabled is True
    assert report.rollback_triggered is False


def test_calibration_guard_alert_and_disable_drift():
    guard = CalibrationGuard(baseline_fpr=0.05)
    # High discrepancy causing ECE > 0.15
    for _ in range(30):
        guard.record_outcome(predicted_prob=0.90, actual_outcome=0)  # Overconfident mistakes!
        guard.record_outcome(predicted_prob=0.85, actual_outcome=1)

    report = guard.evaluate_health()
    assert report.health in (CalibrationHealth.AUTONOMOUS_DISABLED, CalibrationHealth.SHUTDOWN_REVERT)
    assert report.autonomous_enabled is False


def test_calibration_guard_rollback_trigger_on_high_fpr():
    guard = CalibrationGuard(baseline_fpr=0.05)
    # Induce high false positive rate (> 0.05 * 1.2 = 0.06)
    for _ in range(15):
        guard.record_outcome(predicted_prob=0.75, actual_outcome=0)  # 15 false positives out of 15 negatives!

    report = guard.evaluate_health()
    assert report.rollback_triggered is True
    assert report.health == CalibrationHealth.SHUTDOWN_REVERT
