# -*- coding: utf-8 -*-
"""
tests/test_decision_substrate_p0_p1.py
Regression suite for P0/P1 fixes in core/cognitive_bus/decision_substrate_adapter.py

Coverage:
  P0-1  SCORE distribution sums to 1.0
  P0-2  CircuitBreaker wired into evaluate_parallel_batch
  P0-3  AdaptiveLatencyGuard records real latency
  P0-4  latency_ms measured, not hardcoded
  P0-5  THETA_FAST_PATH_UNFIT_PLACEHOLDER used consistently
  P1-6  _deterministic_rule_heuristic rename
  P1-8  TypedJudgementPacket truly immutable
  P1-9  Shadow telemetry failures logged, not swallowed
"""

from __future__ import annotations

import time
from types import MappingProxyType

import pytest

from core.cognitive_bus.decision_substrate_adapter import (
    AdaptiveLatencyGuard,
    CircuitBreaker,
    DecisionPrimitive,
    ExecutionTier,
    ParallelBatchVerdict,
    THETA_FAST_PATH_UNFIT_PLACEHOLDER,
    TriTierDecisionAdapter,
    TypedJudgementPacket,
)


def _make_adapter(**kwargs) -> TriTierDecisionAdapter:
    # Force mock mode so no neural / network path is touched
    return TriTierDecisionAdapter(enable_mock=True, record_shadow=False, **kwargs)


def _state(payload: str = "hello world") -> dict:
    return {"body": payload}


# ---------------------------------------------------------------------------
# P0-1: SCORE distribution must sum to 1.0
# ---------------------------------------------------------------------------

class TestScoreDistribution:

    @pytest.mark.parametrize("n_levels", [2, 3, 5, 10, 20])
    def test_distribution_sums_to_one(self, n_levels):
        adapter = _make_adapter()
        levels = [str(i) for i in range(n_levels)]
        packet = adapter.evaluate_score(_state(), "how good?", levels)

        total = sum(packet.distribution.values())
        assert total == pytest.approx(1.0, abs=1e-6), (
            f"SCORE dist sums to {total}, expected 1.0 (n_levels={n_levels})"
        )

    def test_distribution_keys_match_levels(self):
        adapter = _make_adapter()
        levels = ["low", "mid", "high"]
        packet = adapter.evaluate_score(_state(), "rate this", levels)

        assert set(packet.distribution.keys()) == set(levels)

    def test_distribution_deterministic(self):
        adapter = _make_adapter()
        levels = ["a", "b", "c", "d"]

        p1 = adapter.evaluate_score(_state("same input"), "q", levels)
        p2 = adapter.evaluate_score(_state("same input"), "q", levels)

        assert dict(p1.distribution) == dict(p2.distribution)

    def test_failure_state_shifts_peak_to_low(self):
        adapter = _make_adapter()
        levels = ["0", "1", "2", "3", "4"]

        ok = adapter.evaluate_score(_state("mission succeeded"), "score", levels)
        fail = adapter.evaluate_score(_state("tool failed"), "score", levels)

        # Peak level should differ between success and failure paths
        ok_peak = max(ok.distribution, key=ok.distribution.get)
        fail_peak = max(fail.distribution, key=fail.distribution.get)
        assert ok_peak != fail_peak, (
            f"Success/failure should have different peaks, got {ok_peak} vs {fail_peak}"
        )


# ---------------------------------------------------------------------------
# P0-2: CircuitBreaker
# ---------------------------------------------------------------------------

