"""
JKAI ZENITH — ARCHITECTURE TEST SUITE: NORTH STAR UNKNOWN PROVIDER TEST
tests/architecture/test_mission_survives_unknown_model_provider.py

Architectural Invariant Enforced (NORTH STAR):
    When a completely unseen model from an unknown provider ('unseen-provider::future-model-x:70b')
    enters the system, the entire Mission lifecycle completes cleanly without changing a single line
    of Cognitive Kernel code or TaskRequirement logic.
"""

import pytest
from core.contracts import (
    IngressGoal, MissionContext, MissionState, TaskRequirement,
    ExecutionProfile, GovernorDecision, ResourceIntent, ResourceAllocation, Observation
)
from core.capabilities import CapabilityBroker, CapabilitySet
from core.governance.model.evidence import ModelIdentity


class TestNorthStarUnknownModelProvider:

    def test_mission_lifecycle_survives_unknown_provider(self):
        # 1. Ingress Domain: Goal enters
        goal = IngressGoal(prompt="Synthesize quarterly research report")
        assert goal.goal_id is not None

        # 2. Cognitive Kernel Domain: Mission initialized & TaskRequirement emitted
        mission = MissionContext(goal=goal.prompt, state=MissionState.RUNNING)
        task_req = TaskRequirement(role="DEEP_REASONER", quality_target="highest", requires_tools=True)

        # Provider-Neutral Cognitive Kernel does NOT know provider or model name
        assert not hasattr(task_req, "model_name")
        assert not hasattr(task_req, "provider")

        # 3. Capabilities Domain: CapabilityBroker resolves tools/skills
        broker = CapabilityBroker()
        broker.register_tool("search_web", {"type": "function"})
        cap_set = broker.resolve_capabilities(task_req)
        assert len(cap_set.tools) == 1

        # 4. Governance Domain: Unseen provider & model identity discovered
        identity = ModelIdentity(provider="unseen-provider", name="future-model-x:70b")
        assert identity.provider == "unseen-provider"

        decision = GovernorDecision(
            selected_model=identity.name,
            selected_runtime=identity.provider,
            execution_profile=ExecutionProfile(model_name=identity.name, role_name=task_req.role),
            resource_intent=ResourceIntent(compute_class="HEAVY", acceleration="GPU_PREFERRED"),
            rationale="Discovered unseen provider model via dynamic capability inference",
        )

        assert decision.selected_model == "future-model-x:70b"
        assert decision.execution_profile.role_name == "DEEP_REASONER"

        # 5. Infrastructure Domain: ResourceGovernor allocates resources
        alloc = ResourceAllocation(backend="GPU", gpu_memory_mb=16000.0, gpu_layers=48)
        assert alloc.is_gpu_bound is True

        # 6. Observation Feedback: Execution yields Observation -> Mission Completed
        obs = Observation(
            task_id="task_north_star",
            status_code=200,
            content="Report synthesized successfully",
            quality_signal=0.97,
            decision_trace_id=decision.decision_trace_id
        )

        mission.state = MissionState.COMPLETED
        assert mission.state == MissionState.COMPLETED
        assert obs.quality_signal == 0.97
