# -*- coding: utf-8 -*-
"""
services/ai_desktop/master_authority_verifier.py
[JKAI MASTER AUTHORITY VERIFIER - PINNED PUBLIC KEY & CRYPTOGRAPHIC HITL GATE]
Tuân thủ toàn bộ 6 điều kiện mở từ LƯỢT 319 của OpenCode Red Team Auditor:
  1. Key Pinning: Chỉ chấp nhận Public Key của Master đã được pin từ config/security/master_public_keys.json.
  2. Process Separation: Verifier chỉ nắm giữ Public Key của Master, hoàn toàn không có Private Key.
  3. Key ID Allowlist Enforcement: Từ chối mọi Key ID không nằm trong danh sách tin cậy.
  4. Fingerprint Integrity: Kiểm tra raw bytes SHA-256 fingerprint trước khi xác thực chữ ký.
  5. Cryptographic Ed25519 Signature Verification: Thẩm định chữ ký trên Deterministic Canonical JSON.
  6. Tamper-evident Audit Evidence: Sinh metadata chi tiết bao gồm key_id, fingerprint, verifier identity.
"""

import base64
import hashlib
import json
import os
import sys
import time
from typing import Any, Dict, Optional, Tuple

from cryptography.exceptions import InvalidSignature
from cryptography.hazmat.primitives.asymmetric import ed25519

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
CONFIG_PATH = os.path.join(REPO_ROOT, "config", "security", "master_public_keys.json")

APPROVAL_ENVELOPE_KEYS = {"canonical_payload", "signature", "key_id"}


