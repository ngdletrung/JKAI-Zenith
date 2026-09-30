# -*- coding: utf-8 -*-
"""
tests/test_tier2_backend_contract.py
Contract tests for Tier2Backend Protocol and its implementations.
"""

from __future__ import annotations

import time
import pytest

from core.cognitive_bus.backends import (
    build,
    build_active,
    list_registered,
    register,
)
from core.cognitive_bus.backends.fake_backend import FakeTier2Backend
from core.cognitive_bus.backends.local_reflex_backend import LocalReflexTier2Backend
from core.cognitive_bus.decision_substrate_adapter import (
    DecisionPrimitive,
    ExecutionTier,
    TriTierDecisionAdapter,
)
from core.cognitive_bus.tier2_backend import BackendMetadata, Tier2Backend


# ---------------------------------------------------------------------------
# Protocol conformance
# ---------------------------------------------------------------------------

class TestProtocolConformance:

    def test_fake_satisfies_protocol(self):
        assert isinstance(FakeTier2Backend(), Tier2Backend)

    def test_sovereign_reflex_satisfies_protocol(self):
        assert isinstance(LocalReflexTier2Backend(), Tier2Backend)

    def test_protocol_requires_key_methods(self):
        class Incomplete:
            pass
        assert not isinstance(Incomplete(), Tier2Backend)


# ---------------------------------------------------------------------------
# FakeTier2Backend behavior
# ---------------------------------------------------------------------------

class TestFakeBackend:

    def test_load_unload_idempotent(self):
        b = FakeTier2Backend()
        assert not b.is_loaded()
        b.load()
        b.load()  # must not raise
        assert b.is_loaded()
        b.unload()
        b.unload()
        assert not b.is_loaded()

    def test_predict_before_load_raises(self):
        b = FakeTier2Backend()
        with pytest.raises(RuntimeError, match="before load"):
            b.predict({}, [(DecisionPrimitive.BOOLEAN, "q", None)])

    def test_predict_returns_packet_per_question(self):
        b = FakeTier2Backend(confidence=0.9)
        b.load()
        out = b.predict({}, [
            (DecisionPrimitive.BOOLEAN, "q1", None),
            (DecisionPrimitive.CHOICE, "q2", ["a", "b"]),
            (DecisionPrimitive.SCORE, "q3", ["0", "1", "2"]),
        ])
        assert set(out.keys()) == {"q1", "q2", "q3"}

    def test_packet_tier_is_tier2_local(self):
        b = FakeTier2Backend()
        b.load()
        out = b.predict({}, [(DecisionPrimitive.BOOLEAN, "q", None)])
        assert out["q"].execution_tier == ExecutionTier.TIER_2_LOCAL

    def test_distribution_sums_to_one(self):
        b = FakeTier2Backend(confidence=0.88)
        b.load()
        out = b.predict({}, [
            (DecisionPrimitive.BOOLEAN, "b", None),
            (DecisionPrimitive.CHOICE, "c", ["x", "y", "z"]),
            (DecisionPrimitive.SCORE, "s", ["0", "1", "2", "3", "4"]),
        ])
        for q, p in out.items():
            assert sum(p.distribution.values()) == pytest.approx(1.0, abs=1e-6), q

    def test_latency_measured_not_hardcoded(self):
        b = FakeTier2Backend(delay_ms=5.0)
        b.load()
        out = b.predict({}, [(DecisionPrimitive.BOOLEAN, "q", None)])
        assert out["q"].latency_ms >= 5.0

    def test_deterministic_across_calls(self):
        b = FakeTier2Backend(confidence=0.77)
        b.load()
        qs = [(DecisionPrimitive.BOOLEAN, "q", None)]
        r1 = b.predict({"x": 1}, qs)
        r2 = b.predict({"x": 1}, qs)
        assert r1["q"].result == r2["q"].result
        assert r1["q"].confidence == r2["q"].confidence
        assert dict(r1["q"].distribution) == dict(r2["q"].distribution)

    def test_failure_mode_raise(self):
        b = FakeTier2Backend(failure_mode="raise")
        b.load()
        with pytest.raises(RuntimeError, match="fake backend failure"):
            b.predict({}, [(DecisionPrimitive.BOOLEAN, "q", None)])

    def test_failure_mode_low_conf(self):
        b = FakeTier2Backend(failure_mode="low_conf")
        b.load()
        out = b.predict({}, [(DecisionPrimitive.BOOLEAN, "q", None)])
        assert out["q"].confidence < 0.5

    def test_failure_mode_bad_dist(self):
        b = FakeTier2Backend(failure_mode="bad_dist")
        b.load()
        out = b.predict({}, [(DecisionPrimitive.SCORE, "q", ["0", "1", "2"])])
        assert sum(out["q"].distribution.values()) != pytest.approx(1.0)


