import time
import logging

logger = logging.getLogger("CognitiveMetrics")

try:
    from prometheus_client import Counter, Gauge, Histogram, generate_latest, CONTENT_TYPE_LATEST
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

if PROMETHEUS_AVAILABLE:
    HALLUCINATION_COUNTER = Counter('jkai_hallucination_total', 'Total hallucination detections')
    PLANNER_DRIFT_COUNTER = Counter('jkai_planner_drift_total', 'Total planner reasoning drift detections')
    FIREWALL_HIT_COUNTER = Counter('jkai_semantic_firewall_hits_total', 'Total semantic firewall hit count')
    RETRY_SPIKES_COUNTER = Counter('jkai_retry_spikes_total', 'Total retry spike events')
    
    TOOL_LATENCY_HISTOGRAM = Histogram('jkai_tool_latency_seconds', 'Latency of tool execution in seconds')
    PLANNER_LATENCY_HISTOGRAM = Histogram('jkai_planner_latency_seconds', 'Latency of planner execution in seconds')

class CognitiveMetrics:
    """
    📊 Huyết Áp Hệ Thống (Prometheus & In-Memory Cognitive Health Metrics)
    """
    def __init__(self):
        self.hallucination_rate = 0.0
        self.planner_drift_count = 0
        self.retry_spikes = 0
        self.semantic_firewall_hits = 0
        self.quarantine_count = 0
        self.tool_latency_avg = 0.0
        self.planner_latency_avg = 0.0

    def record_hallucination(self):
        self.hallucination_rate += 1
        if PROMETHEUS_AVAILABLE:
            HALLUCINATION_COUNTER.inc()

    def record_semantic_hit(self):
        self.semantic_firewall_hits += 1
        if PROMETHEUS_AVAILABLE:
            FIREWALL_HIT_COUNTER.inc()

    def record_planner_drift(self):
        self.planner_drift_count += 1
        if PROMETHEUS_AVAILABLE:
            PLANNER_DRIFT_COUNTER.inc()

    def record_tool_latency(self, seconds: float):
        self.tool_latency_avg = (self.tool_latency_avg + seconds) / 2.0
        if PROMETHEUS_AVAILABLE:
            TOOL_LATENCY_HISTOGRAM.observe(seconds)

    def record_planner_latency(self, seconds: float):
        self.planner_latency_avg = (self.planner_latency_avg + seconds) / 2.0
        if PROMETHEUS_AVAILABLE:
            PLANNER_LATENCY_HISTOGRAM.observe(seconds)

    def get_prometheus_bytes(self) -> tuple:
        """Xuất dữ liệu Prometheus cho endpoint /metrics."""
        if PROMETHEUS_AVAILABLE:
            return generate_latest(), CONTENT_TYPE_LATEST
        else:
            fallback_text = (
                f"# HELP jkai_hallucination_total Total hallucination detections\n"
                f"jkai_hallucination_total {self.hallucination_rate}\n"
                f"# HELP jkai_semantic_firewall_hits_total Total semantic firewall hits\n"
                f"jkai_semantic_firewall_hits_total {self.semantic_firewall_hits}\n"
            )
            return fallback_text.encode("utf-8"), "text/plain; version=0.0.4"

cognitive_metrics = CognitiveMetrics()
