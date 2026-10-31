#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Team Bidirectional Sync Bridge
File: scripts/ai_team_sync_bridge.py
Ownership: Master LeeTrung | Swarm: Antigravity, OpenCode, Cursor
Governed by SOP-MULTI-AI-V10 & Protocol Spec V11.1
"""

import os
import sys
import time
import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AI_TEAM_DIR = PROJECT_ROOT / "AI_TEAM"
CONTROL_DIR = AI_TEAM_DIR / "control"
INBOX_DIR = AI_TEAM_DIR / "inbox"
RESULTS_DIR = AI_TEAM_DIR / "results"
DISCUSSION_DIR = AI_TEAM_DIR / "discussion"

CURSOR_INBOX_FILE = INBOX_DIR / "cursor" / "TASK_CURRENT.md"
CURSOR_OUTBOX_STATUS = RESULTS_DIR / "cursor" / "STATUS.json"
CURSOR_OUTBOX_REPORT = RESULTS_DIR / "cursor" / "COMPLETION_REPORT.md"
CURSOR_DISCUSSION_FILE = DISCUSSION_DIR / "cursor.md"

FLAG_CURSOR_TASK = CONTROL_DIR / "CURSOR_TASK.flag"
FLAG_CURSOR_REPLY = CONTROL_DIR / "CURSOR_REPLY.flag"
FLAG_STOP = CONTROL_DIR / "STOP.flag"


def get_file_hash(path: Path) -> str:
    """Compute sha256 hash of a file if it exists."""
    if not path.exists():
        return ""
    content = path.read_bytes()
    return hashlib.sha256(content).hexdigest()


class BidirectionalSyncBridge:
    """
    Manages two-way event synchronization between Antigravity/OpenCode and Cursor.
    Prevents token burn by running as a zero-token OS-level file watcher.
    """
    def __init__(self):
        self.last_cursor_hash = get_file_hash(CURSOR_DISCUSSION_FILE)
        self.last_outbox_hash = get_file_hash(CURSOR_OUTBOX_REPORT)

    def check_cursor_reply(self) -> Optional[Dict[str, Any]]:
        """
        Detects if Cursor has responded via:
        1. Explicit flag: CURSOR_REPLY.flag
        2. Content change in cursor.md
        3. Completion report in results/cursor/
        """
        # Case 1: Explicit reply flag
        if FLAG_CURSOR_REPLY.exists():
            flag_msg = FLAG_CURSOR_REPLY.read_text(encoding="utf-8").strip()
            FLAG_CURSOR_REPLY.unlink(missing_ok=True)
            return {
                "source": "FLAG_CURSOR_REPLY",
                "message": flag_msg,
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")
            }

        # Case 2: New completion report in results
        curr_outbox_hash = get_file_hash(CURSOR_OUTBOX_REPORT)
        if curr_outbox_hash and curr_outbox_hash != self.last_outbox_hash:
            self.last_outbox_hash = curr_outbox_hash
            status_data = {}
            if CURSOR_OUTBOX_STATUS.exists():
                try:
                    status_data = json.loads(CURSOR_OUTBOX_STATUS.read_text(encoding="utf-8"))
                except Exception:
                    pass
            return {
                "source": "CURSOR_COMPLETION_REPORT",
                "status": status_data,
                "report": CURSOR_OUTBOX_REPORT.read_text(encoding="utf-8"),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")
            }

        # Case 3: New comments in discussion/cursor.md
        curr_cursor_hash = get_file_hash(CURSOR_DISCUSSION_FILE)
        if curr_cursor_hash and curr_cursor_hash != self.last_cursor_hash:
            self.last_cursor_hash = curr_cursor_hash
            return {
                "source": "CURSOR_DISCUSSION_UPDATE",
                "content": CURSOR_DISCUSSION_FILE.read_text(encoding="utf-8"),
                "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")
            }

        return None

    def post_task_to_cursor(self, task_id: str, title: str, instructions: str, owned_paths: list):
        """Dispatches a task from Orchestrator into Cursor's inbox."""
        payload = {
            "task_id": task_id,
            "title": title,
            "assigned_to": "cursor",
            "assigned_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "owned_paths": owned_paths,
            "instructions": instructions
        }
        
        md_content = f"""# 🎯 NHIỆM VỤ HIỆN TẠI CHO CURSOR: {title}

- **Mã nhiệm vụ (Task ID)**: `{task_id}`
- **Thời gian giao**: `{payload['assigned_at']}`
- **Phạm vi file được phép sửa (`owned_paths`)**:
{chr(10).join([f"  - `{p}`" for p in owned_paths])}

---

## 📝 Hướng dẫn thực thi:
{instructions}

---

## ⚡ Hướng dẫn trả lời 2 chiều:
1. Khi hoàn thành hoặc có ý kiến phản hồi, Cursor ghi vào:
   - Thảo luận nhanh: `AI_TEAM/discussion/cursor.md`
   - Hoặc hoàn thành code: Tạo `AI_TEAM/results/cursor/COMPLETION_REPORT.md` và `AI_TEAM/results/cursor/STATUS.json`.
2. Tạo tệp cờ rỗng để kích hoạt tự động:
   `AI_TEAM/control/CURSOR_REPLY.flag`
"""
        CURSOR_INBOX_FILE.parent.mkdir(parents=True, exist_ok=True)
        CURSOR_INBOX_FILE.write_text(md_content, encoding="utf-8")
        
        # Place notification flag
        FLAG_CURSOR_TASK.write_text(f"TASK_READY:{task_id}", encoding="utf-8")
        print(f"[SyncBridge] Dispatched task {task_id} to Cursor inbox.")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    bridge = BidirectionalSyncBridge()
    print("[SyncBridge] AI Team Bidirectional Sync Bridge Initialized.")
    print(f"[SyncBridge] Monitoring {AI_TEAM_DIR}")
    
    # Check current state once
    reply = bridge.check_cursor_reply()
    if reply:
        print(f"[SyncBridge] Detected Cursor event: {reply['source']}")
    else:
        print("[SyncBridge] No pending Cursor reply. System idle.")


if __name__ == "__main__":
    main()
