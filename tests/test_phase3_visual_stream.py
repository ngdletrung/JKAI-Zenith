# -*- coding: utf-8 -*-
"""
tests/test_phase3_visual_stream.py
[M5 Phase 3: Visual Capture & WebSocket Stream Test Suite]:
Thực hiện đầy đủ 17 bài kiểm thử bảo mật & read-only invariants theo Turn 333 của OpenCode:
Visual Tests:
  1. VISUAL_CAPTURE_SIZE_CAP
  2. VISUAL_INVALID_JPEG_REJECTED
  3. VISUAL_BASE64_OVERSIZE_REJECTED
  4. VISUAL_SOM_HASH_BINDING
  5. VISUAL_STALE_EXPIRED_REJECTED
  6. VISUAL_READ_ONLY_INVARIANT
WebSocket Stream Tests:
  7. WS_MUTATION_MESSAGE_REJECTED
  8. WS_AUTH_REQUIRED
  9. WS_ORIGIN_REJECTED
  10. WS_UNKNOWN_SESSION_REJECTED
  11. WS_UNAUTHORIZED_TARGET_REJECTED
  12. WS_PAYLOAD_TOO_LARGE_REJECTED
  13. WS_RATE_LIMIT_ENFORCED
  14. WS_BACKPRESSURE
  15. WS_DISCONNECT_CLEANUP
  16. WS_100_CONNECT_CYCLE_HANDLE_LEAK
  17. WS_READ_ONLY_INVARIANT
  18. R5_WS_TOKEN_NOT_CONFIGURED
  19. R5_WS_WRONG_TOKEN
  20. R5_WS_LEGACY_DEFAULT_TOKEN
  21. R5_WS_ORIGIN_MANDATORY
  22. R5_WS_NESTED_MUTATION
  23. R5_WS_HWND_TYPE
  24. R6_WS_POLICY_SSOT
  25. R5_WS_NO_VALUE_BROADCAST
"""

import time
import os
import pytest
from unittest.mock import patch, MagicMock
from services.ai_desktop.visual_engine import VisualWindowCaptureEngine, WindowVisualSnapshot
from services.ai_desktop.host_bridge_stream_guard import (
    HostBridgeStreamGuard,
    WebSocketSecurityException,
    validate_ws_token,
    validate_ws_origin,
    validate_target_process_allowlist,
)

WS_TEST_TOKEN = "a_valid_custom_token_123456"


class TestPhase3VisualCaptureSuite:

    def test_visual_capture_size_cap(self):
        """VISUAL_CAPTURE_SIZE_CAP: Độ phân giải và kích thước ảnh chụp được kiểm soát trần 1280x720."""
        engine = VisualWindowCaptureEngine(is_live_mode=False)
        snap = engine.capture_window(1234)
        assert snap.width <= 1280
        assert snap.height <= 720
        assert len(snap.image_base64) <= engine.MAX_BASE64_BYTES

    def test_visual_invalid_jpeg_rejected(self):
        """VISUAL_INVALID_JPEG_REJECTED: Chuỗi payload không phải JPEG chuẩn (thiếu FF D8 FF) bị từ chối."""
        engine = VisualWindowCaptureEngine(is_live_mode=False)
        assert engine.validate_jpeg_payload("not_valid_base64") is False
        import base64
        fake_png = base64.b64encode(b"\x89PNG\r\n\x1a\nfake").decode("utf-8")
        assert engine.validate_jpeg_payload(fake_png) is False

    def test_visual_base64_oversize_rejected(self):
        """VISUAL_BASE64_OVERSIZE_REJECTED: Payload Base64 vượt quá trần 2MB bị từ chối fail-closed."""
        engine = VisualWindowCaptureEngine(is_live_mode=False)
        oversized = "A" * (engine.MAX_BASE64_BYTES + 10)
        assert engine.validate_jpeg_payload(oversized) is False

    def test_visual_som_hash_binding(self):
        """VISUAL_SOM_HASH_BINDING: Ảnh chụp và overlay Set-of-Marks ràng buộc chặt chẽ với snapshot_hash."""
        engine = VisualWindowCaptureEngine(is_live_mode=False)
        expected_hash = "sha256_abcdef1234567890abcdef1234567890abcdef1234567890abcdef1234567890"
        snap = engine.capture_window(1234, snapshot_hash=expected_hash)
        assert snap.snapshot_hash == expected_hash

    def test_visual_stale_expired_rejected(self):
        """VISUAL_STALE_EXPIRED_REJECTED: Sau TTL 0.5s, visual snapshot được đánh dấu hết hạn (expired)."""
        engine = VisualWindowCaptureEngine(is_live_mode=False)
        snap = engine.capture_window(1234)
        assert snap.is_expired is False

        with patch("time.time", return_value=time.time() + 0.6):
            assert snap.is_expired is True

    def test_visual_read_only_invariant(self):
        """VISUAL_READ_ONLY_INVARIANT: Visual snapshot là perception evidence, tuyệt đối không phải dispatch proof."""
        engine = VisualWindowCaptureEngine(is_live_mode=False)
        snap = engine.capture_window(1234)
        assert snap.is_dispatch_proof is False


