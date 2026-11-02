# -*- coding: utf-8 -*-
"""
tests/test_phase3_scoped_actuator.py
[M5 Phase 3: Scoped Focus & Click Actuator Test Suite]:
Thực hiện đầy đủ 17 bài kiểm thử IR, Dispatcher & After-State Verification theo Turn 333 của OpenCode:
  1. FOCUS_IR_SCHEMA_VALIDATION
  2. FOCUS_STALE_REVALIDATION_REJECTED
  3. FOCUS_TARGET_MISMATCH_REJECTED
  4. FOCUS_ONE_SHOT_LEASE_REQUIRED
  5. CLICK_IR_SCHEMA_VALIDATION
  6. CLICK_RAW_XY_REJECTED
  7. CLICK_OUT_OF_BOUNDS_REJECTED
  8. CLICK_INVOKABLE_PATTERN_REQUIRED
  9. CLICK_DISABLED_ELEMENT_REJECTED
  10. CLICK_STALE_ELEMENT_REJECTED
  11. CLICK_PROCESS_ALLOWLIST
  12. CLICK_APPROVAL_EXPIRED
  13. CLICK_REPLAY_BLOCKED (revised: click simulated-only, real replay covered in hardening suite)
  14. CLICK_DESTRUCTIVE_TARGET_BLOCKED
  15. CLICK_NO_AUTO_RETRY (revised: simulation dispatches nothing)
  16. FOCUS_SIMULATION_HAS_NO_KEYBOARD_SIDE_EFFECT
  17. CLICK_SIMULATION_RECEIPT_IS_MARKED_SIMULATED
"""

import time
import pytest
from unittest.mock import patch, MagicMock
from services.ai_desktop.semantic_action_ir import (
    ActionType,
    ClickParams,
    FocusParams,
    ModifierKeyEnum,
    SemanticActionIR,
    SemanticActionValidator,
    compute_canonical_element_hash,
    compute_canonical_snapshot_hash
)
from services.ai_desktop.semantic_action_dispatcher import SemanticActionDispatcher, SemanticDispatchResult
from services.ai_desktop.uia_tree_inspector import UIATreeSnapshot, UIAElementNode