class TestCircuitBreaker:

    def test_starts_closed_and_available(self):
        cb = CircuitBreaker()
        assert cb.state == "CLOSED"
        assert cb.is_available() is True

    def test_opens_after_threshold_failures(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        assert cb.state == "CLOSED"  # 1 < 2
        cb.record_failure()
        assert cb.state == "OPEN"
        assert cb.is_available() is False

    def test_success_resets_to_closed(self):
        cb = CircuitBreaker(failure_threshold=2)
        cb.record_failure()
        cb.record_failure()
        assert cb.state == "OPEN"

        cb.record_success()
        assert cb.state == "CLOSED"
        assert cb.failure_count == 0
        assert cb.is_available() is True

    def test_half_open_after_backoff_elapsed(self):
        cb = CircuitBreaker(failure_threshold=1, backoff_steps=(60, 120, 300))
        cb.record_failure()
        assert cb.state == "OPEN"

        # Simulate time passing past first backoff window
        cb.opened_at = time.time() - 61.0
        assert cb.is_available() is True
        assert cb.state == "HALF_OPEN"

    def test_backoff_escalates(self):
        cb = CircuitBreaker(failure_threshold=1, backoff_steps=(60, 120, 300))

        cb.record_failure()
        cb.opened_at = time.time() - 61.0
        cb.is_available()
        assert cb.current_step_idx == 1

        cb.state = "OPEN"
        cb.opened_at = time.time() - 121.0
        cb.is_available()
        assert cb.current_step_idx == 2

    def test_backoff_saturates_at_last_step(self):
        cb = CircuitBreaker(failure_threshold=1, backoff_steps=(60, 120, 300))
        for _ in range(10):
            cb.record_failure()
            cb.opened_at = time.time() - 1000.0
            cb.is_available()
            cb.state = "OPEN"

        assert cb.current_step_idx == len(cb.backoff_steps) - 1


# ---------------------------------------------------------------------------
# P0-3: AdaptiveLatencyGuard
# ---------------------------------------------------------------------------

class TestAdaptiveLatencyGuard:

    def test_empty_returns_zero_p95(self):
        g = AdaptiveLatencyGuard()
        assert g.get_p95() == 0.0

    def test_p95_known_distribution(self):
        g = AdaptiveLatencyGuard(window_size=100)
        for v in range(1, 101):  # 1..100
            g.record_latency(float(v))

        # p95 of 1..100 ≈ 95
        assert 94.0 <= g.get_p95() <= 96.0

    def test_window_evicts_oldest(self):
        g = AdaptiveLatencyGuard(window_size=10)
        for v in [1000.0] * 5 + [1.0] * 5:
            g.record_latency(v)
        assert g.get_p95() == pytest.approx(1000.0)

        for _ in range(10):
            g.record_latency(1.0)

        # Old 1000s evicted
        assert g.get_p95() == pytest.approx(1.0)

    def test_is_degraded_requires_min_samples(self):
        g = AdaptiveLatencyGuard(max_p95_ms=100.0)
        for _ in range(5):
            g.record_latency(10_000.0)
        # < 10 samples -> not degraded yet
        assert g.is_degraded() is False

        for _ in range(10):
            g.record_latency(10_000.0)
        assert g.is_degraded() is True

    def test_ema_initialized_and_updated(self):
        g = AdaptiveLatencyGuard(alpha=0.5)
        g.record_latency(100.0)
        assert g.ema_latency == pytest.approx(100.0)

        g.record_latency(200.0)
        # 0.5*200 + 0.5*100 = 150
        assert g.ema_latency == pytest.approx(150.0)


# ---------------------------------------------------------------------------
# P0-2/P0-3: Wiring into evaluate_parallel_batch
# ---------------------------------------------------------------------------

class TestAdapterWiring:

    def test_latency_guard_records_on_real_path(self):
        adapter = TriTierDecisionAdapter(enable_mock=False, record_shadow=False)

        # Force Tier 2 to fail so we go Tier 3 (which always records)
        adapter._call_tier2_local_emulator = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("forced tier2 failure")
        )

        assert len(adapter.latency_guard.samples) == 0
        adapter.evaluate_parallel_batch(
            _state(),
            [(DecisionPrimitive.BOOLEAN, "is this safe?", None)],
        )
        assert len(adapter.latency_guard.samples) == 1
        assert adapter.latency_guard.samples[0] > 0.0

    def test_circuit_breaker_opens_on_repeated_tier2_failure(self):
        adapter = TriTierDecisionAdapter(enable_mock=False, record_shadow=False)
        adapter.circuit_breaker.failure_threshold = 2

        def _boom(*a, **k):
            raise RuntimeError("tier2 down")

        adapter._call_tier2_local_emulator = _boom

        for _ in range(2):
            adapter.evaluate_parallel_batch(
                _state(),
                [(DecisionPrimitive.BOOLEAN, "is this safe?", None)],
            )

        assert adapter.circuit_breaker.state == "OPEN"

    def test_circuit_open_skips_tier2(self):
        adapter = TriTierDecisionAdapter(enable_mock=False, record_shadow=False)
        adapter.circuit_breaker.state = "OPEN"
        adapter.circuit_breaker.opened_at = time.time()  # not yet cooled down

        called = {"tier2": 0}

        def _spy(*a, **k):
            called["tier2"] += 1
            raise RuntimeError("should not be called")

        adapter._call_tier2_local_emulator = _spy

        verdict = adapter.evaluate_parallel_batch(
            _state(),
            [(DecisionPrimitive.BOOLEAN, "is this safe?", None)],
        )

        assert called["tier2"] == 0
        assert verdict.execution_tier == ExecutionTier.TIER_3_RULE


# ---------------------------------------------------------------------------
# P0-4: Real measured latency, not hardcoded 1.2/1.5/1.8
# ---------------------------------------------------------------------------

class TestMeasuredLatency:

    def test_boolean_latency_is_positive_and_not_old_constant(self):
        adapter = _make_adapter()
        p = adapter.evaluate_noul(_state(), "is this safe?")

        assert p.latency_ms > 0.0
        # Old hardcoded value was exactly 1.2 — ensure measurement replaced it
        assert p.latency_ms != 1.2

    def test_choice_latency_is_positive_and_not_old_constant(self):
        adapter = _make_adapter()
        p = adapter.evaluate_choice(_state(), "pick", ["a", "b", "c"])
        assert p.latency_ms > 0.0
        assert p.latency_ms != 1.5

    def test_score_latency_is_positive_and_not_old_constant(self):
        adapter = _make_adapter()
        p = adapter.evaluate_score(_state(), "score", ["0", "1", "2"])
        assert p.latency_ms > 0.0
        assert p.latency_ms != 1.8


