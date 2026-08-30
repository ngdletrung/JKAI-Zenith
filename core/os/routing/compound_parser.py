# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — COMPOUND INTENT PARSER v1.0                      ║
║   Phân Tách Mệnh Đề Đa Mục Tiêu & Nhận Diện Intent Phức Hợp      ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Xử Lý Đa Nhiệm Vụ Trong Một Câu Lệnh. 🧩🧠⚡*
"""

import re
from typing import List, Tuple


class CompoundIntentParser:
    """
    🧩 Phân tách câu phức của Master thành các mệnh đề thành phần để gán nhãn đa tác vụ.
    """

    # Các liên từ kết nối mệnh đề phức hợp
    _CONJUNCTIONS = (
        r"\b(?:và|đồng thời|sau đó|kết hợp|cùng với|kèm theo|song song|rồi|and|then|also)\b",
        r"[,;\+&]"
    )

    @classmethod
    def split_clauses(cls, goal: str) -> List[str]:
        """Tách câu thành các mệnh đề hành động riêng biệt."""
        if not goal:
            return []

        # Tách theo liên từ
        pattern = "|".join(cls._CONJUNCTIONS)
        raw_parts = re.split(pattern, goal, flags=re.IGNORECASE)
        clauses = [p.strip() for p in raw_parts if len(p.strip()) >= 5]
        
        return clauses if len(clauses) > 1 else [goal.strip()]

    @classmethod
    def is_compound_intent(cls, goal: str) -> bool:
        """Kiểm tra xem câu hỏi có phải là câu lệnh phức hợp hay không."""
        clauses = cls.split_clauses(goal)
        return len(clauses) > 1


compound_intent_parser = CompoundIntentParser()
