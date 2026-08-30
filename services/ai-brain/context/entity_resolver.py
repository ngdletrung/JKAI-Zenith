# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — ENTITY & TOPIC SHIFT RESOLVER v3.0               ║
║   Đa Tầng Chủ Đề (Topic Stack), Khôi Phục Ngữ Cảnh & Đại Từ      ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Ngữ Cảnh Đàm Thoại Đa Lượt. 🧠🧬✨*
"""

import re
import logging
from typing import Optional, List, Dict, Tuple

from mission_state import EntityResolver as EntityResolverV2

logger = logging.getLogger("JKAI.EntityResolver")

_VIETNAMESE_STRIP = str.maketrans({
    'à': 'a', 'á': 'a', 'ạ': 'a', 'ả': 'a', 'ã': 'a',
    'â': 'a', 'ầ': 'a', 'ấ': 'a', 'ậ': 'a', 'ẩ': 'a', 'ẫ': 'a',
    'ă': 'a', 'ằ': 'a', 'ắ': 'a', 'ặ': 'a', 'ẳ': 'a', 'ẵ': 'a',
    'è': 'e', 'é': 'e', 'ẹ': 'e', 'ẻ': 'e', 'ẽ': 'e',
    'ê': 'e', 'ề': 'e', 'ế': 'e', 'ệ': 'e', 'ể': 'e', 'ễ': 'e',
    'ì': 'i', 'í': 'i', 'ị': 'i', 'ỉ': 'i', 'ĩ': 'i',
    'ò': 'o', 'ó': 'o', 'ọ': 'o', 'ỏ': 'o', 'õ': 'o',
    'ô': 'o', 'ồ': 'o', 'ố': 'o', 'ộ': 'o', 'ổ': 'o', 'ỗ': 'o',
    'ơ': 'o', 'ờ': 'o', 'ớ': 'o', 'ợ': 'o', 'ở': 'o', 'ỡ': 'o',
    'ù': 'u', 'ú': 'u', 'ụ': 'u', 'ủ': 'u', 'ũ': 'u',
    'ư': 'u', 'ừ': 'u', 'ứ': 'u', 'ự': 'u', 'ử': 'u', 'ữ': 'u',
    'ỳ': 'y', 'ý': 'y', 'ỵ': 'y', 'ỷ': 'y', 'ỹ': 'y',
    'đ': 'd',
})

_ANAPHORA_PATTERNS = [
    (r"\bn(o|ó|ò|ọ|ỏ|õ)\b", "last_subject"),
    (r"\bc(á|a|à|ạ|ả|ã)i (đ|d)(ó|o|ò|ọ|ỏ|õ)\b", "last_subject"),
    (r"\bvi(e|ê|ệ|ề|ế|ể|ễ)c n(a|à|á|ạ|ả|ã)y\b", "last_subject"),
    (r"\bv(â|a|ầ|ấ|ậ|ẩ|ẫ)n (đ|d)(ê|e|ề|ế|ệ|ể|ễ) n(a|à|á|ạ|ả|ã)y\b", "last_subject"),
    (r"\bt(ì|i|ị|ỉ|ĩ)nh h(ì|i|ị|ỉ|ĩ)nh n(a|à|á|ạ|ả|ã)y\b", "last_subject"),
    (r"\bcon s(ố|o|ò|ọ|ỏ|õ) n(a|à|á|ạ|ả|ã)y\b", "last_subject"),
    (r"\bch(ỉ|i|ị|ỉ|ĩ) s(ố|o|ò|ọ|ỏ|õ) n(a|à|á|ạ|ả|ã)y\b", "last_subject"),
    (r"\bm(ứ|u|ừ|ú|ụ|ủ|ũ)c n(a|à|á|ạ|ả|ã)y\b", "last_subject"),
    (r"\bnh(ư|u|ừ|ú|ụ|ủ|ũ) v(â|a|ầ|ấ|ậ|ẩ|ẫ)y\b", "last_subject"),
    (r"\bnh(ư|u|ừ|ú|ụ|ủ|ũ) th(ế|e|ề|ế|ệ|ể|ễ)\b", "last_subject"),
    (r"\btươ(ng|g|ngf) t(ư|u|ừ|ú|ụ|ủ|ũ)\b", "last_subject"),
    (r"\bc(ó|o|ò|ọ|ỏ|õ) (tăng|t|ta|tag|giảm|g|gia|giam|lên|l|le|len|xuống|x|xu|xuong) không\b", "last_subject"),
    (r"\bli(e|ê|ệ|ề|ế|ể|ễ)u.*c(ó|o|ò|ọ|ỏ|õ).*không\b", "last_subject"),
    (r"\bc(ó|o|ò|ọ|ỏ|õ) nên\b", "last_subject"),
]

_ANAPHORA_NODIA = [
    (r"\bno\b", "last_subject"),
    (r"\bcai do\b", "last_subject"),
    (r"\bviec nay\b", "last_subject"),
    (r"\bvan de nay\b", "last_subject"),
    (r"\btinh hinh nay\b", "last_subject"),
    (r"\bcon so nay\b", "last_subject"),
    (r"\bchi so nay\b", "last_subject"),
    (r"\bmuc nay\b", "last_subject"),
    (r"\bnhu vay\b", "last_subject"),
    (r"\bnhu the\b", "last_subject"),
    (r"\btuong tu\b", "last_subject"),
    (r"\bco (tang|giam|len|xuong) khong\b", "last_subject"),
    (r"\blieu.*co.*khong\b", "last_subject"),
    (r"\bco nen\b", "last_subject"),
]


class EntityResolver:
    """
    🧠 Bộ Giải Quyết Thực Thể & Chuyển Đổi Chủ Đề (Topic Shift Resolver) v3.0
    """
    def __init__(self):
        self.v2_resolver = EntityResolverV2()
        self.topic_stack: List[str] = []

    @staticmethod
    def _strip_diacritics(text: str) -> str:
        return text.lower().translate(_VIETNAMESE_STRIP)

    def push_topic(self, topic: str) -> None:
        """Đẩy một chủ đề mới vào Topic Stack (tối đa 5 chủ đề)."""
        clean_t = topic.strip()
        if clean_t and clean_t not in self.topic_stack:
            self.topic_stack.append(clean_t)
            if len(self.topic_stack) > 5:
                self.topic_stack.pop(0)

    def detect_topic_resumption(self, query: str) -> Optional[str]:
        """
        Nhận diện khi Master muốn quay lại một chủ đề cũ trong Stack.
        Ví dụ: "quay lại cái bảng lương lúc nãy", "tiếp tục file docx"
        """
        q_norm = self._strip_diacritics(query)
        if any(w in q_norm for w in ["quay lai", "tiep tuc", "quay ve", "cai luc nay", "file vua roi", "chu de cu"]):
            for top in reversed(self.topic_stack):
                top_norm = self._strip_diacritics(top)
                # Tìm xem có từ khóa nào của top nằm trong query không
                top_words = [w for w in top_norm.split() if len(w) > 2]
                if any(w in q_norm for w in top_words):
                    return top
            # Nếu không tìm thấy tên cụ thể, lấy chủ đề gần nhất trước đó
            if len(self.topic_stack) >= 2:
                return self.topic_stack[-2]
        return None

    def resolve(self, query: str, last_subject: str = "", last_query: str = "") -> str:
        # 0. DEMS Multi-Turn Coreference Resolution (EntityStack)
        from core.os.cognition.entity_stack import get_entity_stack
        stack = get_entity_stack()
        coref_resolved = stack.resolve_coreference(query)
        if coref_resolved != query:
            logger.info(f"🧠 [DEMS-COREF]: Coreference resolved '{query}' -> '{coref_resolved}'")
            return coref_resolved

        # 1. Kiểm tra khôi phục chủ đề cũ (Topic Resumption)
        resumed = self.detect_topic_resumption(query)
        if resumed:
            logger.info(f"🔄 [TOPIC-RESUME]: Khôi phục chủ đề '{resumed}' cho câu hỏi: '{query}'.")
            return f"[{resumed}] {query}"

        # 2. Utilize v2 Resolver with active entity stack pattern
        effective_subject = last_subject or (self.topic_stack[-1] if self.topic_stack else "")
        if effective_subject:
            mock_stack = [{"entity": effective_subject, "confidence": 0.9}]
            resolved, conf = self.v2_resolver.resolve(query, mock_stack)
            if resolved and conf > 0.6:
                return resolved

        # 3. Fallback to legacy regex heuristics if v2 didn't trigger
        if not effective_subject:
            return query

        query_lower = query.lower()
        needs_resolution = False
        for pattern, _ in _ANAPHORA_PATTERNS:
            if re.search(pattern, query_lower):
                needs_resolution = True
                break

        if not needs_resolution:
            query_nodia = self._strip_diacritics(query)
            for pattern, _ in _ANAPHORA_NODIA:
                if re.search(pattern, query_nodia):
                    needs_resolution = True
                    break

        if not needs_resolution:
            return query

        expanded = f"{effective_subject} {query}"
        return expanded

    def extract_subject(self, query: str, answer: str = "") -> str:
        q = query.lower()
        patterns = [
            r"gi(á|a|à|ạ|ả|ã) (vàng|v|va|vang|bạc|b|ba|bac|dầu|d|da|dau|xăng|x|xa|xang|usd|eur|bitcoin|eth)",
            r"(vàng|v|va|vang|bạc|b|ba|bac|dầu|d|da|dau|xăng|x|xa|xang|bitcoin|eth) (thế|th|the) (giới|g|gioi|trong nước|hôm nay)",
            r"thời (tiết|t|tiet) (tại|ở|) (\w+)",
            r"tỷ (giá|gia) (usd|eur|jpy|gbp|aud|cny)",
            r"chứng (khoán|khoan) (\w+)",
            r"l(ãi|ai) su(ất|at) (\w+)",
            r"cổ (phiếu|phieu) (\w+)",
            r"b(ả|a|à|á|ạ)ng (lương|luong|tính|tinh|chấm công|cham cong)",
            r"b(á|a|à|ạ|ả)o c(á|a|à|ạ|ả)o (doanh thu|tài chính|tiến độ)",
            r"file (excel|word|pdf|docx|xlsx)"
        ]
        for p in patterns:
            m = re.search(p, q)
            if m:
                subj = m.group(0)
                self.push_topic(subj)
                return subj

        if answer:
            a_lower = answer.lower()
            nouns = re.findall(r"\b(giá|vàng|thế giới|chứng khoán|tỷ giá|lãi suất|bảng lương|báo cáo)\b", a_lower, re.IGNORECASE)
            if nouns:
                subj = " ".join(nouns[:3])
                self.push_topic(subj)
                return subj

        subj = q[:60]
        self.push_topic(subj)
        return subj

    def is_anaphora(self, query: str) -> bool:
        """Kiểm tra xem câu truy vấn có chứa đại từ thay thế (nó, cái đó, việc này...) hay không."""
        query_lower = query.lower()
        for pattern, _ in _ANAPHORA_PATTERNS:
            if re.search(pattern, query_lower):
                return True
        query_nodia = self._strip_diacritics(query)
        for pattern, _ in _ANAPHORA_NODIA:
            if re.search(pattern, query_nodia):
                return True
        return False
