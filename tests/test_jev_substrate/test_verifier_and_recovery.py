"""
Unit Tests for L3 Semantic Verifier & T7 Error Classifier (AMG v2)
"""

import pytest
from core.cognitive_bus.jev_substrate_adapter import TriTierJevAdapter
from core.verification.l3_semantic_verifier import (
    L3SemanticVerifier,
    VerificationStatus
)
from core.recovery.error_classifier import (
    ErrorClassifier,
    ErrorSubclass,
    RecoveryGroup,
    ModelScale,
    E15AnomalyWatcher
)


def test_l3_verifier_passes_valid_mission():
    verifier = L3SemanticVerifier()

    mission = "Export school desk inventory to CSV"
    artifacts = {"report_csv": "id,name,qty\n1,Desk A,50"}
    criteria = [
        ("crit_1", "Output is in valid CSV format"),
        ("crit_2", "All desk records are accounted for")
    ]

    verdict = verifier.verify_mission_goal(mission, artifacts, criteria)
    assert verdict.status == VerificationStatus.PASS
    assert verdict.score >= 2.75
    assert verdict.confidence >= 0.85
    assert verdict.escalate_to_system_two is False
    assert len(verdict.criteria_results) == 2


def test_error_classifier_identifies_subclass_and_recovery_group():
    classifier = ErrorClassifier()

    # Network transient error
    err_trace = "ConnectionResetError: [WinError 10054] An existing connection was forcibly closed by the remote host"
    verdict = classifier.classify_and_resolve(err_trace, current_model=ModelScale.MODEL_4B, recovery_turn=1)

    assert verdict.subclass in [e for e in ErrorSubclass]
    assert verdict.confidence >= 0.85
    assert verdict.target_model in (ModelScale.MODEL_4B, ModelScale.MODEL_8B)


def test_amg_v2_30b_ceiling_triggers_mission_pause():
    classifier = ErrorClassifier()

    complex_error = "LogicalDeadlock: Circular dependency detected between course prerequisite and graduation rule"
    # When already at 30B and fails turn 2
    verdict = classifier.classify_and_resolve(
        complex_error, 
        current_model=ModelScale.MODEL_30B, 
        recovery_turn=2
    )

    assert verdict.requires_escalation is True
    assert verdict.target_model == ModelScale.MISSION_PAUSE
    assert "CRITICAL_COGNITIVE_CEILING_EXCEEDED" in verdict.recommended_action


def test_e15_anomaly_watcher_triggers_alert():
    watcher = E15AnomalyWatcher(window_size=10, alert_threshold=0.15)
    
    # 8 normal errors
    for _ in range(8):
        assert watcher.record(ErrorSubclass.E01_SYNTAX_PARSING_ERROR) is False

    # 2 unknown anomalies (2 / 10 = 20% > 15%)
    watcher.record(ErrorSubclass.E15_UNKNOWN_ANOMALY)
    alert = watcher.record(ErrorSubclass.E15_UNKNOWN_ANOMALY)
    
    assert alert is True
    assert watcher.alert_triggered is True
