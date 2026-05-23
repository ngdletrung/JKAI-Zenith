import json
import os

class CalibrationEngine:
    """
    ⚖️ Động Cơ Định Chuẩn Niềm Tin (Adaptive Confidence Calibration)
    Confidence thực tế = LLM Confidence * Điểm Uy Tín Lịch Sử
    """
    def __init__(self, weights_path: str = "d:/Docker/N8N/services/ai-brain/memory/calibration_weights.json"):
        self.weights_path = weights_path
        self.historical_weights = self._load_weights()

    def _load_weights(self) -> dict:
        if os.path.exists(self.weights_path):
            with open(self.weights_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        # Điểm uy tín mặc định là 1.0 (Tin tưởng hoàn toàn)
        return {}

    def get_calibrated_confidence(self, intent: str, llm_confidence: float) -> float:
        """Hạ điểm tự tin nếu Intent này trong lịch sử hay bị lỗi."""
        # Nếu chưa có lịch sử, uy tín = 1.0
        reliability_score = self.historical_weights.get(intent, 1.0)
        
        calibrated = llm_confidence * reliability_score
        
        if reliability_score < 0.6:
            print(f"⚠️ [CALIBRATION]: Skill `{intent}` có lịch sử rủi ro cao (Uy tín: {reliability_score:.2f}). Đã ép điểm Confidence từ {llm_confidence:.2f} xuống {calibrated:.2f}!")
            
        return round(calibrated, 3)

    def update_reliability(self, intent: str, is_success: bool):
        """Được gọi bởi OutcomeLearner để cập nhật điểm uy tín."""
        current_score = self.historical_weights.get(intent, 1.0)
        
        # Công thức EWMA (Exponential Weighted Moving Average)
        # Nhạy cảm với thất bại hơn là thành công
        alpha = 0.2 if is_success else 0.4 
        target = 1.0 if is_success else 0.0
        
        new_score = (1 - alpha) * current_score + alpha * target
        self.historical_weights[intent] = round(new_score, 3)
        
        with open(self.weights_path, 'w', encoding='utf-8') as f:
            json.dump(self.historical_weights, f, indent=4)
