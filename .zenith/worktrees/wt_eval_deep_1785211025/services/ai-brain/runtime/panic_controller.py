import time

class PanicController:
    """
    🚨 Còi Báo Động Khẩn Cấp 3 Cấp Độ (3-Tier Panic Mode)
    Có Rate-limiting để tránh hệ thống dao động (Oscillation: Normal -> Panic -> Normal).
    """
    def __init__(self):
        self.panic_level = "NORMAL"
        self.last_panic_trigger = 0.0
        self.cooldown_period = 300 # 5 phút Cooldown
        self.panic_threshold_window = 60 

    def trigger_panic(self, hallucination_rate: float, drift_score: float):
        now = time.time()
        
        # Rate Limiting
        if now - self.last_panic_trigger < self.cooldown_period:
            print("⏳ Đang trong thời gian Cooldown. Bỏ qua trigger panic mới.")
            return

        # Đánh giá cấp độ
        if hallucination_rate > 0.8:
            self._activate_level("CRITICAL", "Full Legacy Fallback")
        elif hallucination_rate > 0.5 or drift_score > 0.7:
            self._activate_level("HARD", "Disable Runtime Writes (Read-only)")
        elif hallucination_rate > 0.3:
            self._activate_level("SOFT", "Disable Planner")

    def _activate_level(self, level: str, action: str):
        self.panic_level = level
        self.last_panic_trigger = time.time()
        print(f"🔥 [PANIC MODE]: {level} - Hành động: {action}")
        
    def get_status(self):
        return self.panic_level
