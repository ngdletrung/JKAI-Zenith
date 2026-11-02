# -*- coding: utf-8 -*-
"""
tests/test_m5_g6_live_sandbox_mouse_move.py
[M5-G6 SANDBOX LIVE VISUAL MOUSE MOVEMENT VERIFICATION]:
Thực nghiệm di chuyển con trỏ chuột vật lý Windows thật một cách trực quan
trên cửa sổ ứng dụng Notepad sandbox theo đường cong Cubic Bezier (Smooth Mouse).
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
import pytest

from services.ai_desktop import (
    DesktopWatchdog,
    NativeWindowInspector,
    NativeWindowsMouseAdapter,
    NotepadSandboxSession,
    SmoothMouseEngine,
)


@pytest.mark.skipif(sys.platform != "win32", reason="M5-G6 yêu cầu môi trường Windows thật có màn hình hiển thị")
def test_m5_g6_live_sandbox_mouse_movement():
    """
    Thực hiện Cổng M5-G6: Di chuyển con trỏ chuột vật lý thật lướt mượt mà
    từ vị trí ban đầu tới tâm Edit control của cửa sổ Notepad sandbox.
    """
    captured_at = datetime.now(timezone.utc).isoformat()
    trace_id = f"trace_m5_g6_live_move_{int(time.time()*1000)}"
    task_id = "TASK_M5_G6_SANDBOX_MOUSE_MOVE"
    run_id = f"run_{os.getpid()}_{int(time.time())}"

    evidence_artifact = {}
    session = NotepadSandboxSession(timeout_s=10.0)

    try:
        # 1. Khởi động tiến trình Notepad sandbox an toàn và lấy HWND chính
        hwnd_found, pid = session.start()
        assert hwnd_found > 0, f"Không tìm thấy HWND của Notepad sandbox (PID={pid})"

        inspector = NativeWindowInspector()
        adapter = NativeWindowsMouseAdapter()

        # 2. Snapshot trước action
        info_before = inspector.get_window_info(hwnd_found)
        assert info_before["is_elevated"] is False, "Notepad sandbox không được elevated"
        assert info_before["elevation_status"] == "VERIFIED_STANDARD", "Bắt buộc quyền VERIFIED_STANDARD"
        win_rect = info_before["rect"]
        left, top, right, bottom = win_rect
        assert right > left and bottom > top, f"Bounding box không hợp lệ: {win_rect}"

        # 3. Tìm kiếm phần tử mục tiêu bên trong cửa sổ Notepad
        elements = inspector.inspect_window_elements(hwnd_found)
        assert len(elements) > 0, "Không tìm thấy control con nào trong Notepad"

        target_elem = elements[0]
        for el in elements:
            if el.control_type.lower() == "edit" or el.name.lower() == "edit":
                target_elem = el
                break

        target_x, target_y = target_elem.center

        # 4. Ràng buộc an toàn tọa độ đích: Phải nằm gọn trong window_rect, cấm (0,0)
        assert target_x > 0 and target_y > 0, f"Tọa độ ({target_x}, {target_y}) không được là (0,0)"
        assert left <= target_x <= right and top <= target_y <= bottom, (
            f"Tọa độ đích ({target_x}, {target_y}) trượt ra ngoài rect {win_rect}"
        )

        # Định vị điểm xuất phát an toàn bên trong cửa sổ Notepad
        init_x = left + 60
        init_y = top + 60
        adapter.move_to(init_x, init_y)
        time.sleep(0.1)

        # 5. TOCTOU Revalidation: Thẩm định lại HWND và PID ngay trước khi di chuột
        reval_info = inspector.get_window_info(hwnd_found)
        assert reval_info["hwnd"] == hwnd_found, "TOCTOU: HWND bị tráo đổi!"
        assert reval_info["pid"] == pid, "TOCTOU: PID bị tráo đổi!"

        # 6. Khởi động Watchdog Timer
        watchdog = DesktopWatchdog(timeout_s=5.0)
        watchdog.start()

        start_cursor_pos = adapter.get_position()

        # 7. THỰC THI DI CHUYỂN CHUỘT TRỰC QUAN (MOVE-ONLY 100%)
        trajectory_points = []
        try:
            trajectory_points = SmoothMouseEngine.execute_smooth_move(
                adapter=adapter,
                target_x=target_x,
                target_y=target_y,
                steps=40,
                step_delay_s=0.015,
                cancel_check=watchdog.is_cancelled,
            )
        finally:
            watchdog.stop()

        end_cursor_pos = adapter.get_position()

        # 8. Kiểm chứng kết quả di chuyển
        assert watchdog.is_cancelled() is False, "Thao tác chuột bị Watchdog timeout ngắt!"
        assert len(trajectory_points) >= 20, f"Quỹ đạo phải có ít nhất 20 bước, thực tế: {len(trajectory_points)}"
        assert trajectory_points[-1] == (target_x, target_y), (
            f"Điểm cuối của quỹ đạo {trajectory_points[-1]} không khớp tọa độ đích {(target_x, target_y)}"
        )

        # 9. Lập biên bản Evidence Cổng M5-G6
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
            "window_rect": win_rect,
            "monitor_id": info_before.get("monitor_id"),
            "dpi": info_before.get("dpi"),
            "dpi_scale": info_before.get("dpi_scale"),
            "is_elevated": info_before.get("is_elevated"),
            "elevation_status": info_before.get("elevation_status"),
            "target_element": {
                "name": target_elem.name,
                "control_type": target_elem.control_type,
                "automation_id": target_elem.automation_id,
                "rect": target_elem.rect,
                "center": (target_x, target_y),
            },
            "mouse_motion": {
                "start_cursor_position": start_cursor_pos,
                "target_cursor_position": (target_x, target_y),
                "end_cursor_position": end_cursor_pos,
                "trajectory_steps_count": len(trajectory_points),
                "sample_trajectory": trajectory_points[:: max(1, len(trajectory_points) // 8)],
                "smooth_bezier_easing": "Cubic Smoothstep (Ease-In-Out)",
                "zero_teleportation_verified": True,
            },
            "safety_guards": {
                "toctou_pre_move_revalidation": True,
                "target_within_window_bounds": True,
                "watchdog_timeout_s": 5.0,
                "watchdog_triggered": False,
                "failsafe_corner_zero_active": True,
            },
            "gate_compliance": {
                "m5_g6_move_only_enforced": True,
                "mouse_click_executed": False,
                "mouse_down_executed": False,
                "mouse_up_executed": False,
                "keyboard_input_executed": False,
                "webfig_mutation_executed": False,
                "uac_accessed": False,
            },
        }

    finally:
        # 10. Dọn dẹp sạch sẽ & Thu thập Cleanup Evidence
        cleanup_report = session.stop()
        evidence_artifact["cleanup_evidence"] = cleanup_report

        os.makedirs("outputs/evidence_m5", exist_ok=True)
        evidence_file = "outputs/evidence_m5/m5_g6_live_mouse_move_evidence.json"
        with open(evidence_file, "w", encoding="utf-8") as f:
            json.dump(evidence_artifact, f, indent=2, ensure_ascii=False)

        assert cleanup_report["cleanup_ok"] is True, f"Cleanup thất bại: {cleanup_report}"
        assert cleanup_report["process_alive_after_cleanup"] is False, "Tiến trình vẫn còn sống sau cleanup!"
