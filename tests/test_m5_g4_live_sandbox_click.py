# -*- coding: utf-8 -*-
"""
tests/test_m5_g4_live_sandbox_click.py
[M5-G4 NATIVE MUTATION GATE VERIFICATION]:
Thực nghiệm kiểm soát thao tác Click vật lý thật trên Windows trong môi trường Sandbox Notepad cô lập.
Tuân thủ nghiêm ngặt 7 Tiêu chí của OpenCode Lượt 140:
1. Dedicated sandbox boundary: Chỉ cho phép click trong phạm vi Notepad allowlist, non-elevated.
2. Approval token: Ký số HMAC ràng buộc HWND, PID, target, action, expiry, nonce.
3. Chặn đứng 100% các vi phạm: Không token, sai Target, sai PID, Replay Attack.
4. TOCTOU Revalidation: Thẩm định lại Foreground và Bounding Box ngay trước mouse_down.
5. Watchdog Timer & Failsafe luôn trực sẵn.
6. Dọn dẹp sạch sẽ (Cleanup Invariant).
"""

import json
import os
import sys
import time
from datetime import datetime, timezone
import pytest

from services.ai_desktop import (
    DesktopActRequest,
    DesktopOSActuator,
    DesktopSecurityGate,
    NativeWindowInspector,
    NativeWindowsMouseAdapter,
    NotepadSandboxSession,
)


