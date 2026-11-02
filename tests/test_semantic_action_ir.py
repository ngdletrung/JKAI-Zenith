# -*- coding: utf-8 -*-
"""
Exhaustive unit tests for JKAI Typed Action IR Schema & Anti-TOCTOU Validator (M5 Phase 2)
Kiểm thử toàn diện 100% các khuyến nghị an ninh và edge case từ LƯỢT 303 của OpenCode:
  1. Finding 1: Ref format canonical strictly 'eN' (reject @ref:e1, @e1, ref_1).
  2. Finding 2: KeyComboParams type safety (reject bool, int, unauthorized strings).
  3. Finding 3: Numeric type safety (type(x) is int, reject bool as int, bounded max_length).
  4. Finding 4: Allowlist empty set safe (allowed_processes=set() denies all).
  5. Finding 5: ActionType / Parameter Class 1-1 pairing (reject ACTION_PARAMETER_MISMATCH).
  6. Finding 6: Full 64-hex SHA-256 collision resistance (len == 64).
  7. Finding 7: Clock-skew (reject issued_at > now + 5.0s) & strict TTL bounds (<= 300.0s).
  8. Finding 8: Process identity and snapshot binding checks.
"""

import time
import pytest
from services.ai_desktop.semantic_action_ir import (
    ActionType,
    StandardKeyEnum,
    ClickParams,
    TypeTextParams,
    KeyComboParams,
    ScrollParams,
    SemanticActionIR,
    SemanticActionValidator,
    compute_canonical_element_hash,
    compute_canonical_snapshot_hash,
)
from services.ai_desktop.uia_tree_inspector import UIATreeInspector, UIATreeSnapshot, UIAElementNode


