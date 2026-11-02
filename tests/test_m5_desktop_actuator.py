# -*- coding: utf-8 -*-
"""
tests/test_m5_desktop_actuator.py
Bộ kiểm thử tự động toàn diện cho Cấp độ 2: Desktop OS Actuator (M5).
Tuân thủ nghiêm ngặt 8 Cổng Kiểm định (M5-G0 đến M5-G7) được OpenCode phê duyệt:
1. Threat Model & Process/Window Boundary Guard & Elevated Blocker (M5-G0).
2. Pure Mock UIA Tree & Coordinate Transformation (M5-G1).
3. Mock Mouse Adapter & Smooth Bezier Trajectory (M5-G2).
4. Window Boundary & Anti-Drift Invariant (M5-G3).
5. Signed One-Time Mutation Approval Gate & Anti-Replay (M5-G4).
6. Evidence Contract Verification (M5-G0 -> M5-G4).
7. Tool Arbiter Intent Routing (Hexad Sovereign Actuators Matrix).
"""

import math
import pytest
from core.kernel.tool_arbiter import tool_arbiter, ToolDomain
from services.ai_desktop import (
    DesktopSecurityGate,
    DesktopSecurityViolation,
    SmoothMouseEngine,
    MockDesktopMouseAdapter,
    WindowElementRef,
    MockWindowInspector,
    DesktopOSActuator,
    DesktopActRequest,
    DesktopActResponse,
)


class TestM5ThreatModelAndSecurityGate:
    """[M5-G0 & M5-G4] Kiểm thử Threat Model & Cổng phòng vệ Desktop."""

    @pytest.mark.parametrize("denied_proc", [
        "taskmgr.exe",
        "regedit.exe",
        "cmd.exe",
        "powershell.exe",
        "pwsh.exe",
        "consent.exe",
        "credentialuibroker.exe",
        "logonui.exe",
    ])
    def test_threat_model_strictly_denies_blacklisted_processes(self, denied_proc: str):
        """Tiến trình thuộc Blacklist quản trị/UAC phải bị từ chối tuyệt đối."""
        ok, reason = DesktopSecurityGate.validate_process_scope(denied_proc)
        assert ok is False
        assert "SECURITY_DENIAL" in reason

    @pytest.mark.parametrize("allowed_proc", [
        "notepad.exe",
        "calc.exe",
        "calculatorapp.exe",
        "win32calc.exe",
        "mspaint.exe",
        "explorer.exe",
    ])
    def test_threat_model_allows_safe_allowlisted_processes(self, allowed_proc: str):
        """Tiến trình thuộc Safe Allowlist được cấp quyền."""
        ok, reason = DesktopSecurityGate.validate_process_scope(allowed_proc)
        assert ok is True
        assert reason == "AUTHORIZED"

    def test_threat_model_denies_unrecognized_process(self):
        """Tiến trình lạ ngoài Allowlist bị chặn (Fail-Closed)."""
        ok, reason = DesktopSecurityGate.validate_process_scope("suspicious_miner.exe")
        assert ok is False
        assert "SCOPE_DENIAL" in reason

    @pytest.mark.parametrize("denied_title", [
        "User Account Control",
        "Registry Editor",
        "Task Manager",
        "Windows Security - Enter Password",
        "Cửa sổ Quản trị viên: Command Prompt",
    ])
    def test_threat_model_denies_dangerous_window_titles(self, denied_title: str):
        """Tiêu đề cửa sổ chứa từ khóa UAC/Admin/Security phải bị chặn."""
        ok, reason = DesktopSecurityGate.validate_window_title(denied_title)
        assert ok is False
        assert "SECURITY_DENIAL" in reason

    def test_threat_model_denies_elevated_administrator_window(self):
        """Cửa sổ chạy quyền Elevated Administrator bị từ chối dứt khoát."""
        ok, reason = DesktopSecurityGate.validate_elevation(is_elevated=True)
        assert ok is False
        assert "SECURITY_DENIAL" in reason
        assert "Administrator" in reason

        ok_safe, reason_safe = DesktopSecurityGate.validate_elevation(is_elevated=False)
        assert ok_safe is True
        assert reason_safe == "AUTHORIZED"

    def test_threat_model_validates_window_bounding_box(self):
        """Kiểm tra ràng buộc tọa độ trong BoundingBox cửa sổ."""
        win_rect = (100, 100, 800, 600)  # (left, top, right, bottom)
        assert DesktopSecurityGate.validate_coordinates_within_window(400, 300, win_rect) is True
        assert DesktopSecurityGate.validate_coordinates_within_window(100, 100, win_rect) is True
        assert DesktopSecurityGate.validate_coordinates_within_window(800, 600, win_rect) is True

        # Trượt ra ngoài cửa sổ
        assert DesktopSecurityGate.validate_coordinates_within_window(50, 300, win_rect) is False
        assert DesktopSecurityGate.validate_coordinates_within_window(850, 300, win_rect) is False
        assert DesktopSecurityGate.validate_coordinates_within_window(400, 50, win_rect) is False
        assert DesktopSecurityGate.validate_coordinates_within_window(400, 650, win_rect) is False

    def test_desktop_approval_token_issuance_and_verification(self):
        """[M5-G4] Cấp phát và xác minh chữ ký One-Time Token cho Mutation."""
        hwnd = 12345
        proc = "notepad.exe"
        target = "Edit"
        act = "click"

        token = DesktopSecurityGate.issue_approval_token(hwnd, proc, target, act)
        assert token and "." in token

        # Xác minh hợp lệ lần 1
        ok, msg = DesktopSecurityGate.verify_approval_token(token, hwnd, proc, target, act)
        assert ok is True
        assert msg == "AUTHORIZED"

        # Tái sử dụng lần 2 bị chặn ngay (Chống Replay Attack)
        ok2, msg2 = DesktopSecurityGate.verify_approval_token(token, hwnd, proc, target, act)
        assert ok2 is False
        assert "TOKEN_REPLAY_ATTACK" in msg2


