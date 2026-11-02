# -*- coding: utf-8 -*-
"""
services/ai_desktop/semantic_action_dispatcher.py
Gated Semantic Action Dispatcher for JKAI Desktop Actuator (M5).

Ranh giới kiểm soát tối hậu giữa Kernel và Host OS. Mọi chốt đều fail-closed:

  1. JKAI_MUTATION_ENABLED=1 mới được phép thực thi (mặc định 0).
  2. Policy SSoT: config/security/desktop_app_allowlist.json quyết định process,
     action, element và destructive keywords — không hard-code.
  3. CLICK/FOCUS hiện chỉ được MÔ PHỎNG (DRY_RUN_SIMULATED), không gọi Win32.
     KEY_COMBO/SCROLL bị từ chối tường minh bằng REJECTED_UNSUPPORTED_ACTION.
  4. Snapshot quá TTL bị từ chối (SNAPSHOT_STALE) trước khi dispatch.
  5. TYPE_TEXT chỉ chạy khi có approval envelope Ed25519 của Master (pinned key),
     nonce được tiêu thụ nguyên tử qua SQLite (chống replay kể cả sau restart).
  6. After-state được đọc độc lập từ Win32; không có bằng chứng thì
     verified_after_state=False và status FAIL — không có PASS giả.
  7. Receipt có digest SHA-256; chữ ký Ed25519 chỉ được gắn khi HITL truyền
     receipt_signer, và receipt ghi rõ receipt_signed.
"""

import hashlib
import json
import os
import time
from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

from services.ai_desktop.app_policy import DesktopActionPolicy, get_policy
from services.ai_desktop.host_after_state_verifier import HostAfterStateVerifier
from services.ai_desktop.master_authority_verifier import MasterAuthorityVerifier
from services.ai_desktop.nonce_store import PersistentNonceStore
from services.ai_desktop.semantic_action_ir import (
    ActionType,
    SemanticActionIR,
    SemanticActionValidator,
    TypeTextParams,
)
from services.ai_desktop.uia_tree_inspector import UIATreeInspector, UIATreeSnapshot

# Hành động có thể thực thi thật trong phạm vi pilot hiện tại.
EXECUTABLE_ACTIONS = {ActionType.TYPE_TEXT}
# Hành động chỉ được mô phỏng (không chạm hệ điều hành).
SIMULATED_ACTIONS = {ActionType.CLICK, ActionType.FOCUS}
# Hành động hợp lệ trong IR nhưng chưa được hỗ trợ dispatch.
UNSUPPORTED_ACTIONS = {ActionType.KEY_COMBO, ActionType.SCROLL}


@dataclass
class SemanticDispatchResult:
    status: str
    success: bool
    reason: str
    action_type: str
    target_ref: str
    target_hwnd: int
    target_pid: int
    before_text: Optional[str] = None
    after_text: Optional[str] = None
    execution_receipt: Optional[Dict[str, Any]] = None
    revalidation_details: Optional[Dict[str, Any]] = None


