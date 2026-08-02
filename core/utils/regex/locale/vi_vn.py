"""
Vietnamese-specific regex patterns for intent detection & NLP.
Gathered from: deep_routing.py, project_workspace.py, reflex_gate.py,
intent_taxonomy.py, jkai_capabilities.py, fast_fix_routing.py
"""

import re
from typing import Pattern

__all__ = [
    # Knowledge / Definition
    "KNOWLEDGE_QUERY",
    # Error / Debug
    "ERROR_VI", "AUDIT_VI", "FIX_VI",
    # Search / News
    "SEARCH_NEWS",
    # Social / Greeting
    "CHAT", "SOCIAL_GREETING", "IDENTITY_INQUIRY", "CAPABILITIES_INQUIRY",
    # Build / Operate
    "BUILD", "OPERATE",
    # Fast fix
    "SINGLE_FILE_FIX", "SMALL_SCOPE",
    # Normalization
    "clean_vn_for_match",
]

# ── Knowledge / Definition ─────────────────────────────────────────────
KNOWLEDGE_QUERY = re.compile(
    r"\b(là gì|la gi|là ai|la ai|định nghĩa|dinh nghia|khái niệm|khai niem|"
    r"giải thích|giai thich|explain|what is|who is|what are|"
    r"tìm hiểu|tim hieu|có nghĩa là|co nghia la|"
    r"khác nhau|khac nhau|so sánh|so sanh|"
    r"tại sao|tai sao|vì sao|vi sao|nguyên nhân|nguyen nhan|"
    r"làm thế nào|lam the nao|làm sao|lam sao|"
    r"cách nào|cach nao|cách.*(làm|học|dùng|sử dụng)|"
    r"cach.*(lam|hoc|dung|su dung)|"
    r"hướng dẫn|huong dan|tutorial|guide|"
    r"học\s+\w+|hoc\s+\w+|"
    r"\w+\s+gì\b|\w+\s+gi\b|\w+\s+nhỉ\b)\b",
    re.IGNORECASE,
)

# ── Error / Debug ─────────────────────────────────────────────────────
ERROR_VI = re.compile(
    r"\b(lỗi|loi|bug|crash|hỏng|hong|đứt|dut|sập|sap|"
    r"không chạy|khong chay|không hoạt động|khong hoat dong|"
    r"sửa lỗi|sua loi|tìm lỗi|tim loi|tìm nguyên nhân|tim nguyen nhan|"
    r"fix\s+bug|broken|no output|connection refused)\b",
    re.IGNORECASE,
)

AUDIT_VI = re.compile(
    r"\b(rà soát|ra soat|điểm nghẽn|diem nghen|audit|bottleneck|"
    r"tối ưu hệ thống|toi uu he thong|"
    r"kiểm tra|kiem tra|check|phân tích|phan tich|"
    r"xem lỗi|xem loi|chạy thử|chay thu|đọc code|doc code)\b",
    re.IGNORECASE,
)

FIX_VI = re.compile(
    r"\b(sửa|sua|fix|repair|sửa lỗi|sua loi|khắc phục|khac phuc|"
    r"typo|đổi|doi)\b",
    re.IGNORECASE,
)

# ── Search / News ─────────────────────────────────────────────────────
SEARCH_NEWS = re.compile(
    r"\b(tin tức|tin tuc|tìm kiếm|tim kiem|tra cứu|tra cuu|"
    r"search|news|thời sự|thoi su|hôm nay|hom nay|mới nhất|moi nhat)\b",
    re.IGNORECASE,
)

# ── Social / Greeting ─────────────────────────────────────────────────
CHAT = re.compile(
    r"^(xin chào|chào|hello|hi\b|cảm ơn|cam on|thanks|thời tiết|thoi tiet)\b",
    re.IGNORECASE,
)

SOCIAL_GREETING = re.compile(
    r"\b(chào|chao|xin chào|xin chao|hi|hello|hey|"
    r"cảm ơn|cam on|cám ơn|cam on|thanks|thank you)\b",
    re.IGNORECASE,
)

IDENTITY_INQUIRY = re.compile(
    r"\b(bạn là ai|ban la ai|ai là|ai la|who are you|"
    r"tên là gì|ten la gi|ai tạo ra|ai tao ra|người tạo|nguoi tao|"
    r"công ty nào|cong ty nao)\b",
    re.IGNORECASE,
)

CAPABILITIES_INQUIRY = re.compile(
    r"(?:"
    r"(?:liệt kê|liet ke|list|kể|ke)\s+(?:ra\s+)?(?:các\s+)?"
    r"(?:tính năng|tinh nang|khả năng|kha nang|chức năng|chuc nang)"
    r"|(?:tính năng|tinh nang|features?|khả năng|kha nang)"
    r".{0,40}(?:của bạn|cuaban|jkai|chính mình|chinh minh|ban|bạn có|ban co|mình)"
    r"|(?:bạn là gì|ban la gi|bạn làm được gì|ban lam duoc gi)"
    r"|(?:giới thiệu|gioi thieu)"
    r".{0,30}(?:jkai|bản thân|ban than|hệ thống|he thong)"
    r"|what (?:are your|can you) (?:features|do)"
    r")",
    re.IGNORECASE | re.DOTALL,
)

# ── Build / Operate ───────────────────────────────────────────────────
BUILD = re.compile(
    r"\b(tạo|tao|build|implement|scaffold|viết api|viet api|deploy|"
    r"docker compose)\b",
    re.IGNORECASE,
)

OPERATE = re.compile(
    r"\b(docker|deploy|chạy lệnh|chay lenh|"
    r"kubectl|systemctl|restart)\b",
    re.IGNORECASE,
)

# ── Fast fix ──────────────────────────────────────────────────────────
SINGLE_FILE_FIX = re.compile(
    r"\b(sửa|sua|fix|typo|đổi|doi)\b.*"
    r"\b([\w\-]+(?:/[\w\-]+)*\.(?:py|md|json|yaml|yml|ts|tsx|js))\b",
    re.IGNORECASE,
)

SMALL_SCOPE = re.compile(
    r"\b(một file|mot file|single file|chỉ file|chi file|this file)\b",
    re.IGNORECASE,
)


# ── Normalization helpers ─────────────────────────────────────────────
def clean_vn_for_match(text: str) -> str:
    """Strip diacritics and lowercase for loose matching."""
    text = text.replace("đ", "d").replace("Đ", "D")
    import unicodedata
    return unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("ascii").lower().strip()
