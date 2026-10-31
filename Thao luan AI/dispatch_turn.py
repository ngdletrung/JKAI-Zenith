#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
FAST DISPATCH & UNIFIED TWO-AGENT WORKFLOW
File: Thao luan AI/dispatch_turn.py
Purpose: Hợp nhất toàn bộ quy trình 5 bước thành ĐÚNG 1 LỆNH DUY NHẤT.

Capabilities:
1. Tự động dò session active của OpenCode Desktop.
2. Tự động đọc Lượt cuối, tính turn_id và parent_turn_id.
3. Tự động đóng gói Turn Block, tính SHA-256 content_hash chuẩn xác.
4. Tự động ghi nguyên tử vào 'Noi dung thao luan.md'.
5. Tự động đồng bộ 'state.json'.
6. Tự động kích hoạt OpenCode qua HTTP REST API.
7. Tùy chọn --wait: Lắng nghe phản hồi siêu tốc với chu kỳ 1s.
"""

import os
import sys
import time
import json
import argparse
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(SCRIPT_DIR))

from file_lock import (
    file_lock, atomic_write, compute_turn_content_hash,
    MAX_DISCUSSION_LINES, MAX_DISCUSSION_BYTES
)
from trigger_opencode import (
    find_opencode_port, get_opencode_auth_header, get_active_session_id as resolve_active_session_id,
    recover_state, log_dispatch_command, DISCUSSION_FILE, STATE_FILE, load_state
)
from wait_for_opencode_reply import parse_turn_blocks, wait_for_reply


def get_active_session_id() -> str:
    """Tự động tìm session OpenCode Desktop active mới nhất."""
    port = find_opencode_port()
    if not port:
        raise RuntimeError("Không tìm thấy OpenCode Desktop đang chạy trên 127.0.0.1!")
    auth_header = get_opencode_auth_header()
    session_id = resolve_active_session_id(port, auth_header)
    if not session_id:
        raise RuntimeError("Không tìm thấy session nào của OpenCode cho workspace D:\\Docker\\JKAI!")
    return session_id


def dispatch_turn(
    speaker: str,
    phase: str,
    title: str,
    body: str,
    wait: bool = False,
    timeout: int = 180,
    poll_interval: int = 1
):
    print("=" * 70)
    print("⚡ FAST DISPATCH V3.0 — HỢP NHẤT QUY TRÌNH THẢO LUẬN SIÊU TỐC")
    print("=" * 70)

    # 1. Tìm session OpenCode Desktop
    session_id = get_active_session_id()
    print(f"🎯 Target OpenCode Session: {session_id}")

    # 2. Đọc lượt cuối cùng trong file thảo luận
    if not DISCUSSION_FILE.exists():
        raise FileNotFoundError(f"Không tìm thấy tệp {DISCUSSION_FILE}")

    content = DISCUSSION_FILE.read_text(encoding="utf-8")
    blocks = parse_turn_blocks(content)
    if blocks:
        last_block = blocks[-1]
        turn_str = str(last_block.get("meta", {}).get("turn_id", ""))
        parent_turn_id = int(turn_str) if turn_str.isdigit() else 0
        turn_id = parent_turn_id + 1
    else:
        parent_turn_id = 0
        turn_id = 1

    print(f"🔢 Phân bổ lượt: Lượt {turn_id} (Parent: {parent_turn_id}) | Người nói: {speaker}")

    # 3. Chuẩn hóa thân bài & tính chữ ký
    now_str = time.strftime("%Y-%m-%d %H:%M:%S")
    clean_body = body.strip()
    full_turn_body = (
        f"### Lượt {turn_id}: {speaker} — {title.strip()}\n\n"
        f"{clean_body}\n\n"
        f"— Ký tên: **{speaker}** | {now_str} (GMT+7)"
    )

    content_hash = compute_turn_content_hash(full_turn_body)

    # 4. Đóng gói Turn Block hoàn chỉnh
    turn_block = (
        f"\n---\n\n"
        f"<!-- TURN_BEGIN\n"
        f"turn_id: {turn_id}\n"
        f"parent_turn_id: {parent_turn_id}\n"
        f"speaker: {speaker}\n"
        f"phase: {phase}\n"
        f"session_id: {session_id}\n"
        f"-->\n\n"
        f"{full_turn_body}\n\n"
        f"<!-- TURN_END\n"
        f"turn_id: {turn_id}\n"
        f"speaker: {speaker}\n"
        f"content_hash: {content_hash}\n"
        f"-->\n"
    )

    # 5. Ghi nguyên tử vào Noi dung thao luan.md
    with file_lock(str(DISCUSSION_FILE)):
        current_text = DISCUSSION_FILE.read_text(encoding="utf-8")
        updated_text = current_text.rstrip() + turn_block
        atomic_write(str(DISCUSSION_FILE), updated_text)

    line_count = len(updated_text.splitlines())
    byte_count = len(updated_text.encode("utf-8"))
    print(f"📝 Đã ghi Lượt {turn_id} vào '{DISCUSSION_FILE.name}' (Dòng: {line_count}/{MAX_DISCUSSION_LINES}, Size: {round(byte_count/1024, 2)} KB)")

    # 6. Đồng bộ hóa state.json
    recover_state(force_unlock=True)
    print("🔄 Đã đồng bộ nguyên tử 'state.json'!")

    # 7. Phát lệnh Trigger đánh thức OpenCode
    port = find_opencode_port()
    auth_header = get_opencode_auth_header()
    # Kiểm tra xem session có thay đổi so với session ghi nhận gần nhất không
    live_state = load_state()
    last_known_sess = live_state.get("session", {}).get("opencode_session_id") or live_state.get("opencode_session_id")
    is_session_changed = (last_known_sess is None or last_known_sess != session_id)
    session_change_directive = ""
    if is_session_changed:
        session_change_directive = (
            "⚠️ [CHỈ THỊ MASTER - PHÁT HIỆN SESSION MỚI TỪ OPENCODE]:\n"
            "OpenCode BẮT BUỘC ĐỌC tệp 'Thao luan AI/Quy trinh & Nguyen tac thao luan AI.md' "
            "và GHI NHỚ, THỰC HIỆN NGHIÊM NGẶT các nguyên tắc làm việc tại '.keyword.md' (.keywork.md)!\n\n"
        )

    dispatch_msg = (
        f"{session_change_directive}"
        f"Kính gửi {('OpenCode' if speaker != 'Opencode' else 'Antigravity')}: "
        f"{speaker} đã gửi Lượt {turn_id} ('{title[:60]}'). "
        f"Mời bạn đọc cuối tệp 'Thao luan AI/Noi dung thao luan.md' và ghi phản hồi Lượt {turn_id + 1}."
    )

    import urllib.request
    url = f"http://127.0.0.1:{port}/api/session/{session_id}/prompt"
    payload = json.dumps({"text": dispatch_msg}).encode("utf-8")
    req = urllib.request.Request(
        url, data=payload, headers={"Content-Type": "application/json", "Authorization": f"Basic {auth_header}"}
    )
    with urllib.request.urlopen(req, timeout=10) as resp:
        if resp.status in (200, 201):
            print(f"🚀 Đã kích hoạt OpenCode thành công qua port {port}!")
            log_dispatch_command(session_id, turn_id, dispatch_msg)
        else:
            print(f"⚠️ Trigger trả về mã: {resp.status}")

    # 8. Lắng nghe phản hồi siêu tốc nếu --wait
    if wait:
        print(f"\n⏳ [FAST WAITER] Bắt đầu lắng nghe phản hồi (Chu kỳ: {poll_interval}s, Timeout: {timeout}s)...")
        wait_for_reply(
            timeout_sec=timeout,
            poll_interval_sec=poll_interval,
            allow_legacy_fallback=False,
            strict_hash=False
        )


def main():
    parser = argparse.ArgumentParser(description="Fast Dispatch V3.0 — 1 Lệnh Duy Nhất Cho Thảo Luận AI")
    parser.add_argument("--speaker", default="Antigravity", help="Người nói (mặc định: Antigravity)")
    parser.add_argument("--phase", default="THAO_LUAN_KY_THUAT_SIEU_TOC", help="Tên phase giao thức")
    parser.add_argument("--title", required=True, help="Tiêu đề lượt thảo luận")
    parser.add_argument("--body", help="Nội dung lượt thảo luận")
    parser.add_argument("--body-file", help="Đường dẫn tệp chứa nội dung lượt thảo luận")
    parser.add_argument("--wait", action="store_true", help="Chờ phản hồi của OpenCode ngay sau khi gửi")
    parser.add_argument("--timeout", type=int, default=180, help="Thời gian chờ tối đa (mặc định: 180s)")
    parser.add_argument("--interval", type=int, default=1, help="Chu kỳ thăm dò (mặc định: 1s)")

    args = parser.parse_args()

    body_content = ""
    if args.body_file:
        p = Path(args.body_file)
        if p.exists():
            body_content = p.read_text(encoding="utf-8")
        else:
            raise FileNotFoundError(f"Không tìm thấy file: {args.body_file}")
    elif args.body:
        body_content = args.body
    else:
        raise ValueError("Bắt buộc cung cấp --body hoặc --body-file!")

    dispatch_turn(
        speaker=args.speaker,
        phase=args.phase,
        title=args.title,
        body=body_content,
        wait=args.wait,
        timeout=args.timeout,
        poll_interval=args.interval
    )


if __name__ == "__main__":
    main()