class TestM5SmoothMouseEngineAndMockAdapter:
    """[M5-G1 & M5-G2] Kiểm thử Động cơ Quỹ đạo Chuột Bezier & Mock Adapter."""

    def test_bezier_trajectory_generates_smooth_progression(self):
        """Kiểm tra đường cong Bezier tạo chuyển động mượt mà, không teleport giật cục."""
        start = (100, 100)
        end = (600, 450)
        trajectory = SmoothMouseEngine.calculate_trajectory(start, end, steps=25, wobble_px=0.0)

        assert len(trajectory) >= 15
        assert trajectory[-1] == end

        # Bước nhảy tối đa trong một bước không vượt quá 60px
        for i in range(len(trajectory) - 1):
            p1 = trajectory[i]
            p2 = trajectory[i + 1]
            step_dist = math.hypot(p2[0] - p1[0], p2[1] - p1[1])
            assert step_dist < 60.0

    def test_mock_mouse_adapter_records_trajectory_and_clicks(self):
        """Mock Adapter phải ghi nhận đầy đủ lịch sử di chuyển và click vật lý."""
        mock_mouse = MockDesktopMouseAdapter(initial_pos=(200, 200))
        SmoothMouseEngine.execute_smooth_click(
            mock_mouse,
            target_x=450,
            target_y=350,
            button="left",
            aim_pause_s=0.0,
            hold_time_s=0.0,
        )

        assert mock_mouse.get_position() == (450, 350)
        assert len(mock_mouse.trajectory_log) > 10
        assert len(mock_mouse.click_log) == 2  # down và up
        assert mock_mouse.click_log[0]["event"] == "down"
        assert mock_mouse.click_log[1]["event"] == "up"
        assert mock_mouse.click_log[0]["x"] == 450
        assert mock_mouse.click_log[0]["y"] == 350
        assert mock_mouse.mouse_state == "UP"

    def test_mock_mouse_adapter_failsafe_at_corner_zero(self):
        """Góc màn hình (0,0) phải kích hoạt Failsafe dừng khẩn cấp."""
        mock_mouse = MockDesktopMouseAdapter(initial_pos=(100, 100))
        assert mock_mouse.failsafe_triggered is False
        mock_mouse.move_to(0, 0)
        assert mock_mouse.failsafe_triggered is True