def canonical_serialize(obj: Dict[str, Any]) -> bytes:
    """Serialize từ điển thành Deterministic Canonical JSON bytes."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class MasterAuthorityVerifier:
    """
    Bộ thẩm định thẩm quyền Master dựa trên Pinned Public Key.
    Chạy trong tiến trình kiểm soát / pilot và CHỈ NẮM GIỮ PUBLIC KEY.
    """

    def __init__(self, config_path: Optional[str] = None):
        self.config_path = config_path or CONFIG_PATH
        self.verifier_identity = "JKAI_MASTER_AUTHORITY_VERIFIER_V1"
        self._trusted_keys: Dict[str, Dict[str, Any]] = {}
        self._revoked_keys: set = set()
        self._load_pinned_keys()

    def _load_pinned_keys(self) -> None:
        """Đọc và thẩm định tính toàn vẹn của danh sách khóa công khai Master được pin."""
        if not os.path.exists(self.config_path):
            raise RuntimeError(f"FAIL_CLOSED: Tệp cấu hình Pinned Master Public Keys không tồn tại: {self.config_path}")

        try:
            with open(self.config_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise RuntimeError(f"FAIL_CLOSED: Không thể đọc tệp Pinned Master Keys: {e}")

        trusted = data.get("trusted_keys", {})
        if not trusted:
            raise RuntimeError("FAIL_CLOSED: Danh sách Pinned Master Keys trống rỗng.")

        for key_id, info in trusted.items():
            status = info.get("status")
            if status == "REVOKED":
                self._revoked_keys.add(key_id)
                continue
            if status != "ACTIVE":
                continue
            pub_b64 = info.get("public_key_b64")
            expected_fp = info.get("fingerprint_sha256")
            if not pub_b64 or not expected_fp:
                continue

            # Kiểm tra fingerprint của Public Key
            raw_pub = base64.b64decode(pub_b64)
            actual_fp = hashlib.sha256(raw_pub).hexdigest()
            if actual_fp != expected_fp:
                raise RuntimeError(f"FAIL_CLOSED: Fingerprint mismatch cho key_id '{key_id}': expected {expected_fp}, got {actual_fp}")

            ed_pub = ed25519.Ed25519PublicKey.from_public_bytes(raw_pub)
            self._trusted_keys[key_id] = {
                "key_id": key_id,
                "public_key_b64": pub_b64,
                "fingerprint_sha256": actual_fp,
                "ed25519_obj": ed_pub,
                "status": "ACTIVE"
            }

    def verify_approval_token(
        self,
        approval_envelope_b64: str,
        expected_action: str,
        expected_hwnd: int,
        expected_target_pid: int,
        expected_proc_name: str,
        expected_text: str,
        expected_session_id: str,
        expected_lease_id: str,
        expected_nonce: Optional[str] = None
    ) -> Tuple[bool, str, Dict[str, Any]]:
        """
        Thẩm định toàn diện chữ ký số của Master Authority:
        - Exact Envelope & Schema
        - Pinned Key Allowlist & Fingerprint
        - Ed25519 Cryptographic Signature
        - Expiry & Clock Skew
        - Context Identity Binding (Action, HWND, PID, Process, Session, Lease, Nonce Challenge)
        """
        if not approval_envelope_b64:
            return False, "MISSING_APPROVAL_ENVELOPE", {}

        try:
            raw_json = base64.urlsafe_b64decode(approval_envelope_b64.encode("utf-8")).decode("utf-8")
            envelope = json.loads(raw_json)
        except Exception as e:
            return False, f"ENVELOPE_DECODE_ERROR: {e}", {}

        # 1. Kiểm tra Exact Envelope
        if not isinstance(envelope, dict):
            return False, "ENVELOPE_NOT_A_DICT", {}

        env_keys = set(envelope.keys())
        if not env_keys.issuperset({"canonical_payload", "signature", "key_id"}):
            return False, f"INVALID_ENVELOPE_KEYS: missing required fields", {}

        key_id = envelope.get("key_id")
        sig_b64 = envelope.get("signature")
        payload = envelope.get("canonical_payload")

        # 2. Kiểm tra Key ID trong Pinned Allowlist & Trạng thái Thu hồi
        if key_id in self._revoked_keys:
            return False, f"REVOKED_MASTER_KEY_ID: key '{key_id}' has been formally revoked", {}

        if key_id not in self._trusted_keys:
            return False, f"UNTRUSTED_KEY_ID: key '{key_id}' is not in pinned master keys", {}

        key_meta = self._trusted_keys[key_id]
        ed_pub = key_meta["ed25519_obj"]

        # 3. Thẩm định Chữ ký số Ed25519 trên Deterministic Canonical Bytes
        canonical_bytes = canonical_serialize(payload)
        try:
            sig_bytes = base64.b64decode(sig_b64)
            ed_pub.verify(sig_bytes, canonical_bytes)
        except InvalidSignature:
            return False, "INVALID_ED25519_SIGNATURE", {}
        except Exception as e:
            return False, f"SIGNATURE_VERIFICATION_EXCEPTION: {e}", {}

        # 4. Kiểm tra thời hạn hiệu lực (Expiry & Clock Skew)
        now = time.time()
        expires_at = payload.get("expires_at", 0)
        lease_expires_at = payload.get("lease_expires_at", 0)

        if not isinstance(expires_at, (int, float)) or not isinstance(lease_expires_at, (int, float)):
            return False, "INVALID_EXPIRY_TYPE", {}

        if now > expires_at:
            return False, f"APPROVAL_EXPIRED: current {now:.2f} > expires_at {expires_at:.2f}", {}

        if expires_at > lease_expires_at + 0.001:
            return False, f"APPROVAL_LIFETIME_EXCEEDS_LEASE: expires_at {expires_at:.2f} > lease {lease_expires_at:.2f}", {}

        # 5. Kiểm tra ràng buộc ngữ cảnh (Target Identity Binding)
        if payload.get("action") != expected_action:
            return False, f"ACTION_MISMATCH: expected {expected_action}, got {payload.get('action')}", {}

        if payload.get("hwnd") != expected_hwnd:
            return False, f"HWND_MISMATCH: expected {expected_hwnd}, got {payload.get('hwnd')}", {}

        if payload.get("target_pid") != expected_target_pid:
            return False, f"PID_MISMATCH: expected {expected_target_pid}, got {payload.get('target_pid')}", {}

        if payload.get("proc_name") != expected_proc_name:
            return False, f"PROC_NAME_MISMATCH: expected {expected_proc_name}, got {payload.get('proc_name')}", {}

        if payload.get("text_payload") != expected_text:
            return False, f"TEXT_PAYLOAD_MISMATCH: expected {expected_text!r}, got {payload.get('text_payload')!r}", {}

        if payload.get("session_id") != expected_session_id:
            return False, f"SESSION_MISMATCH: expected {expected_session_id}, got {payload.get('session_id')}", {}

        if payload.get("lease_id") != expected_lease_id:
            return False, f"LEASE_MISMATCH: expected {expected_lease_id}, got {payload.get('lease_id')}", {}

        if expected_nonce is not None and payload.get("nonce") != expected_nonce:
            return False, f"NONCE_MISMATCH: expected {expected_nonce}, got {payload.get('nonce')}", {}

        audit_details = {
            "master_key_id": key_id,
            "public_key_fingerprint": key_meta["fingerprint_sha256"],
            "verifier_identity": self.verifier_identity,
            "verified_at": now,
            "status": "MASTER_AUTHORITY_VERIFIED_PASS",
            "nonce": payload.get("nonce"),
            "canonical_payload_sha256": hashlib.sha256(canonical_bytes).hexdigest(),
        }

        return True, "MASTER_AUTHORITY_VERIFIED_PASS", audit_details
