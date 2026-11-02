# -*- coding: utf-8 -*-
"""
scripts/master_approval_verifier.py
[JKAI ASYMMETRIC MASTER APPROVAL VERIFIER - PUBLIC KEY ONLY MODULE v2.3]

Nguyên tắc an ninh tối thượng:
1. Public Key Only Boundary:
   - Module này CHỈ import Ed25519PublicKey từ cryptography.
   - Tuyệt đối KHÔNG có bất kỳ tham chiếu hay import nào tới Ed25519PrivateKey!
2. Exact Envelope & Payload Schema:
   - Enforce exact envelope keys {"payload", "signature"} và {"canonical_payload", "signature"}.
   - Enforce exact payload keys (reject mọi unknown keys lạ hoặc thiếu required keys).
3. Anti-Bool & Finite Numeric Type Checking:
   - Chặn đứng hoàn toàn việc Python coi bool là subclass của int (reject bool).
   - Chặn đứng NaN và Infinity bằng math.isfinite().
4. Mandatory Trusted Session Binding:
   - Bắt buộc expected_session_id không rỗng, từ chối mọi yêu cầu thiếu session ID tin cậy.
5. Strict Expiry Rule:
   - approval_expires_at <= lease_expires_at (không có bất kỳ tolerance window nào).
   - Clock skew check: issued_at <= now + 1.0s.
"""

import os
import sys
import time
import json
import base64
import math
from typing import Dict, Any, Optional, Tuple, Set

from cryptography.hazmat.primitives.asymmetric import ed25519
from cryptography.exceptions import InvalidSignature

from scripts.persistent_nonce_store import PersistentNonceStore

AUTH_ENVELOPE_KEYS: Set[str] = {"payload", "signature"}
APPROVAL_ENVELOPE_KEYS: Set[str] = {"canonical_payload", "signature"}

AUTH_REQUIRED_KEYS: Set[str] = {
    "session_id", "caller_id", "nonce", "issued_at", "expires_at"
}

ACTIVATION_REQUIRED_KEYS: Set[str] = {
    "session_id", "caller_id", "nonce", "issued_at", "expires_at", "target_hwnd", "scope"
}

APPROVAL_REQUIRED_KEYS: Set[str] = {
    "action", "element_ref", "expires_at", "hwnd", "lease_expires_at", "lease_id",
    "nonce", "proc_name", "scroll_direction", "scroll_steps", "scroll_unit",
    "session_id", "target_pid", "text_payload", "worker_generation"
}

SCROLL_DIRECTIONS: Set[str] = {"up", "down"}
SCROLL_UNITS: Set[str] = {"page", "line"}
MAX_SCROLL_STEPS: int = 5

def is_valid_int(val: Any) -> bool:
    """Kiểm tra giá trị là int thực sự, tuyệt đối không chấp nhận bool."""
    return type(val) is int and not isinstance(val, bool)

def is_valid_numeric(val: Any) -> bool:
    """Kiểm tra giá trị là số hợp lệ (int hoặc float hữu hạn), tuyệt đối không nhận bool/NaN/Inf."""
    if isinstance(val, bool):
        return False
    if isinstance(val, (int, float)):
        return math.isfinite(val)
    return False

