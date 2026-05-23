from telemetry.pressure_monitor import RuntimePressureMonitor

class AdaptiveController:
    """
    🚦 Hệ thống Tự Điều Áp (Graceful Degradation)
    Tránh Kernel bị ngộp chết bằng cách hạ cấp tính năng.
    """
    def __init__(self, monitor: RuntimePressureMonitor):
        self.monitor = monitor

    def evaluate_pressure(self):
        score = self.monitor.get_pressure_score()
        
        if score > 0.8:
            return {
                "planner_mode": "FAST", # Rút gọn Planner
                "max_planner_depth": 1,
                "allow_retries": False,
                "reject_low_priority": True
            }
        elif score > 0.5:
            return {
                "planner_mode": "NORMAL",
                "max_planner_depth": 3,
                "allow_retries": True,
                "reject_low_priority": False
            }
        else:
            return {
                "planner_mode": "DEEP",
                "max_planner_depth": 5,
                "allow_retries": True,
                "reject_low_priority": False
            }
