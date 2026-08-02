import psutil
import logging

logger = logging.getLogger("RuntimePressureMonitor")

class RuntimePressureMonitor:
    """
    🌡️ Nhiệt Kế Áp Suất (Runtime Pressure) kết nối psutil thực tế và Redis.
    """
    def __init__(self):
        self._redis_client = None

    def _get_redis(self):
        if self._redis_client is None:
            try:
                from core.utils.engine import engine
                self._redis_client = engine._get_redis()
            except Exception:
                pass
        return self._redis_client

    @property
    def memory_pressure_pct(self) -> float:
        """Đo đạc tỉ lệ RAM thực tế từ psutil."""
        try:
            return float(psutil.virtual_memory().percent)
        except Exception:
            return 0.0

    @property
    def sandbox_cpu_usage(self) -> float:
        """Đo đạc tỉ lệ CPU thực tế từ psutil."""
        try:
            return float(psutil.cpu_percent(interval=None))
        except Exception:
            return 0.0

    @property
    def planner_queue_depth(self) -> int:
        """Đo độ sâu queue từ Redis queue key thực tế."""
        try:
            r = self._get_redis()
            if r:
                return r.llen("queue:tasks:planner") or 0
        except Exception:
            pass
        return 0

    @property
    def event_lag_ms(self) -> int:
        return 0

    def get_pressure_score(self) -> float:
        """Tính điểm áp lực thực tế 0.0 -> 1.0."""
        mem = self.memory_pressure_pct
        cpu = self.sandbox_cpu_usage
        q_depth = self.planner_queue_depth
        
        score = (q_depth / 50.0) * 0.3 + (mem / 100.0) * 0.4 + (cpu / 100.0) * 0.3
        return round(min(max(score, 0.0), 1.0), 3)

runtime_pressure_monitor = RuntimePressureMonitor()
