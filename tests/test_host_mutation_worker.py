# -*- coding: utf-8 -*-
"""
tests/test_host_mutation_worker.py
[NEGATIVE GATE & UNIT TEST SUITE FOR M5 HOST MUTATION WORKER - v2.3 EXACT SCHEMA & SESSION BINDING]
Bao quát toàn bộ 15 rào chắn an toàn tiêu cực với Ed25519 Public Key Verification.
"""

import unittest
from unittest.mock import patch, MagicMock
import time
import os
import sys

sys.path.insert(0, ".")

from scripts.host_mutation_worker import HostMutationWorker, MutationSecurityError
from scripts.master_approval_signer import MasterApprovalSigner
from scripts.bounds_validator import OutOfBoundsSecurityError, WindowTargetMismatchError
from services.ai_desktop.uia_click_executor import ResolvedElement, UIAClickError

TEST_MUTATION_SECRET = "TEST_MUTATION_SECRET_KEY_2026_VERY_SECURE"
TEST_SESSION = "test_session_001"

class TestHostMutationWorker(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Sinh một cặp khóa Ed25519 cho Master
        cls.master_priv_b64, cls.master_pub_b64 = MasterApprovalSigner.generate_keypair()

    def setUp(self):
        self.master_signer = MasterApprovalSigner(private_key_b64=self.master_priv_b64)
        # Worker CHỈ ĐƯỢC CẤP PUBLIC KEY CỦA MASTER!
        self.worker = HostMutationWorker(
            port=9996,
            secret_key=TEST_MUTATION_SECRET,
            master_public_key=self.master_pub_b64
        )
        self.worker.mutation_enabled = False  # Mặc định an toàn
        self.worker.watchdog._stopped = False
        self.worker.watchdog._stop_reason = ""
        
        # Sinh Master Auth Token hợp lệ dùng cho các test case
        self.valid_master_token = self.master_signer.create_master_auth_token(
            session_id=TEST_SESSION,
            caller_id="master_test_runner"
        )

    def _sign_approval_for_lease(self, lease: dict) -> str:
        """Hàm trợ giúp Master ký phê duyệt đầy đủ ngữ cảnh cho lease (gồm session_id)."""
        return self.master_signer.sign_mutation_approval(
            lease_id=lease["lease_id"],
            nonce=lease["nonce"],
            hwnd=lease["hwnd"],
            target_pid=lease["pid"],
            proc_name=lease["proc_name"],
            action=lease["action"],
            text_payload=lease["text_payload"],
            element_ref=lease.get("element_ref", ""),
            scroll_direction=lease.get("scroll_direction", ""),
            scroll_unit=lease.get("scroll_unit", ""),
            scroll_steps=lease.get("scroll_steps", 0),
            worker_generation=lease["worker_generation"],
            lease_expires_at=lease["expires_at"],
            session_id=lease.get("session_id", TEST_SESSION)
        )

    def test_01_default_state_mutation_disabled_and_fail_closed(self):
        """Mặc định Mutation Worker phải ở trạng thái disabled và báo cáo rõ ràng."""
        status = self.worker.get_status()
        self.assertFalse(status["mutation_enabled"])
        self.assertEqual(status["safety_invariant"], "MUTATION_DISABLED_BY_DEFAULT")
        self.assertEqual(status["port"], 9996)
        self.assertIn("notepad.exe", status["allowed_target_scope"])
        self.assertIn("wordpad.exe", status["allowed_target_scope"])

    def test_02_request_lease_missing_or_invalid_auth_token_rejected(self):
        """Yêu cầu cấp Lease không có Master Auth Token hoặc token sai chữ ký phải bị từ chối PermissionError."""
        with self.assertRaises(PermissionError):
            self.worker.request_one_time_lease(
                hwnd=12345, action="type", text_payload="test", master_auth_token="", expected_session_id=TEST_SESSION
            )
        with self.assertRaises(PermissionError):
            self.worker.request_one_time_lease(
                hwnd=12345, action="type", text_payload="test", master_auth_token="fake_token_tampered_123456", expected_session_id=TEST_SESSION
            )

    def test_02b_request_lease_missing_expected_session_rejected(self):
        """Yêu cầu cấp Lease thiếu expected_session_id bắt buộc bị từ chối PermissionError."""
        with self.assertRaises(PermissionError) as ctx:
            self.worker.request_one_time_lease(
                hwnd=12345, action="type", text_payload="test", master_auth_token=self.valid_master_token, expected_session_id=""
            )
        self.assertIn("expected_session_id", str(ctx.exception))

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_03_request_lease_wrong_process_rejected(self, mock_psutil_proc, mock_user32):
        """Yêu cầu thao tác trên tiến trình khác ngoài notepad.exe (ví dụ: cmd.exe) bị chặn đứng."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "cmd.exe"
        mock_psutil_proc.return_value = proc_mock

        with self.assertRaises(MutationSecurityError):
            self.worker.request_one_time_lease(
                hwnd=12345,
                action="type",
                text_payload="malicious command",
                master_auth_token=self.valid_master_token,
                expected_session_id=TEST_SESSION
            )

    def test_04_request_lease_when_watchdog_stopped_rejected(self):
        """Khi Watchdog STOP Latch đang kích hoạt, từ chối cấp mọi lease mới."""
        self.worker.watchdog.trigger_stop("MANUAL_STOP_ACTIVE")
        with self.assertRaises(MutationSecurityError):
            self.worker.request_one_time_lease(
                hwnd=12345,
                action="type",
                text_payload="test",
                master_auth_token=self.valid_master_token,
                expected_session_id=TEST_SESSION
            )

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_05_request_lease_valid_notepad_success(self, mock_psutil_proc, mock_user32):
        """Cấp Lease thành công cho notepad.exe với chữ ký HMAC và hạn 30s."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "notepad.exe"
        mock_psutil_proc.return_value = proc_mock

        res = self.worker.request_one_time_lease(
            hwnd=12345,
            action="type",
            text_payload="Hello Notepad",
            master_auth_token=self.valid_master_token,
            expected_session_id=TEST_SESSION
        )

        self.assertEqual(res["status"], "LEASE_ISSUED")
        self.assertTrue(res["lease_id"].startswith("lease_"))
        self.assertEqual(res["proc_name"], "notepad.exe")
        self.assertEqual(res["validity_seconds"], 30.0)
        self.assertEqual(res["session_id"], TEST_SESSION)
        self.assertTrue(len(res["signature"]) > 16)

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_06_execute_replay_attack_rejected(self, mock_psutil_proc, mock_user32):
        """Tái sử dụng lease token lần 2 (Replay Attack) phải bị chặn REPLAY_ATTACK_DETECTED."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "notepad.exe"
        mock_psutil_proc.return_value = proc_mock

        lease = self.worker.request_one_time_lease(
            hwnd=12345, action="type", text_payload="Test", master_auth_token=self.valid_master_token, expected_session_id=TEST_SESSION
        )
        master_sig = self._sign_approval_for_lease(lease)

        # Lần 1: Thực thi thành công (ghi nhận Dry-Run)
        exec1 = self.worker.execute_with_lease(
            lease_id=lease["lease_id"],
            signature=lease["signature"],
            master_approval_signature=master_sig
        )
        self.assertIn(exec1["status"], ("BLOCKED_BY_DEFAULT", "MUTATION_DISABLED_DRY_RUN", "DELIVERED_VERIFIED"))

        # Lần 2: Tái sử dụng cùng lease_id -> Bị chặn đứng lập tức!
        exec2 = self.worker.execute_with_lease(
            lease_id=lease["lease_id"],
            signature=lease["signature"],
            master_approval_signature=master_sig
        )
        self.assertEqual(exec2["status"], "BLOCKED")
        self.assertEqual(exec2["receipt"], "REPLAY_ATTACK_DETECTED")

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_07_execute_expired_lease_rejected(self, mock_psutil_proc, mock_user32):
        """Lease hết hạn (> 30s) phải bị chặn LEASE_EXPIRED."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "notepad.exe"
        mock_psutil_proc.return_value = proc_mock

        lease = self.worker.request_one_time_lease(
            hwnd=12345, action="type", text_payload="Test", master_auth_token=self.valid_master_token, expected_session_id=TEST_SESSION
        )
        master_sig = self._sign_approval_for_lease(lease)

        # Tua nhanh thời gian hết hạn của lease
        self.worker._active_leases[lease["lease_id"]]["expires_at"] = time.time() - 5.0

        exec_res = self.worker.execute_with_lease(
            lease_id=lease["lease_id"],
            signature=lease["signature"],
            master_approval_signature=master_sig
        )
        self.assertEqual(exec_res["status"], "BLOCKED")
        self.assertEqual(exec_res["receipt"], "LEASE_EXPIRED")

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_08_execute_tampered_signature_rejected(self, mock_psutil_proc, mock_user32):
        """Chữ ký vé cấp phép bị giả mạo phải bị chặn TAMPERED_SIGNATURE."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "notepad.exe"
        mock_psutil_proc.return_value = proc_mock

        lease = self.worker.request_one_time_lease(
            hwnd=12345, action="type", text_payload="Test", master_auth_token=self.valid_master_token, expected_session_id=TEST_SESSION
        )
        master_sig = self._sign_approval_for_lease(lease)

        exec_res = self.worker.execute_with_lease(
            lease_id=lease["lease_id"],
            signature="tampered_fake_signature_abc123",
            master_approval_signature=master_sig
        )
        self.assertEqual(exec_res["status"], "BLOCKED")
        self.assertEqual(exec_res["receipt"], "TAMPERED_SIGNATURE")

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_09_execute_toctou_pid_changed_rejected(self, mock_psutil_proc, mock_user32):
        """Anti-TOCTOU: Nếu PID cửa sổ thay đổi giữa lúc cấp lease và thực thi -> chặn TOCTOU_PID_MISMATCH."""
        mock_user32.IsWindow.return_value = 1
        proc_mock1 = MagicMock()
        proc_mock1.name.return_value = "notepad.exe"
        mock_psutil_proc.return_value = proc_mock1

        def fake_pid_call(hwnd, pid_ptr):
            pid_ptr._obj.value = 1000
            return 1
        mock_user32.GetWindowThreadProcessId.side_effect = fake_pid_call

        lease = self.worker.request_one_time_lease(
            hwnd=12345, action="type", text_payload="Test", master_auth_token=self.valid_master_token, expected_session_id=TEST_SESSION
        )
        master_sig = self._sign_approval_for_lease(lease)

        # Khi execute: PID bị tráo thành 2000 (TOCTOU attack)
        def fake_pid_call_tampered(hwnd, pid_ptr):
            pid_ptr._obj.value = 2000
            return 1
        mock_user32.GetWindowThreadProcessId.side_effect = fake_pid_call_tampered

        exec_res = self.worker.execute_with_lease(
            lease_id=lease["lease_id"],
            signature=lease["signature"],
            master_approval_signature=master_sig
        )
        self.assertEqual(exec_res["status"], "BLOCKED")
        self.assertEqual(exec_res["receipt"], "TOCTOU_PID_MISMATCH")

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_10_execute_when_watchdog_stopped_blocked(self, mock_psutil_proc, mock_user32):
        """Nếu Watchdog bị kích hoạt ngay trước khi dispatch, phải chặn EMERGENCY_STOP_TRIGGERED."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "notepad.exe"
        mock_psutil_proc.return_value = proc_mock

        lease = self.worker.request_one_time_lease(
            hwnd=12345, action="type", text_payload="Test", master_auth_token=self.valid_master_token, expected_session_id=TEST_SESSION
        )
        master_sig = self._sign_approval_for_lease(lease)

        # Master bấm dừng khẩn cấp trước khi lệnh phát ra
        self.worker.watchdog.trigger_stop("MASTER_PRESSED_F12")

        exec_res = self.worker.execute_with_lease(
            lease_id=lease["lease_id"],
            signature=lease["signature"],
            master_approval_signature=master_sig
        )
        self.assertEqual(exec_res["status"], "BLOCKED")
        self.assertEqual(exec_res["receipt"], "EMERGENCY_STOP_TRIGGERED")

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_11_mutation_disabled_by_default_safe_fail_closed(self, mock_psutil_proc, mock_user32):
        """Khi JKAI_MUTATION_ENABLED=false, thực thi hợp lệ được ghi nhận Dry-Run và không can thiệp thật."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "notepad.exe"
        mock_psutil_proc.return_value = proc_mock

        lease = self.worker.request_one_time_lease(
            hwnd=12345, action="type", text_payload="Safe Text", master_auth_token=self.valid_master_token, expected_session_id=TEST_SESSION
        )
        master_sig = self._sign_approval_for_lease(lease)

        exec_res = self.worker.execute_with_lease(
            lease_id=lease["lease_id"],
            signature=lease["signature"],
            master_approval_signature=master_sig
        )
        self.assertIn(exec_res["status"], ("BLOCKED_BY_DEFAULT", "MUTATION_DISABLED_DRY_RUN"))
        self.assertEqual(exec_res["receipt"], "MUTATION_DISABLED_DRY_RUN_RECEIPT")
        self.assertTrue(exec_res["precondition_verified"])
        self.assertEqual(exec_res["after_state"], "PRESERVED_UNMODIFIED")

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_12_cryptographic_hitl_approval_signature_verified(self, mock_psutil_proc, mock_user32):
        """Chữ ký phê duyệt Master giả mạo hoặc chuỗi rác như 'APPROVE' bị từ chối."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "notepad.exe"
        mock_psutil_proc.return_value = proc_mock

        fresh_token = self.master_signer.create_master_auth_token(session_id="test_12")
        lease = self.worker.request_one_time_lease(
            hwnd=12345, action="type", text_payload="Test", master_auth_token=fresh_token, expected_session_id="test_12"
        )

        # Thử nghiệm với chuỗi giả mạo không phải Base64 Ed25519
        fake_res = self.worker.execute_with_lease(
            lease_id=lease["lease_id"],
            signature=lease["signature"],
            master_approval_signature="APPROVE_FAKE_SIGNATURE_123456"
        )
        self.assertEqual(fake_res["status"], "BLOCKED")
        self.assertEqual(fake_res["receipt"], "INVALID_MASTER_APPROVAL_SIGNATURE")

        # Thử nghiệm với chuỗi rỗng trên lease mới
        fresh_token2 = self.master_signer.create_master_auth_token(session_id="test_12_b")
        lease2 = self.worker.request_one_time_lease(
            hwnd=12345, action="type", text_payload="Test2", master_auth_token=fresh_token2, expected_session_id="test_12_b"
        )
        empty_res = self.worker.execute_with_lease(
            lease_id=lease2["lease_id"],
            signature=lease2["signature"],
            master_approval_signature=""
        )
        self.assertEqual(empty_res["status"], "BLOCKED")
        self.assertEqual(empty_res["receipt"], "MISSING_MASTER_APPROVAL_SIGNATURE")

    def test_13_fail_closed_secret_without_env_rejected(self):
        """Khởi tạo worker không có secret_key và không có biến môi trường JKAI_MUTATION_SECRET phải ném RuntimeError."""
        old_env = os.environ.get("JKAI_MUTATION_SECRET")
        try:
            if "JKAI_MUTATION_SECRET" in os.environ:
                del os.environ["JKAI_MUTATION_SECRET"]
            with self.assertRaises(RuntimeError) as ctx:
                HostMutationWorker(port=9996, secret_key=None, master_public_key=self.master_pub_b64)
            self.assertIn("FAIL_CLOSED", str(ctx.exception))
        finally:
            if old_env is not None:
                os.environ["JKAI_MUTATION_SECRET"] = old_env

    def test_14_fail_closed_without_master_public_key_rejected(self):
        """Khởi tạo worker không có master_public_key và không có biến môi trường JKAI_MASTER_PUBLIC_KEY phải ném RuntimeError."""
        old_env = os.environ.get("JKAI_MASTER_PUBLIC_KEY")
        try:
            if "JKAI_MASTER_PUBLIC_KEY" in os.environ:
                del os.environ["JKAI_MASTER_PUBLIC_KEY"]
            with self.assertRaises(RuntimeError) as ctx:
                HostMutationWorker(port=9996, secret_key=TEST_MUTATION_SECRET, master_public_key=None)
            self.assertIn("FAIL_CLOSED", str(ctx.exception))
        finally:
            if old_env is not None:
                os.environ["JKAI_MASTER_PUBLIC_KEY"] = old_env

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_15_request_lease_wordpad_allowed_by_policy(self, mock_psutil_proc, mock_user32):
        """WordPad nằm trong policy SSoT nên được cấp lease type_text (D9')."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "wordpad.exe"
        mock_psutil_proc.return_value = proc_mock

        res = self.worker.request_one_time_lease(
            hwnd=12345,
            action="type",
            text_payload="Hello WordPad",
            master_auth_token=self.valid_master_token,
            expected_session_id=TEST_SESSION
        )
        self.assertEqual(res["status"], "LEASE_ISSUED")
        self.assertEqual(res["proc_name"], "wordpad.exe")

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_16_request_lease_destructive_keyword_rejected(self, mock_psutil_proc, mock_user32):
        """Text chứa từ khóa phá hoại trong destructive_keywords phải bị chặn ở scope policy."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "notepad.exe"
        mock_psutil_proc.return_value = proc_mock

        with self.assertRaises(MutationSecurityError) as ctx:
            self.worker.request_one_time_lease(
                hwnd=12345,
                action="type",
                text_payload="please delete everything now",
                master_auth_token=self.valid_master_token,
                expected_session_id=TEST_SESSION
            )
        self.assertIn("SCOPE VIOLATION", str(ctx.exception))
        self.assertIn("từ khóa phá hoại", str(ctx.exception))

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_17_request_lease_over_length_text_rejected(self, mock_psutil_proc, mock_user32):
        """Text vượt max_text_length của app phải bị chặn (không cắt bớt im lặng)."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "notepad.exe"
        mock_psutil_proc.return_value = proc_mock

        with self.assertRaises(MutationSecurityError) as ctx:
            self.worker.request_one_time_lease(
                hwnd=12345,
                action="type",
                text_payload="A" * 501,
                master_auth_token=self.valid_master_token,
                expected_session_id=TEST_SESSION
            )
        self.assertIn("SCOPE VIOLATION", str(ctx.exception))
        self.assertIn("500", str(ctx.exception))

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_18_policy_allowed_click_lease_preflight_resolves_element(self, mock_psutil_proc, mock_user32):
        """Click lease của calculator (num1Button) qua preflight khi executor resolve được element."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "calculator.exe"
        mock_psutil_proc.return_value = proc_mock

        lease = self.worker.request_one_time_lease(
            hwnd=12345,
            action="click",
            text_payload="",
            element_ref="num1Button",
            master_auth_token=self.valid_master_token,
            expected_session_id=TEST_SESSION
        )
        self.assertEqual(lease["status"], "LEASE_ISSUED")
        self.assertEqual(lease["element_ref"], "num1Button")
        master_sig = self._sign_approval_for_lease(lease)

        resolved = ResolvedElement(
            identifier="num1Button", name="One", automation_id="num1Button",
            control_type="Button", class_name="Button", signature="sig_num1",
            element_hash="hash_num1", rect=(0, 0, 10, 10),
            supported_patterns=("InvokePattern",), snapshot_hash="snap_1",
        )
        with patch.object(self.worker.click_executor, "resolve", return_value=resolved):
            ok, reason, locked = self.worker.preflight_verify_authorization(
                lease_id=lease["lease_id"],
                signature=lease["signature"],
                master_approval_signature=master_sig
            )
        self.assertTrue(ok, reason)
        self.assertEqual(reason, "PREFLIGHT_AUTH_PASSED")
        self.assertEqual(locked["element_identity"]["signature"], "sig_num1")

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_20_click_lease_requires_allowlisted_element(self, mock_psutil_proc, mock_user32):
        """Click thiếu element_ref hoặc element ngoài allowlist bị chặn ngay khi xin lease."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "calculator.exe"
        mock_psutil_proc.return_value = proc_mock

        with self.assertRaises(MutationSecurityError) as ctx:
            self.worker.request_one_time_lease(
                hwnd=12345, action="click", text_payload="",
                master_auth_token=self.master_signer.create_master_auth_token(session_id=TEST_SESSION),
                expected_session_id=TEST_SESSION
            )
        self.assertIn("element_ref", str(ctx.exception))

        with self.assertRaises(MutationSecurityError) as ctx2:
            self.worker.request_one_time_lease(
                hwnd=12345, action="click", text_payload="", element_ref="evilButton",
                master_auth_token=self.master_signer.create_master_auth_token(session_id=TEST_SESSION),
                expected_session_id=TEST_SESSION
            )
        self.assertIn("SCOPE VIOLATION", str(ctx2.exception))

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_21_type_lease_rejects_element_ref(self, mock_psutil_proc, mock_user32):
        """element_ref chỉ dành cho click; type_text kèm element_ref bị chặn (binding không mơ hồ)."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "notepad.exe"
        mock_psutil_proc.return_value = proc_mock

        with self.assertRaises(MutationSecurityError) as ctx:
            self.worker.request_one_time_lease(
                hwnd=12345, action="type", text_payload="hello", element_ref="Text Editor",
                master_auth_token=self.master_signer.create_master_auth_token(session_id=TEST_SESSION),
                expected_session_id=TEST_SESSION
            )
        self.assertIn("SCOPE VIOLATION", str(ctx.exception))

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_22_click_tampered_element_ref_breaks_lease_hmac(self, mock_psutil_proc, mock_user32):
        """Đổi element_ref trong lease record phải làm HMAC của worker không còn khớp."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "calculator.exe"
        mock_psutil_proc.return_value = proc_mock

        lease = self.worker.request_one_time_lease(
            hwnd=12345, action="click", text_payload="", element_ref="num1Button",
            master_auth_token=self.valid_master_token, expected_session_id=TEST_SESSION
        )
        master_sig = self._sign_approval_for_lease(lease)
        self.worker._active_leases[lease["lease_id"]]["element_ref"] = "num9Button"

        ok, reason, _ = self.worker.preflight_verify_authorization(
            lease_id=lease["lease_id"],
            signature=lease["signature"],
            master_approval_signature=master_sig
        )
        self.assertFalse(ok)
        self.assertEqual(reason, "TAMPERED_SIGNATURE")

    @patch("scripts.host_mutation_worker.user32")
    @patch("psutil.Process")
    def test_23_click_preflight_fails_closed_when_element_unresolved(self, mock_psutil_proc, mock_user32):
        """Element không resolve được trong cây UIA hiện tại -> preflight fail-closed."""
        mock_user32.IsWindow.return_value = 1
        proc_mock = MagicMock()
        proc_mock.name.return_value = "calculator.exe"
        mock_psutil_proc.return_value = proc_mock

        lease = self.worker.request_one_time_lease(
            hwnd=12345, action="click", text_payload="", element_ref="num1Button",
            master_auth_token=self.valid_master_token, expected_session_id=TEST_SESSION
        )
        master_sig = self._sign_approval_for_lease(lease)

        with patch.object(self.worker.click_executor, "resolve",
                          side_effect=UIAClickError("ELEMENT_NOT_FOUND", "num1Button")):
            ok, reason, locked = self.worker.preflight_verify_authorization(
                lease_id=lease["lease_id"],
                signature=lease["signature"],
                master_approval_signature=master_sig
            )
        self.assertFalse(ok)
        self.assertEqual(reason, "CLICK_TARGET_UNRESOLVED: ELEMENT_NOT_FOUND")
        self.assertIsNone(locked)

    @patch("win32gui.FindWindowEx")
    @patch("win32gui.GetClassName")
    def test_19_find_text_control_resolves_wordpad_richedit(self, mock_class_name, mock_find_ex):
        """Resolver phải tìm được RICHEDIT50W của WordPad (và nhận diện khi hwnd chính là text control)."""
        mock_class_name.return_value = "WordPadClass"
        mock_find_ex.side_effect = lambda parent, child, cls, title: 777 if cls == "RICHEDIT50W" else 0
        self.assertEqual(HostMutationWorker._find_text_control(1234), 777)

        mock_class_name.return_value = "RICHEDIT50W"
        self.assertEqual(HostMutationWorker._find_text_control(1234), 1234)

class TestDeliverySemanticsMapping(unittest.TestCase):
    """A failed executor call must never be mislabeled as NOT_DELIVERED."""

    NOT_DELIVERED = {
        "status": "BLOCKED",
        "receipt": "CLAIMED_NOT_DELIVERED",
        "claim_state": "CLAIMED_NOT_DELIVERED",
        "recovery_policy": "NEW_LEASE_AND_NEW_MASTER_APPROVAL_REQUIRED",
    }

    def _map(self, exc):
        return HostMutationWorker._claim_from_executor_error(
            exc, dict(self.NOT_DELIVERED), "click", 12345, "Line down"
        )

    def test_01_pre_dispatch_error_stays_not_delivered(self):
        result = self._map(UIAClickError("ELEMENT_NOT_FOUND", "Line down"))
        self.assertEqual(result["receipt"], "CLAIMED_NOT_DELIVERED")
        self.assertEqual(result["reason"], "ELEMENT_NOT_FOUND")

    def test_02_invoke_failure_maps_to_delivery_uncertain(self):
        result = self._map(UIAClickError("INVOKE_FAILED", "provider", delivery_state="UNCERTAIN"))
        self.assertEqual(result["receipt"], "CLAIMED_DELIVERY_UNCERTAIN")
        self.assertEqual(result["claim_state"], "CLAIMED_DELIVERY_UNCERTAIN")
        self.assertEqual(result["recovery_policy"], "MANUAL_STATE_INSPECTION_REQUIRED")
        self.assertEqual(result["element_ref"], "Line down")

    def test_03_scroll_progress_maps_to_partial_with_counts(self):
        exc = UIAClickError(
            "SCROLL_FAILED", "after 2 step(s)", delivery_state="PARTIAL",
            details={"scroll_steps_applied": 2, "vertical_percent_before": 10.0},
        )
        result = HostMutationWorker._claim_from_executor_error(
            exc, dict(self.NOT_DELIVERED), "scroll", 12345, "Text Editor"
        )
        self.assertEqual(result["receipt"], "CLAIMED_PARTIALLY_DELIVERED")
        self.assertEqual(result["scroll_steps_applied"], 2)
        self.assertEqual(result["vertical_percent_before"], 10.0)


if __name__ == "__main__":
    unittest.main()