class TestPhase3WebSocketStreamSuite:

    @pytest.fixture
    def guard(self):
        return HostBridgeStreamGuard(
            max_connections=5,
            max_payload_size=1024 * 1024,
            max_rate_per_sec=10,
            stream_token=WS_TEST_TOKEN,
        )

    def test_ws_mutation_message_rejected(self, guard):
        """WS_MUTATION_MESSAGE_REJECTED: Mọi message có chứa từ khoá mutation đều bị từ chối dứt điểm."""
        conn_id = "test_conn_01"
        guard.register_connection(conn_id, token=WS_TEST_TOKEN, origin="http://localhost:3000", session_id="ses_hud")

        mutation_payloads = [
            '{"type": "click", "x": 100, "y": 200}',
            '{"type": "type_text", "text": "hello"}',
            '{"action": "dispatch", "cmd": "run"}',
            '{"type": "mutation", "target": "notepad"}',
            '{"type": "approve", "lease_id": "123"}',
            '{"type": "focus", "hwnd": 1234}'
        ]

        for payload in mutation_payloads:
            with pytest.raises(WebSocketSecurityException) as excinfo:
                guard.filter_incoming_message(conn_id, payload)
            assert excinfo.value.code == "WS_MUTATION_MESSAGE_REJECTED"

    def test_ws_auth_required(self, guard):
        """WS_AUTH_REQUIRED: Thiếu token hoặc token không hợp lệ bị từ chối kết nối."""
        with pytest.raises(WebSocketSecurityException) as excinfo:
            guard.register_connection("conn_bad", token=None, origin="http://localhost:3000", session_id="ses_1234")
        assert excinfo.value.code == "WS_AUTH_REQUIRED"

        with pytest.raises(WebSocketSecurityException) as excinfo:
            guard.register_connection("conn_short", token="short", origin="http://localhost:3000", session_id="ses_1234")
        assert excinfo.value.code == "WS_AUTH_REQUIRED"

    def test_ws_origin_rejected(self, guard):
        """WS_ORIGIN_REJECTED: Origin từ domain lạ (ngoài localhost/127.0.0.1) bị từ chối chống CSWSH."""
        with pytest.raises(WebSocketSecurityException) as excinfo:
            guard.register_connection("conn_evil", token=WS_TEST_TOKEN, origin="http://evil-attacker.com", session_id="ses_1234")
        assert excinfo.value.code == "WS_ORIGIN_REJECTED"

    def test_ws_unknown_session_rejected(self, guard):
        """WS_UNKNOWN_SESSION_REJECTED: Kết nối thiếu session_id hợp lệ bị từ chối."""
        with pytest.raises(WebSocketSecurityException) as excinfo:
            guard.register_connection("conn_no_ses", token=WS_TEST_TOKEN, origin="http://localhost:3000", session_id="")
        assert excinfo.value.code == "WS_UNKNOWN_SESSION_REJECTED"

    def test_ws_unauthorized_target_rejected(self, guard):
        """WS_UNAUTHORIZED_TARGET_REJECTED: Đăng ký quan sát ứng dụng ngoài allowlist Phase 3 bị từ chối."""
        conn_id = "test_conn_02"
        guard.register_connection(conn_id, token=WS_TEST_TOKEN, origin="http://localhost:3000", session_id="ses_hud")

        with pytest.raises(WebSocketSecurityException) as excinfo:
            guard.filter_incoming_message(conn_id, '{"type": "subscribe", "process_name": "cmd.exe"}')
        assert excinfo.value.code == "WS_UNAUTHORIZED_TARGET_REJECTED"

    def test_ws_payload_too_large_rejected(self, guard):
        """WS_PAYLOAD_TOO_LARGE_REJECTED: Payload vượt quá trần dung lượng bị từ chối."""
        conn_id = "test_conn_03"
        guard.register_connection(conn_id, token=WS_TEST_TOKEN, origin="http://localhost:3000", session_id="ses_hud")

        oversized_msg = '{"type": "ping", "data": "' + ("X" * (1024 * 1024 + 100)) + '"}'
        with pytest.raises(WebSocketSecurityException) as excinfo:
            guard.filter_incoming_message(conn_id, oversized_msg)
        assert excinfo.value.code == "WS_PAYLOAD_TOO_LARGE_REJECTED"

    def test_ws_rate_limit_enforced(self, guard):
        """WS_RATE_LIMIT_ENFORCED: Gửi quá 10 messages/giây bị rate limit chặn đứng."""
        conn_id = "test_conn_04"
        guard.register_connection(conn_id, token=WS_TEST_TOKEN, origin="http://localhost:3000", session_id="ses_hud")

        # Gửi 10 messages hợp lệ liên tiếp
        for i in range(10):
            res = guard.filter_incoming_message(conn_id, '{"type": "ping"}')
            assert res["status"] == "ALLOWED"

        # Message thứ 11 trong cùng 1 giây phải bị chặn
        with pytest.raises(WebSocketSecurityException) as excinfo:
            guard.filter_incoming_message(conn_id, '{"type": "ping"}')
        assert excinfo.value.code == "WS_RATE_LIMIT_ENFORCED"

    def test_ws_backpressure(self, guard):
        """WS_BACKPRESSURE: Kiểm soát tải kết nối, từ chối khi vượt ngưỡng MAX_CONNECTIONS."""
        for i in range(5):
            guard.register_connection(f"client_{i}", token=WS_TEST_TOKEN, origin="http://localhost:3000", session_id=f"ses_{i}")

        # Kết nối thứ 6 vượt ngưỡng max_connections = 5
        with pytest.raises(WebSocketSecurityException) as excinfo:
            guard.register_connection("client_overflow", token=WS_TEST_TOKEN, origin="http://localhost:3000", session_id="ses_overflow")
        assert excinfo.value.code == "MAX_CONNECTIONS_EXCEEDED"

    def test_ws_disconnect_cleanup(self, guard):
        """WS_DISCONNECT_CLEANUP: Khi client ngắt kết nối, toàn bộ session info và rate buffer được giải phóng."""
        conn_id = "test_conn_cleanup"
        guard.register_connection(conn_id, token=WS_TEST_TOKEN, origin="http://localhost:3000", session_id="ses_hud")
        assert conn_id in guard.active_sessions

        guard.unregister_connection(conn_id)
        assert conn_id not in guard.active_sessions
        assert conn_id not in guard.client_message_timestamps

    def test_ws_100_connect_cycle_handle_leak(self, guard):
        """WS_100_CONNECT_CYCLE_HANDLE_LEAK: Qua 100 chu kỳ connect/disconnect, không rò rỉ bộ nhớ session."""
        for i in range(100):
            cid = f"conn_cycle_{i}"
            guard.register_connection(cid, token=WS_TEST_TOKEN, origin="http://localhost:3000", session_id=f"ses_{i}")
            guard.filter_incoming_message(cid, '{"type": "ping"}')
            guard.unregister_connection(cid)

        assert len(guard.active_sessions) == 0
        assert len(guard.client_message_timestamps) == 0

    def test_ws_read_only_invariant(self, guard):
        """WS_READ_ONLY_INVARIANT: Các message hợp lệ duy nhất là subscribe, unsubscribe, ping, frame, error, heartbeat."""
        conn_id = "test_conn_ro"
        guard.register_connection(conn_id, token=WS_TEST_TOKEN, origin="http://localhost:3000", session_id="ses_hud")

        valid_types = ["subscribe", "unsubscribe", "ping", "heartbeat"]
        for vt in valid_types:
            res = guard.filter_incoming_message(conn_id, f'{{"type": "{vt}"}}')
            assert res["status"] == "ALLOWED"
            assert res["type"] == vt

    # ── R5 hardening: token thật, origin bắt buộc, chặn mutation lồng nhau ──

    def test_ws_token_not_configured_fails_closed(self, monkeypatch):
        """R5_WS_TOKEN_NOT_CONFIGURED: Không cấu hình SATELLITE_WS_TOKEN => mọi kết nối bị từ chối."""
        monkeypatch.delenv("SATELLITE_WS_TOKEN", raising=False)
        guard = HostBridgeStreamGuard(stream_token="")
        with pytest.raises(WebSocketSecurityException) as excinfo:
            guard.register_connection("conn_nocfg", token=WS_TEST_TOKEN, origin="http://localhost:3000", session_id="ses_1234")
        assert excinfo.value.code == "WS_TOKEN_NOT_CONFIGURED"

    def test_ws_wrong_token_rejected_even_if_well_formed(self, guard):
        """R5_WS_WRONG_TOKEN: Token đúng định dạng nhưng không khớp token server bị từ chối."""
        with pytest.raises(WebSocketSecurityException) as excinfo:
            guard.register_connection(
                "conn_wrong", token="another_valid_token_1234567890", origin="http://localhost:3000", session_id="ses_1234"
            )
        assert excinfo.value.code == "WS_AUTH_REQUIRED"

    def test_ws_default_legacy_token_rejected(self, guard):
        """R5_WS_LEGACY_DEFAULT_TOKEN: Token mặc định công khai cũ không còn hiệu lực."""
        with pytest.raises(WebSocketSecurityException) as excinfo:
            guard.register_connection(
                "conn_legacy",
                token="jkai_ws_read_only_stream_token_v3",
                origin="http://localhost:3000",
                session_id="ses_1234",
            )
        assert excinfo.value.code == "WS_AUTH_REQUIRED"

    def test_ws_missing_origin_rejected(self, guard):
        """R5_WS_ORIGIN_MANDATORY: Thiếu Origin bị từ chối (không còn ngoại lệ native/test)."""
        with pytest.raises(WebSocketSecurityException) as excinfo:
            guard.register_connection("conn_no_origin", token=WS_TEST_TOKEN, origin=None, session_id="ses_1234")
        assert excinfo.value.code == "WS_ORIGIN_REJECTED"

        with pytest.raises(WebSocketSecurityException) as excinfo:
            guard.register_connection("conn_file_origin", token=WS_TEST_TOKEN, origin="file:///tmp/x", session_id="ses_1234")
        assert excinfo.value.code == "WS_ORIGIN_REJECTED"

    def test_ws_nested_mutation_rejected(self, guard):
        """R5_WS_NESTED_MUTATION: Mutation field/type lồng sâu trong payload bị chặn."""
        conn_id = "test_conn_nested"
        guard.register_connection(conn_id, token=WS_TEST_TOKEN, origin="http://localhost:3000", session_id="ses_hud")

        nested_payloads = [
            '{"type": "subscribe", "data": {"action": "click"}}',
            '{"type": "subscribe", "data": {"command": "run"}}',
            '{"type": "ping", "data": {"type": "click"}}',
            '{"type": "subscribe", "data": {"items": [{"dispatch": "x"}]}}',
            '{"type": "ping", "data": {"deep": {"deeper": {"key": "ctrl"}}}}',
        ]
        for payload in nested_payloads:
            with pytest.raises(WebSocketSecurityException) as excinfo:
                guard.filter_incoming_message(conn_id, payload)
            assert excinfo.value.code == "WS_MUTATION_MESSAGE_REJECTED"

    def test_ws_subscribe_hwnd_type_validated(self, guard):
        """R5_WS_HWND_TYPE: hwnd không phải số nguyên dương bị từ chối thay vì ném ValueError."""
        conn_id = "test_conn_hwnd"
        guard.register_connection(conn_id, token=WS_TEST_TOKEN, origin="http://localhost:3000", session_id="ses_hud")

        for payload in ('{"type": "subscribe", "hwnd": "1234"}', '{"type": "subscribe", "hwnd": -5}'):
            with pytest.raises(WebSocketSecurityException) as excinfo:
                guard.filter_incoming_message(conn_id, payload)
            assert excinfo.value.code == "WS_INVALID_PAYLOAD"

    def test_ws_target_allowlist_uses_policy_ssot(self):
        """R6_WS_POLICY_SSOT: Allowlist target đọc từ policy JSON, không hard-code."""
        assert validate_target_process_allowlist("notepad.exe") is True
        assert validate_target_process_allowlist("calculator.exe") is True
        assert validate_target_process_allowlist("desktop") is True
        assert validate_target_process_allowlist("cmd.exe") is False
        assert validate_target_process_allowlist("powershell.exe") is False

    def test_stream_elements_never_expose_value(self):
        """R5_WS_NO_VALUE_BROADCAST: Payload stream không bao giờ chứa el.value (PII/password)."""
        from scripts.host_bridge import serialize_stream_elements

        class FakeEl:
            ref = "e1"
            name = "Password"
            control_type = "Edit"
            automation_id = "passwordField"
            rect = (1, 2, 3, 4)
            center = (2, 3)
            is_enabled = True
            value = "super-secret-password"

        serialized = serialize_stream_elements([FakeEl()])
        assert len(serialized) == 1
        assert "value" not in serialized[0]
        assert "super-secret-password" not in str(serialized)
