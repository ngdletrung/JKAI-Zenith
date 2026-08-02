"""
Phát diff + mở tab file trên Mission Control (giống Cursor).

Gọi sau mỗi lần ghi/sửa file trong workspace agent hoặc promote.
"""

from __future__ import annotations

import difflib
import json
import time
from typing import Optional


def build_unified_diff(path: str, old_text: str, new_text: str) -> str:
    old_lines = (old_text or "").splitlines(keepends=True)
    new_lines = (new_text or "").splitlines(keepends=True)
    if not old_lines and not new_lines:
        return ""
    diff = difflib.unified_diff(
        old_lines,
        new_lines,
        fromfile=f"a/{path}",
        tofile=f"b/{path}",
        lineterm="",
    )
    lines = list(diff)
    if not lines:
        return f"--- a/{path}\n+++ b/{path}\n (nội dung không đổi hoặc thay toàn bộ)\n"
    return "\n".join(lines) + "\n"


def emit_file_edit(
    path: str,
    old_text: str,
    new_text: str,
    task_id: str = "sys",
    open_tab: bool = True,
) -> str:
    """
    Redis -> Mission Control socket `file_edit` + log tag FILE-EDIT (JSON).
    Payload bao gom added/removed de hien thi "+X -Y" kieu Antigravity.
    Tra ve chuoi diff.
    """
    diff_str = build_unified_diff(path, old_text, new_text)

    # Dem so dong them / xoa (bo qua header --- +++)
    added   = sum(1 for l in diff_str.splitlines() if l.startswith('+') and not l.startswith('+++'))
    removed = sum(1 for l in diff_str.splitlines() if l.startswith('-') and not l.startswith('---'))

    payload = {
        "type": "file_edit",
        "path": path.replace("\\", "/"),
        "diff": diff_str,
        "added": added,
        "removed": removed,
        "task_id": task_id,
        "ts": time.time(),
        "open_tab": open_tab,
    }
    body = json.dumps(payload, ensure_ascii=False)

    try:
        from core.redis_client import redis_safe

        r = redis_safe(lambda client: client, None)
        if r:
            r.publish("monitor:file_edit_channel", body)
            r.lpush("zenith:file_edits", body)
            r.ltrim("zenith:file_edits", 0, 99)
    except Exception:
        pass

    try:
        from core.utils.engine import engine

        engine.publish_mission_log("FILE-EDIT", body, task_id)
    except Exception:
        pass

    return diff_str



def read_text_if_exists(abs_path: str) -> str:
    try:
        with open(abs_path, "r", encoding="utf-8", errors="replace") as f:
            return f.read()
    except OSError:
        return ""
