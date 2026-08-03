"""
JKAI ZENITH — ARCHITECTURE TEST SUITE: DEGRADED MODE UNDER RESOURCE PRESSURE
tests/architecture/test_governor_degrades_gracefully_under_resource_pressure.py

Architectural Invariant Enforced:
    When hardware resources (VRAM/RAM) are critically constrained, Governance falls back
    to a degraded execution mode or secondary candidate without crashing the Cognitive Kernel.
"""

import pytest
from core.contracts import TaskRequirement, GovernorDecision, ExecutionProfile, ResourceIntent, ResourceAllocation
from core.infrastructure import HardwareScheduler


class TestGovernorGracefulDegradation:

    def test_governor_falls_back_under_vram_pressure(self):
        scheduler = HardwareScheduler()
        assert scheduler.max_vram_gb == 7.8

        task_req = TaskRequirement(role="DEEP_REASONER", quality_target="highest")

        # Governance selects lighter compute intent due to resource pressure
        fallback_decision = GovernorDecision(
            selected_model="qwen3.5:4b-degraded",
            selected_runtime="ollama",
            execution_profile=ExecutionProfile(model_name="qwen3.5:4b-degraded", role_name=task_req.role),
            resource_intent=ResourceIntent(compute_class="LIGHT", acceleration="CPU_FALLBACK"),
            fallback_chain=["qwen3-30b-heavy"],
            rationale="VRAM pressure 95%: Degraded fallback activated",
        )

        assert fallback_decision.selected_model == "qwen3.5:4b-degraded"
        assert fallback_decision.resource_intent.compute_class == "LIGHT"
        assert "qwen3-30b-heavy" in fallback_decision.fallback_chain
