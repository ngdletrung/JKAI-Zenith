class RuntimePressureMonitor:
    """
    🌡️ Nhiệt Kế Áp Suất (Runtime Pressure)
    """
    def __init__(self):
        self.planner_queue_depth = 0
        self.sandbox_cpu_usage = 0.0
        self.event_lag_ms = 0
        self.memory_pressure_pct = 0.0

    def get_pressure_score(self) -> float:
        """Trả về điểm áp lực 0.0 -> 1.0"""
        score = (self.planner_queue_depth / 100.0) * 0.4 + (self.memory_pressure_pct / 100.0) * 0.6
        return min(score, 1.0)
