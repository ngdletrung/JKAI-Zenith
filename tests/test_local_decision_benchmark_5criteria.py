# -*- coding: utf-8 -*-
"""
tests/test_local_decision_benchmark_5criteria.py
Test suite executing and asserting the 5-criteria benchmark harness on Master machine:
1. Per-decision-point measurement (ROUTING, RISK_ASSESSMENT, REPLAN, COMPLETION)
2. Vietnamese technical accuracy >= 0.95
3. Latency P95 <= 50ms on local machine
4. VRAM headroom compliant
5. Expected Calibration Error (ECE) <= 0.08
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from core.benchmark.local_decision_benchmark import LocalDecisionBenchmarkHarness


def test_5_criteria_local_benchmark_execution():
    harness = LocalDecisionBenchmarkHarness()
    report = harness.run_benchmark()

    # 1. Check all 4 decision points are individually measured
    expected_points = {"ROUTING", "RISK_ASSESSMENT", "REPLAN", "COMPLETION"}
    assert set(report.per_point_metrics.keys()) == expected_points
    for pt, metric in report.per_point_metrics.items():
        assert metric.total_samples > 0
        assert metric.accuracy >= 0.95, f"Decision point {pt} accuracy below 0.95: {metric.accuracy}"

    # 2. Vietnamese technical accuracy >= 0.95
    assert report.meets_vietnamese_floor is True
    assert report.vietnamese_accuracy >= 0.95

    # 3. Latency on Master machine
    assert report.p95_latency_ms <= 50.0, f"P95 latency {report.p95_latency_ms}ms exceeded 50ms"
    assert report.p50_latency_ms <= 20.0

    # 4. VRAM Headroom
    assert report.vram_headroom_passed is True

    # 5. ECE Calibration
    assert report.ece_passed is True
    assert report.expected_calibration_error <= 0.08

    # Overall verdict
    assert report.all_5_criteria_passed is True
    assert report.summary_verdict == "PASSED_LOCAL_5_CRITERIA"
