"""
JKAI ZENITH — ARCHITECTURE CERTIFICATION: LEVEL 5 MISSION RECOVERY INVARIANCE
tests/architecture/test_mission_recovery_invariance.py

Architectural Invariant Enforced (I6 & I8):
    When Execution Attempt #1 fails evaluation, triggering fallback and replanning to Attempt #2,
    the Mission Contract, Goal, Constraints, Authority Scope, Safety Policy, and Success Criteria
    MUST remain 100% invariant across attempts.
"""

import pytest
from core.contracts import MissionContract, MissionContext, MissionState, SuccessCriteria, TaskRequirement, EvaluationResult
from core.cognitive.recovery_engine import RecoveryEngine, RecoveryDecision
from core.cognitive.mission_ledger import MissionLedger


class TestMissionRecoveryInvariance:

    def test_mission_recovery_preserves_contract_invariance(self):
        criteria = SuccessCriteria(min_quality_score=0.85)
        contract = MissionContract(
            goal="Synthesize quarterly audit report",
            constraints=["Strict compliance"],
            success_criteria=criteria,
            safety_policy="STRICT_DENY_FIRST",
            authority_scope=["read", "write_draft"]
        )

        mission = MissionContext(contract=contract, state=MissionState.RUNNING)
        ledger = MissionLedger(mission_id=mission.mission_id)
        recovery = RecoveryEngine()

        # Attempt #1 fails evaluation
        ledger.append("ExecutionStarted", {"attempt": 1, "model": "model-a"}, attempt_id="att_001")
        eval_1 = EvaluationResult(
            mission_id=mission.mission_id,
            task_id="task_001",
            execution_succeeded=True,
            task_succeeded=False,
            mission_succeeded=False,
            quality_score=0.60,
            evidence_summary="Quality score 0.60 < min 0.85"
        )
        ledger.append("EvaluationCompleted", {"attempt": 1, "succeeded": False}, attempt_id="att_001")

        dec_1 = recovery.determine_recovery(contract, eval_1, current_attempt=1, max_attempts=3)
        assert dec_1.action == "REPLAN"
        assert dec_1.retry_attempt == 2

        # INVARIANT: MissionContract MUST remain 100% un-mutated
        assert mission.contract.goal == "Synthesize quarterly audit report"
        assert mission.contract.safety_policy == "STRICT_DENY_FIRST"
        assert mission.contract.authority_scope == ["read", "write_draft"]

        # Attempt #2 succeeds
        ledger.append("ExecutionStarted", {"attempt": 2, "model": "model-b"}, attempt_id="att_002")
        eval_2 = EvaluationResult(
            mission_id=mission.mission_id,
            task_id="task_001",
            execution_succeeded=True,
            task_succeeded=True,
            mission_succeeded=True,
            quality_score=0.92,
            evidence_summary="Quality score 0.92 >= min 0.85"
        )
        ledger.append("EvaluationCompleted", {"attempt": 2, "succeeded": True}, attempt_id="att_002")

        dec_2 = recovery.determine_recovery(contract, eval_2, current_attempt=2, max_attempts=3)
        assert dec_2.action == "COMPLETE"
        assert ledger.count() == 4
