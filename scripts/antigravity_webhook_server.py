#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Antigravity Inbound Webhook Server (True 2-Way Push Listener)
File: scripts/antigravity_webhook_server.py
Port: 45279
Ownership: Master LeeTrung | Architecture: Antigravity & OpenCode
Purpose: Listens for incoming POST notifications from OpenCode, Cursor, or other agents.
         When a notification arrives, it immediately wakes up Antigravity / dispatches the next turn
         without Antigravity having to poll or busy-wait on files!
"""

import os
import sys
import json
import time
from pathlib import Path
from http.server import HTTPServer, BaseHTTPRequestHandler

HOST = "127.0.0.1"
PORT = 45279

PROJECT_ROOT = Path(__file__).resolve().parent.parent
AI_TEAM_DIR = PROJECT_ROOT / "AI_TEAM"
RUNTIME_DIR = AI_TEAM_DIR / "runtime"
LOGS_DIR = AI_TEAM_DIR / "logs" / "audit"
INBOUND_EVENTS_FILE = RUNTIME_DIR / "inbound_events.jsonl"
SERVER_PID_FILE = RUNTIME_DIR / "health" / "antigravity_webhook.pid"


def log_inbound_event(data: dict):
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%dT%H:%M:%S%z")
    record = {
        "received_at": ts,
        "payload": data
    }
    with open(INBOUND_EVENTS_FILE, "a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")
    print(f"[{ts}] 🔔 [2-WAY PUSH RECEIVED] From: {data.get('sender', 'UNKNOWN')} | Action: {data.get('action', 'NOTIFY')} | Message: {data.get('message', '')}")


class WebhookHandler(BaseHTTPRequestHandler):
    def do_POST(self):
        content_length = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_length)
        
        try:
            payload = json.loads(body.decode("utf-8")) if body else {}
        except Exception:
            payload = {"raw_text": body.decode("utf-8", errors="ignore")}
        
        # Log event immediately
        log_inbound_event(payload)
        
        # Play local chime sound if on Windows
        try:
            import winsound
            winsound.MessageBeep(winsound.MB_ICONASTERISK)
        except Exception:
            pass

        # Send response back to caller
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        response = {
            "status": "RECEIVED",
            "server": "antigravity_inbound_webhook",
            "received_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "ack": True
        }
        self.wfile.write(json.dumps(response).encode("utf-8"))

    def do_GET(self):
        """Health check endpoint."""
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.end_headers()
        self.wfile.write(json.dumps({
            "status": "ONLINE",
            "service": "Antigravity Inbound Webhook Listener",
            "port": PORT
        }).encode("utf-8"))

    def log_message(self, format, *args):
        # Suppress noisy default http logging
        return


def run_server():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    SERVER_PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    SERVER_PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

    server_address = (HOST, PORT)
    httpd = HTTPServer(server_address, WebhookHandler)
    print("=" * 70)
    print(f"🚀 ANTIGRAVITY INBOUND WEBHOOK SERVER RUNNING ON http://{HOST}:{PORT}")
    print("   OpenCode & Cursor can now push direct signals to Antigravity!")
    print("=" * 70)

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[!] Webhook server stopped.")
    finally:
        httpd.server_close()


if __name__ == "__main__":
    run_server()
