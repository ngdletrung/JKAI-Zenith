# -*- coding: utf-8 -*-
"""
Unit test suite cho MissionCompletionGate & RecoveryManager (D1, D21, D24)
"""

import pytest
from core.os.cognition.mission_completion_gate import MissionCompletionGate, RecoveryManager
from core.os.cognition.deep_schemas import (
    MissionCriterion,
    CriterionStatus,
    MissionOutcomeStatus,
    RecoveryPolicyType
)


class TestMissionCompletionGate:
    """Kiểm tra tính nghiêm ngặt của cổng hoàn tất sứ mệnh và chính sách phục hồi."""

    def test_completion_gate_all_verified(self):
        c1 = MissionCriterion(criterion_id="c1", description="Excel created", status=CriterionStatus.VERIFIED)
        c2 = MissionCriterion(criterion_id="c2", description="Integrity verified", status=CriterionStatus.VERIFIED)

        outcome = MissionCompletionGate.evaluate(
            mission_id="m_100",
            criteria=[c1, c2],
            verification_context_hash="hash123",
            evidence_count=2
        )

        assert outcome.status == MissionOutcomeStatus.COMPLETED_VERIFIED
        assert outcome.success_criteria_verified == 2
        assert outcome.success_criteria_unresolved == 0

    def test_completion_gate_partial_verified(self):
        c1 = MissionCriterion(criterion_id="c1", description="Search done", status=CriterionStatus.VERIFIED)
        c2 = MissionCriterion(criterion_id="c2", description="File formatted", status=CriterionStatus.UNVERIFIED)

        outcome = MissionCompletionGate.evaluate(
            mission_id="m_101",
            criteria=[c1, c2],
            verification_context_hash="hash456",
            evidence_count=1
        )

        assert outcome.status == MissionOutcomeStatus.COMPLETED_WITH_LIMITATIONS
        assert outcome.success_criteria_verified == 1
        assert outcome.success_criteria_unresolved == 1

    def test_recovery_manager_resolves_policies(self):
        assert RecoveryManager.resolve_policy("SYNTAX_ERROR") == RecoveryPolicyType.RETRY
        assert RecoveryManager.resolve_policy("SAFETY_VIOLATION") == RecoveryPolicyType.ABORT
        assert RecoveryManager.resolve_policy("PREMISE_FALSIFIED") == RecoveryPolicyType.REPLAN
        assert RecoveryManager.resolve_policy("TOOL_TIMEOUT_UNKNOWN") == RecoveryPolicyType.RECONCILE
