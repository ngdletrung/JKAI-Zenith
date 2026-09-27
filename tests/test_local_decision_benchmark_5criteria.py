# -*- coding: utf-8 -*-
"""
tests/test_local_decision_benchmark_5criteria.py
Test suite asserting the rigorous 5-criteria benchmark harness per Opencode Turn 78:
1. Runs REAL_LOCAL_SUBSTRATE (enable_mock=False) as primary, with MOCK_MODE for comparative check.
2. Dataset size n=50 items (ROUTING, RISK_ASSESSMENT, REPLAN, COMPLETION).
3. Vietnamese technical accuracy >= 0.95 across 31 Vietnamese items.
4. Latency P95 <= 50ms on local machine.
5. Honest VRAM reporting: vram_measurement_status == 'NOT_MEASURED (In-Process CPU/RAM Baseline)', vram_headroom_passed is None.
6. ECE sample size == 50 and ECE <= 0.08.
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.benchmark.local_decision_benchmark import LocalDecisionBenchmarkHarness


def test_5_criteria_rigorous_real_benchmark_execution():
    """Validates real local substrate execution without mocking."""
    harness = LocalDecisionBenchmarkHarness(enable_mock=False)
    report = harness.run_benchmark()

    # 1. Mode check
    assert report.execution_mode == "REAL_LOCAL_SUBSTRATE"
    assert report.total_samples == 50
    assert report.ece_sample_size == 50

    # 2. Decision Points check
    expected_points = {"ROUTING", "RISK_ASSESSMENT", "REPLAN", "COMPLETION"}
    assert set(report.per_point_metrics.keys()) == expected_points
    for pt, metric in report.per_point_metrics.items():
        assert metric.total_samples > 0
        assert metric.accuracy >= 0.95, f"Decision point {pt} accuracy below 0.95: {metric.accuracy}"

    # 3. Vietnamese Technical Domain (31 items)
    assert report.vietnamese_samples_count == 31
    assert report.meets_vietnamese_floor is True
    assert report.vietnamese_accuracy >= 0.95

    # 4. Latency
    assert report.p95_latency_ms <= 50.0, f"P95 latency {report.p95_latency_ms}ms exceeded 50ms"
    assert report.p50_latency_ms <= 20.0

    # 5. Honest Memory & VRAM Status (Cấm bịa True per Opencode Turn 78)
    assert "NOT_MEASURED" in report.vram_measurement_status
    assert report.vram_headroom_passed is None
    assert report.rss_memory_delta_mb >= 0.0

    # 6. ECE
    assert report.ece_passed is True
    assert report.expected_calibration_error <= 0.08

    # Overall verdict
    assert report.all_5_criteria_passed is True
    assert report.summary_verdict == "VALID_BASELINE_SEALED"


def test_dual_mode_mock_vs_real_comparison():
    """Compares mock vs real execution to prove dual-mode capability."""
    harness_mock = LocalDecisionBenchmarkHarness(enable_mock=True)
    report_mock = harness_mock.run_benchmark()
    assert report_mock.execution_mode == "MOCK_MODE"
    assert report_mock.total_samples == 50

    harness_real = LocalDecisionBenchmarkHarness(enable_mock=False)
    report_real = harness_real.run_benchmark()
    assert report_real.execution_mode == "REAL_LOCAL_SUBSTRATE"
    assert report_real.total_samples == 50
