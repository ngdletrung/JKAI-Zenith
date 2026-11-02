# -*- coding: utf-8 -*-
"""
Test Suite for Gateway-Owned Verifier Synthesis & Token Expectation Binding.
Đáp ứng đầy đủ các tiêu chuẩn kiểm định Zero-Trust của JKAI & OpenCode Lượt 163:
1. Caller KHÔNG truyền callback tùy ý; Gateway tự động synthesize verifier từ token payload.
2. Gateway synthesis target_mutation phát hiện stale state và Fail-Closed.
3. Token Expectation Binding: Chặn đứng khi có sự sai lệch expectation giữa Token và Request.
4. Chặn đứng các expectation lạ không nằm trong danh mục hỗ trợ của Gateway.
"""

import pytest
from services.ai_desktop import (
    DesktopActRequest,
    DesktopActResponse,
    DesktopOSActuator,
    DesktopSecurityGate,
    GatewayObservationVerifier,
    MockDesktopMouseAdapter,
    MockWindowInspector,
    WindowMessageAdapter,
)


class TestM5GatewaySynthesisSuite:

    @pytest.fixture(autouse=True)
    def setup_security(self, monkeypatch):
        DesktopSecurityGate.reset_consumed_tokens()
        self.inspector = MockWindowInspector()
        self.hwnd = 12345
        self.pid = 5678
        self.target = "Edit"

        # Mock Win32 low-level APIs để WindowMessageAdapter chạy mã nguồn nguyên bản
        monkeypatch.setattr("win32gui.IsWindow", lambda hwnd: True)
        monkeypatch.setattr("win32process.GetWindowThreadProcessId", lambda hwnd: (1, self.pid))
        monkeypatch.setattr("win32gui.ScreenToClient", lambda hwnd, pt: (pt[0] - 100, pt[1] - 100))
        monkeypatch.setattr("win32gui.SendMessage", lambda hwnd, msg, wparam, lparam: 0)

    def test_01_gateway_synthesizes_control_state_verifier_from_token(self):
        """[GATEWAY SYNTHESIS 1]: Caller KHÔNG truyền callback, Gateway tự giải mã token và tổng hợp Control State Verifier."""
        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        # Cấp token ràng buộc cứng kỳ vọng 'control_state'
        token = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="background_message",
            expected_postcondition="control_state",
        )

        # Request KHÔNG truyền postcondition_verifier (để None!)
        req = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token,
            execution_mode="background_message",
            expected_postcondition="control_state",
            postcondition_verifier=None,
        )

        res = actuator.execute_action(req)
        assert res.status == "success"
        assert res.evidence["post_action_state"]["delivery_status"] == "delivered_verified"
        assert res.evidence["post_action_state"]["arrived_at_target"] is True

        # Kiểm chứng Verifier Provenance do Central Gateway sở hữu và tổng hợp
        prov = res.evidence["verifier_provenance"]
        assert prov["synthesized_by"] == "CENTRAL_GATEWAY"
        assert prov["expected_postcondition"] == "control_state"
        assert "GATEWAY_VERIFIER_CONTROL_STATE" in prov["verifier_id"]

    def test_02_gateway_synthesizes_target_mutation_verifier_fails_closed_on_stale(self):
        """[GATEWAY SYNTHESIS 2]: Gateway tự tổng hợp Target-Specific Mutation Verifier, phát hiện node không đổi -> Fail Closed."""
        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        # Cấp token ràng buộc cứng kỳ vọng 'target_mutation'
        token = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="background_message",
            expected_postcondition="target_mutation",
        )

        # Request KHÔNG truyền callback, chỉ truyền expectation
        req = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token,
            execution_mode="background_message",
            expected_postcondition="target_mutation",
            postcondition_verifier=None,
        )

        # Gateway tự tạo target_mutation_verifier. Mock tree không đổi -> Verifier trả False -> Fail Closed!
        res = actuator.execute_action(req)
        assert res.status == "failed"
        assert "FAIL_CLOSED_UNVERIFIED" in res.msg
        assert res.evidence["receipt"]["delivery_status"] == "delivered_unverified"

    def test_03_token_expectation_mismatch_rejected(self):
        """[TOKEN EXPECTATION BINDING]: Token cấp với 'control_state' nhưng Request đòi 'target_mutation' -> Rejected."""
        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        token = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="background_message",
            expected_postcondition="control_state",
        )

        # Gửi request với expectation tráo đổi
        req = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token,
            execution_mode="background_message",
            expected_postcondition="target_mutation",
        )

        res = actuator.execute_action(req)
        assert res.status == "rejected"
        assert "APPROVAL_REJECTED" in res.msg
        assert "TOKEN_BINDING_MISMATCH" in res.msg

    def test_04_unknown_expectation_rejected_by_gateway(self):
        """[EXPECTATION WHITELIST]: Expectation không nằm trong danh mục Gateway hỗ trợ -> Rejected tức thì."""
        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        token = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="background_message",
            expected_postcondition="malicious_custom_verifier",
        )

        req = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token,
            execution_mode="background_message",
            expected_postcondition="malicious_custom_verifier",
        )

        res = actuator.execute_action(req)
        assert res.status == "rejected"
        assert "POLICY_VIOLATION_UNKNOWN_EXPECTATION" in res.msg
    def test_05_caller_callback_injection_rejected_before_dispatch(self, monkeypatch):
        """[CALLBACK INJECTION DENIAL]: Caller cố tình truyền postcondition_verifier tùy ý -> Bị Gateway REJECT ngay trước SendMessage."""
        sendmessage_called = False

        def mock_sendmessage(*args, **kwargs):
            nonlocal sendmessage_called
            sendmessage_called = True
            return 0

        monkeypatch.setattr("win32gui.SendMessage", mock_sendmessage)

        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        token = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="background_message",
            expected_postcondition="control_state",
        )

        # Caller cố tình tiêm một callback lambda tùy ý để bypass
        req_injected = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token,
            execution_mode="background_message",
            expected_postcondition="control_state",
            postcondition_verifier=lambda h: True,  # Arbitrary bypass attempt!
        )

        res = actuator.execute_action(req_injected)
        assert res.status == "rejected"
        assert "POLICY_VIOLATION_CALLER_CALLBACK_FORBIDDEN" in res.msg
        assert not sendmessage_called, "SendMessage tuyệt đối không được gọi khi có hành vi tiêm callback tùy ý!"
