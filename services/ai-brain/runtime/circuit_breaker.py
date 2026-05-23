class CircuitBreaker:
    """
    🔌 Cầu Dao An Toàn (Automatic Quarantine)
    Nếu một skill timeout/lỗi liên tục, tự động ngắt kết nối tạm thời subsystem đó.
    """
    def __init__(self):
        self.failure_counts = {}
        self.MAX_FAILURES = 5

    def record_failure(self, subsystem: str):
        self.failure_counts[subsystem] = self.failure_counts.get(subsystem, 0) + 1
        if self.failure_counts[subsystem] >= self.MAX_FAILURES:
            return True # Kích hoạt trạng thái DEGRADED / QUARANTINED
        return False

    def record_success(self, subsystem: str):
        self.failure_counts[subsystem] = 0

    def is_open(self, subsystem: str) -> bool:
        """Nếu mạch bị ngắt (open), không cho phép tiếp tục gọi hệ thống đó."""
        return self.failure_counts.get(subsystem, 0) >= self.MAX_FAILURES
