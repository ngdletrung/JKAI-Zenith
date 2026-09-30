# -*- coding: utf-8 -*-
"""
tests/test_tier2_benchmark_harness.py
Tests for the Tier 2 benchmark harness itself (not the backends).
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from core.benchmark.tier2_bench import (
    BenchmarkCase,
    Tier2Benchmark,
    _ece,
    _latency_stats,
)
from core.cognitive_bus.backends.fake_backend import FakeTier2Backend
from core.cognitive_bus.decision_substrate_adapter import DecisionPrimitive


def _cases(n: int = 5) -> list[BenchmarkCase]:
    return [
        BenchmarkCase(
            case_id=f"c{i}",
            state={"body": f"benign {i}"},
            primitive=DecisionPrimitive.BOOLEAN,
            question="is this safe?",
            expected=None,
        )
        for i in range(n)
    ]


class TestInputHash:

    def test_same_input_same_hash(self):
        c1 = BenchmarkCase("a", {"x": 1}, DecisionPrimitive.BOOLEAN, "q", None, None, None)
        c2 = BenchmarkCase("a", {"x": 1}, DecisionPrimitive.BOOLEAN, "q", None, None, None)
        assert c1.input_hash() == c2.input_hash()

    def test_different_state_different_hash(self):
        c1 = BenchmarkCase("a", {"x": 1}, DecisionPrimitive.BOOLEAN, "q", None, None, None)
        c2 = BenchmarkCase("a", {"x": 2}, DecisionPrimitive.BOOLEAN, "q", None, None, None)
        assert c1.input_hash() != c2.input_hash()

    def test_different_question_different_hash(self):
        c1 = BenchmarkCase("a", {"x": 1}, DecisionPrimitive.BOOLEAN, "q1", None, None, None)
        c2 = BenchmarkCase("a", {"x": 1}, DecisionPrimitive.BOOLEAN, "q2", None, None, None)
        assert c1.input_hash() != c2.input_hash()


class TestLatencyStats:

    def test_empty(self):
        s = _latency_stats([])
        assert s.n == 0 and s.p95_ms == 0.0

    def test_known_distribution(self):
        s = _latency_stats([float(i) for i in range(1, 101)])
        assert s.p50_ms == pytest.approx(51.0, abs=1.0)
        assert s.p95_ms == pytest.approx(96.0, abs=1.0)


class TestECE:

    def test_perfect_calibration(self):
        # Confidence 1.0 always correct -> ECE 0
        ece = _ece([1.0, 1.0, 1.0], [True, True, True])
        assert ece == pytest.approx(0.0, abs=1e-9)

    def test_worst_case(self):
        # Confidence 1.0 always wrong -> ECE 1
        ece = _ece([1.0, 1.0], [False, False])
        assert ece == pytest.approx(1.0, abs=1e-9)

    def test_no_labels(self):
        assert _ece([], []) is None


class TestHarnessIntegration:

    def test_run_fake_backend(self):
        backend = FakeTier2Backend(confidence=0.95)
        result = Tier2Benchmark(backend, warmup_runs=1).run(_cases(10))

        assert result.n_cases == 10
        assert result.n_errors == 0
        assert result.latency.n == 10
        assert result.latency.p95_ms >= 0.0
        assert result.accuracy is None  # no expected labels
        assert result.ece_measured is None

    def test_accuracy_computed_when_labels_present(self):
        backend = FakeTier2Backend(confidence=0.99)
        cases = [
            BenchmarkCase(
                case_id=f"c{i}",
                state={"body": "benign"},
                primitive=DecisionPrimitive.BOOLEAN,
                question="q",
                expected=0.99,   # matches FakeBackend's boolean result
            )
            for i in range(5)
        ]
        result = Tier2Benchmark(backend, warmup_runs=0).run(cases)
        assert result.accuracy == pytest.approx(1.0)

    def test_error_counting(self):
        backend = FakeTier2Backend(failure_mode="raise")
        result = Tier2Benchmark(backend, warmup_runs=0).run(_cases(3))
        assert result.n_errors == 3

    def test_json_roundtrip(self, tmp_path: Path):
        backend = FakeTier2Backend()
        result = Tier2Benchmark(backend, warmup_runs=0).run(_cases(2))
        out = tmp_path / "result.json"
        result.to_json(out)

        data = json.loads(out.read_text(encoding="utf-8"))
        assert data["backend_name"] == "fake-tier2"
        assert data["n_cases"] == 2
        assert "environment" in data
        assert data["environment"]["git_commit"] != ""
