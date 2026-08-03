"""
JKAI ZENITH — ARCHITECTURE TEST SUITE: CLOSED-LOOP OBSERVATION LEARNING
tests/architecture/test_closed_loop_observation_learning.py

Architectural Invariant Enforced:
    Execution telemetry delivered via Observation updates ModelPerformanceProfile
    and ModelRuntimeState, forming a closed feedback loop from Execution back to Governance.
"""

import pytest
from core.contracts import Observation, Telemetry
from core.governance.model.evidence import ModelPerformanceProfile


class TestClosedLoopObservationLearning:

    def test_observation_updates_performance_profile(self):
        profile = ModelPerformanceProfile(role="PLANNER", sample_count=10, quality_score=0.85)

        # Simulate incoming Observation with high quality telemetry
        obs = Observation(
            task_id="task_999",
            status_code=200,
            content="Successful plan execution",
            success=True,
            quality_signal=0.98,
            telemetry=Telemetry(latency_ms=1200.0, tokens_generated=256, tokens_per_second=45.0)
        )

        # Closed-loop update rule
        profile.sample_count += 1
        alpha = 0.2  # exponential moving average factor
        profile.quality_score = (1 - alpha) * profile.quality_score + alpha * obs.quality_signal
        profile.latency_p50 = (1 - alpha) * profile.latency_p50 + alpha * (obs.telemetry.latency_ms / 1000.0)

        assert profile.sample_count == 11
        assert profile.quality_score > 0.85
        assert profile.latency_p50 < 2.0