class TestM5DesktopOSActuatorExecution:
    """[M5-G3, M5-G4] Kiểm thử Tác tử DesktopOSActuator tích hợp & Evidence Contract."""

    def test_actuator_observe_returns_mock_controls(self):
        """Observe trả về danh sách controls của cửa sổ Notepad mock."""
        actuator = DesktopOSActuator(is_live_mode=False)
        obs = actuator.observe()

        assert obs["status"] == "success"
        assert obs["foreground"]["process_name"] == "notepad.exe"
        assert obs["element_count"] >= 5
        names = [el["name"] for el in obs["elements"]]
        assert "File" in names
        assert "Edit" in names

    def test_actuator_click_without_approval_token_rejected_m5_g4(self):
        """[M5-G4 ENFORCEMENT]: Click mutation mà thiếu approval_token phải bị từ chối ngay lập tức."""
        mock_mouse = MockDesktopMouseAdapter(initial_pos=(100, 100))
        mock_win = MockWindowInspector()
        actuator = DesktopOSActuator(mouse_adapter=mock_mouse, window_inspector=mock_win, is_live_mode=False)

        req = DesktopActRequest(action="click", target_name="Edit", approval_token=None)
        res = actuator.execute_action(req)

        assert res.status == "rejected"
        assert "APPROVAL_REQUIRED" in res.msg
        assert res.mutation_risk == "MUTATION"
        assert mock_mouse.get_position() == (100, 100)  # Chuột không được di chuyển

    def test_actuator_click_with_valid_token_success(self):
        """[M5-G4 ENFORCEMENT]: Click mutation có chữ ký token hợp lệ được thực thi thành công."""
        mock_mouse = MockDesktopMouseAdapter(initial_pos=(100, 100))
        mock_win = MockWindowInspector()
        actuator = DesktopOSActuator(mouse_adapter=mock_mouse, window_inspector=mock_win, is_live_mode=False)

        token = DesktopSecurityGate.issue_approval_token(
            hwnd=12345,
            process_name="notepad.exe",
            target_name="Edit",
            action="click",
            pid=5678,
        )
        req = DesktopActRequest(action="click", target_name="Edit", approval_token=token)
        res = actuator.execute_action(req)

        assert res.status == "success"
        assert res.action == "click"
        assert res.resolved_target == "Edit"
        assert res.mutation_risk == "MUTATION"
        assert res.final_coords == (175, 142)
        assert mock_mouse.get_position() == (175, 142)

        # Kiểm tra Evidence Contract hoàn chỉnh [OpenCode Lượt 130 Audit]
        ev = res.evidence
        assert ev["hwnd"] == 12345
        assert ev["process_name"] == "notepad.exe"
        assert ev["window_title"] == "Untitled - Notepad"
        assert ev["window_rect"] == (100, 100, 900, 700)
        assert ev["target_name"] == "Edit"
        assert ev["final_position"] == (175, 142)
        assert ev["trajectory_steps_count"] > 0
        assert ev["approval_token_hash"].startswith("sha256_")
        assert ev["mutation_risk"] == "MUTATION"

    def test_actuator_click_with_replay_token_rejected(self):
        """[M5-G4 REPLAY PREVENTION]: Tái sử dụng token cũ bị từ chối dứt khoát."""
        mock_mouse = MockDesktopMouseAdapter(initial_pos=(100, 100))
        mock_win = MockWindowInspector()
        actuator = DesktopOSActuator(mouse_adapter=mock_mouse, window_inspector=mock_win, is_live_mode=False)

        token = DesktopSecurityGate.issue_approval_token(
            hwnd=12345,
            process_name="notepad.exe",
            target_name="Edit",
            action="click",
            pid=5678,
        )
        req1 = DesktopActRequest(action="click", target_name="Edit", approval_token=token)
        res1 = actuator.execute_action(req1)
        assert res1.status == "success"

        # Lần 2 với cùng token
        req2 = DesktopActRequest(action="click", target_name="Edit", approval_token=token)
        res2 = actuator.execute_action(req2)
        assert res2.status == "rejected"
        assert "APPROVAL_REJECTED" in res2.msg

    def test_actuator_move_and_hover_read_only_do_not_require_token(self):
        """Hành động quan sát / di chuột READ_ONLY không yêu cầu token."""
        mock_mouse = MockDesktopMouseAdapter(initial_pos=(100, 100))
        mock_win = MockWindowInspector()
        actuator = DesktopOSActuator(mouse_adapter=mock_mouse, window_inspector=mock_win, is_live_mode=False)

        req = DesktopActRequest(action="move", target_name="File")
        res = actuator.execute_action(req)

        assert res.status == "success"
        assert res.mutation_risk == "READ_ONLY"
        assert res.final_coords == (130, 142)
        assert mock_mouse.get_position() == (130, 142)

    def test_actuator_denies_elevated_window(self):
        """Cửa sổ Elevated Administrator bị từ chối ngay lập tức."""
        mock_mouse = MockDesktopMouseAdapter(initial_pos=(100, 100))
        mock_win = MockWindowInspector()
        mock_win.mock_foreground["is_elevated"] = True
        actuator = DesktopOSActuator(mouse_adapter=mock_mouse, window_inspector=mock_win, is_live_mode=False)

        token = DesktopSecurityGate.issue_approval_token(12345, "notepad.exe", "Edit", "click", pid=5678)
        req = DesktopActRequest(action="click", target_name="Edit", approval_token=token)
        res = actuator.execute_action(req)

        assert res.status == "rejected"
        assert "SECURITY_REJECTED" in res.msg
        assert "Administrator" in res.msg

    def test_actuator_click_out_of_window_bounds_rejected(self):
        """Click tọa độ trượt ra ngoài phạm vi cửa sổ phải bị từ chối (Chống trượt)."""
        mock_mouse = MockDesktopMouseAdapter(initial_pos=(100, 100))
        mock_win = MockWindowInspector()  # win_rect = (100, 100, 900, 700)
        actuator = DesktopOSActuator(mouse_adapter=mock_mouse, window_inspector=mock_win, is_live_mode=False)

        token = DesktopSecurityGate.issue_approval_token(12345, "notepad.exe", "Custom Coordinate", "click")
        req = DesktopActRequest(action="click", target_coords=(50, 50), approval_token=token)
        res = actuator.execute_action(req)

        assert res.status == "rejected"
        assert "BOUNDARY_VIOLATION" in res.msg
        assert mock_mouse.get_position() == (100, 100)

    def test_actuator_denies_blacklisted_foreground_process(self):
        """Nếu cửa sổ Foreground bị tráo sang Task Manager, Actuator phải chặn tức thì."""
        mock_mouse = MockDesktopMouseAdapter(initial_pos=(100, 100))
        mock_win = MockWindowInspector()
        mock_win.mock_foreground = {
            "hwnd": 99999,
            "title": "Task Manager",
            "process_name": "taskmgr.exe",
            "rect": (100, 100, 800, 600),
            "is_elevated": True,
        }
        actuator = DesktopOSActuator(mouse_adapter=mock_mouse, window_inspector=mock_win, is_live_mode=False)

        req = DesktopActRequest(action="click", target_coords=(200, 200))
        res = actuator.execute_action(req)

        assert res.status == "rejected"
        assert "SECURITY_REJECTED" in res.msg


    def test_actuator_token_target_mismatch_rejected(self):
        """[M5-G4 TARGET INTEGRITY]: Token cấp cho nút 'File' không thể dùng để click nút 'Edit'."""
        mock_mouse = MockDesktopMouseAdapter(initial_pos=(100, 100))
        mock_win = MockWindowInspector()
        actuator = DesktopOSActuator(mouse_adapter=mock_mouse, window_inspector=mock_win, is_live_mode=False)

        # Cấp token cho nút 'File'
        token_for_file = DesktopSecurityGate.issue_approval_token(
            hwnd=12345,
            process_name="notepad.exe",
            target_name="File",
            action="click",
            pid=5678,
        )

        # Nhưng request lại yêu cầu click vào nút 'Edit'
        req = DesktopActRequest(action="click", target_name="Edit", approval_token=token_for_file)
        res = actuator.execute_action(req)

        assert res.status == "rejected"
        assert "APPROVAL_REJECTED" in res.msg
        assert "Target" in res.msg


    def test_actuator_token_pid_mismatch_rejected(self):
        """[M5-G4 PID INTEGRITY]: Token cấp cho PID khác hoặc thiếu PID bị từ chối dứt khoát."""
        mock_mouse = MockDesktopMouseAdapter(initial_pos=(100, 100))
        mock_win = MockWindowInspector()
        actuator = DesktopOSActuator(mouse_adapter=mock_mouse, window_inspector=mock_win, is_live_mode=False)

        # Cấp token cho PID 9999 thay vì 5678
        token_wrong_pid = DesktopSecurityGate.issue_approval_token(
            hwnd=12345,
            process_name="notepad.exe",
            target_name="Edit",
            action="click",
            pid=9999,
        )

        req = DesktopActRequest(action="click", target_name="Edit", approval_token=token_wrong_pid)
        res = actuator.execute_action(req)

        assert res.status == "rejected"
        assert "APPROVAL_REJECTED" in res.msg
        assert "PID" in res.msg

    def test_actuator_toctou_foreground_switch_rejected(self):
        """[M5-G4 TOCTOU GUARD]: Nếu cửa sổ Foreground bị tráo đổi ngay trước khi thao tác, lệnh bị hủy tức thì."""
        mock_mouse = MockDesktopMouseAdapter(initial_pos=(100, 100))

        class FlakyWindowInspector(MockWindowInspector):
            def __init__(self):
                super().__init__()
                self.call_count = 0

            def get_foreground_window_info(self):
                self.call_count += 1
                if self.call_count == 1:
                    # Lần 1: Trả về Notepad hợp lệ
                    return self.mock_foreground
                else:
                    # Lần 2 (TOCTOU revalidation): Tráo đổi sang HWND khác
                    return {
                        "hwnd": 88888,
                        "title": "Calculator",
                        "process_name": "calc.exe",
                        "rect": (200, 200, 600, 600),
                        "is_elevated": False,
                    }

        flaky_win = FlakyWindowInspector()
        actuator = DesktopOSActuator(mouse_adapter=mock_mouse, window_inspector=flaky_win, is_live_mode=False)

        token = DesktopSecurityGate.issue_approval_token(12345, "notepad.exe", "Edit", "click", pid=5678)
        req = DesktopActRequest(action="click", target_name="Edit", approval_token=token)
        res = actuator.execute_action(req)

        assert res.status == "rejected"
        assert "TOCTOU_IDENTITY_DRIFT" in res.msg

    def test_watchdog_timer_and_cancellation(self):
        """[M5-G5 WATCHDOG]: Kiểm tra Watchdog Timer phát hiện ngắt khẩn cấp hoặc timeout."""
        from services.ai_desktop import DesktopWatchdog
        watchdog = DesktopWatchdog(timeout_s=0.1)
        assert watchdog.is_cancelled() is False
        watchdog.start()
        import time
        time.sleep(0.15)
        assert watchdog.is_cancelled() is True
        watchdog.stop()


