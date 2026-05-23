class PredictiveWorldModel:
    """
    🌍 Mô Hình Thế Giới Nội Tại (Predictive World Model)
    Tưởng tượng hệ quả của một hành động trước khi thực sự chạy nó ở Runtime.
    Đây là ranh giới giữa "Tự động hóa" (Automation) và "Nhận thức" (Cognition).
    """
    def __init__(self):
        # Tập luật nhân-quả cơ sở (Causal Links)
        self.causal_links = {
            "RESTART_DOCKER": {"consequence": "Mất kết nối API tạm thời, có thể fail các task đang chạy.", "risk_score": 0.8},
            "CLEAR_CACHE": {"consequence": "Có thể làm chậm lần load tiếp theo, hoặc logout các session.", "risk_score": 0.3},
            "REBOOT_ROUTER": {"consequence": "Mất kết nối SSH, ngắt mạng toàn hệ thống.", "risk_score": 0.99},
            "DELETE_TEMP_FILES": {"consequence": "An toàn, giải phóng không gian đĩa.", "risk_score": 0.1}
        }

    def simulate_consequences(self, intent: str, params: dict) -> dict:
        """
        Mô phỏng hậu quả của một Intent.
        Trả về: {"consequence": str, "risk_score": float, "safe_to_proceed": bool}
        """
        # Tra cứu đồ thị nhân quả
        prediction = self.causal_links.get(intent, {"consequence": "Hậu quả chưa rõ ràng (Unknown state evolution).", "risk_score": 0.5})
        
        risk = prediction["risk_score"]
        safe_to_proceed = risk < 0.85  # Nếu rủi ro quá cao, chặn lại hoặc bắt buộc Master duyệt
        
        return {
            "intent": intent,
            "predicted_consequence": prediction["consequence"],
            "risk_score": risk,
            "safe_to_proceed": safe_to_proceed
        }
