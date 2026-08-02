# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/context/entity_resolver.py
# - Role: Entity and Anaphora Resolver bridged to Mission State v2
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v2.0 (Integrated)

import re
from typing import Optional

# Import Zenith OS v2 resolver
from mission_state import EntityResolver as EntityResolverV2

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
    def __init__(self):
        self.v2_resolver = EntityResolverV2()

    @staticmethod
    def _strip_diacritics(text: str) -> str:
        return text.lower().translate(_VIETNAMESE_STRIP)

    def resolve(self, query: str, last_subject: str = "", last_query: str = "") -> str:
        # Utilize v2 Resolver with active entity stack pattern
        if last_subject:
            mock_stack = [{"entity": last_subject, "confidence": 0.9}]
            resolved, conf = self.v2_resolver.resolve(query, mock_stack)
            if resolved and conf > 0.6:
                return resolved

        # Fallback to legacy regex heuristics if v2 didn't trigger
        if not last_subject:
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
        expanded = f"{last_subject} {query}"
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
        ]
        for p in patterns:
            m = re.search(p, q)
            if m:
                return m.group(0)
        if answer:
            a_lower = answer.lower()
            nouns = re.findall(r"\b(giá|vàng|thế giới|chứng khoán|tỷ giá|lãi suất)\b", a_lower, re.IGNORECASE)
            if nouns:
                return " ".join(nouns[:3])
        return q[:60]

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
