# -*- coding: utf-8 -*-
"""
scripts/host_mutation_worker.py
[JKAI M5 HOST MUTATION WORKER SANDBOX - ASYMMETRIC HITL v2.3]

Nguyên tắc an ninh:
1. Cổng độc lập: Chạy trên port 9996 (Cổng 9997 giữ nguyên Read-Only vĩnh viễn).
2. Tách biệt File & Process Boundary:
   - Worker CHỈ IMPORT MasterApprovalVerifier từ 'scripts.master_approval_verifier'.
   - Tuyệt đối không import MasterApprovalSigner hay Ed25519PrivateKey.
3. Ràng buộc toàn diện (Comprehensive Identity & Lifecycle Binding):
   - Auth Token (Tầng 1): Single-use nonce, mandatory session binding, caller validation, TTL bounds, exact envelope/payload schema.
   - Approval Token (Tầng 2): Ed25519 trên Canonical JSON, exact envelope/payload schema, bind lease_id, nonce, hwnd,
     target_pid, proc_name, action, text_payload, worker_generation, lease_expires_at, session_id.
4. Fail-Closed Secrets: Bắt buộc cả 'JKAI_MUTATION_SECRET' và 'JKAI_MASTER_PUBLIC_KEY'.
5. Khóa an toàn mặc định: JKAI_MUTATION_ENABLED = false (mặc định dry-run).
6. Giới hạn mục tiêu theo policy SSoT (config/security/desktop_app_allowlist.json); policy lỗi/thiếu → fail-closed.
7. Vé cấp phép một lần: Hạn <= 30s, Single-Use, Nonce Anti-Replay.
8. Anti-TOCTOU: Revalidate HWND + PID + Process Name + Bounds trước khi phát lệnh.
9. Khẩn cấp tức thì: Tích hợp HostEmergencyWatchdog (STOP latch qua ESC/F12/(0,0)).
"""

import os
import re
import sys
import time
import json
import uuid
import hmac
import hashlib
import ctypes
import threading
from ctypes import wintypes
from typing import Dict, Any, Optional, Tuple

from services.ai_desktop.app_policy import DesktopPolicyError, get_policy
from services.ai_desktop.delivery_policy import retry_disposition
from services.ai_desktop.uia_click_executor import UIAClickExecutor, UIAClickError
from services.ai_desktop.uia_scroll_executor import UIAScrollExecutor, UIAScrollError

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

sys.path.insert(0, ".")
from scripts.host_watchdog import HostEmergencyWatchdog
from scripts.bounds_validator import DesktopBoundsValidator, WindowTargetMismatchError, OutOfBoundsSecurityError
# CHỈ IMPORT VERIFIER (PUBLIC KEY ONLY)
from scripts.master_approval_verifier import MasterApprovalVerifier
from scripts.persistent_nonce_store import PersistentNonceStore
from scripts.target_identity_validator import TargetIdentityValidator

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

class MutationSecurityError(Exception):
    """Lỗi an ninh khi vi phạm chính sách kiểm soát Mutation."""
    pass

