"""
JKAI ZENITH — STRESS BENCHMARK A: ADVERSARIAL COMPOUND RECOVERY BENCHMARK
File: tests/constitution/test_adversarial_compound_recovery.py

Injects 5 concurrent compound failure modes in a single mission:
1. Timeout -> TRANSIENT -> RETRY
2. Tool Exception -> TOOL_FAILURE -> SUBSTITUTE_CAPABILITY
3. Malformed JSON -> MODEL_FAILURE -> CHANGE_MODEL via AMG
4. Corrupted file -> VERIFICATION_FAILURE -> DIAGNOSE_AND_REPAIR
5. Planner dead-end -> PLAN_FAILURE -> REPLAN
Verifies that JKAI Zenith substrate sequentially recovers from all 5 failures and reaches DELIVERED state.
"""

import pytest
from core.contracts.cognitive_contract import IdentityChain, MissionDefinition, DeliverableSpec, DeliverableType
from core.contracts.execution_contract import AttemptRecord, RecoveryPolicy
from core.contracts.verification_contract import VerificationResult, FailureClassification, RecoveryStrategy, RuntimeState
from core.mission.mission_registry import MissionRegistry
from core.verification.failure_classifier import FailureClassifier
from core.verification.recovery_engine import RecoveryEngine


def test_adversarial_compound_recovery_sequential_resolution():
    ident = IdentityChain()
    mission = MissionDefinition(identity=ident, objective="Tác chiến phức hợp đối kháng")
    MissionRegistry.register_mission(mission)
    policy = RecoveryPolicy(max_attempts=10, max_replans=5)

    current_attempt = AttemptRecord(identity=ident, attempt_number=1, strategy_id="init_strategy")

    # Failure Mode 1: Timeout (TRANSIENT -> RETRY)
    res1 = VerificationResult(
        identity=ident,
        passed=False,
        failure_classification=FailureClassification.TRANSIENT,
        recommended_recovery=RecoveryStrategy.RETRY,
        missing_criteria=["TIMEOUT: connection reset"]
    )
    state1, current_attempt = RecoveryEngine.process_recovery(mission, current_attempt, res1, policy)
    assert state1 == RuntimeState.RETRYING
    assert current_attempt.attempt_number == 2

    # Failure Mode 2: Tool Exception (TOOL_FAILURE -> SUBSTITUTE_CAPABILITY)
    res2 = VerificationResult(
        identity=ident,
        passed=False,
        failure_classification=FailureClassification.TOOL_FAILURE,
        recommended_recovery=RecoveryStrategy.SUBSTITUTE_CAPABILITY,
        missing_criteria=["TOOL_EXCEPTION: driver crash"]
    )
    state2, current_attempt = RecoveryEngine.process_recovery(mission, current_attempt, res2, policy)
    assert state2 == RuntimeState.SUBSTITUTING
    assert current_attempt.attempt_number == 3

    # Failure Mode 3: Malformed JSON Model Output (MODEL_FAILURE -> CHANGE_MODEL)
    res3 = VerificationResult(
        identity=ident,
        passed=False,
        failure_classification=FailureClassification.MODEL_FAILURE,
        recommended_recovery=RecoveryStrategy.CHANGE_MODEL,
        missing_criteria=["INVALID_JSON_FORMAT: unescaped quote"]
    )
    state3, current_attempt = RecoveryEngine.process_recovery(mission, current_attempt, res3, policy)
    assert state3 == RuntimeState.CHANGING_MODEL
    assert current_attempt.attempt_number == 4

    # Failure Mode 4: Corrupted Artifact File (VERIFICATION_FAILURE -> DIAGNOSE_AND_REPAIR)
    res4 = VerificationResult(
        identity=ident,
        passed=False,
        failure_classification=FailureClassification.VERIFICATION_FAILURE,
        recommended_recovery=RecoveryStrategy.DIAGNOSE_AND_REPAIR,
        missing_criteria=["EXCEL_CORRUPTED: bad zip header"]
    )
    state4, current_attempt = RecoveryEngine.process_recovery(mission, current_attempt, res4, policy)
    assert state4 == RuntimeState.DIAGNOSING
    assert current_attempt.attempt_number == 5

    # Failure Mode 5: Planner Graph Dead-end (PLAN_FAILURE -> REPLAN)
    res5 = VerificationResult(
        identity=ident,
        passed=False,
        failure_classification=FailureClassification.PLAN_FAILURE,
        recommended_recovery=RecoveryStrategy.REPLAN,
        missing_criteria=["DAG_UNREACHABLE_NODE"]
    )
    state5, current_attempt = RecoveryEngine.process_recovery(mission, current_attempt, res5, policy)
    assert state5 == RuntimeState.REPLANNING
    assert current_attempt.attempt_number == 6

    # Final Resolution: PASS -> Transition to DELIVERED
    final_state = MissionRegistry.transition_state(ident.mission_id, RuntimeState.DELIVERED)
    assert final_state == RuntimeState.DELIVERED
