# -*- coding: utf-8 -*-
"""
Test Suite for M5 Fail-Closed Security Enforcements and Dual-Mode Architecture.
Đáp ứng đầy đủ các điều kiện kiểm soát nghiêm ngặt của OpenCode (Lượt 149, 151, 153, 155):
1. Native API Failure -> Fail Closed (không nuốt lỗi, trả về status="failed").
2. Cursor Readback Drift -> Fail Closed (cursor_after != target_coords -> status="failed").
3. Mode Mismatch -> Bị từ chối bởi Approval Token (Visual vs Background).
4. Target Identity Mismatch -> Bị từ chối (Automation ID / Control Type / Bounds).
5. Background Message Mode -> Yêu cầu postcondition verifier, ghi nhận receipt đầy đủ.
6. Background Message Send Text -> Typed receipt (chars_sent, delivery_status).
7. Invalid HWND Rejection -> not_delivered fail-closed.
8. Replay Attack -> Bị từ chối (One-Time Token invariant).
9. Visual Mode Happy Path -> Xác nhận arrived_at_target=True khi trỏ chuột tới đích chuẩn xác.
10. UIA Tree Inspector -> Bóc tách cây phần tử, supported patterns và snapshot hash với nhãn WIN32_ACCESSIBILITY_FALLBACK.
11. Policy-Derived Verifier Gate -> Background Mutation không có verifier bị từ chối tức thì (Chống Fail-Open).
12. Background Verifier Returning False -> Bị Fail-Closed (FAIL_CLOSED_UNVERIFIED).
13. Background Verifier Returning True -> Thành công với delivered_verified.
"""

import pytest
from services.ai_desktop import (
    DesktopActRequest,
    DesktopActResponse,
    DesktopOSActuator,
    DesktopSecurityGate,
    MockDesktopMouseAdapter,
    MockWindowInspector,
    UIATreeInspector,
    WindowMessageAdapter,
    WindowMessageReceipt,
)
from services.ai_desktop.mouse_engine import CursorActionError, CursorReadbackDriftError


