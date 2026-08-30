# -*- coding: utf-8 -*-
"""
🏛️ [ZENITH-REFLEX-CORE]: ReflexGate (FastPath Governor & Social Reflex Layer)
File: core/utils/reflex_gate.py
"""

from __future__ import annotations
import re
from typing import Dict, Any, Optional


class ReflexGate:
    """
    💎 [REFLEX-GATE]: Xử lý các câu chào hỏi, giao tiếp xã giao phản xạ tức thì (L0 Reflex)
    mà không cần khởi động pipeline nặng nề.
    """
    
    SOCIAL_PATTERNS = [
        r"^(chào|hi|hello|hey|alo|alo\s+jkai|ê|ơi)\b",
        r"^(bạn\s+là\s+ai|bạn\s+tên\s+gì|who\s+are\s+you|giới\s+thiệu\s+về\s+bạn)\b",
        r"^(khỏe\s+không|có\s+khỏe\s+không|hôm\s+nay\s+thế\s+nào|how\s+are\s+you)\b",
        r"^(cảm\s+ơn|thanks|thank\s+you|tks)\b",
        r"^(tạm\s+biệt|bye|goodbye)\b"
    ]

    @classmethod
    def is_social(cls, text: str) -> bool:
        if not text or not isinstance(text, str):
            return False
        clean = text.strip().lower()
        if len(clean) > 80:
            return False
        return any(re.search(pat, clean) for pat in cls.SOCIAL_PATTERNS)

    @classmethod
    def get_response(cls, text: str) -> str:
        clean = text.strip().lower() if text else ""
        if "ai" in clean or "tên" in clean or "who" in clean:
            return "Tôi là **JKAI Zenith**, Hệ điều hành Trí tuệ Nhân tạo Tối cao sẵn sàng phụng sự Master."
        if "cảm ơn" in clean or "thank" in clean:
            return "Rất vinh hạnh được hỗ trợ Master! Hãy giao thêm nhiệm vụ bất cứ lúc nào."
        if "tạm biệt" in clean or "bye" in clean:
            return "Tạm biệt Master! Hệ thống luôn duy trì trạng thái trực ban 24/7."
        return "Chào Master! Ban Thư Ký JKAI Zenith đã sẵn sàng tiếp nhận mệnh lệnh tác chiến."


__all__ = ["ReflexGate"]
