#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
AI Team Orchestrator Watcher Daemon
File: scripts/ai_team_orchestrator_daemon.py
Ownership: Master LeeTrung | Orchestrator (Antigravity)
Purpose: Runs continuously in the background to monitor Cursor and OpenCode file events,
         update system state, maintain heartbeats, and bridge 2-way communication.
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
RUNTIME_DIR = AI_TEAM_DIR / "runtime"
LOGS_DIR = AI_TEAM_DIR / "logs" / "audit"

FLAG_REPLY = CONTROL_DIR / "CURSOR_REPLY.flag"
FLAG_STOP = CONTROL_DIR / "STOP.flag"
STATE_FILE = CONTROL_DIR / "TRANG_THAI.json"
PID_FILE = RUNTIME_DIR / "health" / "orchestrator_daemon.pid"
HEARTBEAT_FILE = RUNTIME_DIR / "heartbeats" / "antigravity.json"
CURSOR_REPORT = AI_TEAM_DIR / "results" / "cursor" / "COMPLETION_REPORT.md"
EVENT_LOG = LOGS_DIR / "cursor_events.log"


def log_event(msg: str):
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(EVENT_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] {msg}\n")
    print(f"[{ts}] {msg}")


def update_heartbeat():
    HEARTBEAT_FILE.parent.mkdir(parents=True, exist_ok=True)
    payload = {
        "agent_id": "antigravity",
        "pid": os.getpid(),
        "timestamp": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "status": "RUNNING"
    }
    HEARTBEAT_FILE.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def main():
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    PID_FILE.parent.mkdir(parents=True, exist_ok=True)
    PID_FILE.write_text(str(os.getpid()), encoding="utf-8")

    log_event("🚀 AI_TEAM ORCHESTRATOR WATCHER DAEMON STARTED.")
    log_event(f"Monitoring: {AI_TEAM_DIR}")

    last_heartbeat_time = 0

    while True:
        try:
            now = time.time()
            if now - last_heartbeat_time >= 5:
                update_heartbeat()
                last_heartbeat_time = now

            if FLAG_STOP.exists():
                log_event("🚨 STOP.flag detected! Halting automated dispatch.")
                time.sleep(5)
                continue

            # Detect Cursor reply flag
            if FLAG_REPLY.exists():
                reply_content = FLAG_REPLY.read_text(encoding="utf-8").strip()
                FLAG_REPLY.unlink(missing_ok=True)
                log_event(f"📥 [2-WAY EVENT] Detected Cursor Reply: '{reply_content}'")

                # Update system state
                if STATE_FILE.exists():
                    try:
                        st = json.loads(STATE_FILE.read_text(encoding="utf-8"))
                        st["cursor_status"] = "REPLIED"
                        st["last_cursor_reply_at"] = time.strftime("%Y-%m-%dT%H:%M:%S%z")
                        st["last_cursor_message"] = reply_content
                        STATE_FILE.write_text(json.dumps(st, indent=2, ensure_ascii=False), encoding="utf-8")
                    except Exception as e:
                        log_event(f"Error updating state: {e}")

            time.sleep(2)
        except KeyboardInterrupt:
            log_event("Orchestrator daemon stopped by user.")
            break
        except Exception as e:
            log_event(f"Daemon exception: {e}")
            time.sleep(2)


if __name__ == "__main__":
    main()
