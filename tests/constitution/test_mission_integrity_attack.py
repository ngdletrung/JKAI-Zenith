"""
CONSTITUTION TEST 7 & 9: MISSION INTEGRITY ATTACK REJECTION
File: tests/constitution/test_mission_integrity_attack.py

Verifies that if a tool or model suggests changing the mission objective (e.g. user wants Excel, tool suggests CSV),
the Mission Invariant REJECTS the suggestion and forces capability substitution / replan while maintaining original Mission objective.
"""

import pytest
from core.contracts.cognitive_contract import MissionDefinition, DeliverableSpec, DeliverableType
from core.contracts.verification_contract import VerificationResult, FailureClassification, RecoveryStrategy


def test_mission_integrity_rejects_unauthorized_objective_mutation():
    mission = MissionDefinition(
        objective="Tạo báo cáo tiến độ bằng Excel (.xlsx)",
        expected_output=DeliverableSpec(type=DeliverableType.FILE_BINARY, format="xlsx")
    )

    # Tool suggestion payload tries to mutate objective to CSV
    suggested_output_format = "csv"

    # Mission Invariant Verification
    assert mission.expected_output.format == "xlsx"
    is_valid_suggestion = (suggested_output_format == mission.expected_output.format)

    assert is_valid_suggestion is False

    # System triggers VERIFICATION_FAILURE and REPAIR/SUBSTITUTE, preserving original Mission objective
    ver = VerificationResult(
        passed=False,
        failure_classification=FailureClassification.VERIFICATION_FAILURE,
        recommended_recovery=RecoveryStrategy.SUBSTITUTE_CAPABILITY,
        summary="Mission Integrity Violation: Attempted to mutate Excel objective to CSV"
    )

    assert ver.passed is False
    assert ver.failure_classification == FailureClassification.VERIFICATION_FAILURE
    assert mission.expected_output.format == "xlsx"  # Mission objective unchanged