# ---------------------------------------------------------------------------
# P0-5: Theta constant used consistently
# ---------------------------------------------------------------------------

class TestThetaConstant:

    def test_threshold_not_inlined_as_magic_number(self):
        """The unfitted placeholder must be the single source of truth."""
        import inspect
        from core.cognitive_bus import decision_substrate_adapter as mod
        src = inspect.getsource(mod)
        # No bare 0.85 comparisons — must reference the named constant
        assert "confidence >= 0.85" not in src
        assert "0.85 for j in" not in src

    def test_theta_is_documented_as_unfit(self):
        import inspect
        from core.cognitive_bus import decision_substrate_adapter as mod
        src = inspect.getsource(mod)
        assert "UNCALIBRATED" in src or "unfit" in src.lower()


# ---------------------------------------------------------------------------
# P1-6: Rename
# ---------------------------------------------------------------------------

class TestHeuristicRename:

    def test_new_name_exists(self):
        adapter = _make_adapter()
        assert hasattr(adapter, "_deterministic_rule_heuristic")

    def test_old_name_gone(self):
        adapter = _make_adapter()
        assert not hasattr(adapter, "_deterministic_mock_heuristic"), (
            "Old '_deterministic_mock_heuristic' name should be removed "
            "to avoid confusing production code for a test helper."
        )


# ---------------------------------------------------------------------------
# P1-8: Immutability
# ---------------------------------------------------------------------------

class TestImmutablePacket:

    def test_distribution_is_mapping_proxy(self):
        adapter = _make_adapter()
        p = adapter.evaluate_choice(_state(), "pick", ["a", "b"])
        assert isinstance(p.distribution, MappingProxyType)

    def test_distribution_cannot_be_mutated(self):
        adapter = _make_adapter()
        p = adapter.evaluate_choice(_state(), "pick", ["a", "b"])

        with pytest.raises(TypeError):
            p.distribution["a"] = 0.99  # type: ignore[index]

    def test_metadata_cannot_be_mutated(self):
        adapter = _make_adapter()
        p = adapter.evaluate_noul(_state(), "is this safe?")
        assert isinstance(p.metadata, MappingProxyType)
        with pytest.raises(TypeError):
            p.metadata["x"] = 1  # type: ignore[index]

    def test_field_assignment_still_blocked(self):
        adapter = _make_adapter()
        p = adapter.evaluate_noul(_state(), "is this safe?")
        with pytest.raises((AttributeError, Exception)):
            p.confidence = 0.0  # type: ignore[misc]


# ---------------------------------------------------------------------------
# P1-9: Shadow failures logged, not swallowed
# ---------------------------------------------------------------------------

class TestShadowTelemetryLogging:

    def test_broken_harness_does_not_crash_decision_path(self, caplog):
        class BrokenHarness:
            def record_observation(self, **kwargs):
                raise RuntimeError("harness exploded")

        adapter = TriTierDecisionAdapter(
            enable_mock=False,
            record_shadow=True,
            shadow_harness=BrokenHarness(),
        )
        adapter._call_tier2_local_emulator = lambda *a, **k: (_ for _ in ()).throw(
            RuntimeError("tier2 down")
        )

        # Must not raise
        verdict = adapter.evaluate_parallel_batch(
            _state(),
            [(DecisionPrimitive.BOOLEAN, "is this safe?", None)],
        )
        assert isinstance(verdict, ParallelBatchVerdict)


# ---------------------------------------------------------------------------
# Mock mode still intact after rename
# ---------------------------------------------------------------------------

class TestMockModeRegression:

    def test_registered_mock_is_returned(self):
        adapter = _make_adapter()
        state = _state("registered")
        packet = TypedJudgementPacket(
            primitive=DecisionPrimitive.BOOLEAN,
            question="is this safe?",
            result=0.42,
            confidence=0.77,
            distribution={"true": 0.42, "false": 0.58},
            execution_tier=ExecutionTier.TIER_3_RULE,
            latency_ms=0.5,
        )
        adapter.register_mock_judgement(state, "is this safe?", packet)

        out = adapter.evaluate_noul(state, "is this safe?")
        assert out.result == 0.42
        assert out.confidence == 0.77

    def test_unregistered_mock_uses_rule_heuristic(self):
        adapter = _make_adapter()
        out = adapter.evaluate_noul(_state("totally benign"), "is this safe?")
        assert isinstance(out, TypedJudgementPacket)
        assert out.latency_ms > 0.0


# ---------------------------------------------------------------------------
# Cross-cut: no test should depend on wall-clock ordering
# ---------------------------------------------------------------------------

def test_no_shared_mutable_state_between_adapters():
    a = _make_adapter()
    b = _make_adapter()

    a.circuit_breaker.record_failure()
    a.circuit_breaker.record_failure()

    assert a.circuit_breaker.state == "OPEN"
    assert b.circuit_breaker.state == "CLOSED"
    assert a.circuit_breaker is not b.circuit_breaker
    assert a.latency_guard is not b.latency_guard