# ---------------------------------------------------------------------------
# Registry
# ---------------------------------------------------------------------------

class TestRegistry:

    def test_fake_registered(self):
        assert "fake" in list_registered()

    def test_build_fake(self):
        b = build("fake")
        assert isinstance(b, FakeTier2Backend)

    def test_build_unknown_raises(self):
        with pytest.raises(KeyError, match="Unknown Tier 2 backend"):
            build("nonexistent-backend")

    def test_build_active_returns_backend(self):
        b = build_active()
        assert isinstance(b, Tier2Backend)

    def test_custom_registration(self):
        marker = {"called": False}

        def factory():
            marker["called"] = True
            return FakeTier2Backend()

        register("test-custom", factory)
        build("test-custom")
        assert marker["called"] is True


# ---------------------------------------------------------------------------
# Integration with TriTierDecisionAdapter
# ---------------------------------------------------------------------------

class TestAdapterTier2Integration:

    def _make(self, backend):
        return TriTierDecisionAdapter(
            enable_mock=False,
            record_shadow=False,
            tier2_backend=backend,
        )

    def test_tier2_success_path(self):
        b = FakeTier2Backend(confidence=0.99)
        a = self._make(b)
        verdict = a.evaluate_parallel_batch(
            {"body": "benign"},
            [(DecisionPrimitive.BOOLEAN, "is this safe?", None)],
        )
        assert verdict.execution_tier == ExecutionTier.TIER_2_LOCAL

    def test_tier2_low_conf_falls_through_to_tier3(self):
        b = FakeTier2Backend(failure_mode="low_conf")
        a = self._make(b)
        verdict = a.evaluate_parallel_batch(
            {"body": "benign"},
            [(DecisionPrimitive.BOOLEAN, "is this safe?", None)],
        )
        assert verdict.execution_tier in (
            ExecutionTier.TIER_3_RULE, ExecutionTier.ESCALATE
        )

    def test_tier2_raise_opens_circuit(self):
        b = FakeTier2Backend(failure_mode="raise")
        a = self._make(b)
        a.circuit_breaker.failure_threshold = 2

        for _ in range(2):
            a.evaluate_parallel_batch(
                {"body": "x"},
                [(DecisionPrimitive.BOOLEAN, "q", None)],
            )
        assert a.circuit_breaker.state == "OPEN"

    def test_tier2_bad_distribution_rejected(self):
        b = FakeTier2Backend(failure_mode="bad_dist")
        a = self._make(b)
        # Adapter must reject and fall through, not propagate malformed data
        verdict = a.evaluate_parallel_batch(
            {"body": "x"},
            [(DecisionPrimitive.BOOLEAN, "q", None)],
        )
        # Should not have TIER_2_LOCAL tier because contract validator rejected
        assert verdict.execution_tier != ExecutionTier.TIER_2_LOCAL

    def test_no_backend_configured_falls_through_to_tier3(self):
        a = TriTierDecisionAdapter(enable_mock=False, record_shadow=False)
        verdict = a.evaluate_parallel_batch(
            {"body": "x"},
            [(DecisionPrimitive.BOOLEAN, "q", None)],
        )
        assert verdict.execution_tier in (
            ExecutionTier.TIER_3_RULE, ExecutionTier.ESCALATE
        )


# ---------------------------------------------------------------------------
# Metadata contract
# ---------------------------------------------------------------------------

class TestMetadata:

    def test_fake_declares_local_only(self):
        md = FakeTier2Backend().metadata()
        assert md.is_local_only is True

    def test_sovereign_reflex_declares_uncalibrated(self):
        md = LocalReflexTier2Backend().metadata()
        assert md.calibration_state == "uncalibrated"
        assert md.ece is None
        assert md.is_local_only is True
