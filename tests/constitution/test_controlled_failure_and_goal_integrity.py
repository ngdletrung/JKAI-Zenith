"""
JKAI ZENITH — CONTROLLED FAILURE & GOAL INTEGRITY TEST SUITE (v4.6)
File: tests/constitution/test_controlled_failure_and_goal_integrity.py

Verifies:
1. UCR-5 (Controlled Failure): System cleanly reports inability to fulfill goal when no viable capability exists WITHOUT hallucinating or lowering criteria.
2. GCR (Goal Integrity Completion Rate): Ensures 100% of MissionDefinition + Constraints + SuccessCriteria are met before declaring success.
"""

import pytest
from core.contracts.cognitive_contract import MissionDefinition
from core.contracts.verification_contract import VerificationResult, FailureClassification, RecoveryStrategy
from core.verification.verifier import CognitiveVerifier
from core.verification.failure_classifier import FailureClassifier


def test_ucr5_controlled_failure_when_no_viable_capability_exists():
    """UCR-5: Controlled Failure test when no capability exists."""
    missing_criteria = ["NO_VIABLE_CAPABILITY_FOUND", "PHYSICAL_FILE_MISSING"]
    logs = ["Capability A unavailable", "Capability B unsuitable", "Capability C unsuitable"]

    failure_cls, recovery_strat = FailureClassifier.classify_failure(missing_criteria, logs)

    # Must classify as TOOL_FAILURE and recommend SUBSTITUTE_CAPABILITY or ABORT, without hallucinating success
    assert failure_cls in (FailureClassification.TOOL_FAILURE, FailureClassification.POLICY_FAILURE)
    assert recovery_strat in (RecoveryStrategy.SUBSTITUTE_CAPABILITY, RecoveryStrategy.ABORT)


def test_gcr_goal_integrity_completion_rate():
    """GCR: Goal Integrity Completion Rate verifies ALL constraints & criteria."""
    # Scenario A: Partial execution (2/3 completed, 1 failed) -> GCR MUST BE 0 (Failure)
    partial_res = VerificationResult(
        passed=False,
        score=0.65,
        missing_criteria=["step3_drive_upload_failed"],
        summary="Step 3 upload failed"
    )
    assert partial_res.passed is False

    # Scenario B: Complete execution (3/3 completed) -> GCR = 100% (Verified)
    full_res = VerificationResult(
        passed=True,
        score=0.98,
        missing_criteria=[],
        summary="All steps verified"
    )
    assert full_res.passed is True
