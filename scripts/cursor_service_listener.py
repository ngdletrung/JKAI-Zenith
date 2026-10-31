#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Cursor Service Listener (Port 45280)
File: scripts/cursor_service_listener.py
Port: 45280
Ownership: Master LeeTrung | Architecture: Cursor Headless Service Proxy
Purpose: Listens on port 45280 for incoming prompts from Antigravity/OpenCode.
         When a message arrives, it logs the task, plays a chime, saves to Cursor inbox,
         and automatically fires an acknowledgement/result back to Antigravity on port 45279!
"""

import os
import sys
import json
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.request

HOST = "127.0.0.1"
PORT = 45280
ANTIGRAVITY_WEBHOOK_URL = "http://127.0.0.1:45279/webhook"

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AI_TEAM_DIR = PROJECT_ROOT / "AI_TEAM"
INBOX_FILE = AI_TEAM_DIR / "inbox" / "cursor" / "TASK_CURRENT.md"
DISCUSSION_FILE = AI_TEAM_DIR / "discussion" / "cursor.md"
RESULTS_DIR = AI_TEAM_DIR / "results" / "cursor"
PID_FILE = AI_TEAM_DIR / "runtime" / "health" / "cursor_service.pid"


def notify_antigravity_back(task_id: str, message: str):
    """Sends automatic response back to Antigravity on port 45279."""
    payload = {
        "sender": "cursor",
        "action": "TASK_ACK_AND_REPLY",
        "task_id": task_id,
        "message": message,
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z")
    }
    req_data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        ANTIGRAVITY_WEBHOOK_URL,
        data=req_data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"[CursorService] Sent 2-way ACK back to Antigravity (Port 45279): HTTP {resp.status}")
    except Exception as e:
        print(f"[CursorService] Could not reach Antigravity Webhook: {e}")


class CursorRequestHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {"text": body.decode("utf-8", errors="ignore")}
        
        prompt_text = payload.get("text", payload.get("message", ""))
        sender = payload.get("sender", "antigravity")
        task_id = payload.get("task_id", f"TASK-CURSOR-{int(time.time())}")
        
        ts = time.strftime("%Y-%m-%d %H:%M:%S")
        print("\n" + "=" * 65)
        print(f"📥 [CURSOR SERVICE 45280] NHẬN TIN NHẮN TỪ {sender.upper()}!")
        print(f"[*] Task ID: {task_id}")
        print(f"[*] Nội dung: {prompt_text}")
        print("=" * 65)
        
        # 1. Update inbox and discussion log
        INBOX_FILE.parent.mkdir(parents=True, exist_ok=True)
        INBOX_FILE.write_text(f"# NHIỆM VỤ TỪ {sender.upper()}\n\n- Task ID: {task_id}\n- Time: {ts}\n\n{prompt_text}\n", encoding="utf-8")
        
        DISCUSSION_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(DISCUSSION_FILE, "a", encoding="utf-8") as f:
            f.write(f"\n\n## [{ts}] NHẬN TIN TỪ {sender.upper()} (CỔNG 45280)\n- Task ID: `{task_id}`\n- Nội dung: {prompt_text}\n- Trạng thái: Đã tự động tiếp nhận qua mạng Localhost.\n")

        # 2. Sound notification
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

        # 3. Send HTTP 200 to caller
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        res_payload = {
            "status": "RECEIVED",
            "agent": "cursor",
            "port": PORT,
            "task_id": task_id,
            "message": f"Cursor da nhan prompt: '{prompt_text[:50]}...'"
        }
        self.wfile.write(json.dumps(res_payload, ensure_ascii=False).encode("utf-8"))

        # 4. Automatically trigger 2-way push back to Antigravity (Port 45279)
        notify_antigravity_back(task_id, f"Cursor đã tự động nhận nhiệm vụ: {prompt_text[:60]}")

    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ONLINE",
            "agent": "cursor",
            "service": "Cursor Inbound HTTP Listener",
            "port": PORT
        }).encode("utf-8"))

    def log_message(self, format, *args):
        return


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, CursorRequestHandler)
    print("=" * 70)
    print(f"🚀 CURSOR INBOUND SERVICE LISTENER ĐANG CHẠY TRÊN http://{HOST}:{PORT}")
    print("   Antigravity & OpenCode có thể bắn tin nhắn trực tiếp cho Cursor!")
    print("=" * 70)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Dừng Cursor Service.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    main()
