# -*- coding: utf-8 -*-
"""
[DEPRECATED — DO NOT USE]
Tệp `poll_reply.py` thuộc thế hệ Nguyên tắc 154 cũ (poll qua REST API /message với timeout 60s).
Đã bị thay thế hoàn toàn bởi `wait_for_opencode_reply.py` (Protocol v2.3 — Tiered Waiter 400s,
File-Confirmed Turn Gating, 4-condition Turn Block & SHA-256 verification).
"""
import sys

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

if __name__ == "__main__":
    print(
        "[DEPRECATED] 'poll_reply.py' đã ngừng sử dụng từ Protocol v2.0+.\n"
        "Vui lòng sử dụng: python \"Thao luan AI/wait_for_opencode_reply.py\" --timeout 400 --interval 5",
        file=sys.stderr,
    )
    sys.exit(1)
