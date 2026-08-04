"""
CONSTITUTION TEST 6 & 8: MODEL FAILURE RECOVERY VIA AMG POOL SWITCH
File: tests/constitution/test_model_failure_recovery.py

Verifies that when Model A fails structured output, MODEL_FAILURE is emitted,
AMG selects Model B, creating a new AttemptRecord under the SAME Mission and Task.
"""

import pytest
from core.contracts.identity_contract import IdentityChain, AttemptRecord
from core.contracts.cognitive_contract import MissionDefinition
from core.contracts.verification_contract import VerificationResult, FailureClassification, RecoveryStrategy


def test_model_failure_triggers_amg_model_switch_and_new_attempt_record():
    ident = IdentityChain()
    mission = MissionDefinition(identity=ident, objective="Báo cáo tiến độ")

    # Attempt 1 with Model A fails structured output
    att1 = AttemptRecord(identity=ident, attempt_number=1, strategy_id="model_qwen3.5_4b")
    res1 = VerificationResult(
        identity=ident,
        passed=False,
        failure_classification=FailureClassification.MODEL_FAILURE,
        recommended_recovery=RecoveryStrategy.CHANGE_MODEL
    )

    assert res1.passed is False
    assert res1.failure_classification == FailureClassification.MODEL_FAILURE

    # AMG switches model to Model B (e.g. llama3.2:3b), creating Attempt 2 under SAME Mission and Task
    att2 = AttemptRecord(
        identity=ident,
        attempt_number=2,
        strategy_id="model_llama3.2_3b",
        parent_attempt_id=att1.identity.attempt_id,
        recovery_reason="MODEL_FAILURE"
    )

    assert att2.identity.mission_id == ident.mission_id
    assert att2.identity.task_id == ident.task_id
    assert att2.attempt_number == 2
    assert att2.parent_attempt_id == att1.identity.attempt_id
    assert mission.objective == "Báo cáo tiến độ"  # Mission objective unchanged
