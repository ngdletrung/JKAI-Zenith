"""
JKAI ZENITH — TEST SUITE: FAILURE CLASSIFICATION & MISSION RECONSTRUCTOR
tests/test_failure_classification_recovery.py
"""

import pytest
from core.contracts import EvaluationResult, Observation, MissionState
from core.cognitive.mission_ledger import MissionLedger
from core.cognitive.mission_reconstructor import MissionStateReconstructor
from core.cognitive.failure_classifier import FailureClassifier, FailureClassification


class TestFailureClassificationAndReconstruction:

    def test_failure_classifier_resource_failure(self):
        classifier = FailureClassifier()
        obs = Observation(task_id="t1", status_code=507, content="Out of memory")
        eval_res = EvaluationResult(mission_id="m1", task_id="t1", mission_succeeded=False)

        cls = classifier.classify(eval_res, obs)
        assert cls.category == "RESOURCE_FAILURE"
        assert cls.recommended_recovery == "FALLBACK_MODEL"

    def test_failure_classifier_hallucination_failure(self):
        classifier = FailureClassifier()
        eval_res = EvaluationResult(
            mission_id="m1",
            task_id="t1",
            mission_succeeded=False,
            criteria_results={"hallucination_threshold": False, "quality_threshold": True}
        )

        cls = classifier.classify(eval_res)
        assert cls.category == "KNOWLEDGE_FAILURE"
        assert cls.recommended_recovery == "MORE_CONTEXT"

    def test_mission_state_reconstructor_event_sourcing(self):
        ledger = MissionLedger(mission_id="m_recon_001")
        ledger.append("MissionCreated", {})
        ledger.append("ExecutionStarted", {}, attempt_id="a1")
        ledger.append("EvaluationCompleted", {"succeeded": False}, attempt_id="a1")
        ledger.append("ExecutionStarted", {}, attempt_id="a2")
        ledger.append("EvaluationCompleted", {"succeeded": True}, attempt_id="a2")

        reconstructor = MissionStateReconstructor()
        projected_state = reconstructor.reconstruct(ledger)
        assert projected_state == MissionState.COMPLETED