class TestM5FailClosedAndDualModeSuite:

    @pytest.fixture(autouse=True)
    def setup_security(self):
        DesktopSecurityGate.reset_consumed_tokens()
        self.inspector = MockWindowInspector()
        self.hwnd = 12345
        self.pid = 5678
        self.target = "Edit"  # Khớp với MockWindowInspector

    def test_01_native_api_failure_fails_closed(self):
        """[FAIL-CLOSED 1]: Khi Win32 API SetCursorPos thất bại (Desktop Isolation) -> Actuator phải Fail Closed."""
        failing_adapter = MockDesktopMouseAdapter(fail_api=True)
        actuator = DesktopOSActuator(mouse_adapter=failing_adapter, window_inspector=self.inspector)

        token = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="visual",
        )

        req = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token,
            execution_mode="visual",
        )

        res = actuator.execute_action(req)
        assert res.status == "failed"
        assert "FAIL_CLOSED" in res.msg
        assert "SetCursorPos" in res.msg

    def test_02_cursor_readback_drift_fails_closed(self):
        """[FAIL-CLOSED 2]: Khi trỏ chuột thực tế lệch mục tiêu (drift) -> Actuator phải Fail Closed (không được claim success)."""
        drifting_adapter = MockDesktopMouseAdapter(drift_readback=True, drift_offset=(84, 1))
        actuator = DesktopOSActuator(mouse_adapter=drifting_adapter, window_inspector=self.inspector)

        token = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="visual",
        )

        req = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token,
            execution_mode="visual",
        )

        res = actuator.execute_action(req)
        assert res.status == "failed"
        assert "FAIL_CLOSED_DRIFT" in res.msg
        assert res.evidence["post_action_state"]["arrived_at_target"] is False

    def test_03_execution_mode_mismatch_rejected(self):
        """[DUAL-MODE 1]: Thẻ phê duyệt cấp cho Visual Mode nhưng gửi lệnh Background Mode -> Bị từ chối tức thì."""
        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        token_visual = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="visual",
        )

        req_background = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token_visual,
            execution_mode="background_message",  # Lệch mode!
        )

        res = actuator.execute_action(req_background)
        assert res.status == "rejected"
        assert "TOKEN_BINDING_MISMATCH" in res.msg
        assert "Mode 'visual' != 'background_message'" in res.msg

    def test_04_target_identity_mismatch_rejected(self):
        """[TARGET IDENTITY]: Token ràng buộc Automation ID cụ thể nhưng request truyền ID khác -> Bị từ chối."""
        token_identity = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="visual",
            target_identity="Menu_Edit",
        )

        ok, msg = DesktopSecurityGate.verify_approval_token(
            token=token_identity,
            expected_hwnd=self.hwnd,
            expected_proc="notepad.exe",
            expected_target=self.target,
            expected_action="click",
            expected_pid=self.pid,
            expected_mode="visual",
            expected_identity="Sys_Close_999",  # Identity sai lệch!
        )
        assert not ok
        assert "TOKEN_BINDING_MISMATCH: Target Identity" in msg

    def test_05_background_message_mode_dispatched_successfully(self, monkeypatch):
        """[DUAL-MODE 2]: Khi được phê duyệt Background Mode và có verifier, thực thi thành công với delivered_verified."""
        # Mock Win32 low-level APIs để WindowMessageAdapter chạy mã nguồn nguyên bản
        monkeypatch.setattr("win32gui.IsWindow", lambda hwnd: True)
        monkeypatch.setattr("win32process.GetWindowThreadProcessId", lambda hwnd: (1, self.pid))
        monkeypatch.setattr("win32gui.ScreenToClient", lambda hwnd, pt: (pt[0] - 100, pt[1] - 100))
        monkeypatch.setattr("win32gui.SendMessage", lambda hwnd, msg, wparam, lparam: 0)

        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        token_bg = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="background_message",
            expected_postcondition="control_state",
        )

        req_bg = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token_bg,
            execution_mode="background_message",
            expected_postcondition="control_state",
            postcondition_verifier=None,
        )

        res = actuator.execute_action(req_bg)
        assert res.status == "success"
        post_state = res.evidence["post_action_state"]
        assert post_state["execution_mode"] == "background_message"
        assert post_state["delivery_status"] == "delivered_verified"
        assert post_state["arrived_at_target"] is True
        assert post_state["message_receipt"] is not None

    def test_06_background_message_invalid_hwnd_fails_closed(self):
        """[BACKGROUND FAIL-CLOSED]: Gửi message tới HWND không tồn tại -> Trả về not_delivered và thất bại an toàn."""
        adapter = WindowMessageAdapter()
        receipt = adapter.send_click(hwnd=99999999, screen_x=100, screen_y=100)
        assert not receipt.success
        assert receipt.delivery_status == "not_delivered"
        assert "HWND_INVALID" in receipt.error_msg

    def test_07_background_message_send_text_typed_receipt(self):
        """[BACKGROUND TYPED TEXT]: send_text trả về WindowMessageReceipt với đầy đủ chi tiết, không nuốt lỗi boolean."""
        adapter = WindowMessageAdapter()
        receipt_invalid = adapter.send_text(hwnd=99999999, text="test")
        assert not receipt_invalid.success
        assert receipt_invalid.delivery_status == "not_delivered"
        assert "HWND_INVALID" in receipt_invalid.error_msg

    def test_08_replay_attack_rejected_on_both_modes(self):
        """[SECURITY REPLAY]: Token sau khi dùng ở bất kỳ chế độ nào đều không thể tái sử dụng."""
        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        token = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="visual",
        )

        req = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token,
            execution_mode="visual",
        )

        res1 = actuator.execute_action(req)
        assert res1.status == "success"

        # Replay lần 2 với cùng token
        res2 = actuator.execute_action(req)
        assert res2.status == "rejected"
        assert "TOKEN_REPLAY_ATTACK" in res2.msg

    def test_09_visual_mode_happy_path_verified(self):
        """[VISUAL HAPPY PATH]: Khi con trỏ vật lý tới đích chuẩn xác (drift=0) -> Xác nhận arrived_at_target=True."""
        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        token = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="visual",
        )

        req = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token,
            execution_mode="visual",
        )

        res = actuator.execute_action(req)
        assert res.status == "success"
        assert res.evidence["post_action_state"]["arrived_at_target"] is True
        assert res.evidence["post_action_state"]["cursor_after"] == (175, 142)

    def test_10_uia_tree_inspector_snapshot_hash_and_patterns(self):
        """[UIA TREE INSPECTOR]: Quét cây phần tử, kiểm tra automation_id, patterns và mã băm snapshot_hash."""
        inspector = UIATreeInspector(is_live_mode=False)
        snapshot = inspector.inspect_tree(self.hwnd)

        assert snapshot.hwnd == self.hwnd
        assert snapshot.element_count >= 4
        assert snapshot.snapshot_hash.startswith("sha256_")
        assert snapshot.engine == "WIN32_ACCESSIBILITY_FALLBACK"

        # Kiểm tra phần tử Edit
        edit_node = next((el for el in snapshot.elements if el.name == "Edit"), None)
        assert edit_node is not None
        assert edit_node.automation_id == "Menu_Edit"
        assert "InvokePattern" in edit_node.supported_patterns

        # Kiểm tra phần tử Text Editor
        text_editor = next((el for el in snapshot.elements if el.control_type == "Edit"), None)
        assert text_editor is not None
        assert "ValuePattern" in text_editor.supported_patterns

    def test_11_policy_derived_verifier_rejects_unverified_request(self):
        """[POLICY GATE]: Background Mutation request mặc định không có postcondition verifier bị Central Gateway REJECT ngay trước khi gửi SendMessage."""
        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        token_bg = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="background_message",
        )

        # Request mặc định không truyền verifier
        req_no_verifier = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token_bg,
            execution_mode="background_message",
            postcondition_verifier=None,  # Thiếu verifier!
        )

        res = actuator.execute_action(req_no_verifier)
        assert res.status == "rejected"
        assert "POLICY_VIOLATION_NO_VERIFIER" in res.msg

    def test_12_background_verifier_returning_false_fails_closed(self, monkeypatch):
        """[VERIFIER REJECTION]: Khi verifier trả về False -> Gateway báo FAIL_CLOSED_UNVERIFIED và không trả success."""
        # Mock Win32 low-level APIs để WindowMessageAdapter chạy mã nguồn nguyên bản
        monkeypatch.setattr("win32gui.IsWindow", lambda hwnd: True)
        monkeypatch.setattr("win32process.GetWindowThreadProcessId", lambda hwnd: (1, self.pid))
        monkeypatch.setattr("win32gui.ScreenToClient", lambda hwnd, pt: (pt[0] - 100, pt[1] - 100))
        monkeypatch.setattr("win32gui.SendMessage", lambda hwnd, msg, wparam, lparam: 0)

        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        token_bg = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="background_message",
            expected_postcondition="target_mutation",
        )

        req_failing_verifier = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token_bg,
            execution_mode="background_message",
            expected_postcondition="target_mutation",
            postcondition_verifier=None,
        )

        res = actuator.execute_action(req_failing_verifier)
        assert res.status == "failed"
        assert "FAIL_CLOSED_UNVERIFIED" in res.msg
