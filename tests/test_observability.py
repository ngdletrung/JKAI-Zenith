# -*- coding: utf-8 -*-
"""
Unit test suite cho RealTimeObservabilityEngine (Trụ cột 2)
"""

import time
import pytest
from core.telemetry.observability_engine import RealTimeObservabilityEngine, TelemetrySpan, LatencyPercentileTracker


class TestObservabilityEngine:
    """Kiểm tra độ chính xác của Span Profiler, Percentiles (P50, P95, P99) và Telemetry Summary."""

    def test_latency_percentile_calculation(self):
        tracker = LatencyPercentileTracker()
        # Nạp 100 mẫu giả lập từ 1ms đến 100ms
        for i in range(1, 101):
            tracker.record_latency("test_pipeline", float(i))

        pct = tracker.get_percentiles("test_pipeline")
        assert pct["count"] == 100
        assert 49.0 <= pct["p50"] <= 51.0
        assert 94.0 <= pct["p95"] <= 96.0
        assert 98.0 <= pct["p99"] <= 100.0

    def test_span_lifecycle_and_duration(self):
        obs = RealTimeObservabilityEngine()
        span = obs.start_span("fast_pipeline", "trace_12345", attributes={"intent": "math"})
        time.sleep(0.01)  # Giả lập xử lý 10ms
        span.finish(status="EARLY_EXIT")
        
        assert span.duration_ms >= 8.0
        assert span.status == "EARLY_EXIT"
        assert span.attributes["intent"] == "math"

        obs.record_span(span)
        summary = obs.get_system_telemetry_summary()
        assert summary["counters"]["total_requests"] >= 1
        assert "fast_pipeline" in summary["latency_metrics"]

    def test_empty_metrics_returns_default(self):
        tracker = LatencyPercentileTracker()
        pct = tracker.get_percentiles("non_existent")
        assert pct["p50"] == 0.0
        assert pct["count"] == 0