class TestPhase3ScopedActuatorSuite:

    @pytest.fixture(autouse=True)
    def _test_mode_env(self, monkeypatch):
        """Bật chế độ test tường minh: mutation vẫn tắt toàn cục, bypass chỉ hợp lệ khi có TEST_MODE."""
        monkeypatch.delenv("JKAI_MUTATION_ENABLED", raising=False)
        monkeypatch.setenv("JKAI_MUTATION_TEST_MODE", "1")

    @pytest.fixture
    def mock_calc_snapshot(self):
        """Giả lập snapshot của ứng dụng Calculator trong allowlist."""
        hwnd = 4444
        pid = 7777
        proc_name = "calculator.exe"
        nodes = [
            UIAElementNode(
                name="Clear",
                control_type="Button",
                automation_id="clearButton",
                class_name="Button",
                rect=(10, 10, 60, 50),
                center=(35, 30),
                hwnd=hwnd,
                supported_patterns=["InvokePattern"],
                ref="e1"
            ),
            UIAElementNode(
                name="Five",
                control_type="Button",
                automation_id="num5Button",
                class_name="Button",
                rect=(10, 60, 60, 100),
                center=(35, 80),
                hwnd=hwnd,
                supported_patterns=["InvokePattern"],
                ref="e2"
            ),
            UIAElementNode(
                name="Delete File",
                control_type="Button",
                automation_id="deleteButton",
                class_name="Button",
                rect=(10, 110, 60, 150),
                center=(35, 130),
                hwnd=hwnd,
                supported_patterns=["InvokePattern"],
                ref="e3"
            ),
            UIAElementNode(
                name="Disabled Button",
                control_type="Button",
                automation_id="disabledBtn",
                class_name="Button",
                rect=(10, 160, 60, 200),
                center=(35, 180),
                hwnd=hwnd,
                is_enabled=False,
                supported_patterns=["InvokePattern"],
                ref="e4"
            ),
            UIAElementNode(
                name="Static Label",
                control_type="Text",
                automation_id="labelArea",
                class_name="Static",
                rect=(10, 210, 60, 250),
                center=(35, 230),
                hwnd=hwnd,
                supported_patterns=[],
                ref="e5"
            ),
        ]
        snap_hash = compute_canonical_snapshot_hash(hwnd=hwnd, pid=pid, process_name=proc_name, elements=nodes)
        ref_map = {n.ref: n for n in nodes}
        return UIATreeSnapshot(
            hwnd=hwnd,
            window_title="Calculator",
            process_name=proc_name,
            pid=pid,
            element_count=len(nodes),
            snapshot_hash=snap_hash,
            elements=nodes,
            ref_map=ref_map,
            captured_at=time.time(),
            expires_at=time.time() + 30.0,
        )

    def _make_action(self, snapshot, ref="e2", action_type=ActionType.CLICK, params=None, issued_at=None, expires_at=None):
        now = time.time()
        el = snapshot.ref_map[ref]
        p = params
        if p is None:
            if action_type == ActionType.CLICK:
                p = ClickParams(button="left", prefer_invoke_pattern=True)
            elif action_type == ActionType.FOCUS:
                p = FocusParams()

        return SemanticActionIR(
            session_id="ses_phase3_test",
            lease_id="lease_phase3_001",
            nonce="nonce_phase3_12345678",
            issued_at=now if issued_at is None else issued_at,
            expires_at=now + 60.0 if expires_at is None else expires_at,
            approval_digest="sha256_1111222233334444555566667777888811112222333344445555666677778888",
            action_type=action_type,
            target_ref=ref,
            target_hwnd=snapshot.hwnd,
            target_pid=snapshot.pid,
            target_process_name=snapshot.process_name,
            element_hash=el.element_hash,
            snapshot_hash=snapshot.snapshot_hash,
            parameters=p,
            description="Phase 3 Scoped Test Action"
        )

    def test_focus_ir_schema_validation(self, mock_calc_snapshot):
        """FOCUS_IR_SCHEMA_VALIDATION: Schema của FocusElementAction hợp lệ và đầy đủ metadata."""
        action = self._make_action(mock_calc_snapshot, ref="e2", action_type=ActionType.FOCUS)
        ok, reason = action.validate_self_schema()
        assert ok is True
        assert reason == "ACTION_SCHEMA_VALID"

    def test_focus_stale_revalidation_rejected(self, mock_calc_snapshot):
        """FOCUS_STALE_REVALIDATION_REJECTED: Focus trên snapshot có hash sai lệch bị từ chối chống TOCTOU."""
        action = self._make_action(mock_calc_snapshot, ref="e2", action_type=ActionType.FOCUS)
        action.snapshot_hash = "sha256_0000000000000000000000000000000000000000000000000000000000000000"
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, mock_calc_snapshot)
        assert ok is False
        assert "SNAPSHOT_HASH_DRIFT" in reason

    def test_focus_target_mismatch_rejected(self, mock_calc_snapshot):
        """FOCUS_TARGET_MISMATCH_REJECTED: HWND hoặc PID không khớp bị từ chối fail-closed."""
        action = self._make_action(mock_calc_snapshot, ref="e2", action_type=ActionType.FOCUS)
        action.target_hwnd = 9999
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, mock_calc_snapshot)
        assert ok is False
        assert "TARGET_HWND_MISMATCH" in reason

    def test_focus_one_shot_lease_required(self, mock_calc_snapshot):
        """FOCUS_ONE_SHOT_LEASE_REQUIRED: Thiếu lease_id hoặc approval digest bị từ chối ngay ở schema."""
        action = self._make_action(mock_calc_snapshot, ref="e2", action_type=ActionType.FOCUS)
        action.lease_id = ""
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "INVALID_LEASE_ID_FORMAT" in reason

    def test_click_ir_schema_validation(self, mock_calc_snapshot):
        """CLICK_IR_SCHEMA_VALIDATION: Schema của ClickElementAction hợp lệ với Modifier enum."""
        action = self._make_action(mock_calc_snapshot, ref="e2", action_type=ActionType.CLICK)
        ok, reason = action.validate_self_schema()
        assert ok is True
        assert reason == "ACTION_SCHEMA_VALID"

    def test_click_raw_xy_rejected(self, mock_calc_snapshot):
        """CLICK_RAW_XY_REJECTED: Raw (x, y) không có target_ref canonical bị từ chối tuyệt đối."""
        action = self._make_action(mock_calc_snapshot, ref="e2", action_type=ActionType.CLICK)
        action.target_ref = "raw_100_200"
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "INVALID_REF_FORMAT" in reason

    def test_click_out_of_bounds_rejected(self, mock_calc_snapshot):
        """CLICK_OUT_OF_BOUNDS_REJECTED: Toạ độ target_x, target_y nằm ngoài BoundingBox bị từ chối."""
        # e2 rect là (10, 60, 60, 100); bounds luôn được kiểm tra, không có chế độ bỏ qua
        params = ClickParams(button="left", target_x=500, target_y=500)
        action = self._make_action(mock_calc_snapshot, ref="e2", action_type=ActionType.CLICK, params=params)
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, mock_calc_snapshot)
        assert ok is False
        assert "CLICK_OUT_OF_BOUNDS_REJECTED" in reason

    def test_click_invokable_pattern_required(self, mock_calc_snapshot):
        """CLICK_INVOKABLE_PATTERN_REQUIRED: Phần tử tĩnh (Static Label) không có pattern click bị từ chối."""
        action = self._make_action(mock_calc_snapshot, ref="e5", action_type=ActionType.CLICK)
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, mock_calc_snapshot)
        assert ok is False
        assert "CLICK_INVOKABLE_PATTERN_REQUIRED" in reason

    def test_click_disabled_element_rejected(self, mock_calc_snapshot):
        """CLICK_DISABLED_ELEMENT_REJECTED: Phần tử disabled bị từ chối fail-closed."""
        action = self._make_action(mock_calc_snapshot, ref="e4", action_type=ActionType.CLICK)
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, mock_calc_snapshot)
        assert ok is False
        assert "ELEMENT_DISABLED" in reason

    def test_click_stale_element_rejected(self, mock_calc_snapshot):
        """CLICK_STALE_ELEMENT_REJECTED: element_hash không khớp với live element bị từ chối."""
        action = self._make_action(mock_calc_snapshot, ref="e2", action_type=ActionType.CLICK)
        action.element_hash = "0" * 64
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, mock_calc_snapshot)
        assert ok is False
        assert "STALE_ELEMENT_HASH" in reason

    def test_click_process_allowlist(self, mock_calc_snapshot):
        """CLICK_PROCESS_ALLOWLIST: Thao tác trên tiến trình ngoài allowlist bị từ chối."""
        action = self._make_action(mock_calc_snapshot, ref="e2", action_type=ActionType.CLICK)
        action.target_process_name = "explorer.exe"
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, mock_calc_snapshot)
        assert ok is False
        assert "PROCESS_NOT_IN_ALLOWLIST" in reason

    def test_click_approval_expired(self, mock_calc_snapshot):
        """CLICK_APPROVAL_EXPIRED: Action có expires_at trong quá khứ bị từ chối ngay lập tức."""
        past_time = time.time() - 10.0
        action = self._make_action(mock_calc_snapshot, ref="e2", action_type=ActionType.CLICK, issued_at=past_time - 5.0, expires_at=past_time)
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "ACTION_EXPIRED" in reason

    def test_click_replay_blocked(self, mock_calc_snapshot):
        """
        CLICK_REPLAY_BLOCKED: Click trong Phase 3 chỉ được MÔ PHỎNG; không bao giờ chạm Win32
        nên không thể replay thành mutation thật. Chống replay thật (nonce) được kiểm chứng
        trong tests/test_desktop_control_hardening.py::test_replay_nonce_detected.
        """
        dispatcher = SemanticActionDispatcher(dry_run=False, inspector=MagicMock())
        action = self._make_action(mock_calc_snapshot, ref="e2", action_type=ActionType.CLICK)

        with patch("win32gui.SendMessage") as send_message:
            res1 = dispatcher.dispatch_action(action, live_snapshot_override=mock_calc_snapshot, bypass_env_for_test=True)
            res2 = dispatcher.dispatch_action(action, live_snapshot_override=mock_calc_snapshot, bypass_env_for_test=True)

        assert res1.success is True
        assert res2.success is True
        assert res1.status == "DRY_RUN_SIMULATED"
        assert res2.status == "DRY_RUN_SIMULATED"
        assert res1.execution_receipt["simulated"] is True
        assert res1.execution_receipt["verified_after_state"] is False
        send_message.assert_not_called()

    def test_click_destructive_target_blocked(self, mock_calc_snapshot):
        """CLICK_DESTRUCTIVE_TARGET_BLOCKED: Nút có ngữ nghĩa phá hoại (Delete File) bị chặn đứng tuyệt đối."""
        action = self._make_action(mock_calc_snapshot, ref="e3", action_type=ActionType.CLICK)
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, mock_calc_snapshot)
        assert ok is False
        assert "CLICK_DESTRUCTIVE_TARGET_BLOCKED" in reason

    def test_click_no_auto_retry(self, mock_calc_snapshot):
        """
        CLICK_NO_AUTO_RETRY: Click mô phỏng không phát lệnh nào, kể cả khi Win32 sẽ ném lỗi.
        Không tồn tại retry ẩn. (No-auto-retry cho TYPE_TEXT thật nằm trong
        tests/test_desktop_control_hardening.py::test_sendmessage_failure_is_single_attempt.)
        """
        dispatcher = SemanticActionDispatcher(dry_run=False, inspector=MagicMock())
        action = self._make_action(mock_calc_snapshot, ref="e2", action_type=ActionType.CLICK)

        with patch("win32gui.SendMessage", side_effect=Exception("WIN32_RPC_ERROR")) as send_message:
            res = dispatcher.dispatch_action(action, live_snapshot_override=mock_calc_snapshot, bypass_env_for_test=True)

        assert res.success is True
        assert res.status == "DRY_RUN_SIMULATED"
        send_message.assert_not_called()

    def test_focus_simulation_has_no_keyboard_side_effect(self, mock_calc_snapshot):
        """
        FOCUS_AFTER_STATE_HAS_KEYBOARD_FOCUS (revised under R1): Focus chỉ được mô phỏng,
        không gọi SetForegroundWindow và không tuyên bố after-state đã được thẩm định.
        """
        dispatcher = SemanticActionDispatcher(dry_run=False, inspector=MagicMock())
        action = self._make_action(mock_calc_snapshot, ref="e2", action_type=ActionType.FOCUS)

        with patch("win32gui.SetForegroundWindow") as set_foreground, \
             patch("win32gui.SendMessage") as send_message:
            res = dispatcher.dispatch_action(action, live_snapshot_override=mock_calc_snapshot, bypass_env_for_test=True)

        assert res.success is True
        assert res.status == "DRY_RUN_SIMULATED"
        assert res.execution_receipt is not None
        assert res.execution_receipt["simulated"] is True
        assert res.execution_receipt["verified_after_state"] is False
        assert "has_keyboard_focus" not in res.execution_receipt
        set_foreground.assert_not_called()
        send_message.assert_not_called()

    def test_click_after_state_action_evidence(self, mock_calc_snapshot):
        """
        CLICK_AFTER_STATE_ACTION_EVIDENCE (revised under R1): Receipt của click mô phỏng
        ghi rõ simulated=True và verified_after_state=False; không được giả PASS.
        """
        dispatcher = SemanticActionDispatcher(dry_run=False, inspector=MagicMock())
        action = self._make_action(mock_calc_snapshot, ref="e2", action_type=ActionType.CLICK)

        with patch("win32gui.SendMessage") as send_message:
            res = dispatcher.dispatch_action(action, live_snapshot_override=mock_calc_snapshot, bypass_env_for_test=True)

        assert res.success is True
        assert res.status == "DRY_RUN_SIMULATED"
        assert res.execution_receipt is not None
        assert res.execution_receipt["action_type"] == "click"
        assert res.execution_receipt["simulated"] is True
        assert res.execution_receipt["verified_after_state"] is False
        send_message.assert_not_called()
