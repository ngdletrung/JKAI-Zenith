# -*- coding: utf-8 -*-
"""
tests/test_semantic_action_dispatcher.py
[Gated Semantic Action Dispatcher — R1..R4 / R6 / R7 verification suite]

Mỗi bài kiểm thử dưới đây phải FAIL nếu ranh giới an ninh bị nới lỏng:
  1. Fail-closed env gate: JKAI_MUTATION_ENABLED != 1 -> từ chối ngay.
  2. Bypass test chỉ hợp lệ khi JKAI_MUTATION_TEST_MODE=1.
  3. KEY_COMBO / SCROLL -> REJECTED_UNSUPPORTED_ACTION (không có fallback im lặng).
  4. CLICK / FOCUS chỉ mô phỏng, tuyệt đối không gọi Win32.
  5. Process / element / max-length lấy từ policy SSoT (file JSON), không hard-code.
  6. Snapshot quá TTL -> SNAPSHOT_STALE.
  7. Pre-dispatch identity revalidation: HWND/PID/hash drift -> PRE_DISPATCH_IDENTITY_DRIFT.
  8. TYPE_TEXT thật yêu cầu approval envelope + nonce tiêu thụ nguyên tử (chống replay).
  9. SendMessage != 1 hoặc ném lỗi -> EXECUTION_FAILED, chỉ một lần thử (no auto retry).
 10. After-state mismatch / không đọc được -> FAIL, verified_after_state=False (không PASS giả).
 11. Receipt có digest SHA-256 và được ký khi có receipt_signer.
"""

import copy
import hashlib
import time
from unittest.mock import MagicMock, patch

import pytest

from services.ai_desktop.nonce_store import PersistentNonceStore
from services.ai_desktop.semantic_action_dispatcher import SemanticActionDispatcher
from services.ai_desktop.semantic_action_ir import (
    ActionType,
    ClickParams,
    FocusParams,
    KeyComboParams,
    ScrollParams,
    SemanticActionIR,
    TypeTextParams,
    compute_canonical_snapshot_hash,
)
from services.ai_desktop.uia_tree_inspector import UIAElementNode, UIATreeSnapshot

STUB_PAYLOAD_SHA = "b" * 64


# ── Fakes / helpers ──────────────────────────────────────────────────────


class StubVerifier:
    """Thay thế MasterAuthorityVerifier cho unit test (không đụng khóa thật)."""

    def __init__(self, payload_sha: str = STUB_PAYLOAD_SHA, ok: bool = True, reason: str = "MASTER_AUTHORITY_VERIFIED_PASS"):
        self.payload_sha = payload_sha
        self.ok = ok
        self.reason = reason
        self.calls = []

    def verify_approval_token(self, **kwargs):
        self.calls.append(kwargs)
        if not self.ok:
            return False, self.reason, {}
        return True, "MASTER_AUTHORITY_VERIFIED_PASS", {
            "master_key_id": "stub_master_key",
            "public_key_fingerprint": "stub_fingerprint",
            "canonical_payload_sha256": self.payload_sha,
            "status": "MASTER_AUTHORITY_VERIFIED_PASS",
        }


class FakeAfterState:
    """After-state verifier giả lập: điều khiển được kết quả đọc sau thực thi."""

    def __init__(self, before_text: str = "seed", match: bool = True, read_ok: bool = True):
        self.before_text = before_text
        self.match = match
        self.read_ok = read_ok
        self.capture_calls = 0

    def capture_snapshot(self, hwnd, proc_name="notepad.exe"):
        self.capture_calls += 1
        text = self.before_text if self.read_ok else ""
        return {
            "timestamp": time.time(),
            "hwnd": hwnd,
            "proc_name": proc_name,
            "read_success": self.read_ok,
            "text": text,
            "hash": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "error": None if self.read_ok else "SIMULATED_READ_FAILURE",
        }

    def verify_action_result(self, before_snapshot, hwnd, expected_mutation_text, proc_name="notepad.exe",
                             timeout_seconds=2.0, match_mode="append"):
        after_text = expected_mutation_text if self.match else "unexpected-content"
        return {
            "status": "VERIFIED_MATCH" if self.match else "STATE_MISMATCH",
            "target_hwnd": hwnd,
            "proc_name": proc_name,
            "before_hash": before_snapshot.get("hash", ""),
            "after_hash": hashlib.sha256(after_text.encode("utf-8")).hexdigest(),
            "expected_text_sha256": hashlib.sha256(expected_mutation_text.encode("utf-8")).hexdigest(),
            "read_success": True,
            "match": self.match,
            "match_mode": match_mode,
            "receipt_digest": "d" * 64,
        }


