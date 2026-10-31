#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Agent Inbound Wake Tool
File: scripts/wake_antigravity.py
Usage from OpenCode or Cursor:
    python scripts/wake_antigravity.py --sender opencode --action TURN_COMPLETED --msg "Xong bài"
"""

import sys
import json
import urllib.request
import argparse

WEBHOOK_URL = "http://127.0.0.1:45279/webhook"

def wake(sender: str, action: str, message: str):
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    payload = {
        "sender": sender,
        "action": action,
        "message": message
    }
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        WEBHOOK_URL,
        data=data,
        headers={"Content-Type": "application/json"}
    )
    try:
        with urllib.request.urlopen(req, timeout=5) as resp:
            print(f"[SUCCESS] Da ban tin hieu truc tiep danh thuc Antigravity thanh cong! (Ma: {resp.status})")
    except Exception as e:
        print(f"[WARNING] Khong the ket noi toi Antigravity Webhook (Port 45279): {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sender", default="opencode")
    parser.add_argument("--action", default="TURN_COMPLETED")
    parser.add_argument("--msg", default="Da hoan thanh luot phan bien")
    args = parser.parse_args()
    wake(args.sender, args.action, args.msg)
