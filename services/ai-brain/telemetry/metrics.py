import logging

logger = logging.getLogger("CognitiveMetrics")

try:
    from prometheus_client import Counter, CONTENT_TYPE_LATEST, generate_latest
    PROMETHEUS_AVAILABLE = True
except ImportError:
    PROMETHEUS_AVAILABLE = False

CRITIC_OUTCOMES = ("approve", "enforce", "retry", "deterministic_override", "double_reject")

if PROMETHEUS_AVAILABLE:
    HALLUCINATION_COUNTER = Counter('jkai_hallucination_total', 'Total hallucination detections')
    FIREWALL_HIT_COUNTER = Counter('jkai_semantic_firewall_hits_total', 'Total semantic firewall hit count')
    CRITIC_COUNTER = Counter('jkai_critic_decision_total', 'Critic audit decisions', ['outcome'])


class CognitiveMetrics:
    """
    📊 Huyết Áp Hệ Thống (Prometheus & In-Memory Cognitive Health Metrics)

    Chỉ xuất những tín hiệu có nguồn ghi thật (firewall chặn, guardrail chống
    bịa đặt, phán quyết của Critic). Metric không có producer sẽ luôn bằng 0 và
    gây hiểu nhầm.
    """
    def __init__(self):
        self.hallucination_count = 0
        self.semantic_firewall_hits = 0
        self.critic_decisions = {outcome: 0 for outcome in CRITIC_OUTCOMES}

    def record_hallucination(self):
        self.hallucination_count += 1
        if PROMETHEUS_AVAILABLE:
            HALLUCINATION_COUNTER.inc()

    def record_semantic_hit(self):
        self.semantic_firewall_hits += 1
        if PROMETHEUS_AVAILABLE:
            FIREWALL_HIT_COUNTER.inc()

    def record_critic_decision(self, outcome: str):
        if outcome not in self.critic_decisions:
            return
        self.critic_decisions[outcome] += 1
        if PROMETHEUS_AVAILABLE:
            CRITIC_COUNTER.labels(outcome=outcome).inc()

    def snapshot(self) -> dict:
        return {
            "hallucinations": self.hallucination_count,
            "semantic_firewall_hits": self.semantic_firewall_hits,
            "critic_decisions": dict(self.critic_decisions),
        }

    def get_prometheus_bytes(self) -> tuple:
        """Xuất dữ liệu Prometheus cho endpoint /metrics."""
        if PROMETHEUS_AVAILABLE:
            for outcome in CRITIC_OUTCOMES:
                CRITIC_COUNTER.labels(outcome=outcome)
            return generate_latest(), CONTENT_TYPE_LATEST

        fallback_text = (
            "# HELP jkai_hallucination_total Total hallucination detections\n"
            f"jkai_hallucination_total {self.hallucination_count}\n"
            "# HELP jkai_semantic_firewall_hits_total Total semantic firewall hits\n"
            f"jkai_semantic_firewall_hits_total {self.semantic_firewall_hits}\n"
            "# HELP jkai_critic_decision_total Critic audit decisions\n"
            "# TYPE jkai_critic_decision_total counter\n"
        )
        for outcome, count in self.critic_decisions.items():
            fallback_text += f'jkai_critic_decision_total{{outcome="{outcome}"}} {count}\n'
        return fallback_text.encode("utf-8"), "text/plain; version=0.0.4"

cognitive_metrics = CognitiveMetrics()