def canonical_serialize(obj: Dict[str, Any]) -> bytes:
    """Serialize từ điển thành Deterministic Canonical JSON bytes."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode("utf-8")

class MasterApprovalVerifier:
    """
    Nằm trong Worker process.
    CHỈ NẮM GIỮ PUBLIC KEY CỦA MASTER.
    Verification-Only: Tuyệt đối không thể sinh chữ ký.
    """
    def __init__(self, public_key_b64: Optional[str] = None, nonce_store: Optional[PersistentNonceStore] = None):
        if public_key_b64 is None:
            public_key_b64 = os.getenv("JKAI_MASTER_PUBLIC_KEY")
            
        if not public_key_b64:
            raise RuntimeError(
                "FAIL_CLOSED: Thiếu biến môi trường bắt buộc 'JKAI_MASTER_PUBLIC_KEY' (Ed25519 raw 32 bytes base64). "
                "Master Approval Verifier từ chối khởi động mà không có khóa công khai của Master."
            )
            
        try:
            raw_bytes = base64.b64decode(public_key_b64)
            if len(raw_bytes) != 32:
                raise ValueError("Ed25519 public key raw bytes must be exactly 32 bytes.")
            self._public_key = ed25519.Ed25519PublicKey.from_public_bytes(raw_bytes)
        except Exception as e:
            raise RuntimeError(f"FAIL_CLOSED: Khóa công khai Ed25519 của Master không hợp lệ: {e}")

        self._nonce_store = nonce_store if nonce_store is not None else PersistentNonceStore()
        self._used_auth_nonces: set = set()

    def claim_approval_nonce(self, nonce: str, ttl_seconds: float = 60.0) -> bool:
        """Tiêu thụ nguyên tử approval nonce tại thời điểm dispatch cuối cùng."""
        return self._nonce_store.check_and_use_nonce(f"app_sig_{nonce}", scope="approval", ttl_seconds=ttl_seconds)

    def claim_compound_nonces_atomic(
        self,
        approval_nonce: str,
        exec_nonce: str,
        ttl_seconds: float = 60.0
    ) -> bool:
        """
        Tiêu thụ đồng thời Master Approval Nonce và Worker Exec Nonce trong 1 transaction ACID duy nhất.
        Khi approval_nonce == exec_nonce (cùng 1 nonce string), dùng two-scope atomic method để tránh
        PRIMARY KEY collision trong SQLite (app_sig_<nonce> vs worker_exec_<nonce> là hai keys khác nhau).
        """
        if approval_nonce == exec_nonce:
            # Cùng 1 nonce string → dùng hai scope-prefix khác nhau làm composite key
            return self._nonce_store.check_and_use_single_nonce_with_two_scopes_atomic(
                nonce=approval_nonce,
                scope1="app_sig",
                scope2="worker_exec",
                ttl_seconds=ttl_seconds
            )
        else:
            return self._nonce_store.check_and_use_two_nonces_atomic(
                nonce1=f"app_sig_{approval_nonce}",
                scope1="approval",
                nonce2=f"worker_exec_{exec_nonce}",
                scope2="worker_exec",
                ttl_seconds=ttl_seconds
            )

    def verify_master_auth_token(
        self,
        token_str: str,
        expected_session_id: str
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Xác thực tính hợp lệ của Master Auth Token (Tầng 1).
        Enforce Exact Envelope, Exact Payload Schema, Anti-Bool/Finite Types, Clock Skew, Mandatory Session.
        """
        if not token_str:
            return False, "TOKEN_EMPTY", {}
            
        if not expected_session_id or not expected_session_id.strip():
            return False, "MANDATORY_EXPECTED_SESSION_MISSING", {}
            
        try:
            raw_json = base64.urlsafe_b64decode(token_str.encode("utf-8")).decode("utf-8")
            token_data = json.loads(raw_json)
            
            # 1. Exact Envelope Schema Validation
            envelope_keys = set(token_data.keys())
            if envelope_keys != AUTH_ENVELOPE_KEYS:
                return False, f"ENVELOPE_SCHEMA_INVALID: expected {sorted(list(AUTH_ENVELOPE_KEYS))}, got {sorted(list(envelope_keys))}", {}
                
            payload = token_data["payload"]
            sig_b64 = token_data["signature"]
            
            if not isinstance(payload, dict):
                return False, "PAYLOAD_TYPE_INVALID: payload must be dict", {}
            if not isinstance(sig_b64, str):
                return False, "SIGNATURE_TYPE_INVALID: signature must be str", {}

            # 2. Exact Payload Schema Validation
            keys = set(payload.keys())
            if keys != AUTH_REQUIRED_KEYS:
                unknown = keys - AUTH_REQUIRED_KEYS
                missing = AUTH_REQUIRED_KEYS - keys
                if unknown:
                    return False, f"TOKEN_UNKNOWN_KEYS: {sorted(list(unknown))}", payload
                if missing:
                    return False, f"TOKEN_MISSING_REQUIRED_KEYS: {sorted(list(missing))}", payload
                    
            # 3. Anti-Bool & Strict Type Validation
            if not isinstance(payload["session_id"], str) or not payload["session_id"].strip():
                return False, "TOKEN_TYPE_INVALID: session_id must be non-empty str", payload
            if not isinstance(payload["caller_id"], str) or not payload["caller_id"].strip():
                return False, "TOKEN_TYPE_INVALID: caller_id must be non-empty str", payload
            if not isinstance(payload["nonce"], str) or not payload["nonce"].strip():
                return False, "TOKEN_TYPE_INVALID: nonce must be non-empty str", payload
            if not is_valid_numeric(payload["issued_at"]):
                return False, "TOKEN_TYPE_INVALID: issued_at must be valid finite numeric (not bool/nan)", payload
            if not is_valid_numeric(payload["expires_at"]):
                return False, "TOKEN_TYPE_INVALID: expires_at must be valid finite numeric (not bool/nan)", payload
                
            sig_bytes = base64.b64decode(sig_b64)
            canonical_bytes = canonical_serialize(payload)
            
            # 4. Xác thực chữ ký Ed25519 bằng Public Key
            self._public_key.verify(sig_bytes, canonical_bytes)
            
            # 5. Clock Skew & TTL Bounds Check
            now = time.time()
            issued_at = float(payload["issued_at"])
            expires_at = float(payload["expires_at"])
            
            if issued_at > now + 1.0:
                return False, f"TOKEN_FUTURE_ISSUED: issued_at is {issued_at - now:.2f}s in future", payload
                
            ttl = expires_at - issued_at
            if ttl < 1.0 or ttl > 120.0:
                return False, f"TOKEN_TTL_OUT_OF_BOUNDS: ttl={ttl:.1f}s", payload
                
            # 6. Kiểm tra hạn dùng
            if now > expires_at:
                return False, "TOKEN_EXPIRED", payload
                
            # 7. Bắt buộc khớp expected_session_id
            if payload["session_id"] != expected_session_id:
                return False, f"TOKEN_SESSION_MISMATCH: expected {expected_session_id}, got {payload['session_id']}", payload
                
            # 8. Kiểm tra chống Replay Attack ở Tầng 1 (Lớp kép: In-Memory + Persistent Store)
            nonce = payload["nonce"]
            if nonce in self._used_auth_nonces or not self._nonce_store.check_and_use_nonce(f"auth_{nonce}", scope="master_auth", ttl_seconds=ttl):
                return False, "REPLAY_AUTH_TOKEN_DETECTED", payload
                
            self._used_auth_nonces.add(nonce)
            return True, "TOKEN_VALID", payload
            
        except InvalidSignature:
            return False, "INVALID_TOKEN_SIGNATURE", {}
        except Exception as e:
            return False, f"TOKEN_PARSE_ERROR: {e}", {}

    def verify_mutation_approval(
        self,
        approval_token_b64: str,
        lease_id: str,
        nonce: str,
        hwnd: int,
        target_pid: int,
        proc_name: str,
        action: str,
        text_payload: str,
        worker_generation: str,
        lease_expires_at: float,
        session_id: str,
        element_ref: str = "",
        scroll_direction: str = "",
        scroll_unit: str = "",
        scroll_steps: int = 0,
        consume_nonce: bool = False
    ) -> Tuple[bool, str]:
        """
        Kiểm tra chữ ký phê duyệt của Master bằng Public Key (Tầng 2).
        Enforce Exact Envelope, Exact Schema, Anti-Bool/Finite Types, Strict Expiry Rule.
        """
        if not approval_token_b64:
            return False, "MISSING_APPROVAL_TOKEN"
            
        try:
            raw_json = base64.urlsafe_b64decode(approval_token_b64.encode("utf-8")).decode("utf-8")
            token_data = json.loads(raw_json)
            
            # 1. Exact Envelope Schema Validation
            envelope_keys = set(token_data.keys())
            if envelope_keys != APPROVAL_ENVELOPE_KEYS:
                return False, f"APPROVAL_ENVELOPE_INVALID: expected {sorted(list(APPROVAL_ENVELOPE_KEYS))}, got {sorted(list(envelope_keys))}"

            payload = token_data["canonical_payload"]
            sig_b64 = token_data["signature"]

            if not isinstance(payload, dict):
                return False, "APPROVAL_PAYLOAD_NOT_DICT"
            if not isinstance(sig_b64, str):
                return False, "APPROVAL_SIGNATURE_NOT_STR"

            # 2. Exact Payload Schema Validation
            keys = set(payload.keys())
            if keys != APPROVAL_REQUIRED_KEYS:
                unknown = keys - APPROVAL_REQUIRED_KEYS
                missing = APPROVAL_REQUIRED_KEYS - keys
                if unknown:
                    return False, f"APPROVAL_UNKNOWN_KEYS: {sorted(list(unknown))}"
                if missing:
                    return False, f"APPROVAL_MISSING_REQUIRED_KEYS: {sorted(list(missing))}"

            # 3. Anti-Bool & Strict Type Validation
            if not isinstance(payload["action"], str):
                return False, "APPROVAL_TYPE_INVALID: action must be str"
            if not isinstance(payload["element_ref"], str):
                return False, "APPROVAL_TYPE_INVALID: element_ref must be str"
            if not is_valid_numeric(payload["expires_at"]):
                return False, "APPROVAL_TYPE_INVALID: expires_at must be valid finite numeric (not bool/nan)"
            if not is_valid_int(payload["hwnd"]):
                return False, "APPROVAL_TYPE_INVALID: hwnd must be int (not bool)"
            if not is_valid_numeric(payload["lease_expires_at"]):
                return False, "APPROVAL_TYPE_INVALID: lease_expires_at must be valid finite numeric (not bool/nan)"
            if not isinstance(payload["lease_id"], str):
                return False, "APPROVAL_TYPE_INVALID: lease_id must be str"
            if not isinstance(payload["nonce"], str):
                return False, "APPROVAL_TYPE_INVALID: nonce must be str"
            if not isinstance(payload["proc_name"], str):
                return False, "APPROVAL_TYPE_INVALID: proc_name must be str"
            if not isinstance(payload["session_id"], str):
                return False, "APPROVAL_TYPE_INVALID: session_id must be str"
            if not is_valid_int(payload["target_pid"]):
                return False, "APPROVAL_TYPE_INVALID: target_pid must be int (not bool)"
            if not isinstance(payload["text_payload"], str):
                return False, "APPROVAL_TYPE_INVALID: text_payload must be str"
            if not isinstance(payload["worker_generation"], str):
                return False, "APPROVAL_TYPE_INVALID: worker_generation must be str"
            if not isinstance(payload["scroll_direction"], str):
                return False, "APPROVAL_TYPE_INVALID: scroll_direction must be str"
            if not isinstance(payload["scroll_unit"], str):
                return False, "APPROVAL_TYPE_INVALID: scroll_unit must be str"
            if not is_valid_int(payload["scroll_steps"]):
                return False, "APPROVAL_TYPE_INVALID: scroll_steps must be int (not bool)"

            # 3.1 Scroll Semantics: chỉ action 'scroll' được mang tham số scroll
            signed_direction = payload["scroll_direction"]
            signed_unit = payload["scroll_unit"]
            signed_steps = payload["scroll_steps"]
            if payload["action"] == "scroll":
                if signed_direction not in SCROLL_DIRECTIONS:
                    return False, f"APPROVAL_SCROLL_DIRECTION_INVALID: {signed_direction!r}"
                if signed_unit not in SCROLL_UNITS:
                    return False, f"APPROVAL_SCROLL_UNIT_INVALID: {signed_unit!r}"
                if signed_steps < 1 or signed_steps > MAX_SCROLL_STEPS:
                    return False, f"APPROVAL_SCROLL_STEPS_INVALID: {signed_steps}"
            elif signed_direction != "" or signed_unit != "" or signed_steps != 0:
                return False, "APPROVAL_SCROLL_PARAMS_FORBIDDEN_FOR_NON_SCROLL_ACTION"

            sig_bytes = base64.b64decode(sig_b64)
            canonical_bytes = canonical_serialize(payload)
            
            # 4. Xác thực chữ ký Ed25519
            self._public_key.verify(sig_bytes, canonical_bytes)
            
            # 5. Strict Expiry Rule (Tuyệt đối không được vượt quá lease expiry)
            now = time.time()
            approval_expires_at = float(payload["expires_at"])
            if now > approval_expires_at:
                return False, "APPROVAL_SIGNATURE_EXPIRED"
                
            if approval_expires_at > lease_expires_at:
                return False, f"APPROVAL_EXPIRY_EXCEEDS_LEASE_EXPIRY: {approval_expires_at:.2f} > {lease_expires_at:.2f}"

            # 5.1. Persistent Anti-Replay Check (Chưa tiêu thụ nếu thông số sai)
            approval_nonce = payload["nonce"]
            approval_ttl = max(1.0, approval_expires_at - now)
            if self._nonce_store.is_nonce_used(f"app_sig_{approval_nonce}"):
                return False, "REPLAY_APPROVAL_SIGNATURE_DETECTED"
                
            # 6. Đối chiếu chặt chẽ từng trường dữ liệu với lease thực tế
            if payload["lease_id"] != lease_id:
                return False, "LEASE_ID_MISMATCH"
            if payload["nonce"] != nonce:
                return False, "NONCE_MISMATCH"
            if payload["hwnd"] != hwnd:
                return False, "HWND_MISMATCH"
            if payload["target_pid"] != target_pid:
                return False, "PID_MISMATCH"
            if payload["proc_name"] != proc_name:
                return False, "PROC_NAME_MISMATCH"
            if payload["action"] != action:
                return False, "ACTION_MISMATCH"
            if payload["element_ref"] != element_ref:
                return False, "ELEMENT_REF_MISMATCH"
            if signed_direction != scroll_direction:
                return False, "SCROLL_DIRECTION_MISMATCH"
            if signed_unit != scroll_unit:
                return False, "SCROLL_UNIT_MISMATCH"
            if signed_steps != scroll_steps:
                return False, "SCROLL_STEPS_MISMATCH"
            if payload["text_payload"] != text_payload:
                return False, "TEXT_PAYLOAD_MISMATCH"
            if payload["worker_generation"] != worker_generation:
                return False, "WORKER_GENERATION_MISMATCH"
            if payload["session_id"] != session_id:
                return False, "SESSION_ID_MISMATCH"
            if abs(float(payload["lease_expires_at"]) - lease_expires_at) > 0.001:
                return False, "LEASE_EXPIRES_AT_MISMATCH"
                
            # Đánh dấu tiêu thụ nonce hợp lệ chỉ khi consume_nonce=True (Atomic Claim chống race condition)
            if consume_nonce:
                claimed = self._nonce_store.check_and_use_nonce(f"app_sig_{approval_nonce}", scope="approval", ttl_seconds=approval_ttl)
                if not claimed:
                    return False, "REPLAY_APPROVAL_SIGNATURE_DETECTED"
            return True, "APPROVAL_VERIFIED"
            
        except InvalidSignature:
            return False, "INVALID_MASTER_APPROVAL_SIGNATURE"
        except Exception as e:
            return False, f"APPROVAL_PARSE_ERROR: {e}"

    def verify_and_claim_activation_token(
        self,
        token_str: str,
        expected_session_id: str,
        expected_target_hwnd: int
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Xác thực và Durable Atomic Claim Master One-Shot Activation Token (Finding 2, 3, 4):
        - Kiểm tra chữ ký Ed25519 bằng Master Public Key
        - Ràng buộc cứng target_hwnd và session_id trong payload đã ký (reject nếu mismatch)
        - Kiểm tra TTL nghiêm ngặt (reject nếu ngoài [1.0s, 300.0s], không clamp)
        - Atomic Persistent Claim chống replay qua SQLite durable store
        """
        if not token_str:
            return False, "TOKEN_EMPTY", {}
        try:
            raw_json = base64.urlsafe_b64decode(token_str.encode("utf-8")).decode("utf-8")
            token_data = json.loads(raw_json)
            if set(token_data.keys()) != AUTH_ENVELOPE_KEYS:
                return False, "ENVELOPE_SCHEMA_INVALID", {}
            payload = token_data["payload"]
            sig_b64 = token_data["signature"]
            if not isinstance(payload, dict) or not isinstance(sig_b64, str):
                return False, "TOKEN_SCHEMA_INVALID", {}
            if set(payload.keys()) != ACTIVATION_REQUIRED_KEYS:
                return False, "TOKEN_SCHEMA_INVALID", payload
            if not isinstance(payload["session_id"], str) or not payload["session_id"].strip():
                return False, "TOKEN_SESSION_INVALID", payload
            if not isinstance(payload["caller_id"], str) or not payload["caller_id"].strip():
                return False, "TOKEN_CALLER_INVALID", payload
            if not isinstance(payload["nonce"], str) or not payload["nonce"].strip():
                return False, "TOKEN_NONCE_INVALID", payload
            if not is_valid_numeric(payload["issued_at"]) or not is_valid_numeric(payload["expires_at"]):
                return False, "TOKEN_TIME_INVALID", payload
            if not is_valid_int(payload["target_hwnd"]):
                return False, "TOKEN_TARGET_HWND_INVALID", payload

            # 1. Xác thực chữ ký Ed25519 bằng Public Key
            canonical_bytes = canonical_serialize(payload)
            sig_bytes = base64.b64decode(sig_b64)
            self._public_key.verify(sig_bytes, canonical_bytes)

            now = time.time()
            issued_at = float(payload["issued_at"])
            expires_at = float(payload["expires_at"])
            ttl = expires_at - issued_at
            if issued_at > now + 1.0 or expires_at <= issued_at:
                return False, "TOKEN_TIME_INVALID", payload

            # 2. Strict TTL Bounds Check (Reject nếu ngoài khoảng [1.0, 300.0], tuyệt đối không clamp)
            if ttl < 1.0 or ttl > 300.0:
                return False, f"TOKEN_TTL_OUT_OF_BOUNDS: {ttl:.2f}s (must be between 1.0s and 300.0s)", payload

            if now > expires_at:
                return False, "TOKEN_EXPIRED", payload

            # 3. Ràng buộc cứng session_id
            if payload.get("session_id") != expected_session_id:
                return False, f"TOKEN_SESSION_MISMATCH: expected {expected_session_id}, got {payload.get('session_id')}", payload

            # 4. Ràng buộc cứng target_hwnd
            if int(payload.get("target_hwnd", 0)) != int(expected_target_hwnd):
                return False, f"TOKEN_TARGET_HWND_MISMATCH: expected {expected_target_hwnd}, got {payload.get('target_hwnd')}", payload

            # 5. Durable Atomic Claim chống replay qua SQLite durable store
            nonce = payload.get("nonce", "")
            if not self._nonce_store.check_and_use_nonce(f"act_{nonce}", scope="master_activation", ttl_seconds=ttl):
                return False, "REPLAY_ACTIVATION_TOKEN_DETECTED", payload

            return True, "ACTIVATION_TOKEN_VALID", payload
        except InvalidSignature:
            return False, "INVALID_TOKEN_SIGNATURE", {}
        except Exception as e:
            return False, f"ACTIVATION_TOKEN_PARSE_ERROR: {e}", {}
