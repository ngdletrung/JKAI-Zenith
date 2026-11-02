# -*- coding: utf-8 -*-
"""
tests/test_m5_g3_live_observe.py
[M5-G3 LIVE READ-ONLY OBSERVE VERIFICATION]:
Thực nghiệm quan sát trực tiếp trên một cửa sổ ứng dụng Windows thật (Notepad sandbox).
Ràng buộc nghiêm ngặt:
- 100% READ-ONLY: TUYỆT ĐỐI KHÔNG CLICK, KHÔNG MOVE, KHÔNG KEYBOARD.
- Thu thập bằng chứng thực tế: HWND thật, PID thật, process path, rect, monitor ID, DPI scale.
- Native Elevation Check: Xác thực quyền hạn TokenElevation qua Windows API (bắt buộc VERIFIED_STANDARD).
- Tự động đóng cửa sổ và dọn dẹp sạch sẽ (Cleanup Verification Invariant).
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
import pytest

from services.ai_desktop import NativeWindowInspector, NotepadSandboxSession


@pytest.mark.skipif(sys.platform != "win32", reason="M5-G3 chỉ chạy trên môi trường hệ điều hành Windows thật")
def test_m5_g3_live_read_only_observe_notepad():
    """
    Thực hiện Cổng M5-G3: Đọc trạng thái và cây điều khiển của cửa sổ Notepad thật
    mà không tương tác hay làm thay đổi bất kỳ trạng thái nào của hệ điều hành.
    """
    captured_at = datetime.now(timezone.utc).isoformat()
    trace_id = f"trace_m5_g3_live_{int(time.time()*1000)}"
    task_id = "TASK_M5_G3_NOTEPAD_OBSERVE"
    run_id = f"run_{os.getpid()}_{int(time.time())}"

    evidence_artifact = {}
    session = NotepadSandboxSession(timeout_s=10.0)

    try:
        # 1. Khởi động Notepad sandbox và bóc tách chính xác HWND
        hwnd_found, pid = session.start()
        assert hwnd_found > 0, f"Không tìm thấy HWND của Notepad (PID={pid})"

        inspector = NativeWindowInspector()

        # 2. Quan sát trạng thái cửa sổ thực tế (Window Info)
        info_before = inspector.get_window_info(hwnd_found)

        # 3. Bóc tách cây điều khiển (Child Controls - Win32 Child Window Enumeration)
        elements = inspector.inspect_window_elements(hwnd_found)

        # 4. Quan sát lại sau (Stability Check)
        info_after = inspector.get_window_info(hwnd_found)

        # 5. Đối soát an toàn theo Hợp đồng M5-G3
        assert info_before["is_elevated"] is False, "Cửa sổ Notepad thử nghiệm không được chạy dưới quyền Elevated"
        assert info_before["elevation_status"] == "VERIFIED_STANDARD", (
            f"Chỉ chấp nhận VERIFIED_STANDARD cho sandbox live observe, thực tế: {info_before['elevation_status']}"
        )
        assert info_before["dpi"] > 0
        assert info_before["dpi_scale"] > 0.0
        assert "notepad" in info_before.get("process_name", "").lower()
        assert info_before["hwnd"] == hwnd_found
        assert len(elements) > 0, "Phải tìm thấy ít nhất 1 control con trong cửa sổ Notepad thật"

        # 6. Tạo gói evidence hoàn chỉnh cho Cổng M5-G3
        evidence_artifact = {
            "captured_at": captured_at,
            "run_id": run_id,
            "task_id": task_id,
            "trace_id": trace_id,
            "target_pid": pid,
            "target_hwnd": hwnd_found,
            "process_name": info_before.get("process_name"),
            "process_path": info_before.get("process_path"),
            "window_title": info_before.get("title"),
            "window_rect": info_before.get("rect"),
            "monitor_id": info_before.get("monitor_id"),
            "dpi": info_before.get("dpi"),
            "dpi_scale": info_before.get("dpi_scale"),
            "is_elevated": info_before.get("is_elevated"),
            "elevation_status": info_before.get("elevation_status"),
            "control_tree_classification": "Win32 Child Window Enumeration (win32gui.EnumChildWindows), NOT full UI Automation",
            "controls_enumerated_count": len(elements),
            "sample_controls": [
                {
                    "name": el.name,
                    "control_type": el.control_type,
                    "automation_id": el.automation_id,
                    "rect": el.rect,
                    "center": el.center,
                }
                for el in elements[:10]
            ],
            "foreground_stability": {
                "hwnd_before": info_before.get("hwnd"),
                "hwnd_after": info_after.get("hwnd"),
                "stable": info_before.get("hwnd") == info_after.get("hwnd"),
            },
            "visual_evidence_policy": "SCREENSHOT_AND_UIA_CAPTURE_EXCLUDED_IN_G3_READ_ONLY_POLICY",
            "gate_compliance": {
                "m5_g3_read_only_enforced": True,
                "mouse_click_executed": False,
                "mouse_move_executed": False,
                "keyboard_input_executed": False,
            },
        }

    finally:
        # 7. Dọn dẹp sạch sẽ & Thu thập Cleanup Evidence
        cleanup_report = session.stop()
        evidence_artifact["cleanup_evidence"] = cleanup_report

        os.makedirs("outputs/evidence_m5", exist_ok=True)
        evidence_file = "outputs/evidence_m5/m5_g3_live_observe_evidence.json"
        with open(evidence_file, "w", encoding="utf-8") as f:
            json.dump(evidence_artifact, f, indent=2, ensure_ascii=False)

        assert cleanup_report["cleanup_ok"] is True, f"Cleanup thất bại: {cleanup_report}"
        assert cleanup_report["process_alive_after_cleanup"] is False, "Tiến trình vẫn còn sống sau cleanup!"
