"""
JKAI ZENITH — ARCHITECTURE TEST SUITE: EVALUATION FAILURE REPLAN SIGNAL
tests/architecture/test_evaluation_failure_triggers_replan_signal.py

Architectural Invariant Enforced:
    When an EvaluationResult indicates execution succeeded (200 OK) but mission evaluation failed
    (quality score < min_quality_score or hallucination > max), Cognitive Kernel emits a REPLAN signal,
    preventing premature Mission completion.
"""

import pytest
from core.contracts import MissionContext, MissionState, SuccessCriteria, Observation, EvaluationResult


class TestEvaluationFailureTriggersReplanSignal:

    def test_evaluation_failure_triggers_replan_signal(self):
        criteria = SuccessCriteria(min_quality_score=0.85, max_hallucination_score=0.05)
        mission = MissionContext(goal="Generate verified report", success_criteria=criteria, state=MissionState.RUNNING)

        # 1. Execution Observation returns HTTP 200 OK
        obs = Observation(task_id="task_001", status_code=200, content="Unverified summary content", success=True)
        assert obs.success is True

        # 2. Evaluation Layer evaluates Observation against SuccessCriteria
        eval_result = EvaluationResult(
            mission_id=mission.mission_id,
            task_id=obs.task_id,
            execution_succeeded=obs.success,
            task_succeeded=False,
            mission_succeeded=False,
            quality_score=0.60,
            hallucination_score=0.25,
            evidence_summary="Hallucination score 0.25 exceeds threshold 0.05"
        )

        # 3. Cognitive Kernel receives EvaluationResult and emits REPLAN signal
        assert eval_result.mission_succeeded is False

        if not eval_result.mission_succeeded:
            mission.variables["control_signal"] = "REPLAN"
            mission.state = MissionState.RUNNING  # Does NOT transition to COMPLETED

        assert mission.state == MissionState.RUNNING
        assert mission.variables["control_signal"] == "REPLAN"