class TestSemanticActionIR:
    @pytest.fixture
    def inspector(self):
        return UIATreeInspector(is_live_mode=False)

    @pytest.fixture
    def snapshot(self, inspector):
        return inspector.inspect_tree(hwnd=1234)

    def _make_valid_action(
        self,
        snapshot: UIATreeSnapshot,
        ref: str = "e1",
        action_type: ActionType = ActionType.CLICK,
        parameters=None
    ) -> SemanticActionIR:
        el = snapshot.ref_map[ref]
        params = parameters or ClickParams(button="left", prefer_invoke_pattern=True)
        now = time.time()
        return SemanticActionIR(
            session_id="test_session_001",
            lease_id="lease_test_001",
            nonce="nonce_abc123",
            issued_at=now,
            expires_at=now + 60.0,
            approval_digest="sha256_" + "a" * 64,
            action_type=action_type,
            target_ref=ref,
            target_hwnd=snapshot.hwnd,
            target_pid=snapshot.pid,
            target_process_name=snapshot.process_name,
            element_hash=el.element_hash,
            snapshot_hash=snapshot.snapshot_hash,
            parameters=params,
            description="Test automated semantic action"
        )

    # ── Test Finding 1: Strict Canonical Ref ─────────────────────────────

    def test_strict_canonical_ref_format_enforcement(self, snapshot):
        """target_ref phải strictly là canonical 'eN' (e1, e2...), cấm hoàn toàn normalize lỏng lẻo."""
        # 1. Hợp lệ
        action_ok = self._make_valid_action(snapshot, ref="e1")
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action_ok, snapshot)
        assert ok is True
        assert reason == "ACTION_VALIDATED_READY_FOR_GATED_EXECUTION"

        # 2. Các biến thể chứa tiền tố @ref:, @, hoặc sai định dạng đều phải bị reject
        invalid_refs = ["@ref:e1", "@e1", "ref_01", "btn_close", "e0", "-e1", "e", "E1", "e 1"]
        for bad_ref in invalid_refs:
            action_bad = self._make_valid_action(snapshot, ref="e1")
            action_bad.target_ref = bad_ref
            ok_bad, reason_bad, _ = SemanticActionValidator.validate_action_against_snapshot(action_bad, snapshot)
            assert ok_bad is False, f"Ref {bad_ref!r} should have been rejected"
            assert "INVALID_REF_FORMAT" in reason_bad

    # ── Test Finding 2: Strict KeyCombo Types ────────────────────────────

    def test_key_combo_strict_types_and_unauthorized_rejection(self, snapshot):
        """KeyComboParams phải reject bool, int, kiểu dữ liệu lạ và phím ngoài enum."""
        # 1. Enum hợp lệ
        valid_params = KeyComboParams(keys=[StandardKeyEnum.CTRL, StandardKeyEnum.S])
        assert valid_params.validate()[0] is True

        # 2. String hợp lệ (khớp value của enum)
        valid_str_params = KeyComboParams(keys=["ctrl", "s"])
        assert valid_str_params.validate()[0] is True

        # 3. Reject bool (True/False)
        bad_bool_params = KeyComboParams(keys=[True, "s"])
        ok, reason = bad_bool_params.validate()
        assert ok is False
        assert "INVALID_KEY_TYPE: bool" in reason

        # 4. Reject int (123)
        bad_int_params = KeyComboParams(keys=[123])
        ok, reason = bad_int_params.validate()
        assert ok is False
        assert "INVALID_KEY_TYPE: int" in reason

        # 5. Reject phím lạ
        bad_key_params = KeyComboParams(keys=["DangerousKey"])
        ok, reason = bad_key_params.validate()
        assert ok is False
        assert "UNAUTHORIZED_KEY" in reason

    # ── Test Finding 3: Numeric Type Safety (Reject bool as int) ─────────

    def test_numeric_type_safety_rejects_bool(self, snapshot):
        """Bảo đảm type(x) is int: bool (subclass của int) không được lọt qua."""
        # 1. ClickParams: click_count = True
        bad_click = ClickParams(button="left", click_count=True)
        ok, reason = bad_click.validate()
        assert ok is False
        assert "INVALID_CLICK_COUNT" in reason

        # 2. ScrollParams: delta = True
        bad_scroll = ScrollParams(delta=True)
        ok, reason = bad_scroll.validate()
        assert ok is False
        assert "DELTA_MUST_BE_INT" in reason

        # 3. TypeTextParams: max_length âm hoặc bool
        bad_type1 = TypeTextParams(text="hello", max_length=True)
        assert bad_type1.validate()[0] is False

        bad_type2 = TypeTextParams(text="hello", max_length=-10)
        assert bad_type2.validate()[0] is False

        bad_type3 = TypeTextParams(text="hello", max_length=999999)  # quá 5000
        assert bad_type3.validate()[0] is False

    # ── Test Finding 4: Allowlist Empty Set Safe ─────────────────────────

    def test_allowlist_empty_set_denies_all(self, snapshot):
        """Caller truyền allowed_processes=set() phải deny-all, không bị fallback về default."""
        action = self._make_valid_action(snapshot, ref="e1")
        # Truyền set() rỗng
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(
            action, snapshot, allowed_processes=set()
        )
        assert ok is False
        assert "PROCESS_NOT_IN_ALLOWLIST" in reason

        # Truyền None -> dùng default (chứa notepad.exe -> pass)
        ok_def, _, _ = SemanticActionValidator.validate_action_against_snapshot(
            action, snapshot, allowed_processes=None
        )
        assert ok_def is True

    # ── Test Finding 5: Action Type / Parameter Pairing ──────────────────

    def test_action_parameter_pairing_enforced(self, snapshot):
        """ActionType.CLICK đi kèm TypeTextParams phải bị từ chối với ACTION_PARAMETER_MISMATCH."""
        # 1. CLICK nhưng truyền TypeTextParams
        bad_pair1 = self._make_valid_action(
            snapshot, ref="e1", action_type=ActionType.CLICK,
            parameters=TypeTextParams(text="illegal")
        )
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(bad_pair1, snapshot)
        assert ok is False
        assert "ACTION_PARAMETER_MISMATCH" in reason

        # 2. TYPE_TEXT nhưng truyền ClickParams
        bad_pair2 = self._make_valid_action(
            snapshot, ref="e3", action_type=ActionType.TYPE_TEXT,
            parameters=ClickParams()
        )
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(bad_pair2, snapshot)
        assert ok is False
        assert "ACTION_PARAMETER_MISMATCH" in reason

        # 3. SCROLL nhưng truyền KeyComboParams
        bad_pair3 = self._make_valid_action(
            snapshot, ref="e3", action_type=ActionType.SCROLL,
            parameters=KeyComboParams(keys=[StandardKeyEnum.CTRL])
        )
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(bad_pair3, snapshot)
        assert ok is False
        assert "ACTION_PARAMETER_MISMATCH" in reason

    # ── Test Finding 6: Full 64-Hex SHA-256 ──────────────────────────────

    def test_full_64_hex_sha256_hashes(self, snapshot):
        """Mã băm element_hash và snapshot_hash phải bảo đảm toàn phần 64 ký tự hex."""
        el = snapshot.ref_map["e1"]
        # Element hash: 64 hex chars
        assert len(el.element_hash) == 64
        int(el.element_hash, 16)  # hợp lệ hex

        # Snapshot hash: "sha256_" + 64 hex chars
        assert snapshot.snapshot_hash.startswith("sha256_")
        raw_snap_hex = snapshot.snapshot_hash.replace("sha256_", "")
        assert len(raw_snap_hex) == 64
        int(raw_snap_hex, 16)

    # ── Test Finding 7: Clock-Skew & Max TTL Bounds ──────────────────────

    def test_future_issued_clock_skew_rejected(self, snapshot):
        """issued_at nằm trong tương lai quá 5.0s phải bị từ chối."""
        action = self._make_valid_action(snapshot, ref="e1")
        action.issued_at = time.time() + 10.0  # 10s trong tương lai
        action.expires_at = action.issued_at + 60.0
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, snapshot)

        assert ok is False
        assert "ACTION_ISSUED_IN_FUTURE" in reason

    def test_ttl_exceeds_max_300s_rejected(self, snapshot):
        """TTL (expires_at - issued_at) vượt quá 300.0s phải bị từ chối."""
        action = self._make_valid_action(snapshot, ref="e1")
        action.expires_at = action.issued_at + 305.0  # 305s > 300s
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, snapshot)

        assert ok is False
        assert "TTL_EXCEEDS_MAX_300S" in reason

    def test_expired_action_rejected(self, snapshot):
        """Hành động đã hết hạn (now > expires_at) phải bị từ chối."""
        action = self._make_valid_action(snapshot, ref="e1")
        action.issued_at = time.time() - 100.0
        action.expires_at = time.time() - 10.0
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, snapshot)

        assert ok is False
        assert "ACTION_EXPIRED" in reason

    # ── Test Finding 8: Process & State Integrity ────────────────────────

    def test_target_hwnd_mismatch_rejected(self, snapshot):
        """target_hwnd lệch phải bị từ chối."""
        action = self._make_valid_action(snapshot, ref="e1")
        action.target_hwnd = 999999
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, snapshot)
        assert ok is False
        assert "TARGET_HWND_MISMATCH" in reason

    def test_target_pid_mismatch_rejected(self, snapshot):
        """target_pid lệch phải bị từ chối."""
        action = self._make_valid_action(snapshot, ref="e1")
        action.target_pid = 99999
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, snapshot)
        assert ok is False
        assert "TARGET_PID_MISMATCH" in reason

    def test_snapshot_hash_drift_rejected(self, snapshot):
        """snapshot_hash lệch (UI drift) phải bị từ chối."""
        action = self._make_valid_action(snapshot, ref="e1")
        action.snapshot_hash = "sha256_" + "0" * 64
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, snapshot)
        assert ok is False
        assert "SNAPSHOT_HASH_DRIFT" in reason

    def test_stale_element_hash_rejected(self, snapshot):
        """element_hash lệch (phần tử bị sửa đổi thuộc tính) phải bị từ chối."""
        action = self._make_valid_action(snapshot, ref="e1")
        action.element_hash = "0" * 64
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, snapshot)
        assert ok is False
        assert "STALE_ELEMENT_HASH" in reason

    def test_disabled_or_invisible_element_rejected(self, snapshot):
        """Phần tử bị vô hiệu hóa hoặc vô hình phải bị từ chối."""
        snapshot.ref_map["e1"].is_enabled = False
        action = self._make_valid_action(snapshot, ref="e1")
        ok1, reason1, _ = SemanticActionValidator.validate_action_against_snapshot(action, snapshot)
        assert ok1 is False
        assert "ELEMENT_DISABLED" in reason1

        snapshot.ref_map["e1"].is_enabled = True
        snapshot.ref_map["e1"].is_visible = False
        ok2, reason2, _ = SemanticActionValidator.validate_action_against_snapshot(action, snapshot)
        assert ok2 is False
        assert "ELEMENT_NOT_VISIBLE" in reason2

    def test_type_text_control_characters_rejected(self, snapshot):
        """TypeText chứa ký tự điều khiển trái phép phải bị từ chối."""
        bad_text_params = TypeTextParams(text="Text with \x00 null byte")
        action = self._make_valid_action(
            snapshot, ref="e3", action_type=ActionType.TYPE_TEXT,
            parameters=bad_text_params
        )
        ok, reason, _ = SemanticActionValidator.validate_action_against_snapshot(action, snapshot)
        assert ok is False
        assert "CONTROL_CHARACTER_REJECTED" in reason

    # ── Test Findings Lượt 305: Hardening & Edge Cases ──────────────────

    def test_finite_numeric_timestamps_reject_nan_and_inf(self, snapshot):
        """Timestamp chứa NaN, +Inf, -Inf phải bị từ chối hoàn toàn (Finding 5 Lượt 305)."""
        action = self._make_valid_action(snapshot, ref="e1")

        # 1. issued_at = NaN
        action.issued_at = float("nan")
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "ISSUED_AT_MUST_BE_FINITE_NUMERIC" in reason

        # 2. issued_at = +Inf
        action.issued_at = float("inf")
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "ISSUED_AT_MUST_BE_FINITE_NUMERIC" in reason

        # 3. expires_at = NaN
        action.issued_at = time.time()
        action.expires_at = float("nan")
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "EXPIRES_AT_MUST_BE_FINITE_NUMERIC" in reason

        # 4. expires_at = -Inf
        action.expires_at = float("-inf")
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "EXPIRES_AT_MUST_BE_FINITE_NUMERIC" in reason

    def test_key_combo_max_keys_bounded_and_type_safe(self):
        """max_keys phải là int trong khoảng [1, 10] và từ chối bool (Finding 2 Lượt 305)."""
        # Hợp lệ
        p_ok = KeyComboParams(keys=[StandardKeyEnum.CTRL, StandardKeyEnum.A], max_keys=5)
        assert p_ok.validate()[0] is True

        # max_keys = 0
        p_zero = KeyComboParams(keys=[StandardKeyEnum.CTRL], max_keys=0)
        ok, reason = p_zero.validate()
        assert ok is False
        assert "INVALID_MAX_KEYS" in reason

        # max_keys = 11 (vượt quá 10)
        p_too_big = KeyComboParams(keys=[StandardKeyEnum.CTRL], max_keys=11)
        ok, reason = p_too_big.validate()
        assert ok is False
        assert "INVALID_MAX_KEYS" in reason

        # max_keys = True (bool)
        p_bool = KeyComboParams(keys=[StandardKeyEnum.CTRL], max_keys=True)
        ok, reason = p_bool.validate()
        assert ok is False
        assert "INVALID_MAX_KEYS" in reason

    def test_scroll_max_delta_bounded_and_type_safe(self):
        """max_delta phải là int trong khoảng [1, 10000] và từ chối bool (Finding 2 Lượt 305)."""
        # Hợp lệ
        p_ok = ScrollParams(delta=120, max_delta=5000)
        assert p_ok.validate()[0] is True

        # max_delta = 0
        p_zero = ScrollParams(delta=120, max_delta=0)
        ok, reason = p_zero.validate()
        assert ok is False
        assert "INVALID_MAX_DELTA" in reason

        # max_delta = 10001 (vượt quá 10000)
        p_too_big = ScrollParams(delta=120, max_delta=10001)
        ok, reason = p_too_big.validate()
        assert ok is False
        assert "INVALID_MAX_DELTA" in reason

        # max_delta = True (bool)
        p_bool = ScrollParams(delta=120, max_delta=True)
        ok, reason = p_bool.validate()
        assert ok is False
        assert "INVALID_MAX_DELTA" in reason

    def test_target_identity_types_strictly_enforced(self, snapshot):
        """target_hwnd, target_pid phải là positive int (từ chối bool, <=0), target_process_name non-empty str (Finding 3 Lượt 305)."""
        action = self._make_valid_action(snapshot, ref="e1")

        # target_hwnd = True (bool)
        action.target_hwnd = True
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "INVALID_TARGET_HWND" in reason

        # target_hwnd = 0
        action.target_hwnd = 0
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "INVALID_TARGET_HWND" in reason

        # target_hwnd = -10
        action.target_hwnd = -10
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "INVALID_TARGET_HWND" in reason

        # target_pid = True (bool)
        action.target_hwnd = snapshot.hwnd
        action.target_pid = True
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "INVALID_TARGET_PID" in reason

        # target_pid = 0
        action.target_pid = 0
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "INVALID_TARGET_PID" in reason

        # target_process_name rỗng hoặc chỉ khoảng trắng
        action.target_pid = snapshot.pid
        action.target_process_name = "   "
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "TARGET_PROCESS_NAME_MUST_BE_NON_EMPTY_STR" in reason

    def test_structured_field_patterns_enforced(self, snapshot):
        """session_id, lease_id, nonce, element_hash, snapshot_hash, approval_digest regex checks (Findings 6, 7 Lượt 305)."""
        action = self._make_valid_action(snapshot, ref="e1")

        # 1. session_id sai regex (chứa ký tự lạ)
        action.session_id = "bad$sess!"
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "INVALID_SESSION_ID_FORMAT" in reason

        # 2. lease_id quá ngắn
        action.session_id = "test_session_001"
        action.lease_id = "short"
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "INVALID_LEASE_ID_FORMAT" in reason

        # 3. nonce chứa ký tự cấm
        action.lease_id = "lease_test_001"
        action.nonce = "nonce#1234"
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "INVALID_NONCE_FORMAT" in reason

        # 4. element_hash không đủ 64 hex
        action.nonce = "nonce_abc123"
        action.element_hash = "deadbeef"  # 8 hex
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "INVALID_ELEMENT_HASH_FORMAT" in reason

        # 5. snapshot_hash thiếu tiền tố 'sha256_'
        action.element_hash = snapshot.ref_map["e1"].element_hash
        action.snapshot_hash = "b" * 64
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "INVALID_SNAPSHOT_HASH_FORMAT" in reason

    def test_action_type_enum_instance_enforced(self, snapshot):
        """action_type phải là ActionType enum instance, reject raw string hoặc giá trị ngoài enum (Finding 4 Lượt 305)."""
        action = self._make_valid_action(snapshot, ref="e1")

        # Truyền raw string thay vì ActionType enum
        action.action_type = "click"
        ok, reason = action.validate_self_schema()
        assert ok is False
        assert "INVALID_ACTION_TYPE" in reason

    def test_from_wire_dict_parsing_and_rejections(self, snapshot):
        """from_wire_dict phân tích cú pháp chính xác, an toàn cho cả 4 loại action và reject dữ liệu sai (Finding 4 Lượt 305)."""
        now = time.time()
        base_wire = {
            "session_id": "test_session_001",
            "lease_id": "lease_test_001",
            "nonce": "nonce_abc123",
            "issued_at": now,
            "expires_at": now + 60.0,
            "approval_digest": "sha256_" + "a" * 64,
            "action_type": "click",
            "target_ref": "e1",
            "target_hwnd": snapshot.hwnd,
            "target_pid": snapshot.pid,
            "target_process_name": snapshot.process_name,
            "element_hash": snapshot.ref_map["e1"].element_hash,
            "snapshot_hash": snapshot.snapshot_hash,
            "parameters": {"button": "left", "click_count": 1, "prefer_invoke_pattern": True},
            "description": "Wire test click"
        }

        # 1. Parse click hợp lệ
        parsed_click = SemanticActionIR.from_wire_dict(base_wire)
        assert parsed_click.action_type == ActionType.CLICK
        assert isinstance(parsed_click.parameters, ClickParams)
        assert parsed_click.parameters.button == "left"

        # 2. Parse type_text hợp lệ
        text_wire = dict(base_wire)
        text_wire["action_type"] = "type_text"
        text_wire["target_ref"] = "e3"
        text_wire["element_hash"] = snapshot.ref_map["e3"].element_hash
        text_wire["parameters"] = {"text": "hello", "max_length": 500, "clear_before_type": True, "prefer_value_pattern": True}
        parsed_text = SemanticActionIR.from_wire_dict(text_wire)
        assert parsed_text.action_type == ActionType.TYPE_TEXT
        assert isinstance(parsed_text.parameters, TypeTextParams)
        assert parsed_text.parameters.text == "hello"

        # 3. Parse key_combo hợp lệ
        combo_wire = dict(base_wire)
        combo_wire["action_type"] = "key_combo"
        combo_wire["parameters"] = {"keys": ["ctrl", "s"], "max_keys": 4}
        parsed_combo = SemanticActionIR.from_wire_dict(combo_wire)
        assert parsed_combo.action_type == ActionType.KEY_COMBO
        assert isinstance(parsed_combo.parameters, KeyComboParams)
        assert parsed_combo.parameters.keys == ["ctrl", "s"]

        # 4. Parse scroll hợp lệ
        scroll_wire = dict(base_wire)
        scroll_wire["action_type"] = "scroll"
        scroll_wire["parameters"] = {"direction": "down", "delta": 120, "max_delta": 5000}
        parsed_scroll = SemanticActionIR.from_wire_dict(scroll_wire)
        assert parsed_scroll.action_type == ActionType.SCROLL
        assert isinstance(parsed_scroll.parameters, ScrollParams)
        assert parsed_scroll.parameters.delta == 120

        # 5. Reject nếu wire không phải dict
        with pytest.raises(ValueError, match="WIRE_DATA_MUST_BE_DICT"):
            SemanticActionIR.from_wire_dict("not_a_dict")

        # 6. Reject nếu action_type không hợp lệ
        bad_type_wire = dict(base_wire)
        bad_type_wire["action_type"] = "nuke_system"
        with pytest.raises(ValueError, match="UNRECOGNIZED_ACTION_TYPE"):
            SemanticActionIR.from_wire_dict(bad_type_wire)

        # 7. Reject nếu parameters không phải dict
        bad_params_wire = dict(base_wire)
        bad_params_wire["parameters"] = "invalid_string_params"
        with pytest.raises(ValueError, match="PARAMETERS_MUST_BE_DICT"):
            SemanticActionIR.from_wire_dict(bad_params_wire)

        # 8. Reject nếu schema validation fail (ví dụ target_ref sai định dạng)
        bad_schema_wire = dict(base_wire)
        bad_schema_wire["target_ref"] = "@ref:e1"
        with pytest.raises(ValueError, match="ACTION_SCHEMA_VALIDATION_FAILED"):
            SemanticActionIR.from_wire_dict(bad_schema_wire)

        # 9. Reject nếu có trường lạ ở root dictionary (Lượt 307 finding)
        bad_unknown_root = dict(base_wire)
        bad_unknown_root["injected_root_field"] = "malicious"
        with pytest.raises(ValueError, match="UNKNOWN_ROOT_FIELDS"):
            SemanticActionIR.from_wire_dict(bad_unknown_root)

        # 10. Reject nếu thiếu trường bắt buộc ở root dictionary (Lượt 307 finding)
        bad_missing_root = dict(base_wire)
        del bad_missing_root["element_hash"]
        with pytest.raises(ValueError, match="MISSING_ROOT_FIELDS"):
            SemanticActionIR.from_wire_dict(bad_missing_root)

        # 11. Reject nếu có trường lạ trong parameters (Lượt 307 finding)
        bad_unknown_param = dict(base_wire)
        bad_unknown_param["parameters"] = {"button": "left", "click_count": 1, "injected_param": True}
        with pytest.raises(ValueError, match="UNKNOWN_PARAM_FIELDS"):
            SemanticActionIR.from_wire_dict(bad_unknown_param)

        # 12. Reject bool cho target_hwnd ở wire boundary (Lượt 307 finding)
        bad_hwnd_wire = dict(base_wire)
        bad_hwnd_wire["target_hwnd"] = True
        with pytest.raises(ValueError, match="FIELD_MUST_BE_INT: target_hwnd"):
            SemanticActionIR.from_wire_dict(bad_hwnd_wire)

        # 13. Reject bool cho target_pid ở wire boundary (Lượt 307 finding)
        bad_pid_wire = dict(base_wire)
        bad_pid_wire["target_pid"] = True
        with pytest.raises(ValueError, match="FIELD_MUST_BE_INT: target_pid"):
            SemanticActionIR.from_wire_dict(bad_pid_wire)

        # 14. Reject bool cho click_count trong ClickParams wire (Lượt 307 finding)
        bad_click_cnt = dict(base_wire)
        bad_click_cnt["parameters"] = {"button": "left", "click_count": True}
        with pytest.raises(ValueError, match="CLICK_COUNT_MUST_BE_INT"):
            SemanticActionIR.from_wire_dict(bad_click_cnt)

        # 15. Reject bool cho delta trong ScrollParams wire (Lượt 307 finding)
        bad_scroll_delta = dict(scroll_wire)
        bad_scroll_delta["parameters"] = {"direction": "down", "delta": True}
        with pytest.raises(ValueError, match="DELTA_MUST_BE_INT"):
            SemanticActionIR.from_wire_dict(bad_scroll_delta)

        # 16. Reject non-string cho string fields ở wire boundary (Lượt 307 finding)
        bad_str_wire = dict(base_wire)
        bad_str_wire["session_id"] = 12345
        with pytest.raises(ValueError, match="FIELD_MUST_BE_STR: session_id"):
            SemanticActionIR.from_wire_dict(bad_str_wire)

    def test_wire_parser_exact_schema_allowlists(self, snapshot):
        """Kiểm chứng toàn diện Exact Whitelist của wire parser chống parameter & root injection (Lượt 307)."""
        now = time.time()
        base_wire = {
            "session_id": "test_session_001",
            "lease_id": "lease_test_001",
            "nonce": "nonce_abc123",
            "issued_at": now,
            "expires_at": now + 60.0,
            "approval_digest": "sha256_" + "a" * 64,
            "action_type": "type_text",
            "target_ref": "e3",
            "target_hwnd": snapshot.hwnd,
            "target_pid": snapshot.pid,
            "target_process_name": snapshot.process_name,
            "element_hash": snapshot.ref_map["e3"].element_hash,
            "snapshot_hash": snapshot.snapshot_hash,
            "parameters": {"text": "hello"},
            "description": "Wire exact test"
        }

        # 1. Reject trường lạ trong TypeTextParams
        bad_type_wire = dict(base_wire)
        bad_type_wire["parameters"] = {"text": "hello", "extra_param": "forbidden"}
        with pytest.raises(ValueError, match="UNKNOWN_PARAM_FIELDS"):
            SemanticActionIR.from_wire_dict(bad_type_wire)

        # 2. Reject trường lạ trong KeyComboParams
        bad_combo_wire = dict(base_wire)
        bad_combo_wire["action_type"] = "key_combo"
        bad_combo_wire["parameters"] = {"keys": ["ctrl"], "extra_param": 123}
        with pytest.raises(ValueError, match="UNKNOWN_PARAM_FIELDS"):
            SemanticActionIR.from_wire_dict(bad_combo_wire)

        # 3. Reject trường lạ trong ScrollParams
        bad_scroll_wire = dict(base_wire)
        bad_scroll_wire["action_type"] = "scroll"
        bad_scroll_wire["parameters"] = {"direction": "up", "extra_param": 123}
        with pytest.raises(ValueError, match="UNKNOWN_PARAM_FIELDS"):
            SemanticActionIR.from_wire_dict(bad_scroll_wire)

        # 4. Reject issued_at / expires_at là bool
        bad_time_bool1 = dict(base_wire)
        bad_time_bool1["issued_at"] = True
        with pytest.raises(ValueError, match="FIELD_MUST_BE_NUMERIC: issued_at"):
            SemanticActionIR.from_wire_dict(bad_time_bool1)

        bad_time_bool2 = dict(base_wire)
        bad_time_bool2["expires_at"] = False
        with pytest.raises(ValueError, match="FIELD_MUST_BE_NUMERIC: expires_at"):
            SemanticActionIR.from_wire_dict(bad_time_bool2)

        # 5. Reject target_process_name không phải str
        bad_proc_type = dict(base_wire)
        bad_proc_type["target_process_name"] = 9999
        with pytest.raises(ValueError, match="FIELD_MUST_BE_STR: target_process_name"):
            SemanticActionIR.from_wire_dict(bad_proc_type)

        # 6. Reject raw data không phải dict (None, list, int)
        for bad_raw in [None, [1, 2, 3], 123, "string"]:
            with pytest.raises(ValueError, match="WIRE_DATA_MUST_BE_DICT"):
                SemanticActionIR.from_wire_dict(bad_raw)

    def test_live_pre_dispatch_revalidation_boundary(self, snapshot):
        """Kiểm chứng ranh giới Live Pre-Dispatch Target Identity Revalidation chống blind dispatch (Lượt 311)."""
        action = self._make_valid_action(snapshot, ref="e1")

        # 1. Revalidation hợp lệ khi mọi điều kiện live khớp
        ok, reason, details = SemanticActionValidator.revalidate_target_identity(action, snapshot)
        assert ok is True
        assert reason == "ACTION_VALIDATED_READY_FOR_GATED_EXECUTION"
        assert details["target_element_name"] == snapshot.ref_map["e1"].name

        # 2. Revalidation từ chối nếu action hết hạn trước thời điểm dispatch
        action_expired = self._make_valid_action(snapshot, ref="e1")
        action_expired.expires_at = time.time() - 1.0  # Hết hạn 1s trước
        ok_exp, reason_exp, _ = SemanticActionValidator.revalidate_target_identity(action_expired, snapshot)
        assert ok_exp is False
        assert "ACTION_EXPIRED" in reason_exp

        # 3. Revalidation từ chối nếu live HWND thay đổi (cửa sổ bị tái tạo)
        import copy
        live_drifted_hwnd = copy.deepcopy(snapshot)
        live_drifted_hwnd.hwnd = 999999
        ok_hwnd, reason_hwnd, _ = SemanticActionValidator.revalidate_target_identity(action, live_drifted_hwnd)
        assert ok_hwnd is False
        assert "TARGET_HWND_MISMATCH" in reason_hwnd

        # 4. Revalidation từ chối nếu live PID thay đổi (tiến trình bị tráo đổi)
        live_drifted_pid = copy.deepcopy(snapshot)
        live_drifted_pid.pid = 88888
        ok_pid, reason_pid, _ = SemanticActionValidator.revalidate_target_identity(action, live_drifted_pid)
        assert ok_pid is False
        assert "TARGET_PID_MISMATCH" in reason_pid

        # 5. Revalidation từ chối nếu live process name thay đổi
        live_drifted_proc = copy.deepcopy(snapshot)
        live_drifted_proc.process_name = "cmd.exe"
        ok_proc, reason_proc, _ = SemanticActionValidator.revalidate_target_identity(action, live_drifted_proc)
        assert ok_proc is False
        assert "PROCESS_NOT_IN_ALLOWLIST" in reason_proc or "PROCESS_NAME_MISMATCH" in reason_proc

        # 6. Revalidation từ chối nếu live UI drift (snapshot_hash lệch)
        live_ui_drift = copy.deepcopy(snapshot)
        live_ui_drift.snapshot_hash = "sha256_" + "9" * 64
        ok_drift, reason_drift, _ = SemanticActionValidator.revalidate_target_identity(action, live_ui_drift)
        assert ok_drift is False
        assert "SNAPSHOT_HASH_DRIFT" in reason_drift

        # 7. Revalidation từ chối nếu element bị stale hash trước dispatch
        live_stale_el = copy.deepcopy(snapshot)
        live_stale_el.ref_map["e1"].element_hash = "f" * 64
        ok_stale, reason_stale, _ = SemanticActionValidator.revalidate_target_identity(action, live_stale_el)
        assert ok_stale is False
        assert "STALE_ELEMENT_HASH" in reason_stale

        # 8. Revalidation từ chối nếu element bị vô hiệu hóa ngay trước dispatch
        live_disabled = copy.deepcopy(snapshot)
        live_disabled.ref_map["e1"].is_enabled = False
        ok_dis, reason_dis, _ = SemanticActionValidator.revalidate_target_identity(action, live_disabled)
        assert ok_dis is False
        assert "ELEMENT_DISABLED" in reason_dis