class StubReceiptSigner:
    def __init__(self):
        self.signed = []

    def sign_receipt(self, receipt_bytes: bytes):
        self.signed.append(receipt_bytes)
        return {"key_id": "stub_master_key", "signature_b64": "c3R1Yl9zaWc="}


def _make_snapshot(proc_name="notepad.exe", hwnd=5555, pid=8888, elements=None, captured_at=None, ttl=30.0):
    nodes = elements or [
        UIAElementNode(
            name="Text Editor",
            control_type="Edit",
            automation_id="Edit",
            class_name="Edit",
            rect=(0, 0, 400, 300),
            center=(200, 150),
            hwnd=hwnd,
            supported_patterns=["ValuePattern"],
            ref="e1",
            value="",
        )
    ]
    snap_hash = compute_canonical_snapshot_hash(hwnd=hwnd, pid=pid, process_name=proc_name, elements=nodes)
    base = time.time() if captured_at is None else captured_at
    return UIATreeSnapshot(
        hwnd=hwnd,
        window_title="Test Window",
        process_name=proc_name,
        pid=pid,
        element_count=len(nodes),
        snapshot_hash=snap_hash,
        elements=nodes,
        ref_map={n.ref: n for n in nodes},
        captured_at=base,
        expires_at=base + ttl,
    )


def _calculator_snapshot():
    hwnd, pid, proc = 4444, 7777, "calculator.exe"
    nodes = [
        UIAElementNode(
            name="Five",
            control_type="Button",
            automation_id="num5Button",
            class_name="Button",
            rect=(10, 60, 60, 100),
            center=(35, 80),
            hwnd=hwnd,
            supported_patterns=["InvokePattern"],
            ref="e1",
        )
    ]
    snap_hash = compute_canonical_snapshot_hash(hwnd=hwnd, pid=pid, process_name=proc, elements=nodes)
    now = time.time()
    return UIATreeSnapshot(
        hwnd=hwnd,
        window_title="Calculator",
        process_name=proc,
        pid=pid,
        element_count=len(nodes),
        snapshot_hash=snap_hash,
        elements=nodes,
        ref_map={n.ref: n for n in nodes},
        captured_at=now,
        expires_at=now + 30.0,
    )


def _make_action(snapshot, ref="e1", action_type=ActionType.TYPE_TEXT, params=None, text="Pilot Hello",
                 approval_digest="sha256_" + STUB_PAYLOAD_SHA, nonce="nonce_pilot_0001"):
    now = time.time()
    el = snapshot.ref_map[ref]
    if params is None:
        if action_type == ActionType.TYPE_TEXT:
            params = TypeTextParams(text=text, max_length=1000, clear_before_type=True)
        elif action_type == ActionType.CLICK:
            params = ClickParams(button="left", click_count=1)
        elif action_type == ActionType.FOCUS:
            params = FocusParams()
        elif action_type == ActionType.KEY_COMBO:
            params = KeyComboParams(keys=["ctrl", "s"])
        elif action_type == ActionType.SCROLL:
            params = ScrollParams(direction="down", delta=120)

    return SemanticActionIR(
        session_id="pilot_session_001",
        lease_id="lease_pilot_001",
        nonce=nonce,
        issued_at=now,
        expires_at=now + 60.0,
        approval_digest=approval_digest,
        action_type=action_type,
        target_ref=ref,
        target_hwnd=snapshot.hwnd,
        target_pid=snapshot.pid,
        target_process_name=snapshot.process_name,
        element_hash=el.element_hash,
        snapshot_hash=snapshot.snapshot_hash,
        parameters=params,
        description="R1..R4 dispatcher test action",
    )


