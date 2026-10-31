# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — COMPOUND INTENT PARSER v5.0 (REFLEX CENTER V5)   ║
║   Phân Tách Mệnh Đề Đa Mục Tiêu & Nhận Diện Intent Phức Hợp      ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Xử Lý Đa Nhiệm Vụ Trong Một Câu Lệnh. 🧩🧠⚡*
"""

import re
from typing import List, Tuple, Dict, Any, Optional

_RE_MATH_EXPR = re.compile(r'^(?:tính|tinh|calculate|compute)?\s*[\d\.\s\+\-\*\/\(\)\%\^]+$', re.IGNORECASE)
_RE_MAJOR_SEPS = [
    re.compile(r'(?i)(?:,\s*|\s+)(?:sau đó|sau do|đồng thời|dong thoi|kết hợp|ket hop|then|after that|tiếp theo)\s+'),
    re.compile(r'(?i)(?<!lâu)(?<!lắm)(?<!ngày)(?<!xong)\s+rồi\s+'),
    re.compile(r'[;]')
]
_RE_VA_AND = re.compile(r'(?i)\b(?:và|and)\b')
_RE_GREET_COMMA = re.compile(r'(?i)^(?:xin\s+)?chào\b|^hello\b|^hi\b')
_RE_WORDS = re.compile(r'\w+')

ACTION_VERBS = {
    'tính', 'tinh', 'tìm', 'tim', 'tìm kiếm', 'tim kiem', 'tra cứu', 'tra cuu',
    'viết', 'viet', 'tạo', 'tao', 'soạn', 'soan', 'soạn thảo', 'soan thao',
    'chạy', 'chay', 'thực thi', 'thuc thi', 'xem', 'đọc', 'doc', 'kiểm tra', 'kiem tra',
    'phân tích', 'phan tich', 'đánh giá', 'danh gia', 'hỏi', 'hoi', 'hãy', 'hay',
    'giải thích', 'giai thich', 'xuất', 'xuat', 'lập', 'lap', 'cập nhật', 'cap nhat',
    'sửa', 'sua', 'thời tiết', 'thoi tiet', 'giá', 'gia', 'bitcoin', 'thống kê'
}


class CompoundIntentParser:
    """
    🧩 Phân tách câu phức của Master thành các mệnh đề thành phần để gán nhãn đa tác vụ.
    Reflex Center V5:
    - Bảo vệ liên kết danh từ (Noun Coordination Guard, e.g. "postgres và mongo" không bị tách).
    - Phân biệt liên từ chỉ thời gian ("sau đó", "rồi") với tiểu từ khép câu ("lâu lắm rồi").
    - Hỗ trợ câu ghép mở đầu bằng lời chào ("chào bạn, giúp tôi...").
    """

    @classmethod
    def split_clauses(cls, goal: str) -> List[str]:
        """Tách câu thành các mệnh đề hành động riêng biệt (<0.1ms)."""
        if not goal:
            return []
        g = goal.strip()
        if _RE_MATH_EXPR.match(g):
            return [g]

        parts = [g]
        for sep in _RE_MAJOR_SEPS:
            new_parts = []
            for p in parts:
                subs = sep.split(p)
                for s in subs:
                    s_st = s.strip()
                    if len(s_st) >= 3:
                        new_parts.append(s_st)
            parts = new_parts

        final_clauses = []
        for p in parts:
            if _RE_VA_AND.search(p):
                sub_items = _RE_VA_AND.split(p)
                accum = sub_items[0].strip()
                for next_item in sub_items[1:]:
                    ni = next_item.strip()
                    if not ni:
                        continue
                    words_ni = _RE_WORDS.findall(ni.lower())
                    has_action = any(av in ni.lower() for av in ACTION_VERBS) or any(w in ACTION_VERBS for w in words_ni)
                    words_acc = _RE_WORDS.findall(accum.lower())
                    has_action_acc = any(av in accum.lower() for av in ACTION_VERBS) or any(w in ACTION_VERBS for w in words_acc) or any(sk in accum.lower() for sk in ('chào', 'chao', 'xin chào', 'buổi sáng', 'buoi sang', 'hello', 'hi'))

                    if (has_action or any(w in ni.lower() for w in ('thời tiết', 'giá', 'bitcoin', 'ai', 'gì', 'sao'))) and (has_action_acc or len(words_acc) >= 2) and len(words_ni) >= 2:
                        final_clauses.append(accum)
                        accum = ni
                    else:
                        accum = accum + " và " + ni
                final_clauses.append(accum)
            elif ',' in p and _RE_GREET_COMMA.match(p.strip()):
                c_parts = [cp.strip() for cp in p.split(',', 1) if cp.strip()]
                if len(c_parts) == 2 and any(k in c_parts[1].lower() for k in ('giúp', 'cho', 'hỏi', 'xem', 'thời tiết', 'tính', 'viết', 'soạn', 'giá')):
                    final_clauses.extend(c_parts)
                else:
                    final_clauses.append(p)
            else:
                final_clauses.append(p)

        return [c for c in final_clauses if len(c.strip()) >= 3]

    @classmethod
    def is_compound_intent(cls, goal: str) -> bool:
        """Kiểm tra xem câu hỏi có phải là câu lệnh phức hợp hay không."""
        if not goal:
            return False
        clauses = cls.split_clauses(goal)
        return len(clauses) > 1

    @classmethod
    def parse_compound_intents(cls, goal: str, router=None) -> Dict[str, Any]:
        """
        Phân tách và định tuyến từng mệnh đề con để xây dựng cấu trúc đa tác vụ.
        """
        is_compound = cls.is_compound_intent(goal)
        clauses = cls.split_clauses(goal)
        
        clause_modes = []
        if router and is_compound and len(clauses) > 1:
            for clause in clauses:
                sub_dec = router.route(clause)
                clause_modes.append(sub_dec.mode.value)
        elif router:
            single_dec = router.route(goal)
            clause_modes.append(single_dec.mode.value)

        return {
            "is_compound": is_compound,
            "clauses": clauses,
            "clause_modes": clause_modes
        }


compound_intent_parser = CompoundIntentParser()
