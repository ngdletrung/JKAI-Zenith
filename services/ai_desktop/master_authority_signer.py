# -*- coding: utf-8 -*-
"""
services/ai_desktop/master_authority_signer.py
[JKAI MASTER AUTHORITY SIGNER - HITL CRYPTOGRAPHIC AUTHORITY ISSUER]
Nắm giữ Private Key của Master Authority để ký phát hành approval envelopes.
Chỉ chạy phía Master / HITL, hoàn toàn cách ly khỏi tiến trình pilot thực thi.
"""

import base64
import json
import os
import time
from typing import Any, Dict, Optional

from cryptography.hazmat.primitives.asymmetric import ed25519

REPO_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
DEFAULT_SECRET_KEY_PATH = os.path.join(REPO_ROOT, "data", "secrets", "master_authority_key.json")


def canonical_serialize(obj: Dict[str, Any]) -> bytes:
    """Serialize từ điển thành Deterministic Canonical JSON bytes."""
    return json.dumps(obj, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")


class MasterAuthoritySigner:
    """
    Đại diện cho Thẩm quyền Tối cao của Master (HITL).
    Nắm giữ PRIVATE KEY để ký phát hành Master Approval Envelope.
    """

    def __init__(self, key_path: Optional[str] = None):
        self.key_path = key_path or DEFAULT_SECRET_KEY_PATH
        if not os.path.exists(self.key_path):
            raise RuntimeError(f"FAIL_CLOSED: Không tìm thấy khóa riêng của Master tại: {self.key_path}")

        try:
            with open(self.key_path, "r", encoding="utf-8") as f:
                data = json.load(f)
        except Exception as e:
            raise RuntimeError(f"FAIL_CLOSED: Lỗi đọc tệp khóa riêng Master: {e}")

        self.key_id = data.get("key_id", "master_primary_v1")
        priv_b64 = data.get("private_key_b64")
        if not priv_b64:
            raise RuntimeError("FAIL_CLOSED: Thiếu private_key_b64 trong tệp khóa riêng Master.")

        raw_priv = base64.b64decode(priv_b64)
        if len(raw_priv) != 32:
            raise RuntimeError("FAIL_CLOSED: Ed25519 private key phải có đúng 32 bytes.")

        self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_priv)
        self.public_key_b64 = data.get("public_key_b64")
        self.fingerprint_sha256 = data.get("fingerprint_sha256")

    def build_mutation_approval_payload(
        self,
        lease_id: str,
        nonce: str,
        hwnd: int,
        target_pid: int,
        proc_name: str,
        action: str,
        text_payload: str,
        session_id: str,
        lease_expires_at: float,
        ttl_seconds: float = 60.0
    ) -> Dict[str, Any]:
        """Build the canonical approval payload (expires_at bounded by the lease)."""
        now = time.time()
        expires_at = min(now + ttl_seconds, lease_expires_at)
        return {
            "action": action,
            "expires_at": expires_at,
            "hwnd": hwnd,
            "lease_expires_at": lease_expires_at,
            "lease_id": lease_id,
            "nonce": nonce,
            "proc_name": proc_name,
            "session_id": session_id,
            "target_pid": target_pid,
            "text_payload": text_payload,
            "worker_generation": "master_gen_01",
        }

    def sign_payload(self, payload: Dict[str, Any]) -> str:
        """Sign a canonical payload and return the base64url approval envelope."""
        canonical_bytes = canonical_serialize(payload)
        sig_bytes = self._private_key.sign(canonical_bytes)
        envelope = {
            "key_id": self.key_id,
            "canonical_payload": payload,
            "signature": base64.b64encode(sig_bytes).decode("utf-8"),
        }
        return base64.urlsafe_b64encode(json.dumps(envelope).encode("utf-8")).decode("utf-8")

    def sign_receipt(self, receipt_bytes: bytes) -> Dict[str, str]:
        """
        Sign an execution receipt digest. The verifier side only needs the public key,
        so a receipt signed here proves the HITL authority witnessed the execution record.
        """
        return {
            "key_id": self.key_id,
            "signature_b64": base64.b64encode(self._private_key.sign(receipt_bytes)).decode("utf-8"),
        }

    def issue_mutation_approval(
        self,
        lease_id: str,
        nonce: str,
        hwnd: int,
        target_pid: int,
        proc_name: str,
        action: str,
        text_payload: str,
        session_id: str,
        lease_expires_at: float,
        ttl_seconds: float = 60.0
    ) -> str:
        """
        Ký phát hành Master Approval Envelope bằng Ed25519 trên Canonical JSON.
        Bảo đảm quy tắc: expires_at <= lease_expires_at.
        """
        payload = self.build_mutation_approval_payload(
            lease_id=lease_id,
            nonce=nonce,
            hwnd=hwnd,
            target_pid=target_pid,
            proc_name=proc_name,
            action=action,
            text_payload=text_payload,
            session_id=session_id,
            lease_expires_at=lease_expires_at,
            ttl_seconds=ttl_seconds,
        )
        return self.sign_payload(payload)