def _dispatcher(tmp_path, dry_run=False, verifier=None, after_state=None, signer=None):
    return SemanticActionDispatcher(
        inspector=MagicMock(),
        dry_run=dry_run,
        verifier=verifier or StubVerifier(),
        nonce_store=PersistentNonceStore(tmp_path / "nonces.db"),
        after_state_verifier=after_state or FakeAfterState(),
        receipt_signer=signer,
    )


# ── Suite ────────────────────────────────────────────────────────────────


class TestSemanticActionDispatcherSuite:

    @pytest.fixture(autouse=True)
    def _test_mode_env(self, monkeypatch):
        monkeypatch.delenv("JKAI_MUTATION_ENABLED", raising=False)
        monkeypatch.setenv("JKAI_MUTATION_TEST_MODE", "1")

    # ── 1-2. Environment gate ────────────────────────────────────────────

    def test_env_fail_closed_rejects_when_mutation_disabled(self, tmp_path):
        snapshot = _make_snapshot()
        dispatcher = _dispatcher(tmp_path, dry_run=True)
        res = dispatcher.dispatch_action(
            _make_action(snapshot), live_snapshot_override=snapshot, bypass_env_for_test=False
        )
        assert res.success is False
        assert res.status == "REJECTED_BY_POLICY"
        assert "MUTATION_DISABLED_BY_POLICY" in res.reason

    def test_bypass_requires_explicit_test_mode(self, tmp_path, monkeypatch):
        monkeypatch.delenv("JKAI_MUTATION_TEST_MODE", raising=False)
        snapshot = _make_snapshot()
        dispatcher = _dispatcher(tmp_path, dry_run=True)
        res = dispatcher.dispatch_action(
            _make_action(snapshot), live_snapshot_override=snapshot, bypass_env_for_test=True
        )
        assert res.status == "REJECTED_BY_POLICY"
        assert "MUTATION_DISABLED_BY_POLICY" in res.reason

    def test_env_gate_open_when_mutation_enabled(self, tmp_path, monkeypatch):
        monkeypatch.setenv("JKAI_MUTATION_ENABLED", "1")
        snapshot = _make_snapshot()
        dispatcher = _dispatcher(tmp_path, dry_run=True)
        res = dispatcher.dispatch_action(_make_action(snapshot), live_snapshot_override=snapshot)
        assert res.status == "DRY_RUN_VALIDATED_SUCCESS"

    # ── 3. Unsupported actions ───────────────────────────────────────────

    def test_key_combo_and_scroll_rejected_as_unsupported(self, tmp_path):
        snapshot = _make_snapshot()
        dispatcher = _dispatcher(tmp_path, dry_run=True)

        for action_type in (ActionType.KEY_COMBO, ActionType.SCROLL):
            action = _make_action(snapshot, action_type=action_type)
            res = dispatcher.dispatch_action(action, live_snapshot_override=snapshot, bypass_env_for_test=True)
            assert res.success is False
            assert res.status == "REJECTED_UNSUPPORTED_ACTION"
            assert "ACTION_TYPE_NOT_IMPLEMENTED" in res.reason

    # ── 4. Simulation-only click/focus ──────────────────────────────────

    def test_click_and_focus_are_simulated_only(self, tmp_path):
        snapshot = _calculator_snapshot()
        dispatcher = _dispatcher(tmp_path, dry_run=False)

        with patch("win32gui.SendMessage") as send_message, \
             patch("win32gui.SetForegroundWindow") as set_foreground:
            for action_type in (ActionType.CLICK, ActionType.FOCUS):
                action = _make_action(snapshot, action_type=action_type)
                res = dispatcher.dispatch_action(action, live_snapshot_override=snapshot, bypass_env_for_test=True)
                assert res.success is True
                assert res.status == "DRY_RUN_SIMULATED"
                assert res.execution_receipt["simulated"] is True
                assert res.execution_receipt["verified_after_state"] is False

        send_message.assert_not_called()
        set_foreground.assert_not_called()

    # ── 5. Policy SSoT scope ────────────────────────────────────────────

    def test_process_blocked_outside_policy(self, tmp_path):
        snapshot = _make_snapshot()
        action = _make_action(snapshot)
        action.target_process_name = "cmd.exe"
        dispatcher = _dispatcher(tmp_path, dry_run=True)

        res = dispatcher.dispatch_action(action, live_snapshot_override=snapshot, bypass_env_for_test=True)
        assert res.success is False
        assert res.status == "REJECTED_BY_POLICY"
        assert "PROCESS_NOT_PERMITTED_IN_PILOT" in res.reason

    def test_element_not_in_allowlist_rejected(self, tmp_path):
        snapshot = _make_snapshot(
            elements=[
                UIAElementNode(
                    name="Secret Field",
                    control_type="Edit",
                    automation_id="secretEdit",
                    class_name="Edit",
                    rect=(0, 0, 400, 30),
                    center=(200, 15),
                    hwnd=5555,
                    supported_patterns=["ValuePattern"],
                    ref="e1",
                )
            ]
        )
        dispatcher = _dispatcher(tmp_path, dry_run=True)
        res = dispatcher.dispatch_action(_make_action(snapshot), live_snapshot_override=snapshot, bypass_env_for_test=True)
        assert res.success is False
        assert res.status == "REJECTED_BY_POLICY"
        assert "ELEMENT_NOT_PERMITTED" in res.reason

    def test_text_exceeds_app_max_length(self, tmp_path):
        snapshot = _make_snapshot()
        action = _make_action(snapshot, params=TypeTextParams(text="x" * 501, max_length=1000))
        dispatcher = _dispatcher(tmp_path, dry_run=True)

        res = dispatcher.dispatch_action(action, live_snapshot_override=snapshot, bypass_env_for_test=True)
        assert res.success is False
        assert res.status == "REJECTED_BY_POLICY"
        assert "TEXT_EXCEEDS_APP_MAX_LENGTH" in res.reason

    # ── 6. Snapshot freshness ───────────────────────────────────────────

    def test_stale_snapshot_rejected(self, tmp_path):
        snapshot = _make_snapshot(captured_at=time.time() - 60.0, ttl=1.0)
        action = _make_action(snapshot)
        dispatcher = _dispatcher(tmp_path, dry_run=True)

        res = dispatcher.dispatch_action(action, live_snapshot_override=snapshot, bypass_env_for_test=True)
        assert res.success is False
        assert res.status == "SNAPSHOT_STALE"
        assert "SNAPSHOT_TTL_EXPIRED" in res.reason

    # ── 7. Pre-dispatch identity drift ──────────────────────────────────

    def test_pre_dispatch_identity_drift_aborts_immediately(self, tmp_path):
        snapshot = _make_snapshot()
        action = _make_action(snapshot)
        dispatcher = _dispatcher(tmp_path, dry_run=True)

        drift_hwnd = copy.deepcopy(snapshot)
        drift_hwnd.hwnd = 999999
        res1 = dispatcher.dispatch_action(action, live_snapshot_override=drift_hwnd, bypass_env_for_test=True)
        assert res1.status == "PRE_DISPATCH_IDENTITY_DRIFT"
        assert "TARGET_HWND_MISMATCH" in res1.reason

        drift_pid = copy.deepcopy(snapshot)
        drift_pid.pid = 77777
        res2 = dispatcher.dispatch_action(action, live_snapshot_override=drift_pid, bypass_env_for_test=True)
        assert res2.status == "PRE_DISPATCH_IDENTITY_DRIFT"
        assert "TARGET_PID_MISMATCH" in res2.reason

        drift_snap = copy.deepcopy(snapshot)
        drift_snap.snapshot_hash = "sha256_" + "8" * 64
        res3 = dispatcher.dispatch_action(action, live_snapshot_override=drift_snap, bypass_env_for_test=True)
        assert res3.status == "PRE_DISPATCH_IDENTITY_DRIFT"
        assert "SNAPSHOT_HASH_DRIFT" in res3.reason

        drift_el = copy.deepcopy(snapshot)
        drift_el.ref_map["e1"].element_hash = "7" * 64
        res4 = dispatcher.dispatch_action(action, live_snapshot_override=drift_el, bypass_env_for_test=True)
        assert res4.status == "PRE_DISPATCH_IDENTITY_DRIFT"
        assert "STALE_ELEMENT_HASH" in res4.reason

    # ── 8. Dry-run ──────────────────────────────────────────────────────

    def test_dry_run_validation_passes_cleanly(self, tmp_path):
        snapshot = _make_snapshot()
        dispatcher = _dispatcher(tmp_path, dry_run=True)

        res = dispatcher.dispatch_action(_make_action(snapshot), live_snapshot_override=snapshot, bypass_env_for_test=True)
        assert res.success is True
        assert res.status == "DRY_RUN_VALIDATED_SUCCESS"
        assert res.reason == "ACTION_PRE_DISPATCH_VERIFIED_DRY_RUN"
        assert res.revalidation_details is not None

    # ── 9. Approval envelope & nonce ────────────────────────────────────

    def test_missing_approval_envelope_rejected(self, tmp_path):
        snapshot = _make_snapshot()
        dispatcher = _dispatcher(tmp_path, dry_run=False)

        res = dispatcher.dispatch_action(_make_action(snapshot), live_snapshot_override=snapshot, bypass_env_for_test=True)
        assert res.success is False
        assert res.status == "REJECTED_BY_APPROVAL"
        assert res.reason == "APPROVAL_ENVELOPE_MISSING"

    def test_approval_digest_mismatch_rejected(self, tmp_path):
        snapshot = _make_snapshot()
        action = _make_action(snapshot, approval_digest="sha256_" + "a" * 64)
        dispatcher = _dispatcher(tmp_path, dry_run=False)

        res = dispatcher.dispatch_action(
            action, live_snapshot_override=snapshot, bypass_env_for_test=True, approval_envelope_b64="ZW52ZWxvcGU="
        )
        assert res.success is False
        assert res.status == "REJECTED_BY_APPROVAL"
        assert "APPROVAL_DIGEST_MISMATCH" in res.reason

    def test_approval_context_is_fully_bound(self, tmp_path):
        snapshot = _make_snapshot()
        action = _make_action(snapshot, text="Bound payload")
        verifier = StubVerifier()
        dispatcher = _dispatcher(tmp_path, dry_run=False, verifier=verifier)

        with patch("win32gui.SendMessage", return_value=1):
            res = dispatcher.dispatch_action(
                action, live_snapshot_override=snapshot, bypass_env_for_test=True, approval_envelope_b64="ZW52ZWxvcGU="
            )

        assert res.success is True
        call = verifier.calls[0]
        assert call["expected_action"] == "type_text"
        assert call["expected_hwnd"] == snapshot.hwnd
        assert call["expected_target_pid"] == snapshot.pid
        assert call["expected_proc_name"] == snapshot.process_name
        assert call["expected_text"] == "Bound payload"
        assert call["expected_session_id"] == action.session_id
        assert call["expected_lease_id"] == action.lease_id
        assert call["expected_nonce"] == action.nonce

    def test_replay_nonce_detected(self, tmp_path):
        snapshot = _make_snapshot()
        action = _make_action(snapshot)
        dispatcher = _dispatcher(tmp_path, dry_run=False)

        with patch("win32gui.SendMessage", return_value=1):
            first = dispatcher.dispatch_action(
                action, live_snapshot_override=snapshot, bypass_env_for_test=True, approval_envelope_b64="ZW52ZWxvcGU="
            )
            second = dispatcher.dispatch_action(
                action, live_snapshot_override=snapshot, bypass_env_for_test=True, approval_envelope_b64="ZW52ZWxvcGU="
            )

        assert first.status == "DELIVERED_VERIFIED"
        assert second.success is False
        assert second.status == "REPLAY_NONCE_DETECTED"
        assert "REPLAY_ATTACK_DETECTED" in second.reason

    # ── 10. Execution failure, no auto retry ────────────────────────────

    def test_sendmessage_failure_is_single_attempt(self, tmp_path):
        snapshot = _make_snapshot()
        dispatcher = _dispatcher(tmp_path, dry_run=False)

        with patch("win32gui.SendMessage", return_value=0) as send_message:
            res = dispatcher.dispatch_action(
                _make_action(snapshot), live_snapshot_override=snapshot, bypass_env_for_test=True, approval_envelope_b64="ZW52ZWxvcGU="
            )

        assert res.success is False
        assert res.status == "EXECUTION_FAILED"
        assert "expected 1" in res.reason
        assert send_message.call_count == 1

    def test_sendmessage_exception_fails_closed(self, tmp_path):
        snapshot = _make_snapshot()
        dispatcher = _dispatcher(tmp_path, dry_run=False)

        with patch("win32gui.SendMessage", side_effect=OSError("Access Denied")) as send_message:
            res = dispatcher.dispatch_action(
                _make_action(snapshot), live_snapshot_override=snapshot, bypass_env_for_test=True, approval_envelope_b64="ZW52ZWxvcGU="
            )

        assert res.success is False
        assert res.status == "EXECUTION_FAILED"
        assert "DISPATCH_ERROR" in res.reason
        assert send_message.call_count == 1

    # ── 11. After-state verification ────────────────────────────────────

    def test_before_state_unreadable_is_unverifiable(self, tmp_path):
        snapshot = _make_snapshot()
        dispatcher = _dispatcher(tmp_path, dry_run=False, after_state=FakeAfterState(read_ok=False))

        with patch("win32gui.SendMessage") as send_message:
            res = dispatcher.dispatch_action(
                _make_action(snapshot), live_snapshot_override=snapshot, bypass_env_for_test=True, approval_envelope_b64="ZW52ZWxvcGU="
            )

        assert res.success is False
        assert res.status == "PRECONDITION_UNVERIFIABLE"
        assert "BEFORE_STATE_READ_FAILED" in res.reason
        send_message.assert_not_called()

    def test_after_state_mismatch_fails_closed(self, tmp_path):
        snapshot = _make_snapshot()
        dispatcher = _dispatcher(tmp_path, dry_run=False, after_state=FakeAfterState(match=False))

        with patch("win32gui.SendMessage", return_value=1):
            res = dispatcher.dispatch_action(
                _make_action(snapshot), live_snapshot_override=snapshot, bypass_env_for_test=True, approval_envelope_b64="ZW52ZWxvcGU="
            )

        assert res.success is False
        assert res.status == "AFTER_STATE_VERIFICATION_FAILED"
        assert res.execution_receipt["verified_after_state"] is False

    def test_success_receipt_has_digest_and_signature(self, tmp_path):
        snapshot = _make_snapshot()
        signer = StubReceiptSigner()
        dispatcher = _dispatcher(tmp_path, dry_run=False, signer=signer)

        with patch("win32gui.SendMessage", return_value=1):
            res = dispatcher.dispatch_action(
                _make_action(snapshot, text="Verified payload"),
                live_snapshot_override=snapshot,
                bypass_env_for_test=True,
                approval_envelope_b64="ZW52ZWxvcGU=",
            )

        assert res.success is True
        assert res.status == "DELIVERED_VERIFIED"
        receipt = res.execution_receipt
        assert receipt["verified_after_state"] is True
        assert len(receipt["receipt_digest"]) == 64
        assert receipt["receipt_signed"] is True
        assert receipt["receipt_signature"]["key_id"] == "stub_master_key"
        assert receipt["nonce"] == "nonce_pilot_0001"
        assert receipt["after_state"]["source"] == "INDEPENDENT_WM_GETTEXT"
        assert len(signer.signed) == 1
