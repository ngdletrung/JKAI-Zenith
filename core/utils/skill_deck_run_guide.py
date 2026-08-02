"""
Hướng dẫn chạy skill Command Deck — trả từ manual/workflow thật, không qua LLM bịa.
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

_RUN_HELP_RE = re.compile(
    r"(?:"
    r"(?:cần|can)\s+(?:cung cấp|chuan cap|cung cap|chuẩn bị|chuan bi|đưa|dua|gửi|gui)"
    r"|(?:làm sao|lam sao|how to)\s+(?:chạy|chay|run|dùng|dung|kích hoạt|kich hoat)"
    r"|(?:chạy|chay|run)\s+(?:skill|kỹ năng|ky nang)"
    r"|(?:đầu vào|dau vao|input|tham số|tham so)\s+(?:của|cuа|cho)?\s*skill"
    r"|skill\s+(?:này|nay|đó|do|nao)"
    r")",
    re.IGNORECASE,
)

# Phát hiện khi Master muốn THỰC THI skill với dữ liệu thật (không phải hỏi cách dùng).
# Ví dụ: "dùng skill #1002 để tranh luận về X", "chạy hội đồng về vấn đề Y",
#        "hãy dùng skill ... để phân tích ...", "sử dụng kỹ năng ... cho ..."
_EXECUTE_INTENT_RE = re.compile(
    r"(?:"
    r"(?:dùng|dung|sử\s*dụng|su\s*dung|hãy\s*dùng|hay\s*dung|kích\s*hoạt|kich\s*hoat|triệu\s*hồi|trieu\s*hoi)"
    r"\s+(?:skill|kỹ\s*năng|ky\s*nang|hội\s*đồng|hoi\s*dong|#\d+)[^?!.\n]{0,80}"
    r"(?:để|de|về|ve|cho|với|voi|phân\s*tích|phan\s*tich|tranh\s*luận|tranh\s*luan|thảo\s*luận|thao\s*luan|giải\s*quyết|giai\s*quyet|đánh\s*giá|danh\s*gia)"
    r")",
    re.IGNORECASE,
)

_DECK_REF = re.compile(r"#(\d{2,5})")


def goal_is_skill_run_help(goal: str) -> bool:
    """Trả về True nếu Master muốn BIẾT cách dùng skill (run guide).
    Trả về False nếu Master muốn THỰC THI skill với dữ liệu thật.
    """
    if not goal or goal.strip().startswith("/"):
        return False
    # Nếu câu có execute intent (có mệnh đề mục đích/dữ liệu kèm) → đây là lệnh chạy thật,
    # không phải hỏi cách dùng → bypass run_guide, để pipeline xử lý tiếp.
    if _EXECUTE_INTENT_RE.search(goal):
        return False
    return bool(_RUN_HELP_RE.search(goal))


def _deck_ids_from_text(text: str) -> List[str]:
    return list(dict.fromkeys(_DECK_REF.findall(text or "")))


def resolve_deck_ids(goal: str, history: Optional[List[Any]] = None, mission_id: Optional[str] = None) -> List[str]:
    ids = _deck_ids_from_text(goal)
    if ids:
        return ids
    if mission_id:
        try:
            from core.utils.mission_context import load_context_pack

            pack = load_context_pack(mission_id)
            if pack and pack.get("last_deck_ids"):
                return [str(x).lstrip("#") for x in pack["last_deck_ids"]]
        except Exception:
            pass
    if history:
        for item in reversed(history[-8:]):
            content = ""
            if isinstance(item, dict):
                content = str(item.get("content") or item.get("msg") or "")
            elif isinstance(item, (list, tuple)) and len(item) >= 2:
                content = str(item[1])
            ids = _deck_ids_from_text(content)
            if ids:
                return ids
    try:
        from core.utils.skill_deck_index import SkillDeckIndex

        if re.search(r"\b(skill|kỹ năng|ky nang)\s+(này|nay|đó|do)\b", goal, re.I):
            deck = SkillDeckIndex.get()
            deck.ensure_loaded()
            if deck._by_deck.get("7001"):
                return ["7001"]
    except Exception:
        pass
    return []


def _read_skill_docs(registry_id: str, intel_dir: Path) -> Dict[str, str]:
    out: Dict[str, str] = {}
    try:
        from core.utils.skill_deck_index import SkillDeckIndex

        data = SkillDeckIndex.get()._registry.get(registry_id, {})
        rel = (data.get("rel_path") or "").replace("\\", "/")
        if not rel:
            return out
        skill_dir = intel_dir / Path(rel).parent
        for name in ("manual.md", "workflow.md", "dossier.md", "SKILL.md"):
            p = skill_dir / name
            if p.is_file():
                out[name] = p.read_text(encoding="utf-8", errors="replace")[:4000]
    except Exception:
        pass
    return out


def build_skill_run_guide(deck_ids: List[str]) -> str:
    from core.utils.skill_deck_index import SkillDeckIndex

    deck = SkillDeckIndex.get()
    deck.ensure_loaded()
    intel = deck._intel_dir()
    parts = ["🏛️ **HƯỚNG DẪN CHẠY SKILL (Command Deck)**\n"]

    if not deck_ids:
        parts.append(
            "Chưa xác định số deck. Gõ rõ: `cần gì để chạy skill #7001` hoặc `/run_skill #7001`.\n"
        )
        return "\n".join(parts)

    for did in deck_ids[:3]:
        entry = deck.resolve(did)
        if not entry:
            parts.append(f"## #{did}\n⚠️ Không tìm thấy trên MAP_SKILLS.\n")
            continue
        rid = entry.registry_id or "?"
        parts.append(f"## {entry.display_id} — {entry.title}\n")
        parts.append(f"- **Registry**: `{rid}`\n")

        if rid == "SKILL_HUEIC_TAO_SKILL_DE_XUAT_THEO_FORM":
            parts.append(
                "### Master cần cung cấp (giai đoạn 1 — Deep Scan)\n"
                "1. **File mẫu**: một hoặc nhiều `.docx` / `.xlsx` / `.pdf` (biểu mẫu HUEIC cần tự động hóa).\n"
                "2. **Tên skill mong muốn** (tiếng Việt), ví dụ: `Đề xuất cấp kinh phí`.\n"
                "3. (Tuỳ chọn) Gắn file qua Mission Control **hoặc** đường dẫn trong workspace JKAI.\n\n"
                "### Cách chạy\n"
                "```text\n"
                "/run_skill #7001\n"
                "```\n"
                "Hoặc chat:\n"
                "```text\n"
                "Tạo skill [Tên Skill] — đính kèm file mẫu. Phân tích biến số trước, chưa đúc skill.\n"
                "```\n\n"
                "### Quy trình 4 bước (HUEIC Forge)\n"
                "| Bước | Việc | Master |\n"
                "|------|------|--------|\n"
                "| 1 Deep Scan | Đọc file mẫu, liệt kê biến số | Gửi file + tên skill |\n"
                "| 2 Variable Mapping | Bảng biến (ho_va_ten, …) | Xem & chỉnh |\n"
                "| 3 Confirmation | Xác nhận danh sách biến | Trả lời «đồng ý» / sửa |\n"
                "| 4 Final Forging | Đúc skill + đăng ký registry | Chờ hoàn tất |\n\n"
                "### Tham số kỹ thuật (`logic.py`)\n"
                "- `mode`: `analyze` (mặc định) hoặc `forge`\n"
                "- `skill_name`: tên skill\n"
                "- `files`: danh sách đường dẫn file mẫu\n"
                "- `confirmed_vars`: dict biến đã duyệt (khi `mode=forge`)\n\n"
                "**Lưu ý:** Lỗi «Model không hỗ trợ Tools API» là giới hạn model RECEPTIONIST "
                "(deepseek-r1), **không** phải thiếu `query` SEARCH_WEB. Chạy skill qua "
                "`/run_skill #7001` hoặc DEEP pipeline + executor, không cần ReAct thủ công.\n"
            )
        else:
            docs = _read_skill_docs(rid, intel)
            if docs.get("manual.md"):
                parts.append(f"### manual.md\n{docs['manual.md'][:2000]}\n")
            parts.append(
                f"\n**Chạy nhanh:** `/run_skill #{did}` hoặc `dùng skill #{did}` + mô tả đầu vào trong goal.\n"
            )
        parts.append("")

    parts.append(
        "---\n"
        "💡 Sau khi có file mẫu: upload Mission Control hoặc nêu path `scratch/projects/.../file.docx`.\n"
    )
    return "\n".join(parts)


def try_skill_run_guide(
    goal: str,
    history: Optional[List[Any]] = None,
    mission_id: Optional[str] = None,
) -> Optional[Dict[str, Any]]:
    if not goal_is_skill_run_help(goal):
        return None
    deck_ids = resolve_deck_ids(goal, history, mission_id)
    if not deck_ids and not re.search(r"\b(skill|kỹ năng)\s+(này|nay)\b", goal, re.I):
        return None
    return {
        "status": "success",
        "answer": build_skill_run_guide(deck_ids or ["7001"]),
        "source": "skill_deck_run_guide",
    }
