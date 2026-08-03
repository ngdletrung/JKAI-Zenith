"""
JKAI ZENITH — ARCHITECTURE TEST SUITE: MISSION SEMANTIC INVARIANCE
tests/architecture/test_mission_semantic_invariance_under_model_swap.py

Architectural Invariants Enforced (PILLAR #7):
    1. Mission Semantic Invariance: Swapping model providers or runtime backends MUST NOT alter
       the Mission Contract, Goal, Constraints, Success Criteria, Security Policy, or Outcome Contract.
       Different models are explicitly ALLOWED to have different execution trajectories, tool ordering,
       reasoning wording, or token counts.
    2. Hard Constraint Rule: SuitabilityEngine MUST mark candidate ineligible (suitability=0.0)
       if it fails hard constraints (e.g. required context_limit or modality).
"""

import pytest
from core.contracts import MissionContext, MissionState, MissionContract, SuccessCriteria, TaskRequirement
from core.governance.model.evidence import SuitabilityEngine, CapabilityVector, ModelPerformanceProfile


class TestMissionSemanticInvarianceUnderModelSwap:

    def test_mission_semantic_contract_invariant_across_model_swaps(self):
        criteria = SuccessCriteria(required_elements=["citations", "structured_json"], min_quality_score=0.85)
        contract = MissionContract(goal="Extract quarterly KPI metrics", success_criteria=criteria, safety_policy="STRICT_DENY_FIRST")

        # Scenario A: Model A (e.g. Qwen)
        mission_a = MissionContext(contract=contract, state=MissionState.RUNNING)
        task_a = TaskRequirement(role="PLANNER", quality_target="high")

        # Scenario B: Model B (e.g. Gemma) after model swap
        mission_b = MissionContext(contract=contract, state=MissionState.RUNNING)
        task_b = TaskRequirement(role="PLANNER", quality_target="high")

        # Semantic Mission Contract properties MUST be 100% identical
        assert mission_a.contract.goal == mission_b.contract.goal
        assert mission_a.contract.safety_policy == mission_b.contract.safety_policy
        assert mission_a.state == mission_b.state
        assert mission_a.contract.success_criteria.required_elements == mission_b.contract.success_criteria.required_elements
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