class TestM5ToolArbiterRouting:
    """[HEXAD-ROUTING] Kiểm thử Phân tuyến Tool Arbiter cho Miền M5 (DESKTOP_OS)."""

    def test_desktop_mouse_action_routes_to_desktop_os_domain(self):
        """Khẩu lệnh thao tác chuột trên desktop Windows phải định tuyến về DESKTOP_OS."""
        prompt = "Thao tác chuột desktop di chuyển trực quan và click vào menu File trong Notepad"
        verdict = tool_arbiter.arbitrate(prompt)

        assert verdict.primary_domain == ToolDomain.DESKTOP_OS
        assert verdict.is_desktop_os() is True
        assert verdict.is_visual_required is True
        assert "desktop_act" in verdict.mandatory_tools
        assert "desktop_observe" in verdict.mandatory_tools
        assert "BROWSER_CONTROL" in verdict.forbidden_tools
        assert verdict.primary_target == "notepad.exe"

    def test_toan_man_hinh_windows_calculator_routes_to_desktop_os(self):
        """Khẩu lệnh điều khiển ứng dụng máy tính toàn màn hình Windows về DESKTOP_OS."""
        prompt = "Điều khiển con trỏ chuột windows bấm các số trên ứng dụng calculator toàn màn hình"
        verdict = tool_arbiter.arbitrate(prompt)

        assert verdict.primary_domain == ToolDomain.DESKTOP_OS
        assert verdict.is_desktop_os() is True
        assert "desktop_act" in verdict.mandatory_tools

    def test_web_and_webfig_prompts_still_route_to_browser_m2(self):
        """Khẩu lệnh web/webfig vẫn định tuyến chính xác về M2 BROWSER, không bị lẫn lộn."""
        prompt_web = "Thao tác trên giao diện web click vào nút Đăng nhập và chụp ảnh màn hình"
        verdict_web = tool_arbiter.arbitrate(prompt_web)
        assert verdict_web.primary_domain == ToolDomain.BROWSER

        prompt_webfig = "Cấu hình tường lửa MikroTik qua giao diện WebFig"
        verdict_webfig = tool_arbiter.arbitrate(prompt_webfig)
        assert verdict_webfig.primary_domain == ToolDomain.BROWSER
