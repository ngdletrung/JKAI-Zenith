"""
Trả lời meta: "JKAI có tính năng gì?" từ registry thật — không qua LLM hallucinate.
"""

from __future__ import annotations

import re
from typing import List

_CAPABILITIES_RE = re.compile(
    r"(?:"
    r"(?:liệt kê|liet ke|list|kể|ke)\s+(?:ra\s+)?(?:các\s+)?(?:tính năng|tinh nang|khả năng|kha nang|chức năng|chuc nang)"
    r"|(?:tính năng|tinh nang|features?|khả năng|kha nang).{0,40}(?:của bạn|cuaban|jkai|chính mình|chinh minh|ban|bạn có|ban co|mình)"
    r"|(?:bạn là gì|ban la gi|bạn làm được (?:những )?gì|ban lam duoc (?:nhung )?gi)"
    r"|(?:bạn\s+(?:có\s+thể|có\s+khả\s+năng|có\s+biết)\s+(?:lập\ trình|code|viet\ code|viết\ code).{0,30}(?:không|đuoc\ khong|được\ không)?)"
    r"|(?:giới thiệu|gioi thieu).{0,30}(?:jkai|bản thân|ban than|hệ thống|he thong)"
    r"|what (?:are your|can you) (?:features|do|code|program)"
    r"|can you (?:code|program)"
    r")",
    re.IGNORECASE | re.DOTALL,
)

_SKILL_USE_RE = re.compile(
    r"\b(dùng|dung|sử dụng|su dung|kích hoạt|kich hoat|chạy|chay|run)\s+(skill|kỹ năng|ky nang)",
    re.IGNORECASE,
)

# Chào hỏi kèm hỏi danh tính → ưu tiên SOCIAL thay vì capabilities
_IDENTITY_GREETING_RE = re.compile(
    r"(?:^|[\s,])(?:hello|hi|hey|xin chào|chào|alo)\b.{0,40}\b(?:who are you|bạn là ai|ban la ai|tên gì|ten gi|bạn là gì|ban la gi)\b",
    re.IGNORECASE,
)

def _normalize(text: str) -> str:
    import unicodedata
    text = text.replace("đ", "d").replace("Đ", "D")
    return unicodedata.normalize("NFKD", text).encode("ASCII", "ignore").decode("utf-8")

def goal_is_capabilities_inquiry(goal: str) -> bool:
    if not goal or goal.strip().startswith("/"):
        return False
    # Chào hỏi + hỏi danh tính → trả lời xã giao, không phải danh mục năng lực
    if _IDENTITY_GREETING_RE.search(goal):
        return False
    # Loại trừ goal có ý định DÙNG skill (không phải hỏi về tính năng)
    if _SKILL_USE_RE.search(goal):
        return False
    if not bool(_CAPABILITIES_RE.search(goal)):
        return False
    # Loại trừ các goal bắt đầu bằng động từ tạo/viết để tránh false positive
    writing_starters = ["viet", "write", "tao", "create", "code", "script"]
    norm = _normalize(goal).lower().strip()
    for ws in writing_starters:
        if norm.startswith(ws):
            return False
    return True


def _deck_sample(limit: int = 12) -> List[str]:
    try:
        from core.utils.skill_deck_index import SkillDeckIndex

        deck = SkillDeckIndex.get()
        deck.ensure_loaded()
        items = []
        for did, entry in sorted(deck._by_deck.items(), key=lambda x: x[0])[:limit]:
            title = getattr(entry, "title", "") or did
            rid = getattr(entry, "registry_id", "") or "?"
            items.append(f"- #{did}: {title} → `{rid}`")
        return items
    except Exception:
        return ["- (Command Deck: xem `intelligence/MAP_SKILLS.md` hoặc `/search_skill`)"]


def build_capabilities_report() -> str:
    deck_lines = _deck_sample(10)
    return (
        "# JKAI Zenith — Tính năng hệ thống (báo cáo chính thức)\n\n"
        "Tôi là **JKAI Zenith**, AI OS (không chỉ chatbot). Dưới đây là khả năng **thật** trong stack hiện tại.\n\n"
        "## 1. Điều phối (AI OS)\n"
        "- **Kernel** `orchestrate_request`: reflex → skill deck → mission context → clone GitHub → workspace → chọn FAST/DEEP.\n"
        "- **Team patterns** (Harness): pipeline, fan-out, producer→reviewer, workspace agent.\n"
        "- **Mission Control**: log realtime, Kế hoạch / Giải pháp / Thay đổi / Nhật ký.\n\n"
        "## 2. Pipeline thực thi\n"
        "- **FAST**: phản xạ + tool (chat, tìm kiếm nhanh).\n"
        "- **DEEP**: Planner + CRITIC + từng bước tool.\n"
        "- **DEEP full (T2→T6)**: recon, context, forge, execute, critic, summarize.\n"
        "- **Workspace agent**: đọc/sửa trong `scratch/projects`, `services/`, … (như Cursor trong gốc JKAI).\n"
        "- **Web-only / clone repo**: phân tích URL GitHub (README hoặc shallow clone).\n\n"
        "## 3. Kỹ năng (Skill Deck)\n"
        f"- Hơn **{len(deck_lines)}+** kỹ năng trên Command Deck (MAP `#NNNN`). Ví dụ:\n"
        + "\n".join(deck_lines)
        + "\n"
        "- Tra cứu: `skill #1002 có gì`, `/search_skill docker`, `/run_skill #7001`.\n\n"
        "## 4. Lệnh nhanh\n"
        "- `/help` — toàn bộ lệnh; `/status` — sức khỏe; `/tusualoi` — audit repo.\n"
        "- Chat báo **lỗi** → tự **DEEP**; **phân tích / so sánh** → DEEP + review.\n\n"
        "## 5. Tích hợp ngoài\n"
        "- **MCP server** (`tools/jkai-mcp`): `jkai_chat`, `jkai_submit_task` từ Cursor/VS Code.\n\n"
        "---\n"
        "Gõ `/help` để xem lệnh chi tiết, hoặc hỏi cụ thể: *«dùng skill nào để audit code?»*.\n"
    )
