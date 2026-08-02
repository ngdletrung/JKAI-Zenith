class PromotionPolicy:
    """
    📈 Thuật toán Thăng Cấp (Anti-Learning Garbage)
    Quyết định khi nào dữ liệu từ WORKING / EPISODIC được thăng cấp lên LONG_TERM.
    """
    def __init__(self):
        pass
        
    def evaluate(self, confidence: float, repetition_count: int, verification_score: float, consistency_score: float, sensitive: bool) -> bool:
        """
        Công thức chấm điểm đa biến:
        (confidence * 0.3) + (repetition * 0.2) + (verification * 0.3) + (consistency * 0.2)
        """
        if sensitive:
            # Thông tin nhạy cảm KHÔNG BAO GIỜ lên Long-Term Memory
            return False
            
        # Repetition chuẩn hóa (Ví dụ max 10 = 1.0)
        rep_normalized = min(repetition_count / 10.0, 1.0)
        
        final_score = (confidence * 0.3) + (rep_normalized * 0.2) + (verification_score * 0.3) + (consistency_score * 0.2)
        
        # Chỉ những ký ức chất lượng nhất (Score > 0.85) mới được học.
        return final_score >= 0.85
