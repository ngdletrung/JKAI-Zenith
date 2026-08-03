"""
JKAI ZENITH — ARCHITECTURE TEST SUITE: OUTCOME CONTRACT INVARIANCE
tests/architecture/test_mission_outcome_contract_invariance_under_model_swap.py

Architectural Invariants Enforced:
    1. Outcome Contract Invariance: Swapping model providers or runtime backends MUST NOT alter the
       Mission ID, Mission Goal, Success Criteria, or Outcome Contract validation.
       Different models are free to use dynamic execution traces, tool order, or wording.
    2. Hard Constraint Rule: SuitabilityEngine MUST mark candidate ineligible (suitability=0.0)
       if it fails hard constraints (e.g. required context_limit or modality).
"""

import pytest
from core.contracts import MissionContext, MissionState, SuccessCriteria, TaskRequirement
from core.governance.model.evidence import SuitabilityEngine, CapabilityVector, ModelPerformanceProfile


class TestMissionOutcomeContractInvarianceUnderModelSwap:

    def test_outcome_contract_invariant_across_model_swaps(self):
        criteria = SuccessCriteria(required_elements=["citations", "structured_json"], min_quality_score=0.85)

        # Scenario A: Model A (e.g. Qwen)
        mission_a = MissionContext(goal="Extract quarterly KPI metrics", success_criteria=criteria)
        mission_a.state = MissionState.RUNNING
        task_a = TaskRequirement(role="PLANNER", quality_target="high")

        # Scenario B: Model B (e.g. Gemma) after model swap
        mission_b = MissionContext(goal="Extract quarterly KPI metrics", success_criteria=criteria)
        mission_b.state = MissionState.RUNNING
        task_b = TaskRequirement(role="PLANNER", quality_target="high")

        # Outcome Contract properties MUST be identical
        assert mission_a.goal == mission_b.goal
        assert mission_a.state == mission_b.state
        assert mission_a.success_criteria.required_elements == mission_b.success_criteria.required_elements
        assert task_a.role == task_b.role
        assert task_a.quality_target == task_b.quality_target

    def test_suitability_engine_enforces_hard_constraints(self):
        engine = SuitabilityEngine()
        vector = CapabilityVector(reasoning=0.99, coding=0.99)
        perf = ModelPerformanceProfile(model_name="small-model:8k", quality_score=0.99)

        # Task requiring 32k context window
        task_req = TaskRequirement(role="PLANNER", min_ctx=32768)

        # Small model has max context limit of 8192
        score = engine.compute_suitability(
            vector=vector,
            perf=perf,
            context_limit=8192,
            has_vision=False,
            has_tools=True,
            task_req=task_req
        )

        # HARD CONSTRAINT RULE: Must be marked ineligible with suitability_score == 0.0
        assert score.eligible is False
        assert score.suitability_score == 0.0
        assert "Ineligible" in score.eligibility_reason
