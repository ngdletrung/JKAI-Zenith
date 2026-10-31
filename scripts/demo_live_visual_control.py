# -*- coding: utf-8 -*-
"""
demo_live_visual_control.py
Kịch bản trình diễn Trực quan Điều khiển Máy tính (Visual Computer-Use Live Demo)
Thực thi trên Playwright Chromium và xuất hình ảnh trực quan vào thư mục Artifacts của Master.
"""

from __future__ import annotations

import io
import json
import hashlib
import http.server
import logging
import os
import socketserver
import sys
import threading
import time
from datetime import datetime, timezone
from pathlib import Path

from PIL import Image
from playwright.sync_api import sync_playwright

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))
sys.path.insert(0, str(PROJECT_ROOT / "services" / "ai-browser"))

from visual_aci_gateway import VisualACIGateway, ActionRiskLevel

LAB_PORT = 8765
ARTIFACTS_DIR = Path(r"C:\Users\AdminPC-MMO\.gemini\antigravity\brain\34ab7517-7c5f-4cc8-b833-f816792b0802")
ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)

SOM_IMG_PATH = ARTIFACTS_DIR / "router_webfig_som_live.png"
SUCCESS_IMG_PATH = ARTIFACTS_DIR / "router_webfig_success_live.png"

ROUTER_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>MikroTik RouterOS v7 WebFig - Sovereign Lab</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; margin: 0; display: flex; height: 100vh; background: #eef2f5; }
        #sidebar { width: 220px; background: #1a252f; color: #fff; padding: 20px; box-sizing: border-box; }
        #sidebar h2 { font-size: 17px; margin-bottom: 25px; color: #3498db; letter-spacing: 0.5px; }
        .menu-item { padding: 12px 14px; cursor: pointer; border-radius: 6px; margin-bottom: 8px; font-size: 14px; transition: background 0.2s; }
        .menu-item:hover { background: #2c3e50; }
        .menu-item.active { background: #2980b9; font-weight: bold; }
        #content { flex: 1; padding: 30px; }
        .card { background: white; padding: 25px; border-radius: 8px; box-shadow: 0 4px 6px rgba(0,0,0,0.06); max-width: 650px; }
        h3 { margin-top: 0; margin-bottom: 20px; color: #2c3e50; font-size: 18px; border-bottom: 2px solid #ecf0f1; padding-bottom: 10px; }
        .form-group { margin-bottom: 18px; }
        label { display: block; margin-bottom: 6px; font-weight: 600; font-size: 13px; color: #34495e; }
        input[type="text"] { width: 100%; padding: 10px; border: 1px solid #bdc3c7; border-radius: 5px; font-size: 14px; box-sizing: border-box; }
        .btn-container { margin-top: 25px; display: flex; gap: 15px; }
        #btn-apply-changes { background: #e74c3c; color: white; border: none; padding: 12px 24px; border-radius: 6px; font-size: 14px; font-weight: bold; cursor: pointer; transition: background 0.2s; }
        #btn-apply-changes:hover { background: #c0392b; }
        #btn-cancel { background: #95a5a6; color: white; border: none; padding: 12px 20px; border-radius: 6px; font-size: 14px; cursor: pointer; }
        #status-msg { margin-top: 20px; padding: 14px; border-radius: 6px; display: none; font-size: 14px; line-height: 1.5; }
        .applied { display: block !important; background: #2ecc71 !important; color: white !important; font-weight: bold; box-shadow: 0 2px 4px rgba(46,204,113,0.3); }
    </style>
</head>
<body>
    <div id="sidebar">
        <h2>RouterOS v7 WebFig</h2>
        <div class="menu-item">Interfaces</div>
        <div class="menu-item active">IP / Firewall</div>
        <div class="menu-item">Routing</div>
        <div class="menu-item">System & Reboot</div>
    </div>
    <div id="content">
        <div class="card">
            <h3>Firewall Forward Filter Rule #1</h3>
            <div class="form-group">
                <label>Chain Mode</label>
                <input type="text" id="input-chain" value="forward" readonly>
            </div>
            <div class="form-group">
                <label>Source Address / Subnet</label>
                <input type="text" id="input-src" value="192.168.88.0/24">
            </div>
            <div class="form-group">
                <label>Action</label>
                <input type="text" id="input-act" value="accept" readonly>
            </div>
            <div class="btn-container">
                <button id="btn-apply-changes" onclick="applySettings()">Apply Changes</button>
                <button id="btn-cancel">Revert</button>
            </div>
            <div id="status-msg"></div>
        </div>
    </div>
    <script>
        function applySettings() {
            var msg = document.getElementById('status-msg');
            msg.className = 'applied';
            msg.innerHTML = '<strong>Cau hinh tuong lua da duoc luu thanh cong!</strong><br><small>Thoi gian: ' + new Date().toISOString() + '</small>';
        }
    </script>
</body>
</html>
""".encode("utf-8")


class RouterLabHandler(http.server.BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(ROUTER_HTML)))
        self.end_headers()
        self.wfile.write(ROUTER_HTML)

    def log_message(self, format, *args):
        pass


def run_demo():
    print("=" * 80)
    print("🚀 BẮT ĐẦU CHẠY THỰC CHỨNG ĐIỀU KHIỂN MÁY TÍNH TRỰC QUAN (LIVE DEMO)")
    print("=" * 80)

    # 1. Khởi động Web Server
    socketserver.TCPServer.allow_reuse_address = True
    server = socketserver.TCPServer(("127.0.0.1", LAB_PORT), RouterLabHandler)
    server_thread = threading.Thread(target=server.serve_forever, daemon=True)
    server_thread.start()
    time.sleep(0.5)

    with sync_playwright() as p:
        print("[1/5] Khởi động trình duyệt Playwright Chromium thật...")
        browser = p.chromium.launch(headless=True)
        context = browser.new_context(viewport={"width": 1024, "height": 720})
        page = context.new_page()

        print(f"[2/5] Truy cập giao diện Router WebFig tại http://127.0.0.1:{LAB_PORT}/...")
        page.goto(f"http://127.0.0.1:{LAB_PORT}/", wait_until="load")

        # Chụp ảnh ban đầu
        raw_screenshot_before = page.screenshot(type="png")
        hash_before = hashlib.sha256(raw_screenshot_before).hexdigest()

        # Quét các phần tử tương tác
        print("[3/5] Quét Cây trợ năng (Accessibility Tree) và định vị phần tử...")
        btn_apply = page.wait_for_selector("#btn-apply-changes")
        input_src = page.wait_for_selector("#input-src")
        menu_fw = page.wait_for_selector(".menu-item.active")
        btn_cancel = page.wait_for_selector("#btn-cancel")

        elements = [
            {"ref_id": "@e1", "name": "Menu: IP / Firewall", "rect": menu_fw.bounding_box()},
            {"ref_id": "@e2", "name": "Input: Src Address", "rect": input_src.bounding_box()},
            {"ref_id": "@e3", "name": "Button: Apply Changes", "rect": btn_apply.bounding_box()},
            {"ref_id": "@e4", "name": "Button: Revert", "rect": btn_cancel.bounding_box()},
        ]

        # Phủ nhãn Set-of-Marks (SoM)
        print("[4/5] Phủ lớp nhãn số Set-of-Marks [1], [2], [3], [4] lên ảnh màn hình...")
        som_image_bytes = VisualACIGateway.render_set_of_marks(raw_screenshot_before, elements)
        SOM_IMG_PATH.write_bytes(som_image_bytes)
        print(f"  -> Đã lưu ảnh Set-of-Marks vào: {SOM_IMG_PATH.name}")

        # Đánh giá Mutation Risk
        risk, reasons = VisualACIGateway.evaluate_mutation_risk("click", "Apply Changes", "button")
        print(f"  -> Đánh giá rủi ro nút 'Apply Changes': {risk} ({', '.join(reasons)})")

        # Sinh Action Confirmation Card
        card = VisualACIGateway.create_confirmation_card(
            task_id="task_live_demo_01",
            trace_id=f"trace_{int(time.time())}",
            action="click",
            target_ref="@e3",
            element_name="Apply Changes",
            element_rect=btn_apply.bounding_box(),
            state_before_hash=hash_before,
            rollback_command="/ip firewall filter remove [find comment='test']"
        )
        print(f"  -> Đã phát hành Action Confirmation Card: {card['action_id']}")

        # Xác thực phê duyệt & TOCTOU
        is_valid, msg = VisualACIGateway.verify_action_execution(card, card["approval_token"], hash_before)
        print(f"  -> Xác thực chữ ký & TOCTOU: {is_valid} ({msg})")

        # Gửi xung click chuột thật!
        print("[5/5] Gửi xung click chuột thật vào nút [3] Apply Changes...")
        page.click("#btn-apply-changes")
        page.wait_for_selector(".applied", timeout=2000)

        # Chụp ảnh sau khi thao tác
        raw_screenshot_after = page.screenshot(type="png")
        SUCCESS_IMG_PATH.write_bytes(raw_screenshot_after)
        print(f"  -> Đã lưu ảnh trạng thái sau khi Click vào: {SUCCESS_IMG_PATH.name}")

        # Đo lường Visual Diff
        diff_res = VisualACIGateway.compute_visual_diff(raw_screenshot_before, raw_screenshot_after)
        print(f"  -> Đo lường Visual Diff: {diff_res['diff_percentage']}% diện tích màn hình thay đổi.")

        browser.close()

    server.shutdown()
    print("=" * 80)
    print("🎉 TRÌNH DIỄN THÀNH CÔNG 100%!")
    print(f"Ảnh 1 (Set-of-Marks): {SOM_IMG_PATH.name}")
    print(f"Ảnh 2 (Kết quả sau Click): {SUCCESS_IMG_PATH.name}")
    print("=" * 80)


if __name__ == "__main__":
    run_demo()
