"""
JKAI ZENITH — ARCHITECTURE TEST SUITE: CAPABILITY MISMATCH ISOLATION
tests/architecture/test_capability_mismatch_never_reaches_runtime.py

Architectural Invariant Enforced:
    A model candidate lacking required capabilities (e.g., vision, tools, min_ctx)
    MUST be filtered out by HardFilter (eligible=False) and MUST NEVER reach the RuntimeAdapter.
"""

import pytest
from core.contracts import TaskRequirement
from core.governance.model.evidence import SuitabilityEngine, CapabilityVector, ModelPerformanceProfile


class TestCapabilityMismatchNeverReachesRuntime:

    def test_capability_mismatch_is_blocked_by_hard_filter(self):
        engine = SuitabilityEngine()
        vector = CapabilityVector(vision=0.0, tool_calling=0.0)
        perf = ModelPerformanceProfile(model_name="text-only-model:7b")

        # Task requiring vision capability
        task_req = TaskRequirement(role="VISION_ANALYST", requires_vision=True)

        # Evaluate suitability
        score = engine.compute_suitability(
            vector=vector,
            perf=perf,
            context_limit=32768,
            has_vision=False,
            has_tools=False,
            task_req=task_req
        )

        # INVARIANT: Must be marked ineligible (suitability = 0.0) and NEVER reach runtime execution
        assert score.eligible is False
        assert score.suitability_score == 0.0
        assert "requires_vision" in score.eligibility_reason