class SemanticActionDispatcher:
    """
    Dispatcher có kiểm soát chặt chẽ cho Semantic Action IR.
    Đóng vai trò Ranh giới Kiểm soát Tối hậu (Final Gate) giữa Kernel và Host OS.
    """

    def __init__(
        self,
        inspector: Optional[UIATreeInspector] = None,
        dry_run: bool = False,
        policy: Optional[DesktopActionPolicy] = None,
        verifier: Optional[MasterAuthorityVerifier] = None,
        nonce_store: Optional[PersistentNonceStore] = None,
        after_state_verifier: Optional[HostAfterStateVerifier] = None,
        receipt_signer: Optional[Any] = None,
        nonce_ttl_seconds: float = 60.0,
    ):
        self.inspector = inspector or UIATreeInspector(is_live_mode=True)
        self.dry_run = dry_run
        self._policy = policy
        self._verifier = verifier
        self._nonce_store = nonce_store
        self._after_state = after_state_verifier or HostAfterStateVerifier()
        self._receipt_signer = receipt_signer
        self._nonce_ttl_seconds = nonce_ttl_seconds

    # ── Lazy dependencies (không nạp khóa/cấu hình khi chưa cần) ──────────

    def _get_policy(self) -> DesktopActionPolicy:
        if self._policy is None:
            self._policy = get_policy()
        return self._policy

    def _get_verifier(self) -> MasterAuthorityVerifier:
        if self._verifier is None:
            self._verifier = MasterAuthorityVerifier()
        return self._verifier

    def _get_nonce_store(self) -> PersistentNonceStore:
        if self._nonce_store is None:
            self._nonce_store = PersistentNonceStore()
        return self._nonce_store

    # ── Entry point ──────────────────────────────────────────────────────

    def dispatch_action(
        self,
        action: SemanticActionIR,
        live_snapshot_override: Optional[UIATreeSnapshot] = None,
        bypass_env_for_test: bool = False,
        approval_envelope_b64: Optional[str] = None,
    ) -> SemanticDispatchResult:
        """
        Thứ tự kiểm soát: env → policy → schema → support → snapshot → revalidate
        → element allowlist → approval/nonce → execute (hoặc simulate) → after-state.
        """
        def reject(status: str, reason: str, **kwargs: Any) -> SemanticDispatchResult:
            return SemanticDispatchResult(
                status=status,
                success=False,
                reason=reason,
                action_type=action.action_type.value,
                target_ref=action.target_ref,
                target_hwnd=action.target_hwnd,
                target_pid=action.target_pid,
                **kwargs,
            )

        # ── 1. Fail-closed environment gate ──────────────────────────────
        if not self._mutation_gate_open(bypass_env_for_test):
            return reject("REJECTED_BY_POLICY", "MUTATION_DISABLED_BY_POLICY: JKAI_MUTATION_ENABLED != 1")

        # ── 2. Policy SSoT ───────────────────────────────────────────────
        try:
            policy = self._get_policy()
        except Exception as exc:  # noqa: BLE001 - policy failures must reject, not crash
            return reject("REJECTED_BY_POLICY", f"POLICY_LOAD_FAILED: {exc}")

        rule = policy.app_rule(action.target_process_name)
        if rule is None:
            return reject(
                "REJECTED_BY_POLICY",
                f"PROCESS_NOT_PERMITTED_IN_PILOT: {action.target_process_name} is blocked",
            )

        # ── 3. Schema integrity ──────────────────────────────────────────
        schema_ok, schema_reason = action.validate_self_schema()
        if not schema_ok:
            return reject("REJECTED_BY_SCHEMA", f"ACTION_SCHEMA_INVALID: {schema_reason}")

        # ── 4. Unsupported actions fail loudly (never fall through) ──────
        if action.action_type in UNSUPPORTED_ACTIONS:
            return reject(
                "REJECTED_UNSUPPORTED_ACTION",
                f"ACTION_TYPE_NOT_IMPLEMENTED: {action.action_type.value}",
            )
        if action.action_type not in EXECUTABLE_ACTIONS and action.action_type not in SIMULATED_ACTIONS:
            return reject(
                "REJECTED_UNSUPPORTED_ACTION",
                f"UNKNOWN_ACTION_TYPE: {action.action_type.value}",
            )

        # ── 5. App-level action allowlist ────────────────────────────────
        if not rule.allows_action(action.action_type.value):
            return reject(
                "REJECTED_BY_POLICY",
                f"ACTION_TYPE_NOT_PERMITTED_IN_PILOT: {action.action_type.value} is blocked for {rule.process_name}",
            )

        if action.action_type == ActionType.TYPE_TEXT:
            params = action.parameters
            if not isinstance(params, TypeTextParams):
                return reject("REJECTED_BY_SCHEMA", "ACTION_PARAMETER_MISMATCH: type_text requires TypeTextParams")
            if rule.max_text_length is not None and len(params.text) > rule.max_text_length:
                return reject(
                    "REJECTED_BY_POLICY",
                    f"TEXT_EXCEEDS_APP_MAX_LENGTH: {len(params.text)} > {rule.max_text_length}",
                )

        # ── 6. Live snapshot freshness (TTL) ─────────────────────────────
        live_snap = live_snapshot_override or self.inspector.inspect_tree(hwnd=action.target_hwnd)
        if getattr(live_snap, "is_expired", False):
            return reject(
                "SNAPSHOT_STALE",
                f"SNAPSHOT_TTL_EXPIRED: captured_at={getattr(live_snap, 'captured_at', 0):.3f} "
                f"expires_at={getattr(live_snap, 'expires_at', 0):.3f}",
            )

        # ── 7. Pre-dispatch identity revalidation (anti-TOCTOU) ──────────
        reval_ok, reval_reason, reval_details = SemanticActionValidator.revalidate_target_identity(
            action=action,
            live_snapshot=live_snap,
            allowed_processes=set(policy.allowed_processes),
        )
        if not reval_ok:
            return reject(
                "PRE_DISPATCH_IDENTITY_DRIFT",
                f"PRE_DISPATCH_REVALIDATION_FAILED: {reval_reason}",
                revalidation_details=reval_details,
            )

        target_el = live_snap.ref_map[action.target_ref]
        el_ok, el_reason = rule.allows_element(
            name=target_el.name,
            automation_id=target_el.automation_id,
            class_name=target_el.class_name,
            control_type=target_el.control_type,
        )
        if not el_ok:
            return reject("REJECTED_BY_POLICY", f"ELEMENT_NOT_PERMITTED: {el_reason}")

        # ── 8. Simulated actions never touch the OS ──────────────────────
        if action.action_type in SIMULATED_ACTIONS:
            return SemanticDispatchResult(
                status="DRY_RUN_SIMULATED",
                success=True,
                reason="CLICK_FOCUS_SIMULATION_ONLY_PENDING_VERIFIED_EXECUTION",
                action_type=action.action_type.value,
                target_ref=action.target_ref,
                target_hwnd=action.target_hwnd,
                target_pid=action.target_pid,
                before_text=getattr(target_el, "value", "") or "",
                execution_receipt={
                    "action_type": action.action_type.value,
                    "simulated": True,
                    "verified_after_state": False,
                    "reason": "SIMULATION_ONLY",
                    "timestamp": time.time(),
                },
                revalidation_details=reval_details,
            )

        if self.dry_run:
            return SemanticDispatchResult(
                status="DRY_RUN_VALIDATED_SUCCESS",
                success=True,
                reason="ACTION_PRE_DISPATCH_VERIFIED_DRY_RUN",
                action_type=action.action_type.value,
                target_ref=action.target_ref,
                target_hwnd=action.target_hwnd,
                target_pid=action.target_pid,
                before_text=getattr(target_el, "value", "") or "",
                revalidation_details=reval_details,
            )

        # ── 9. Master approval + atomic nonce consumption ────────────────
        approval_ok, approval_status, approval_reason, approval_details = self._verify_and_consume_approval(
            action=action,
            approval_envelope_b64=approval_envelope_b64,
        )
        if not approval_ok:
            return reject(approval_status, approval_reason)

        return self._execute_type_text(
            action=action,
            target_el=target_el,
            approval_details=approval_details,
            revalidation_details=reval_details,
        )

    # ── Gates ───────────────────────────────────────────────────────────

    @staticmethod
    def _mutation_gate_open(bypass_env_for_test: bool) -> bool:
        if os.environ.get("JKAI_MUTATION_ENABLED", "0").strip() == "1":
            return True
        if not bypass_env_for_test:
            return False
        # The bypass itself only exists in explicitly declared test mode.
        return os.environ.get("JKAI_MUTATION_TEST_MODE", "0").strip() == "1"

    def _verify_and_consume_approval(
        self,
        action: SemanticActionIR,
        approval_envelope_b64: Optional[str],
    ) -> Tuple[bool, str, str, Dict[str, Any]]:
        if not approval_envelope_b64:
            return False, "REJECTED_BY_APPROVAL", "APPROVAL_ENVELOPE_MISSING", {}

        text_payload = ""
        if isinstance(action.parameters, TypeTextParams):
            text_payload = action.parameters.text

        try:
            verifier = self._get_verifier()
        except Exception as exc:  # noqa: BLE001
            return False, "REJECTED_BY_APPROVAL", f"VERIFIER_UNAVAILABLE: {exc}", {}

        ok, reason, details = verifier.verify_approval_token(
            approval_envelope_b64=approval_envelope_b64,
            expected_action=action.action_type.value,
            expected_hwnd=action.target_hwnd,
            expected_target_pid=action.target_pid,
            expected_proc_name=action.target_process_name.lower().strip(),
            expected_text=text_payload,
            expected_session_id=action.session_id,
            expected_lease_id=action.lease_id,
            expected_nonce=action.nonce,
        )
        if not ok:
            return False, "REJECTED_BY_APPROVAL", f"APPROVAL_REJECTED: {reason}", {}

        expected_digest = f"sha256_{details.get('canonical_payload_sha256', '')}"
        if action.approval_digest != expected_digest:
            return False, "REJECTED_BY_APPROVAL", (
                f"APPROVAL_DIGEST_MISMATCH: action={action.approval_digest[:20]}... "
                f"envelope={expected_digest[:20]}..."
            ), {}

        try:
            store = self._get_nonce_store()
            claimed = store.check_and_use_nonce(
                nonce=f"desktop_dispatch_{action.nonce}",
                scope="desktop_dispatch",
                ttl_seconds=self._nonce_ttl_seconds,
            )
        except Exception as exc:  # noqa: BLE001
            return False, "REJECTED_BY_APPROVAL", f"NONCE_STORE_UNAVAILABLE: {exc}", {}

        if not claimed:
            return False, "REPLAY_NONCE_DETECTED", "REPLAY_ATTACK_DETECTED: nonce already consumed", {}

        store.record_lease_claim(
            lease_id=action.lease_id,
            nonce=action.nonce,
            ttl_seconds=max(120.0, self._nonce_ttl_seconds),
        )
        return True, "APPROVAL_VERIFIED_AND_NONCE_CONSUMED", "APPROVAL_VERIFIED_AND_NONCE_CONSUMED", details

    # ── Execution & evidence ────────────────────────────────────────────

    def _execute_type_text(
        self,
        action: SemanticActionIR,
        target_el: Any,
        approval_details: Dict[str, Any],
        revalidation_details: Dict[str, Any],
    ) -> SemanticDispatchResult:
        params: TypeTextParams = action.parameters
        text_to_set = params.text
        dispatch_hwnd = int(getattr(target_el, "hwnd", 0) or action.target_hwnd)

        def result(status: str, success: bool, reason: str, **kwargs: Any) -> SemanticDispatchResult:
            return SemanticDispatchResult(
                status=status,
                success=success,
                reason=reason,
                action_type=action.action_type.value,
                target_ref=action.target_ref,
                target_hwnd=action.target_hwnd,
                target_pid=action.target_pid,
                revalidation_details=revalidation_details,
                **kwargs,
            )

        # 9.1 Before-state must be readable, otherwise the result is unverifiable.
        before_snapshot = self._after_state.capture_snapshot(dispatch_hwnd)
        if not before_snapshot.get("read_success", False):
            return result(
                "PRECONDITION_UNVERIFIABLE",
                False,
                f"BEFORE_STATE_READ_FAILED: {before_snapshot.get('error') or before_snapshot.get('text')}",
                before_text=None,
            )
        before_text = before_snapshot.get("text", "")

        # 9.2 Dispatch.
        dispatch_success = False
        dispatch_error = None
        raw_result = None
        try:
            import win32con
            import win32gui
            raw_result = win32gui.SendMessage(dispatch_hwnd, win32con.WM_SETTEXT, 0, text_to_set)
            dispatch_success = (raw_result == 1)
        except Exception as exc:  # noqa: BLE001
            dispatch_error = str(exc)

        if self.inspector:
            self.inspector.invalidate_cache(action.target_hwnd)

        if not dispatch_success:
            err = f"SendMessage exception: {dispatch_error}" if dispatch_error else f"SendMessage returned {raw_result!r} (expected 1)"
            return result(
                "EXECUTION_FAILED",
                False,
                f"DISPATCH_ERROR: {err}",
                before_text=before_text,
            )

        # 9.3 Independent after-state evidence.
        verification = self._after_state.verify_action_result(
            before_snapshot=before_snapshot,
            hwnd=dispatch_hwnd,
            expected_mutation_text=text_to_set,
            timeout_seconds=2.0,
            match_mode="exact",
        )

        receipt: Dict[str, Any] = {
            "action_type": "type_text",
            "session_id": action.session_id,
            "lease_id": action.lease_id,
            "nonce": action.nonce,
            "target_ref": action.target_ref,
            "target_hwnd": action.target_hwnd,
            "dispatch_hwnd": dispatch_hwnd,
            "target_pid": action.target_pid,
            "target_process_name": action.target_process_name,
            "approval": {
                "master_key_id": approval_details.get("master_key_id"),
                "public_key_fingerprint": approval_details.get("public_key_fingerprint"),
                "canonical_payload_sha256": approval_details.get("canonical_payload_sha256"),
            },
            "before_hash": before_snapshot.get("hash", ""),
            "after_hash": verification.get("after_hash", ""),
            "expected_text_sha256": hashlib.sha256(text_to_set.encode("utf-8")).hexdigest(),
            "expected_text_length": len(text_to_set),
            "after_state": {
                "verified_after_state": bool(verification.get("match", False)),
                "source": "INDEPENDENT_WM_GETTEXT",
                "match_mode": verification.get("match_mode"),
                "verification_digest": verification.get("receipt_digest"),
                "read_success": verification.get("read_success", False),
            },
            "verified_after_state": bool(verification.get("match", False)),
            "timestamp": time.time(),
        }

        receipt_bytes = json.dumps(receipt, sort_keys=True, separators=(",", ":")).encode("utf-8")
        receipt["receipt_digest"] = hashlib.sha256(receipt_bytes).hexdigest()
        receipt["receipt_signed"] = False
        if self._receipt_signer is not None:
            try:
                signature = self._receipt_signer.sign_receipt(receipt_bytes)
                receipt["receipt_signature"] = signature
                receipt["receipt_signed"] = True
            except Exception as exc:  # noqa: BLE001 - signing failure must not fake a signed receipt
                receipt["receipt_signature_error"] = str(exc)

        if not verification.get("match", False):
            return result(
                "AFTER_STATE_VERIFICATION_FAILED",
                False,
                f"AFTER_STATE_MISMATCH: {verification.get('status')}",
                before_text=before_text,
                after_text=None,
                execution_receipt=receipt,
            )

        return result(
            "DELIVERED_VERIFIED",
            True,
            "ACTION_EXECUTED_AND_INDEPENDENTLY_VERIFIED",
            before_text=before_text,
            after_text=None,
            execution_receipt=receipt,
        )
