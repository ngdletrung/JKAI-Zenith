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
    r"|(?:bạn là gì|ban la gi|bạn làm được gì|ban lam duoc gi)"
    r"|(?:giới thiệu|gioi thieu).{0,30}(?:jkai|bản thân|ban than|hệ thống|he thong)"
    r"|what (?:are your|can you) (?:features|do)"
    r")",
    re.IGNORECASE | re.DOTALL,
)


def goal_is_capabilities_inquiry(goal: str) -> bool:
    if not goal or goal.strip().startswith("/"):
        return False
    return bool(_CAPABILITIES_RE.search(goal))


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
