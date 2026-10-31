#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor Local Watcher Daemon
File: scripts/cursor_daemon.py
Ownership: Master LeeTrung | Cursor Watcher
Purpose: Runs inside Cursor Terminal tab to continuously monitor incoming tasks from Antigravity/OpenCode
         and notify Master/Cursor with sound & console alerts without burning LLM tokens.
"""

import os
import sys
import time
import json
import hashlib
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AI_TEAM_DIR = PROJECT_ROOT / "AI_TEAM"
CONTROL_DIR = AI_TEAM_DIR / "control"
INBOX_CURSOR = AI_TEAM_DIR / "inbox" / "cursor" / "TASK_CURRENT.md"
FLAG_TASK = CONTROL_DIR / "CURSOR_TASK.flag"
FLAG_REPLY = CONTROL_DIR / "CURSOR_REPLY.flag"
FLAG_STOP = CONTROL_DIR / "STOP.flag"
RESULTS_CURSOR_REPORT = AI_TEAM_DIR / "results" / "cursor" / "COMPLETION_REPORT.md"


def play_chime():
    """Play Windows asterisk sound if on Windows."""
    try:
        import winsound
        winsound.MessageBeep(winsound.MB_ICONASTERISK)
    except Exception:
        pass


def file_sha256(path: Path) -> str:
    if not path.exists():
        return ""
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except Exception:
        return ""


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    print("=" * 70)
    print("👁️ CURSOR LOCAL WATCHER DAEMON (GIÁM SÁT 2 CHIỀU QUA FILE)")
    print("=" * 70)
    print(f"[*] Thư mục theo dõi: {AI_TEAM_DIR}")
    print("[*] Trạng thái: Đang chạy ngầm liên tục (0% token, cực nhẹ)...")
    print("[*] Để dừng daemon: Nhấn Ctrl + C bất kỳ lúc nào.\n")

    last_inbox_hash = file_sha256(INBOX_CURSOR)
    last_report_hash = file_sha256(RESULTS_CURSOR_REPORT)

    while True:
        try:
            # 1. Kiểm tra cờ STOP khẩn cấp
            if FLAG_STOP.exists():
                print("\n[!] 🚨 PHÁT HIỆN LỆNH DỪNG KHẨN CẤP (STOP.flag) TỪ MASTER!")
                play_chime()
                time.sleep(3)
                continue

            # 2. Chiều NHẬN: Phát hiện nhiệm vụ mới từ Antigravity
            curr_inbox_hash = file_sha256(INBOX_CURSOR)
            task_flag_exists = FLAG_TASK.exists()

            if task_flag_exists or (curr_inbox_hash and curr_inbox_hash != last_inbox_hash):
                last_inbox_hash = curr_inbox_hash
                if task_flag_exists:
                    FLAG_TASK.unlink(missing_ok=True)

                play_chime()
                print("\n" + "=" * 65)
                print("🔔 [TING!] CÓ NHIỆM VỤ MỚI TỪ ANTIGRAVITY DÀNH CHO CURSOR!")
                print("=" * 65)
                if INBOX_CURSOR.exists():
                    lines = INBOX_CURSOR.read_text(encoding="utf-8").splitlines()[:10]
                    for l in lines:
                        print(f"  > {l}")
                print("-" * 65)
                print("👉 HÃY BẢO CURSOR: '@AI_TEAM/inbox/cursor/TASK_CURRENT.md thực hiện nhiệm vụ này'\n")

            # 3. Chiều GỬI: Phát hiện Cursor đã làm xong báo cáo
            curr_report_hash = file_sha256(RESULTS_CURSOR_REPORT)
            if curr_report_hash and curr_report_hash != last_report_hash:
                last_report_hash = curr_report_hash
                # Tự động tạo cờ CURSOR_REPLY.flag nếu Cursor quên tạo
                if not FLAG_REPLY.exists():
                    FLAG_REPLY.write_text("CURSOR_DONE: auto_detected", encoding="utf-8")
                play_chime()
                print("\n" + "=" * 65)
                print("✅ [CURSOR_DAEMON] ĐÃ PHÁT HIỆN BÁO CÁO MỚI TỪ CURSOR!")
                print(f"[*] Đã kích hoạt cờ CURSOR_REPLY.flag gửi về cho Antigravity & OpenCode.")
                print("=" * 65 + "\n")

            time.sleep(2)  # Quét nhẹ nhàng mỗi 2 giây, không ngốn CPU, không ngốn token
        except KeyboardInterrupt:
            print("\n[!] Cursor Daemon đã dừng an toàn theo yêu cầu.")
            break
        except Exception as e:
            time.sleep(2)


if __name__ == "__main__":
    main()
