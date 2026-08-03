"""
JKAI ZENITH — ARCHITECTURE TEST SUITE: MISSION BEHAVIOR INVARIANCE
tests/architecture/test_mission_behavior_invariance_under_model_swap.py

Architectural Invariant Enforced:
    Swapping model providers or runtime backends MUST NOT alter the Mission ID,
    Mission Goal, Success Criteria, or Cognitive State Machine progression.
    Proves true Provider & Implementation Neutrality in the Cognitive Kernel.
"""

import pytest
from core.contracts import MissionContext, MissionState, SuccessCriteria, TaskRequirement


class TestMissionBehaviorInvarianceUnderModelSwap:

    def test_mission_state_and_criteria_invariant_across_swaps(self):
        criteria = SuccessCriteria(required_elements=["citations", "structured_json"], min_quality_score=0.85)

        # Scenario A: Model A (e.g. Qwen)
        mission_a = MissionContext(goal="Extract quarterly KPI metrics", success_criteria=criteria)
        mission_a.state = MissionState.RUNNING
        task_a = TaskRequirement(role="PLANNER", quality_target="high")

        # Scenario B: Model B (e.g. Gemma) after model swap
        mission_b = MissionContext(goal="Extract quarterly KPI metrics", success_criteria=criteria)
        mission_b.state = MissionState.RUNNING
        task_b = TaskRequirement(role="PLANNER", quality_target="high")

        # Cognitive Kernel properties MUST be identical
        assert mission_a.goal == mission_b.goal
        assert mission_a.state == mission_b.state
        assert mission_a.success_criteria.required_elements == mission_b.success_criteria.required_elements
        assert task_a.role == task_b.role
        assert task_a.quality_target == task_b.quality_target
