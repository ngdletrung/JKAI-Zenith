# -*- coding: utf-8 -*-
"""
🎭 [EMOTIONAL & MOTIVATIONAL INTELLIGENCE ENGINE v1.0]
File: core/cognitive/emotional_intelligence.py

Trí Tuệ Cảm Xúc & Động Lực Đồng Hành Cùng Master (Trụ Cột 15):
  1. Sentiment & Emotion Detector: Nhận diện trạng thái tâm lý (FRUSTRATED, CURIOUS, TIRED, URGENT, CALM).
  2. Adaptive Response Tone: Thích ứng phong cách giao tiếp (Ngắn gọn thực tế vs Khơi gợi chuyên sâu).
  3. Caring & Motivational Nudges: Hành động chăm sóc khi Master làm việc cường độ cao.
"""

import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List

logger = logging.getLogger("JKAI.EmotionalIntel")


class MasterEmotionalState(Enum):
    CALM = "CALM"                  # Điềm tĩnh, chuẩn mực
    FRUSTRATED = "FRUSTRATED"      # Căng thẳng, bực bội (khi gặp lỗi / hệ thống chậm)
    CURIOUS = "CURIOUS"            # Tò mò, nghiên cứu sáng tạo
    URGENT = "URGENT"              # Khẩn cấp, cần đáp án ngay
    TIRED = "TIRED"                # Mệt mỏi, làm việc liên tục


@dataclass
class EmotionalAnalysisResult:
    detected_state: MasterEmotionalState
    confidence: float
    recommended_tone: str
    tone_system_instruction: str
    caring_nudge: Optional[str] = None


class EmotionalIntelligenceEngine:
    """
    🎭 Động Cơ Thấu Hiểu Cảm Xúc & Tương Tác Đồng Cảm
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.session_interaction_count: int = 0
        self.session_start_time: float = time.time()

    def analyze_master_input(self, user_prompt: str) -> EmotionalAnalysisResult:
        """Phân tích cảm xúc và văn phong từ câu lệnh của Master."""
        self.session_interaction_count += 1
        text = user_prompt.lower()

        # 1. Phát hiện trạng thái FRUSTRATED / URGENT
        if any(w in text for w in ["sao lại lỗi", "sao lâu thế", "tại sao hỏng", "sao ngu thế", "gấp", "nhanh lên", "bực", "fail"]):
            return EmotionalAnalysisResult(
                detected_state=MasterEmotionalState.FRUSTRATED,
                confidence=0.88,
                recommended_tone="CONCISE_ACTION_ORIENTED",
                tone_system_instruction="Master đang cần xử lý gấp/căng thẳng. Trả lời NGẮN GỌN, TRỰC DIỆN, đưa ngay kết quả/giải pháp, không giải thích vòng vo hay rào đón.",
                caring_nudge="Tôi đã tối ưu hóa luồng xử lý để phản hồi nhanh nhất có thể cho Master."
            )

        # 2. Phát hiện trạng thái CURIOUS
        if any(w in text for w in ["tại sao", "nguyên lý", "như thế nào", "giải thích", "chi tiết", "phân tích sâu", "khám phá"]):
            return EmotionalAnalysisResult(
                detected_state=MasterEmotionalState.CURIOUS,
                confidence=0.85,
                recommended_tone="INSPIRING_AND_COMPREHENSIVE",
                tone_system_instruction="Master đang tìm hiểu sâu sắc. Trình bày bài bản, mạch lạc, có ví dụ minh họa và mở rộng các góc nhìn công nghệ giá trị."
            )

        # 3. Phát hiện trạng thái TIRED hoặc Làm việc quá 2 tiếng liên tục
        session_hours = (time.time() - self.session_start_time) / 3600.0
        if any(w in text for w in ["mệt quá", "nghỉ thôi", "oải"]) or (session_hours > 2.0 and self.session_interaction_count > 15):
            return EmotionalAnalysisResult(
                detected_state=MasterEmotionalState.TIRED,
                confidence=0.80,
                recommended_tone="SUPPORTIVE_AND_CLEAR",
                tone_system_instruction="Master đã làm việc rất nhiều. Trình bày tóm tắt cô đọng nhất các điểm mấu chốt.",
                caring_nudge="Master đã làm việc liên tục rất tập trung! Tôi đã tóm lược sẵn các ý chính để Master có thể thư giãn ít phút."
            )

        # 4. Mặc định CALM
        return EmotionalAnalysisResult(
            detected_state=MasterEmotionalState.CALM,
            confidence=0.90,
            recommended_tone="PROFESSIONAL_ELITE",
            tone_system_instruction="Trình bày theo phong cách Chuyên gia Tối cao (Elite Executive) — chính xác, thực dụng, khách quan."
        )


emotional_intelligence = EmotionalIntelligenceEngine()
