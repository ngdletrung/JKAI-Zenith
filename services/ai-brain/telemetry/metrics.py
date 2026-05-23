class CognitiveMetrics:
    """
    📊 Huyết Áp Hệ Thống (Cognitive Health Metrics)
    """
    def __init__(self):
        # Thông số sức khỏe nhận thức
        self.hallucination_rate = 0.0
        self.planner_drift_count = 0
        self.retry_spikes = 0
        self.semantic_firewall_hits = 0
        self.quarantine_count = 0
        
        # Thông số trễ
        self.tool_latency_avg = 0.0
        self.planner_latency_avg = 0.0

    def record_hallucination(self):
        self.hallucination_rate += 1

    def record_semantic_hit(self):
        self.semantic_firewall_hits += 1
