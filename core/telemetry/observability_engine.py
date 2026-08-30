# -*- coding: utf-8 -*-
"""
📊 [REAL-TIME OBSERVABILITY & TELEMETRY ENGINE v1.0]
File: core/telemetry/observability_engine.py

Hệ thống Đo lường & Thấu thị Thời gian thực (Real-Time Observability & Profiling):
  1. OpenTelemetry-Grade Span Context Tree (Root -> Stage -> Tool -> LLM).
  2. Latency Metrics Aggregator (P50, P95, P99) theo từng Pipeline/Phase.
  3. Real-Time Telemetry Counters (Early-Exit Rate, Cache Hits, Circuit Breaker).
  4. PubSub Telemetry Stream qua Redis (`monitor:pulse_channel`).
"""

import time
import math
import json
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple

logger = logging.getLogger("JKAI.Observability")


@dataclass
class TelemetrySpan:
    name: str
    trace_id: str
    span_id: str
    parent_span_id: Optional[str] = None
    start_time: float = field(default_factory=time.perf_counter)
    end_time: Optional[float] = None
    duration_ms: float = 0.0
    status: str = "OK"  # OK, ERROR, EARLY_EXIT, TIMEOUT
    attributes: Dict[str, Any] = field(default_factory=dict)
    events: List[Dict[str, Any]] = field(default_factory=list)

    def finish(self, status: Optional[str] = None, attributes: Optional[Dict[str, Any]] = None) -> "TelemetrySpan":
        self.end_time = time.perf_counter()
        self.duration_ms = round((self.end_time - self.start_time) * 1000, 2)
        if status:
            self.status = status
        if attributes:
            self.attributes.update(attributes)
        return self


class LatencyPercentileTracker:
    """
    📈 Theo dõi và tính toán phân vị độ trễ (P50, P95, P99)
    """

    def __init__(self, max_samples: int = 1000):
        self.max_samples = max_samples
        self.samples: Dict[str, List[float]] = {}

    def record_latency(self, metric_name: str, latency_ms: float) -> None:
        if metric_name not in self.samples:
            self.samples[metric_name] = []
        
        self.samples[metric_name].append(latency_ms)
        if len(self.samples[metric_name]) > self.max_samples:
            self.samples[metric_name].pop(0)

    def get_percentiles(self, metric_name: str) -> Dict[str, float]:
        values = self.samples.get(metric_name, [])
        if not values:
            return {"p50": 0.0, "p95": 0.0, "p99": 0.0, "avg": 0.0, "count": 0}

        sorted_v = sorted(values)
        count = len(sorted_v)

        def _calc_pct(pct: float) -> float:
            k = (count - 1) * pct
            f = math.floor(k)
            c = math.ceil(k)
            if f == c:
                return sorted_v[int(k)]
            d0 = sorted_v[int(f)] * (c - k)
            d1 = sorted_v[int(c)] * (k - f)
            return d0 + d1

        return {
            "p50": round(_calc_pct(0.50), 2),
            "p95": round(_calc_pct(0.95), 2),
            "p99": round(_calc_pct(0.99), 2),
            "avg": round(sum(sorted_v) / count, 2),
            "count": count
        }


class RealTimeObservabilityEngine:
    """
    🔬 Động Cơ Thấu Thị & Giám Sát Thời Gian Thực
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.tracker = LatencyPercentileTracker()
        self.counters: Dict[str, int] = {
            "total_requests": 0,
            "cache_hits": 0,
            "early_exits": 0,
            "circuit_breaker_triggers": 0,
            "sandbox_executions": 0,
            "errors": 0
        }

    def start_span(
        self,
        name: str,
        trace_id: str,
        parent_span_id: Optional[str] = None,
        attributes: Optional[Dict[str, Any]] = None
    ) -> TelemetrySpan:
        import uuid
        span = TelemetrySpan(
            name=name,
            trace_id=trace_id,
            span_id=uuid.uuid4().hex[:16],
            parent_span_id=parent_span_id,
            attributes=attributes or {}
        )
        return span

    def record_span(self, span: TelemetrySpan) -> None:
        """Ghi nhận span hoàn tất và cập nhật metric phân vị."""
        if not span.end_time:
            span.finish()

        # Cập nhật phân vị theo tên span
        self.tracker.record_latency(span.name, span.duration_ms)

        # Cập nhật các bộ đếm
        self.counters["total_requests"] += 1
        if span.status == "EARLY_EXIT":
            self.counters["early_exits"] += 1
        elif span.status == "ERROR":
            self.counters["errors"] += 1

        # Phát sóng telemetry ra Redis nếu có thể
        self._emit_telemetry_pulse(span)

    def increment_counter(self, counter_name: str, delta: int = 1) -> None:
        if counter_name in self.counters:
            self.counters[counter_name] += delta
        else:
            self.counters[counter_name] = delta

    def get_system_telemetry_summary(self) -> Dict[str, Any]:
        """Xuất bản tóm tắt toàn cảnh hiệu năng của JKAI."""
        metrics_summary = {}
        for metric_name in self.tracker.samples.keys():
            metrics_summary[metric_name] = self.tracker.get_percentiles(metric_name)

        return {
            "timestamp": time.time(),
            "counters": self.counters.copy(),
            "latency_metrics": metrics_summary,
            "health_status": "HEALTHY" if self.counters.get("errors", 0) == 0 else "WARNING"
        }

    def _emit_telemetry_pulse(self, span: TelemetrySpan) -> None:
        """Phát sóng pulse nhẹ qua Redis channel (non-blocking)."""
        import os
        # Nếu đang ở môi trường test không có redis service, bỏ qua
        if os.environ.get("PYTEST_CURRENT_TEST") or not os.environ.get("REDIS_HOST"):
            return

        try:
            from core.utils.redis_client import redis_safe
            pulse_data = json.dumps({
                "event": "telemetry_span_finished",
                "span_name": span.name,
                "duration_ms": span.duration_ms,
                "status": span.status,
                "trace_id": span.trace_id,
                "timestamp": time.time()
            })
            redis_safe(lambda r: r.publish("monitor:pulse_channel", pulse_data))
        except Exception:
            pass


observability = RealTimeObservabilityEngine()