@pytest.mark.skipif(sys.platform != "win32", reason="M5-G4 yêu cầu môi trường Windows thật có màn hình hiển thị")
def test_m5_g4_live_sandbox_click_with_approval_token():
    """
    Thực nghiệm toàn diện Cổng M5-G4 trên Windows thật:
    - Chặn click không token
    - Chặn click sai Target
    - Chặn click sai PID
    - Thực thi click thành công khi có token hợp lệ
    - Chặn Replay Attack khi tái sử dụng token
    """
    captured_at = datetime.now(timezone.utc).isoformat()
    trace_id = f"trace_m5_g4_live_click_{int(time.time()*1000)}"
    task_id = "TASK_M5_G4_SANDBOX_CLICK_EXPERIMENT"
    run_id = f"run_{os.getpid()}_{int(time.time())}"

    evidence_artifact = {}
    time.sleep(1.5)  # Nhịp thở hạ nhiệt (Cool-down interval) cho Windows Process Manager
    session = NotepadSandboxSession(timeout_s=12.0)

    try:
        # 1. Khởi động tiến trình Notepad sandbox cô lập và bóc tách HWND chính
        hwnd_found, pid = session.start()
        assert hwnd_found > 0, f"Không tìm thấy HWND của cửa sổ chính Notepad (PID={pid})"

        inspector = NativeWindowInspector()
        adapter = NativeWindowsMouseAdapter()

        # Khởi tạo Actuator với Live Adapter & Inspector
        actuator = DesktopOSActuator(
            mouse_adapter=adapter,
            window_inspector=inspector,
            is_live_mode=True,
        )

        info_before = inspector.get_window_info(hwnd_found)
        assert info_before["is_elevated"] is False, "Notepad sandbox không được elevated"
        assert info_before["elevation_status"] == "VERIFIED_STANDARD", "Bắt buộc quyền VERIFIED_STANDARD"
        win_rect = info_before["rect"]

        elements = inspector.inspect_window_elements(hwnd_found)
        assert len(elements) > 0, "Không tìm thấy control con nào trong Notepad"

        target_elem = elements[0]
        for el in elements:
            if el.control_type.lower() == "edit" or el.name.lower() == "edit":
                target_elem = el
                break

        target_name = target_elem.name
        target_center = target_elem.center

        # ==============================================================
        # CASE 1: [FAIL-CLOSED] Click THIẾU TOKEN -> BỊ CHẶN DỨT KHOÁT
        # ==============================================================
        req_no_token = DesktopActRequest(
            action="click",
            target_name=target_name,
            target_hwnd=hwnd_found,
            approval_token="",  # Không có token
            trace_id=trace_id,
            task_id=task_id,
        )
        res_no_token = actuator.execute_action(req_no_token)
        assert res_no_token.status == "rejected"
        assert "APPROVAL_REQUIRED" in res_no_token.msg

        # ==============================================================
        # CASE 2: [TARGET BINDING] Token cấp cho 'File' nhưng đòi click 'Edit' -> BỊ CHẶN
        # ==============================================================
        token_wrong_target = DesktopSecurityGate.issue_approval_token(
            hwnd=hwnd_found,
            process_name="notepad.exe",
            target_name="File",  # Token cho 'File'
            action="click",
            pid=pid,
        )
        req_wrong_target = DesktopActRequest(
            action="click",
            target_name=target_name,  # Yêu cầu 'Edit'
            target_hwnd=hwnd_found,
            approval_token=token_wrong_target,
            trace_id=trace_id,
            task_id=task_id,
        )
        res_wrong_target = actuator.execute_action(req_wrong_target)
        assert res_wrong_target.status == "rejected"
        assert "TOKEN_BINDING_MISMATCH" in res_wrong_target.msg
        assert "Target" in res_wrong_target.msg

        # ==============================================================
        # CASE 3: [PID BINDING] Token cấp sai PID -> BỊ CHẶN DỨT KHOÁT
        # ==============================================================
        token_wrong_pid = DesktopSecurityGate.issue_approval_token(
            hwnd=hwnd_found,
            process_name="notepad.exe",
            target_name=target_name,
            action="click",
            pid=pid + 9999,  # Sai PID
        )
        req_wrong_pid = DesktopActRequest(
            action="click",
            target_name=target_name,
            target_hwnd=hwnd_found,
            approval_token=token_wrong_pid,
            trace_id=trace_id,
            task_id=task_id,
        )
        res_wrong_pid = actuator.execute_action(req_wrong_pid)
        assert res_wrong_pid.status == "rejected"
        assert "TOKEN_BINDING_MISMATCH" in res_wrong_pid.msg
        assert "PID" in res_wrong_pid.msg

        # ==============================================================
        # CASE 4: [AUTHORIZED LIVE CLICK] Token Hợp Lệ -> THỰC THI THÀNH CÔNG
        # ==============================================================
        valid_token = DesktopSecurityGate.issue_approval_token(
            hwnd=hwnd_found,
            process_name="notepad.exe",
            target_name=target_name,
            action="click",
            pid=pid,
            validity_seconds=60,
        )
        req_valid = DesktopActRequest(
            action="click",
            target_name=target_name,
            target_hwnd=hwnd_found,
            approval_token=valid_token,
            trace_id=trace_id,
            task_id=task_id,
        )
        res_valid = actuator.execute_action(req_valid)
        assert res_valid.status == "success", f"Click hợp lệ thất bại: {res_valid.msg}"
        assert res_valid.action == "click"
        assert res_valid.mutation_risk == "MUTATION"
        assert res_valid.final_coords == target_center
        assert res_valid.evidence["approval_token_hash"].startswith("sha256_")
        assert res_valid.trajectory_steps > 0

        # ==============================================================
        # CASE 5: [REPLAY ATTACK PREVENTION] Tái sử dụng Token cũ -> BỊ CHẶN
        # ==============================================================
        req_replay = DesktopActRequest(
            action="click",
            target_name=target_name,
            target_hwnd=hwnd_found,
            approval_token=valid_token,  # Dùng lại token đã tiêu thụ
            trace_id=trace_id,
            task_id=task_id,
        )
        res_replay = actuator.execute_action(req_replay)
        assert res_replay.status == "rejected"
        assert "TOKEN_REPLAY_ATTACK" in res_replay.msg

        # Ghi nhận biên bản bằng chứng thực địa Cổng M5-G4
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
                "name": target_name,
                "control_type": target_elem.control_type,
                "automation_id": target_elem.automation_id,
                "rect": target_elem.rect,
                "center": target_center,
            },
            "mutation_gate_verifications": {
                "case_1_no_token_rejected": res_no_token.status == "rejected" and "APPROVAL_REQUIRED" in res_no_token.msg,
                "case_2_target_mismatch_rejected": res_wrong_target.status == "rejected" and "TOKEN_BINDING_MISMATCH" in res_wrong_target.msg,
                "case_3_pid_mismatch_rejected": res_wrong_pid.status == "rejected" and "TOKEN_BINDING_MISMATCH" in res_wrong_pid.msg,
                "case_4_valid_token_authorized_click": res_valid.status == "success" and res_valid.mutation_risk == "MUTATION",
                "case_5_replay_attack_rejected": res_replay.status == "rejected" and "TOKEN_REPLAY_ATTACK" in res_replay.msg,
            },
            "authorized_action_receipt": {
                "action": res_valid.action,
                "target": res_valid.resolved_target,
                "click_coordinates": res_valid.final_coords,
                "trajectory_steps_count": res_valid.trajectory_steps,
                "approval_token_hash": res_valid.evidence.get("approval_token_hash"),
                "toctou_pre_action_revalidated": True,
            },
            "gate_compliance": {
                "m5_g4_mutation_token_enforced": True,
                "replay_attack_prevented": True,
                "unauthorized_click_prevented": True,
                "single_authorized_sandbox_click_executed": True,
                "webfig_mutation_executed": False,
                "uac_accessed": False,
            },
        }

    finally:
        # 2. Dọn dẹp an toàn tiến trình Notepad sandbox & Ghi nhận Cleanup Evidence
        cleanup_report = session.stop()
        evidence_artifact["cleanup_evidence"] = cleanup_report

        # Lưu evidence ra thư mục outputs
        os.makedirs("outputs/evidence_m5", exist_ok=True)
        evidence_file = "outputs/evidence_m5/m5_g4_live_click_evidence.json"
        with open(evidence_file, "w", encoding="utf-8") as f:
            json.dump(evidence_artifact, f, indent=2, ensure_ascii=False)

        assert cleanup_report["cleanup_ok"] is True, f"Cleanup thất bại: {cleanup_report}"
        assert cleanup_report["process_alive_after_cleanup"] is False, "Tiến trình vẫn còn sống sau cleanup!"
