# -*- coding: utf-8 -*-
"""
core/governance/internal_vocabulary.py
Biên giới thông tin: từ vựng nội bộ KHÔNG BAO GIỜ được xuất hiện
trong câu trả lời gửi Master (Red Team: log live 21:58 27/09 —
"Rửa mặt", "stage: ACTIVE", "world_version" lọt ra mặt user).

Quy tắc:
- Mọi tên stage/mã nội bộ/ID kỹ thuật PHẢI đăng ký tại đây.
- Output gate kiểm tra tự động — model không cãi được.
- Thêm tên mới vào đây thay vì vá lẻ từng prompt.
"""

from __future__ import annotations

import re
from typing import List, Tuple

# Tên nội bộ viết thường để so khớp không phân biệt hoa/thường.
# CHỈ chứa token kỹ thuật thuần túy — không chứa từ vai trò (receptionist),
# tên pipeline hay khái niệm Master vẫn đọc trong tài liệu.
INTERNAL_LITERAL_TERMS: Tuple[str, ...] = (
    "world_version",
    "ucws",
    "stage_4_1_deterministic",
    "stage_4_2_semantic",
    "lifecyclestage",
    "actionchainstate",
    "requirementlifecyclestage",
    "failurestage",
    "mission_context_pack",
    "tier_1",
    "tier_2",
    "tier_3",
    "tritierdecisionadapter",
    "tritierjevadapter",
    "jevprimitive",
    "decisionprimitive",
    "theta_fast_path",
    "circuit_breaker",
    "shadow_telemetry",
    "labeled_telemetry",
    "epistemic_auditor",
    "epistemicaudit",
    "fast_pipeline",
    "goalcontract",
    "state_fingerprint",
    "reflex_draft",
    "sanitized_state",
    "execution_receipt",
)

# Mẫu ID/mã kỹ thuật (regex, case-insensitive).
INTERNAL_PATTERNS: Tuple[re.Pattern, ...] = (
    re.compile(r"\bstage_\d+[_\w]*", re.IGNORECASE),
    re.compile(r"\btrace_[0-9a-f]{6,}\b", re.IGNORECASE),
    re.compile(r"\bZENITH_\d+-\d+_[0-9a-f]{6}\b", re.IGNORECASE),
    re.compile(r"\btask_id\s*[:=]", re.IGNORECASE),
    re.compile(r"\btrace_id\s*[:=]", re.IGNORECASE),
)

REDACTION_TOKEN = "[nội bộ]"


def find_internal_terms(text: str) -> List[str]:
    """Trả về các từ/mẫu nội bộ tìm thấy trong text (giữ thứ tự, không trùng)."""
    if not text:
        return []
    lowered = text.lower()
    hits: List[str] = []
    for term in INTERNAL_LITERAL_TERMS:
        if term in lowered and term not in hits:
            hits.append(term)
    for pattern in INTERNAL_PATTERNS:
        for match in pattern.findall(text):
            token = match if isinstance(match, str) else match[0]
            if token not in hits:
                hits.append(token)
    return hits


def gate_user_text(text: str) -> Tuple[str, List[str]]:
    """
    Cửa kiểm tra cuối cho text gửi Master.
    Trả về (text_đã_che, danh_sách_phát_hiện). Không phát hiện thì text nguyên vẹn.
    """
    hits = find_internal_terms(text)
    if not hits:
        return text, []
    cleaned = text
    for term in sorted(set(hits), key=len, reverse=True):
        if re.fullmatch(r"[A-Za-z_][A-Za-z0-9_.:=\- ]*", term):
            cleaned = re.sub(re.escape(term), REDACTION_TOKEN, cleaned, flags=re.IGNORECASE)
    for pattern in INTERNAL_PATTERNS:
        cleaned = pattern.sub(REDACTION_TOKEN, cleaned)
    return cleaned, hits