class HostMutationWorker:
    def __init__(
        self,
        port: int = 9996,
        secret_key: Optional[str] = None,
        master_public_key: Optional[str] = None
    ):
        self.port = port
        
        # Test-mode: trigger watchdog sau N ký tự đã gửi (chỉ trong JKAI_MUTATION_TEST_MODE=1)
        self._test_stop_after_chars: int = 0
        self._test_stop_reason: str = ""
        # Test-mode: inject crash ngay sau compound SQLite commit (trước PostMessageW)
        self._test_crash_after_claim: bool = False
        
        # 1. Fail-Closed Secret Handling (Không bao giờ hardcode fallback)
        if secret_key is None:
            secret_key = os.getenv("JKAI_MUTATION_SECRET")
            
        if not secret_key or len(secret_key.strip()) < 16:
            raise RuntimeError(
                "FAIL_CLOSED: Thiếu biến môi trường bắt buộc 'JKAI_MUTATION_SECRET' (tối thiểu 16 ký tự). "
                "Không được phép khởi động Mutation Worker mà không có khóa bí mật nội bộ."
            )
            
        self.secret_key = secret_key.encode("utf-8")
        
        # 2. Khởi tạo Master Approval Verifier (CHỈ DÙNG PUBLIC KEY CỦA MASTER)
        if master_public_key is None:
            master_public_key = os.getenv("JKAI_MASTER_PUBLIC_KEY")
            
        if not master_public_key:
            raise RuntimeError(
                "FAIL_CLOSED: Thiếu biến môi trường bắt buộc 'JKAI_MASTER_PUBLIC_KEY'. "
                "Worker từ chối khởi động nếu thiếu Public Key của Master để kiểm chứng phê duyệt."
            )
            
        self.master_verifier = MasterApprovalVerifier(public_key_b64=master_public_key)
        
        self.worker_generation = uuid.uuid4().hex[:8]
        self.watchdog = HostEmergencyWatchdog.get_instance()
        self.bounds_validator = DesktopBoundsValidator(safe_inset=8)
        # Fail closed at startup: a missing/broken policy must never widen scope.
        self.target_validator = TargetIdentityValidator(
            allowed_proc_names=set(self._load_policy().allowed_processes)
        )
        self.nonce_store = PersistentNonceStore()
        self.click_executor = UIAClickExecutor()
        self.scroll_executor = UIAScrollExecutor()
        
        # Bảng quản lý Lease Tokens một lần và Khóa đồng bộ Per-Worker / Per-Lease
        self._active_leases: Dict[str, Dict[str, Any]] = {}
        self._used_nonces: set = set()
        self._lock = threading.RLock()
        # Đường IPC bật cờ này: bắt buộc preflight owner + before-snapshot trước execute
        self.require_preflight_owner = False
        
        # Kiểm tra biến môi trường bật/tắt quyền can thiệp
        env_val = os.getenv("JKAI_MUTATION_ENABLED", "0").strip().lower()
        self.mutation_enabled = env_val in ("1", "true", "yes")

        # Cơ chế One-Shot / Lease-Bound Master Activation (Finding 5)
        # Cho phép Master kích hoạt quyền gõ phím thật tạm thời trong một khoảng thời gian (TTL)
        # hoặc cho một session/target cụ thể có chữ ký Ed25519 mà không cần sửa file .env mặc định.
        self._one_shot_activation: Optional[Dict[str, Any]] = None

    def activate_one_shot(
        self,
        master_auth_token: str,
        session_id: str,
        target_hwnd: int
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """Kích hoạt quyền mutation tạm thời (Single-Use One-Shot) theo đúng phê duyệt của Master (Finding 1, 2, 3, 4).
        Yêu cầu Master Activation Token hợp lệ được ký bằng Master Ed25519 Private Key chứa target_hwnd và session."""
        with self._lock:
            current = self._one_shot_activation
            if current and not current.get("consumed") and time.time() < current.get("expires_at", 0):
                return False, "ONE_SHOT_ALREADY_ACTIVE", {}

            ok, reason, payload = self.master_verifier.verify_and_claim_activation_token(
                token_str=master_auth_token,
                expected_session_id=session_id,
                expected_target_hwnd=target_hwnd
            )
            if not ok:
                return False, f"ONE_SHOT_AUTH_FAILED: {reason}", {}

            self._one_shot_activation = {
                "active": True,
                "token_nonce": payload.get("nonce"),
                "caller_id": payload.get("caller_id"),
                "session_id": session_id,
                "target_hwnd": int(target_hwnd),
                "issued_at": payload.get("issued_at"),
                "expires_at": payload.get("expires_at"),
                "consumed": False
            }
            return True, "ONE_SHOT_ACTIVATED", dict(self._one_shot_activation)

    def is_mutation_active(self, hwnd: Optional[int] = None, session_id: Optional[str] = None) -> Tuple[bool, str]:
        """Kiểm tra quyền can thiệp: hoặc qua biến môi trường JKAI_MUTATION_ENABLED,
        hoặc qua One-Shot Master Activation Token còn hiệu lực, đúng phạm vi và chưa bị tiêu thụ."""
        with self._lock:
            if self.mutation_enabled:
                return True, "GLOBAL_ENV_ENABLED"

            if self._one_shot_activation:
                if self._one_shot_activation.get("consumed"):
                    self._one_shot_activation = None
                    return False, "ONE_SHOT_ALREADY_CONSUMED"

                now = time.time()
                if now >= self._one_shot_activation["expires_at"]:
                    self._one_shot_activation = None
                    return False, "ONE_SHOT_EXPIRED"

                # Kiểm tra ràng buộc session_id nếu có
                if session_id and self._one_shot_activation["session_id"] != session_id:
                    return False, "ONE_SHOT_SESSION_MISMATCH"

                # Kiểm tra ràng buộc target_hwnd nếu có
                bound_hwnd = self._one_shot_activation.get("target_hwnd")
                if bound_hwnd is not None and hwnd is not None and int(bound_hwnd) != int(hwnd):
                    return False, "ONE_SHOT_TARGET_HWND_MISMATCH"

                return True, "ONE_SHOT_ACTIVE"

            return False, "MUTATION_DISABLED_SAFE_MODE"

    def claim_activation_for_execution(self, hwnd: Optional[int] = None, session_id: Optional[str] = None) -> Tuple[bool, str]:
        """Atomic check and consume (Finding 1 & 2 Lượt 297):
        Chuyển đổi trạng thái từ ACTIVE -> CONSUMED ngay lập tức trong lock.
        Nếu là ONE_SHOT_ACTIVE, token bị tiêu thụ VĨNH VIỄN ngay tại thời điểm claim,
        bảo đảm không có khoảng trống TOCTOU và mọi nhánh sau đó (STOP, partial, fail, crash, success)
        đều không thể tái sử dụng token này."""
        with self._lock:
            if self.mutation_enabled:
                return True, "GLOBAL_ENV_ENABLED"

            if self._one_shot_activation:
                if self._one_shot_activation.get("consumed"):
                    self._one_shot_activation = None
                    return False, "ONE_SHOT_ALREADY_CONSUMED"

                now = time.time()
                if now >= self._one_shot_activation["expires_at"]:
                    self._one_shot_activation = None
                    return False, "ONE_SHOT_EXPIRED"

                # Binding bắt buộc; thiếu binding không được cấp quyền.
                if not session_id or self._one_shot_activation["session_id"] != session_id:
                    return False, "ONE_SHOT_SESSION_MISMATCH"

                bound_hwnd = self._one_shot_activation.get("target_hwnd")
                if hwnd is None or bound_hwnd is None or int(bound_hwnd) != int(hwnd):
                    return False, "ONE_SHOT_TARGET_HWND_MISMATCH"

                # Atomic consume trong lock, trước ký tự đầu tiên.
                consumed_nonce = self._one_shot_activation.get("token_nonce")
                if not isinstance(consumed_nonce, str) or not consumed_nonce:
                    self._one_shot_activation = None
                    return False, "ONE_SHOT_NONCE_MISSING"
                if not self.nonce_store.record_lease_claim(
                    lease_id=f"consumed_activation_{consumed_nonce}",
                    nonce=consumed_nonce,
                    ttl_seconds=300.0
                ):
                    self._one_shot_activation = None
                    return False, "ONE_SHOT_CLAIM_PERSISTENCE_FAILED"
                self._one_shot_activation = None
                return True, "ONE_SHOT_CLAIMED_FOR_EXECUTION"

            return False, "MUTATION_DISABLED_SAFE_MODE"

    def get_status(self) -> Dict[str, Any]:
        """Trả về trạng thái hoạt động của Mutation Worker."""
        watchdog_status = self.watchdog.get_status()
        return {
            "service": "JKAI Host Mutation Worker Sandbox",
            "version": "v2.3-exact-envelope-schema-hitl",
            "generation": self.worker_generation,
            "port": self.port,
            "mutation_enabled": self.mutation_enabled,
            "allowed_target_scope": sorted(self._load_policy().allowed_processes),
            "watchdog_stopped": watchdog_status.get("is_stopped", False),
            "watchdog_reason": watchdog_status.get("reason", ""),
            "active_lease_count": len(self._active_leases),
            "safety_invariant": "MUTATION_DISABLED_BY_DEFAULT" if not self.mutation_enabled else "MUTATION_ACTIVE_UNDER_SUPERVISION"
        }

    @staticmethod
    def _load_policy():
        """Policy SSoT; a missing/invalid file raises and the call fails closed."""
        return get_policy()

    _POLICY_ACTION = {"type": "type_text", "click": "click", "scroll": "scroll", "focus": "focus"}
    _EXECUTABLE_ACTIONS = ("type", "click", "scroll")

    def _verify_target_allowed(
        self,
        hwnd: int,
        action: str,
        text: str,
        element_ref: str = "",
        scroll_direction: str = "",
        scroll_unit: str = "",
        scroll_steps: int = 0,
    ) -> Tuple[int, str]:
        """Bind HWND to an allowlisted process and validate the action's policy scope."""
        if not user32.IsWindow(hwnd):
            raise WindowTargetMismatchError(f"HWND {hwnd} không hợp lệ hoặc đã bị đóng.")

        pid = wintypes.DWORD()
        user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        process_pid = pid.value

        import psutil
        try:
            proc = psutil.Process(process_pid)
            proc_name = proc.name().lower()
        except Exception as e:
            raise WindowTargetMismatchError(f"Không thể đọc thông tin tiến trình PID {process_pid}: {e}")

        try:
            policy = self._load_policy()
        except DesktopPolicyError as e:
            raise MutationSecurityError(f"POLICY_UNAVAILABLE: {e}")
        rule = policy.app_rule(proc_name)
        if rule is None:
            raise MutationSecurityError(
                f"[SCOPE VIOLATION] Tiến trình '{proc_name}' (PID: {process_pid}) không nằm trong allowlist."
            )

        policy_action = self._POLICY_ACTION.get(action)
        if policy_action is None or not rule.allows_action(policy_action):
            raise MutationSecurityError(
                f"[SCOPE VIOLATION] Hành động '{action}' không được phép cho '{proc_name}'."
            )
        if policy_action == "type_text":
            if element_ref:
                raise MutationSecurityError(
                    f"[SCOPE VIOLATION] element_ref chỉ áp dụng cho click/scroll, không áp dụng cho '{proc_name}'."
                )
            if scroll_direction or scroll_unit or scroll_steps:
                raise MutationSecurityError(
                    f"[SCOPE VIOLATION] tham số scroll chỉ áp dụng cho scroll, không áp dụng cho '{proc_name}'."
                )
            if rule.max_text_length is not None and len(text) > rule.max_text_length:
                raise MutationSecurityError(
                    f"[SCOPE VIOLATION] text dài {len(text)} vượt giới hạn {rule.max_text_length} của '{proc_name}'."
                )
            words = sorted(policy.destructive_keywords)
            if words and re.search(r"\b(" + "|".join(map(re.escape, words)) + r")\b", text, re.IGNORECASE):
                raise MutationSecurityError(
                    f"[SCOPE VIOLATION] text chứa từ khóa phá hoại cho '{proc_name}'."
                )
        elif policy_action in ("click", "scroll"):
            if not rule.allows_element_identifier(element_ref):
                raise MutationSecurityError(
                    f"[SCOPE VIOLATION] element '{element_ref}' không nằm trong allowlist của '{proc_name}'."
                )
            if policy_action == "click" and (scroll_direction or scroll_unit or scroll_steps):
                raise MutationSecurityError(
                    f"[SCOPE VIOLATION] tham số scroll chỉ áp dụng cho scroll, không áp dụng cho '{proc_name}'."
                )
            if policy_action == "scroll":
                if str(scroll_direction).strip().lower() not in ("up", "down"):
                    raise MutationSecurityError(
                        f"[SCOPE VIOLATION] scroll_direction '{scroll_direction}' không hợp lệ (up|down)."
                    )
                if str(scroll_unit).strip().lower() not in ("page", "line"):
                    raise MutationSecurityError(
                        f"[SCOPE VIOLATION] scroll_unit '{scroll_unit}' không hợp lệ (page|line)."
                    )
                if type(scroll_steps) is not int or isinstance(scroll_steps, bool) or not 1 <= scroll_steps <= 5:
                    raise MutationSecurityError(
                        f"[SCOPE VIOLATION] scroll_steps '{scroll_steps}' không hợp lệ (1..5)."
                    )

        return process_pid, proc_name

    @staticmethod
    def _lease_binding_payload(lease: Dict[str, Any]) -> str:
        """Single source of truth for the lease HMAC binding material.

        Every field that bounds a lease is part of this string; adding a field
        here automatically covers lease issuance, preflight, and dispatch.
        """
        return ":".join(
            str(lease.get(field, ""))
            for field in (
                "lease_id", "nonce", "hwnd", "pid", "proc_name", "action",
                "text_payload", "element_ref", "scroll_direction", "scroll_unit",
                "scroll_steps", "expires_at", "session_id",
            )
        )

    def _lease_signature(self, lease: Dict[str, Any]) -> str:
        binding = self._lease_binding_payload(lease)
        return hmac.new(self.secret_key, binding.encode("utf-8"), hashlib.sha256).hexdigest()

    @staticmethod
    def _find_text_control(hwnd: int) -> Optional[int]:
        """Resolve the text control behind a top-level window (Notepad/WordPad)."""
        import win32gui

        classes = ("edit", "richeditd2dpt", "richedit50w")
        if (win32gui.GetClassName(hwnd) or "").lower() in classes:
            return hwnd
        for class_name in ("Edit", "RichEditD2DPT", "RICHEDIT50W"):
            child = win32gui.FindWindowEx(hwnd, 0, class_name, None)
            if child:
                return child
        found = []

        def visit(child, _):
            if (win32gui.GetClassName(child) or "").lower() in classes:
                found.append(child)
            return True

        win32gui.EnumChildWindows(hwnd, visit, 0)
        return found[0] if found else None

    def request_one_time_lease(
        self,
        hwnd: int,
        action: str,
        expected_session_id: str,
        target_coords: Optional[Tuple[int, int]] = None,
        text_payload: str = "",
        element_ref: str = "",
        scroll_direction: str = "",
        scroll_unit: str = "",
        scroll_steps: int = 0,
        master_auth_token: str = ""
    ) -> Dict[str, Any]:
        """
        Khởi tạo và cấp phát vé One-Time Lease Token (Hạn <= 30s, Single-Use, Ràng buộc cứng).
        Yêu cầu Master Auth Token có chữ ký Ed25519 của Master, kiểm tra mandatory session_id và anti-replay.
        """
        if not expected_session_id or not expected_session_id.strip():
            raise PermissionError("Từ chối cấp Lease: Thiếu expected_session_id bắt buộc.")

        # 1. Kiểm tra xác thực Master Auth Token bằng MasterApprovalVerifier độc lập
        is_valid_token, reason, auth_payload = self.master_verifier.verify_master_auth_token(
            token_str=master_auth_token,
            expected_session_id=expected_session_id
        )
        if not is_valid_token:
            raise PermissionError(f"Từ chối cấp Lease: Master Auth Token không hợp lệ ({reason}).")

        session_id = auth_payload.get("session_id", expected_session_id)

        # 2. Kiểm tra STOP Latch của Watchdog
        if self.watchdog.is_stopped:
            raise MutationSecurityError(f"Từ chối cấp Lease: Watchdog STOP Latch đang kích hoạt ({self.watchdog._stop_reason}).")

        # 3. Xác thực hành vi
        if action not in self._EXECUTABLE_ACTIONS:
            raise MutationSecurityError(f"Hành động '{action}' chưa được phê chuẩn.")
        if action in ("click", "scroll") and not str(element_ref).strip():
            raise MutationSecurityError(
                f"[SCOPE VIOLATION] {action} bắt buộc phải có element_ref trong allowlist."
            )
        if action != "scroll" and (scroll_direction or scroll_unit or scroll_steps):
            raise MutationSecurityError(
                f"[SCOPE VIOLATION] tham số scroll chỉ áp dụng cho scroll, không áp dụng cho '{action}'."
            )

        # 4. Xác thực mục tiêu theo policy SSoT & Chụp Snapshot Target Identity
        pid, proc_name = self._verify_target_allowed(
            hwnd, action, text_payload, element_ref, scroll_direction, scroll_unit, scroll_steps)
        target_identity = self.target_validator.get_window_identity(hwnd)

        # 5. Nếu có tọa độ, kiểm tra Bounds Sandbox trước khi cấp vé
        if target_coords:
            self.bounds_validator.validate_coordinate(hwnd, target_coords[0], target_coords[1])

        # 6. Sinh token mật mã ràng buộc
        nonce = uuid.uuid4().hex[:12]
        self.nonce_store.check_and_use_nonce(f"worker_lease_{nonce}", scope="worker_lease", ttl_seconds=30.0)
        lease_id = f"lease_{uuid.uuid4().hex[:16]}"
        issued_at = time.time()
        expires_at = issued_at + 30.0  # Thời hạn tối đa 30s

        lease_record = {
            "lease_id": lease_id,
            "nonce": nonce,
            "hwnd": hwnd,
            "pid": pid,
            "proc_name": proc_name,
            "action": action,
            "target_coords": target_coords,
            "text_payload": text_payload,
            "element_ref": element_ref,
            "scroll_direction": scroll_direction,
            "scroll_unit": scroll_unit,
            "scroll_steps": scroll_steps,
            "issued_at": issued_at,
            "expires_at": expires_at,
            "consumed": False,
            "state": "ISSUED",
            "worker_generation": self.worker_generation,
            "session_id": session_id,
            "target_identity": target_identity
        }
        signature = self._lease_signature(lease_record)
        lease_record["signature"] = signature

        with self._lock:
            self._active_leases[lease_id] = lease_record

        return {
            "status": "LEASE_ISSUED",
            "lease_id": lease_id,
            "nonce": nonce,
            "hwnd": hwnd,
            "pid": pid,
            "proc_name": proc_name,
            "action": action,
            "text_payload": text_payload,
            "element_ref": element_ref,
            "scroll_direction": scroll_direction,
            "scroll_unit": scroll_unit,
            "scroll_steps": scroll_steps,
            "expires_at": expires_at,
            "validity_seconds": 30.0,
            "signature": signature,
            "worker_generation": self.worker_generation,
            "session_id": session_id
        }

    def preflight_verify_authorization(
        self,
        lease_id: str,
        signature: str,
        master_approval_signature: str
    ) -> Tuple[bool, str, Optional[Dict[str, Any]]]:
        """
        Kiểm tra toàn diện tính hợp lệ của Lease và Approval Signature mà KHÔNG tiêu thụ Nonce.
        Dùng cho bước Preflight Authorization trước khi Server thực hiện Before-Snapshot.
        Được bảo vệ bằng self._lock và Per-Lease State Machine (ISSUED -> PREFLIGHT_LOCKED).
        """
        with self._lock:
            lease = self._active_leases.get(lease_id)
            if not lease:
                # v2.5: Cross-restart replay detection.
                # Nếu lease không còn trong memory (server đã restart sau crash), kiểm tra SQLite:
                # nếu lease_id từng được compound claimed → REPLAY_ATTACK_DETECTED (nonce persist in SQLite).
                persisted_nonce = self.nonce_store.get_persisted_lease_nonce(lease_id)
                if persisted_nonce:
                    return False, "REPLAY_ATTACK_DETECTED_NONCE_PERSISTED_AFTER_CRASH", None
                return False, "LEASE_NOT_FOUND", None

            # Per-Lease State Machine Check: chỉ lease ISSUED mới được preflight (một chủ duy nhất)
            current_state = lease.get("state", "ISSUED")
            if current_state == "PREFLIGHT_LOCKED":
                return False, "LEASE_ALREADY_PREFLIGHT_LOCKED", None
            if current_state != "ISSUED":
                return False, f"INVALID_LEASE_STATE: {current_state}", None

            if lease["consumed"] or lease["nonce"] in self._used_nonces or self.nonce_store.is_nonce_used(f"worker_exec_{lease['nonce']}"):
                return False, "REPLAY_ATTACK_DETECTED", None

            now = time.time()
            if now > lease["expires_at"]:
                return False, "LEASE_EXPIRED", None

            if lease["worker_generation"] != self.worker_generation:
                return False, "WORKER_GENERATION_MISMATCH", None

            # Kiểm tra HMAC của worker lease
            expected_sig = self._lease_signature(lease)
            if not hmac.compare_digest(signature, expected_sig):
                return False, "TAMPERED_SIGNATURE", None

            # Kiểm tra Master Approval Signature bằng Ed25519 (chế độ verify-only, KHÔNG tiêu thụ nonce)
            is_approved, approval_reason = self.master_verifier.verify_mutation_approval(
                approval_token_b64=master_approval_signature,
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
                session_id=lease["session_id"],
                consume_nonce=False
            )
            if not is_approved:
                return False, f"INVALID_MASTER_APPROVAL: {approval_reason}", None

            # Executable scope: only actions with a real executor may reach preflight.
            if lease["action"] not in self._EXECUTABLE_ACTIONS:
                return False, f"EXECUTOR_NOT_IMPLEMENTED_FOR_ACTION: {lease['action']}", None

            # Kiểm tra toàn diện mục tiêu (Anti-TOCTOU, Identity, Bounds) trước khi cấp quyền snapshot
            try:
                current_pid, current_proc = self._verify_target_allowed(
                    lease["hwnd"], lease["action"], lease["text_payload"],
                    lease.get("element_ref", ""), lease.get("scroll_direction", ""),
                    lease.get("scroll_unit", ""), lease.get("scroll_steps", 0))
                if current_pid != lease["pid"]:
                    return False, f"TARGET_PID_MISMATCH: expected {lease['pid']}, got {current_pid}", None
            except Exception as e:
                return False, f"TARGET_UNAVAILABLE: {e}", None

            # Full Target Identity validation trong Preflight
            if lease.get("target_identity") and lease["target_identity"].get("valid"):
                ok_ident, reason_ident = self.target_validator.validate_target_identity(lease["hwnd"], lease["target_identity"])
                if not ok_ident:
                    return False, f"TARGET_IDENTITY_DRIFT: {reason_ident}", None

            # Target Coordinates / Bounds validation trong Preflight
            if lease.get("target_coords"):
                try:
                    coords = lease["target_coords"]
                    self.bounds_validator.validate_coordinate(lease["hwnd"], coords[0], coords[1])
                except Exception as e:
                    return False, f"OUT_OF_BOUNDS: {e}", None

            # Click: resolve the allowlisted element NOW and bind its identity.
            # Dispatch re-resolves and refuses ELEMENT_IDENTITY_DRIFT.
            if lease["action"] == "click":
                rule = self._load_policy().app_rule(lease["proc_name"])
                try:
                    resolved = self.click_executor.resolve(
                        lease["hwnd"], lease.get("element_ref", ""), rule)
                except UIAClickError as e:
                    return False, f"CLICK_TARGET_UNRESOLVED: {e.code}", None
                except Exception as e:
                    return False, f"CLICK_TARGET_UNRESOLVED: {e}", None
                lease["element_identity"] = resolved.as_dict()

            if lease["action"] == "scroll":
                rule = self._load_policy().app_rule(lease["proc_name"])
                try:
                    inspected = self.scroll_executor.inspect(
                        lease["hwnd"], lease.get("element_ref", ""), rule)
                except UIAScrollError as e:
                    return False, f"SCROLL_TARGET_UNRESOLVED: {e.code}", None
                except Exception as e:
                    return False, f"SCROLL_TARGET_UNRESOLVED: {e}", None
                lease["element_identity"] = inspected

            # Đánh dấu PREFLIGHT_LOCKED và cấp owner token duy nhất cho request này
            owner_token = uuid.uuid4().hex
            lease["state"] = "PREFLIGHT_LOCKED"
            lease["preflight_owner_token"] = owner_token
            lease["before_snapshot_hash"] = None
            result = dict(lease)
            return True, "PREFLIGHT_AUTH_PASSED", result

    def attach_before_snapshot(self, lease_id: str, owner_token: str, snapshot_hash: str) -> Tuple[bool, str]:
        """Gắn hash của before-snapshot vào lease. Chỉ chủ preflight được gắn, và chỉ gắn một lần."""
        with self._lock:
            lease = self._active_leases.get(lease_id)
            if not lease:
                return False, "LEASE_NOT_FOUND"
            if lease.get("state") != "PREFLIGHT_LOCKED":
                return False, f"INVALID_LEASE_STATE: {lease.get('state')}"
            expected_owner = lease.get("preflight_owner_token") or ""
            if not owner_token or not hmac.compare_digest(str(owner_token), expected_owner):
                return False, "PREFLIGHT_OWNER_MISMATCH"
            if lease.get("before_snapshot_hash"):
                return False, "BEFORE_SNAPSHOT_ALREADY_ATTACHED"
            if not snapshot_hash:
                return False, "BEFORE_SNAPSHOT_HASH_EMPTY"
            lease["before_snapshot_hash"] = snapshot_hash
            return True, "BEFORE_SNAPSHOT_ATTACHED"

    def revoke_lease(self, lease_id: str) -> bool:
        """Thu hồi lease chưa tiêu thụ. Lease bị thu hồi không thể preflight/execute nữa."""
        with self._lock:
            lease = self._active_leases.get(lease_id)
            if not lease:
                return False
            if lease.get("state") != "CONSUMED":
                lease["state"] = "REVOKED"
            return True

    @staticmethod
    def _claim_from_executor_error(
        exc: Exception,
        not_delivered: Dict[str, Any],
        action: str,
        hwnd: int,
        element_ref: str,
    ) -> Dict[str, Any]:
        """Turn an executor error into an honest delivery claim.

        Once the nonce is compound-claimed, a failed call is not automatically
        "not delivered": the provider may have acted (UNCERTAIN) or some steps
        may have landed (PARTIAL). Only a pre-dispatch failure stays
        CLAIMED_NOT_DELIVERED.
        """
        details = dict(getattr(exc, "details", {}) or {})
        state = getattr(exc, "delivery_state", "NOT_DELIVERED")
        base = {
            "reason": getattr(exc, "code", type(exc).__name__),
            "detail": getattr(exc, "detail", str(exc)),
            "action": action,
            "target_hwnd": hwnd,
            "element_ref": element_ref,
            # Only a provably undelivered action may be replayed automatically.
            "retry_disposition": retry_disposition(state),
        }
        if state == "PARTIAL":
            return {
                "status": "BLOCKED",
                "receipt": "CLAIMED_PARTIALLY_DELIVERED",
                "claim_state": "CLAIMED_PARTIALLY_DELIVERED",
                "recovery_policy": "NEW_LEASE_AND_NEW_MASTER_APPROVAL_REQUIRED",
                **details,
                **base,
            }
        if state == "UNCERTAIN":
            return {
                "status": "BLOCKED",
                "receipt": "CLAIMED_DELIVERY_UNCERTAIN",
                "claim_state": "CLAIMED_DELIVERY_UNCERTAIN",
                "recovery_policy": "MANUAL_STATE_INSPECTION_REQUIRED",
                **details,
                **base,
            }
        return dict(not_delivered, **base)

    def execute_with_lease(
        self,
        lease_id: str,
        signature: str,
        master_approval_signature: str,
        owner_token: Optional[str] = None,
        before_snapshot_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Thực thi hành động dựa trên vé cấp phép đã được kiểm chứng bằng Ed25519 HITL độc lập.
        Khi require_preflight_owner=True (đường IPC), bắt buộc lease ở PREFLIGHT_LOCKED,
        đúng owner token và đúng before-snapshot hash đã gắn.
        """
        with self._lock:
            # 1. Kiểm tra sự tồn tại của lease
            lease = self._active_leases.get(lease_id)
            if not lease:
                return {"status": "BLOCKED", "receipt": "LEASE_NOT_FOUND", "reason": "Lease token không tồn tại."}

            # 1.1. Per-lease state machine + preflight owner + snapshot correlation
            state = lease.get("state", "ISSUED")
            if state in ("REVOKED", "CONSUMED"):
                return {"status": "BLOCKED", "receipt": "REPLAY_ATTACK_DETECTED" if state == "CONSUMED" else "LEASE_REVOKED", "reason": f"Lease ở trạng thái {state}."}
            if self.require_preflight_owner or state == "PREFLIGHT_LOCKED":
                if state != "PREFLIGHT_LOCKED":
                    return {"status": "BLOCKED", "receipt": "PREFLIGHT_REQUIRED", "reason": "Lease chưa qua preflight."}
                expected_owner = lease.get("preflight_owner_token") or ""
                if not owner_token or not hmac.compare_digest(str(owner_token), expected_owner):
                    return {"status": "BLOCKED", "receipt": "PREFLIGHT_OWNER_MISMATCH", "reason": "Request không phải chủ preflight của lease."}
                attached = lease.get("before_snapshot_hash") or ""
                if self.require_preflight_owner and not attached:
                    return {"status": "BLOCKED", "receipt": "BEFORE_SNAPSHOT_NOT_ATTACHED", "reason": "Chưa gắn before-snapshot."}
                if attached and (not before_snapshot_hash or not hmac.compare_digest(str(before_snapshot_hash), attached)):
                    return {"status": "BLOCKED", "receipt": "BEFORE_SNAPSHOT_MISMATCH", "reason": "Before-snapshot hash không khớp."}

            # 2. Kiểm tra Single-Use / Anti-Replay (Kép: In-Memory + SQLite Persistent)
            if lease["consumed"] or lease["nonce"] in self._used_nonces or self.nonce_store.is_nonce_used(f"worker_exec_{lease['nonce']}"):
                return {"status": "BLOCKED", "receipt": "REPLAY_ATTACK_DETECTED", "reason": "Lease token đã được sử dụng trước đó."}

            # 3. Kiểm tra hạn dùng (Expiry <= 30s)
            now = time.time()
            if now > lease["expires_at"]:
                return {"status": "BLOCKED", "receipt": "LEASE_EXPIRED", "reason": f"Lease token đã hết hạn (quá {now - lease['expires_at']:.2f}s)."}

            # 4. Kiểm tra worker generation
            if lease["worker_generation"] != self.worker_generation:
                return {"status": "BLOCKED", "receipt": "WORKER_GENERATION_MISMATCH", "reason": "Worker đã bị restart kể từ khi cấp vé."}

            # 5. Kiểm tra chữ ký HMAC của vé cấp phép (Worker Token Verification)
            expected_sig = self._lease_signature(lease)
            if not hmac.compare_digest(signature, expected_sig):
                return {"status": "BLOCKED", "receipt": "TAMPERED_SIGNATURE", "reason": "Chữ ký vé cấp phép bị giả mạo."}

            # 6. [ASYMMETRIC HITL] Xác thực chữ ký phê duyệt của Master bằng MasterApprovalVerifier (Ed25519)
            # Ràng buộc toàn diện; sử dụng consume_nonce=False để bảo tồn token nếu các gate 7-9 phát hiện bất thường
            is_approved, approval_reason = self.master_verifier.verify_mutation_approval(
                approval_token_b64=master_approval_signature,
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
                session_id=lease["session_id"],
                consume_nonce=False
            )
            if not is_approved:
                receipt_code = "MISSING_MASTER_APPROVAL_SIGNATURE" if not master_approval_signature else "INVALID_MASTER_APPROVAL_SIGNATURE"
                return {
                    "status": "BLOCKED",
                    "receipt": receipt_code,
                    "reason": f"Chữ ký phê duyệt của Master không hợp lệ: {approval_reason}."
                }

            # 7. Kiểm tra STOP Latch của Watchdog ngay trước khi dispatch
            if self.watchdog.is_stopped:
                return {"status": "BLOCKED", "receipt": "EMERGENCY_STOP_TRIGGERED", "reason": f"Watchdog STOP Latch kích hoạt ({self.watchdog._stop_reason})."}

            # 8. Anti-TOCTOU Revalidation: Kiểm tra PID và Process thật
            hwnd = lease["hwnd"]
            try:
                current_pid, current_proc = self._verify_target_allowed(
                    hwnd, lease["action"], lease["text_payload"], lease.get("element_ref", ""),
                    lease.get("scroll_direction", ""), lease.get("scroll_unit", ""),
                    lease.get("scroll_steps", 0))
                if current_pid != lease["pid"]:
                    return {"status": "BLOCKED", "receipt": "TOCTOU_PID_MISMATCH", "reason": f"PID đã bị tráo đổi từ {lease['pid']} sang {current_pid}."}
            except Exception as e:
                return {"status": "BLOCKED", "receipt": "TOCTOU_TARGET_UNAVAILABLE", "reason": str(e)}

            if lease.get("target_identity") and lease["target_identity"].get("valid"):
                ok_ident, reason_ident = self.target_validator.validate_target_identity(hwnd, lease["target_identity"])
                if not ok_ident:
                    return {"status": "BLOCKED", "receipt": "TARGET_IDENTITY_DRIFT", "reason": f"Target identity drift: {reason_ident}"}

            # 9. Revalidate Bounds nếu có tọa độ
            if lease.get("target_coords"):
                try:
                    coords = lease["target_coords"]
                    self.bounds_validator.validate_coordinate(hwnd, coords[0], coords[1])
                except Exception as e:
                    return {"status": "BLOCKED", "receipt": "OUT_OF_BOUNDS", "reason": str(e)}

            # 9.1. ATOMIC COMPOUND CLAIM AT DISPATCH:
            # Tiêu thụ đồng thời Master Approval Nonce và Worker Execution Lease Nonce trong duy nhất 1 ACID Transaction!
            claimed = self.master_verifier.claim_compound_nonces_atomic(
                approval_nonce=lease["nonce"],
                exec_nonce=lease["nonce"],
                ttl_seconds=60.0
            )
            if not claimed:
                return {"status": "BLOCKED", "receipt": "REPLAY_ATTACK_DETECTED", "reason": "Compound nonces (approval or execution) already consumed or replayed."}

            lease["consumed"] = True
            lease["state"] = "CONSUMED"
            self._used_nonces.add(lease["nonce"])

            # Ghi claim timestamp vào lease record cho event provenance
            claim_timestamp = time.time()
            lease["claim_timestamp"] = claim_timestamp

            # v2.5: Persist lease_id → nonce mapping vào SQLite NGAY SAU compound claim.
            # Mục đích: cross-restart REPLAY_ATTACK_DETECTED — sau khi server crash và restart,
            # new server không có lease trong memory nhưng có thể tra cứu SQLite để biết
            # lease này đã được claim rồi → trả REPLAY_ATTACK_DETECTED thay vì LEASE_NOT_FOUND.
            self.nonce_store.record_lease_claim(
                lease_id=lease["lease_id"],
                nonce=lease["nonce"],
                ttl_seconds=120.0  # đủ lâu cho test I cycle
            )

            _test_mode = os.getenv("JKAI_MUTATION_TEST_MODE", "0").strip() == "1"

            # TEST MODE ONLY: inject crash ngay sau compound commit, trước PostMessageW
            # Chứng minh: nonce đã persist trong SQLite → restart → replay bị REPLAY_ATTACK_DETECTED
            if _test_mode and self._test_crash_after_claim:
                self._test_crash_after_claim = False  # single-use
                raise RuntimeError(
                    "TEST_CRASH_INJECTED_AFTER_COMPOUND_CLAIM: "
                    f"nonce={lease['nonce']} lease_id={lease['lease_id']} "
                    f"claim_ts={claim_timestamp:.6f} — "
                    "Compound nonces committed to SQLite. Server is intentionally crashing. "
                    "After restart, replay must yield REPLAY_ATTACK_DETECTED."
                )

            # 10. PHÁN QUYẾT THỰC THI (ATOMIC PRE-DISPATCH CONSUME: GLOBAL HOẶC ONE-SHOT)
            # Finding 1 & 2 Lượt 297: TOCTOU eliminated via atomic claim_activation_for_execution.
            # Token bị tiêu thụ vĩnh viễn NGAY TRƯỚC KHI dispatch ký tự đầu tiên,
            # áp dụng bình đẳng cho mọi nhánh: success, partial, failure, runtime exception, và crash!
            is_active, active_reason = self.claim_activation_for_execution(hwnd=hwnd, session_id=lease.get("session_id"))
            if not is_active:
                # Mặc định an toàn: Ghi nhận Dry-Run thành công có kiểm chứng, KHÔNG can thiệp chuột/phím thật
                return {
                    "status": "MUTATION_DISABLED_DRY_RUN",
                    "receipt": "MUTATION_DISABLED_DRY_RUN_RECEIPT",
                    "message": f"Chính sách an toàn: {active_reason}. Hành động đã vượt qua 10 chốt kiểm duyệt mật mã nhưng được giữ nguyên fail-closed.",
                    "action": lease["action"],
                    "target_hwnd": hwnd,
                    "text_payload": lease["text_payload"],
                    "precondition_verified": True,
                    "after_state": "PRESERVED_UNMODIFIED",
                    "dry_run": True
                }

            # 11. THỰC THI NATIVE MUTATION (Khi Master đã bật JKAI_MUTATION_ENABLED=1 hoặc cấp One-Shot Token)
            # Gửi WM_CHAR trực tiếp vào Edit control của Notepad: không chiếm focus, không di chuột,
            # không ảnh hưởng cửa sổ khác. Nếu không tìm thấy Edit control -> fail-closed.
            not_delivered = {
                "status": "BLOCKED",
                "receipt": "CLAIMED_NOT_DELIVERED",
                "claim_state": "CLAIMED_NOT_DELIVERED",
                "recovery_policy": "NEW_LEASE_AND_NEW_MASTER_APPROVAL_REQUIRED"
            }
            try:
                if self.watchdog.is_stopped:
                    return dict(not_delivered, reason="Master kích hoạt STOP trước khi gửi ký tự đầu tiên.")

                if lease["action"] == "click":
                    # Nonce đã bị compound-claim: mọi lỗi sau đây đều là CLAIMED_NOT_DELIVERED.
                    rule = self._load_policy().app_rule(lease["proc_name"])
                    identity = lease.get("element_identity") or {}
                    try:
                        click_result = self.click_executor.execute(
                            hwnd=hwnd,
                            identifier=lease.get("element_ref", ""),
                            rule=rule,
                            expected_signature=identity.get("signature") or None,
                            watchdog=self.watchdog,
                            expected_element_hash=identity.get("element_hash") or None,
                        )
                    except UIAClickError as exc:
                        return self._claim_from_executor_error(
                            exc, not_delivered, "click", hwnd, lease.get("element_ref", "")
                        )
                    except Exception as exc:
                        return dict(not_delivered,
                                    reason="CLICK_EXECUTOR_ERROR",
                                    detail=str(exc),
                                    action="click",
                                    target_hwnd=hwnd,
                                    element_ref=lease.get("element_ref", ""))
                    click_result["claim_timestamp"] = claim_timestamp
                    click_result["dispatch_done_ts"] = time.time()
                    return click_result

                if lease["action"] == "scroll":
                    # Nonce đã bị compound-claim: mọi lỗi sau đây đều là CLAIMED_NOT_DELIVERED.
                    rule = self._load_policy().app_rule(lease["proc_name"])
                    identity = lease.get("element_identity") or {}
                    try:
                        scroll_result = self.scroll_executor.execute(
                            hwnd=hwnd,
                            identifier=lease.get("element_ref", ""),
                            rule=rule,
                            direction=lease.get("scroll_direction", ""),
                            unit=lease.get("scroll_unit", ""),
                            steps=lease.get("scroll_steps", 0),
                            expected_signature=identity.get("signature") or None,
                            watchdog=self.watchdog,
                            expected_element_hash=identity.get("element_hash") or None,
                        )
                    except UIAScrollError as exc:
                        return self._claim_from_executor_error(
                            exc, not_delivered, "scroll", hwnd, lease.get("element_ref", "")
                        )
                    except Exception as exc:
                        return dict(not_delivered,
                                    reason="SCROLL_EXECUTOR_ERROR",
                                    detail=str(exc),
                                    action="scroll",
                                    target_hwnd=hwnd,
                                    element_ref=lease.get("element_ref", ""))
                    if scroll_result.get("watchdog_stopped"):
                        return {
                            "status": "BLOCKED",
                            "receipt": "CLAIMED_PARTIALLY_DELIVERED",
                            "claim_state": "CLAIMED_PARTIALLY_DELIVERED",
                            "recovery_policy": "NEW_LEASE_AND_NEW_MASTER_APPROVAL_REQUIRED",
                            "scroll_steps_applied": scroll_result.get("scroll_steps_applied", 0),
                            "vertical_percent_after": scroll_result.get("vertical_percent_after"),
                            "reason": "Dừng khẩn cấp giữa chuỗi scroll.",
                        }
                    scroll_result["claim_timestamp"] = claim_timestamp
                    scroll_result["dispatch_done_ts"] = time.time()
                    return scroll_result

                if lease["action"] != "type":
                    # Defense in depth: preflight already refuses these; never type into a click lease.
                    return dict(not_delivered,
                                reason=f"EXECUTOR_NOT_IMPLEMENTED_FOR_ACTION: {lease['action']}")

                text_to_type = lease["text_payload"]
                WM_CHAR = 0x0102
                edit_hwnd = self._find_text_control(hwnd)
                if not edit_hwnd:
                    return dict(not_delivered, reason="Không tìm thấy text control của cửa sổ đích; không gửi phím vào cửa sổ cha.")

                # Mã hóa UTF-16 để hỗ trợ cả ký tự ngoài BMP (surrogate pairs)
                utf16 = text_to_type.encode("utf-16-le")
                code_units = [int.from_bytes(utf16[i:i + 2], "little") for i in range(0, len(utf16), 2)]

                sent = 0
                dispatch_start_ts = time.time()
                for unit in code_units:
                    if self.watchdog.is_stopped:
                        watchdog_ts = time.time()
                        if _test_mode:
                            print(
                                f"[DISPATCH][WATCHDOG_STOP] lease_id={lease['lease_id']} "
                                f"unit_idx={sent} reason={self.watchdog._stop_reason!r} "
                                f"ts={watchdog_ts:.6f}",
                                flush=True
                            )
                        if sent == 0:
                            return dict(not_delivered,
                                        reason="Master kích hoạt STOP trước khi gửi ký tự đầu tiên.",
                                        watchdog_stop_ts=watchdog_ts)
                        return {
                            "status": "BLOCKED",
                            "receipt": "CLAIMED_PARTIALLY_DELIVERED",
                            "claim_state": "CLAIMED_PARTIALLY_DELIVERED",
                            "recovery_policy": "NEW_LEASE_AND_NEW_MASTER_APPROVAL_REQUIRED",
                            "units_sent": sent,
                            "watchdog_stop_ts": watchdog_ts,
                            "reason": "Dừng khẩn cấp giữa chuỗi ký tự."
                        }
                    ok = user32.PostMessageW(edit_hwnd, WM_CHAR, unit, 0)
                    if _test_mode:
                        print(
                            f"[DISPATCH][POSTMESSAGE] lease_id={lease['lease_id']} "
                            f"unit_idx={sent} unit=0x{unit:04X} "
                            f"hwnd={edit_hwnd} ok={bool(ok)} "
                            f"ts={time.time():.6f}",
                            flush=True
                        )
                    if not ok:
                        if sent == 0:
                            return dict(not_delivered, reason="PostMessageW thất bại ở ký tự đầu tiên.")
                        return {
                            "status": "FAILED",
                            "receipt": "CLAIMED_PARTIALLY_DELIVERED",
                            "claim_state": "CLAIMED_PARTIALLY_DELIVERED",
                            "recovery_policy": "NEW_LEASE_AND_NEW_MASTER_APPROVAL_REQUIRED",
                            "units_sent": sent,
                            "reason": "PostMessageW thất bại giữa chuỗi."
                        }
                    sent += 1
                    # TEST MODE: trigger watchdog sau N ký tự (mid-dispatch injection)
                    if _test_mode and self._test_stop_after_chars > 0 and sent >= self._test_stop_after_chars:
                        _reason = self._test_stop_reason or "TEST_MID_DISPATCH_STOP"
                        self._test_stop_after_chars = 0  # single-use
                        print(
                            f"[DISPATCH][MID_STOP_TRIGGER] lease_id={lease['lease_id']} "
                            f"after_chars={sent} reason={_reason!r} ts={time.time():.6f}",
                            flush=True
                        )
                        self.watchdog.trigger_stop(_reason)
                        # Loop tiếp tục → kiểm tra watchdog.is_stopped ở đầu vòng tiếp theo
                    time.sleep(0.02)

                dispatch_done_ts = time.time()
                if _test_mode:
                    print(
                        f"[DISPATCH][DONE] lease_id={lease['lease_id']} "
                        f"units_sent={sent} elapsed_ms={(dispatch_done_ts - dispatch_start_ts)*1000:.1f} "
                        f"ts={dispatch_done_ts:.6f}",
                        flush=True
                    )

                # Chờ Notepad xử lý hết hàng đợi message rồi đọc lại
                after_text = ""
                is_verified = False
                deadline = time.time() + 2.0
                while time.time() < deadline:
                    after_text = self._read_text_content(hwnd)
                    if text_to_type in after_text:
                        is_verified = True
                        break
                    time.sleep(0.05)

                return {
                    "status": "DELIVERED_VERIFIED" if is_verified else "DELIVERED_UNVERIFIED",
                    "receipt": "MUTATION_DELIVERED",
                    "action": lease["action"],
                    "target_hwnd": hwnd,
                    "text_payload": text_to_type,
                    "verified_by_reader": is_verified,
                    "read_sample": after_text[:100] if after_text else "",
                    "units_sent": sent,
                    "claim_timestamp": claim_timestamp,
                    "dispatch_done_ts": dispatch_done_ts
                }

            except RuntimeError as e:
                # Re-raise TEST_CRASH_INJECTED để server trả 500 (crash simulation)
                err_msg = str(e)
                if "TEST_CRASH_INJECTED_AFTER_COMPOUND_CLAIM" in err_msg:
                    raise
                return {
                    "status": "FAILED",
                    "receipt": "CLAIMED_NOT_DELIVERED",
                    "claim_state": "CLAIMED_NOT_DELIVERED",
                    "recovery_policy": "NEW_LEASE_AND_NEW_MASTER_APPROVAL_REQUIRED",
                    "error": err_msg
                }
            except Exception as e:
                return {
                    "status": "FAILED",
                    "receipt": "CLAIMED_NOT_DELIVERED",
                    "claim_state": "CLAIMED_NOT_DELIVERED",
                    "recovery_policy": "NEW_LEASE_AND_NEW_MASTER_APPROVAL_REQUIRED",
                    "error": str(e)
                }

    def _read_text_content(self, hwnd: int) -> str:
        """Đọc độc lập nội dung text của cửa sổ đích (Notepad/WordPad) để làm After-State Verifier."""
        try:
            WM_GETTEXTLENGTH = 0x000E
            WM_GETTEXT = 0x000D
            target_read_hwnd = self._find_text_control(hwnd) or hwnd
            
            length = user32.SendMessageW(target_read_hwnd, WM_GETTEXTLENGTH, 0, 0)
            if length <= 0:
                return ""
            buffer = ctypes.create_unicode_buffer(length + 1)
            user32.SendMessageW(target_read_hwnd, WM_GETTEXT, length + 1, ctypes.byref(buffer))
            return buffer.value
        except Exception:
            return ""
