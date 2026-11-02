# -*- coding: utf-8 -*-
"""
scripts/master_approval_signer.py
[JKAI MASTER APPROVAL SIGNER - PRIVATE KEY ONLY MODULE v2.3]

Nguyên tắc an ninh:
1. Private Key Only Boundary:
   - Module này chỉ dùng cho phía Master (Human-In-The-Loop).
   - Nắm giữ Ed25519PrivateKey để ký phát hành Auth Token và Approval Signature.
   - Hoàn toàn tách biệt khỏi worker verifier (scripts/master_approval_verifier.py).
2. Deterministic Canonical JSON Serialization:
   - Sử dụng json.dumps(..., sort_keys=True, separators=(',', ':'), ensure_ascii=False).
3. Signer Strict Expiry Enforcement:
   - Không thể ký phát hành approval có thời hạn vượt quá hạn của lease (fail-closed trước khi ký).
"""

import os
import sys
import time
import json
import base64
import uuid
import math
from typing import Dict, Any, Optional, Tuple

from cryptography.hazmat.primitives.asymmetric import ed25519

def canonical_serialize(obj: Dict[str, Any]) -> bytes:
    """Serialize từ điển thành Deterministic Canonical JSON bytes."""
    return json.dumps(obj, sort_keys=True, separators=(',', ':'), ensure_ascii=False).encode("utf-8")

class MasterApprovalSigner:
    """
    Đại diện cho Master (Human-In-The-Loop).
    Nắm giữ PRIVATE KEY để ký phát hành Auth Token và Approval Signature.
    """
    def __init__(self, private_key_b64: Optional[str] = None):
        if private_key_b64 is None:
            private_key_b64 = os.getenv("JKAI_MASTER_PRIVATE_KEY")
            
        if not private_key_b64:
            raise RuntimeError(
                "FAIL_CLOSED: Thiếu biến môi trường bắt buộc 'JKAI_MASTER_PRIVATE_KEY' (Ed25519 raw 32 bytes base64). "
                "Master Approval Signer từ chối khởi động mà không có khóa riêng an toàn."
            )
            
        try:
            raw_bytes = base64.b64decode(private_key_b64)
            if len(raw_bytes) != 32:
                raise ValueError("Ed25519 private key raw bytes must be exactly 32 bytes.")
            self._private_key = ed25519.Ed25519PrivateKey.from_private_bytes(raw_bytes)
        except Exception as e:
            raise RuntimeError(f"FAIL_CLOSED: Khóa riêng Ed25519 của Master không hợp lệ: {e}")
            
        self._public_key = self._private_key.public_key()

    @classmethod
    def generate_keypair(cls) -> Tuple[str, str]:
        """Sinh một cặp khóa Ed25519 mới dạng Base64 (private_b64, public_b64)."""
        priv = ed25519.Ed25519PrivateKey.generate()
        pub = priv.public_key()
        priv_b64 = base64.b64encode(priv.private_bytes_raw()).decode("utf-8")
        pub_b64 = base64.b64encode(pub.public_bytes_raw()).decode("utf-8")
        return priv_b64, pub_b64

    @property
    def public_key_b64(self) -> str:
        """Xuất Public Key dạng Base64 để nạp cho Worker."""
        return base64.b64encode(self._public_key.public_bytes_raw()).decode("utf-8")

    def create_master_auth_token(
        self,
        session_id: str,
        caller_id: str = "master_desktop_ui",
        ttl_seconds: float = 60.0,
        issued_at: Optional[float] = None
    ) -> str:
        """
        Tạo Master Auth Token (Tầng 1: Cho phép gửi yêu cầu cấp vé One-Time Lease).
        Có nonce chống replay, session_id binding, và chữ ký Ed25519 trên canonical payload.
        """
        now = time.time()
        actual_issued_at = issued_at if issued_at is not None else now
        expires_at = actual_issued_at + ttl_seconds
        nonce = f"auth_{uuid.uuid4().hex[:12]}"
        
        payload = {
            "caller_id": caller_id,
            "expires_at": expires_at,
            "issued_at": actual_issued_at,
            "nonce": nonce,
            "session_id": session_id
        }
        canonical_bytes = canonical_serialize(payload)
        signature = self._private_key.sign(canonical_bytes)
        
        token_data = {
            "payload": payload,
            "signature": base64.b64encode(signature).decode("utf-8")
        }
        return base64.urlsafe_b64encode(json.dumps(token_data).encode("utf-8")).decode("utf-8")

    def sign_mutation_approval(
        self,
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
        ttl_seconds: Optional[float] = None
    ) -> str:
        """
        Tạo Master Approval Signature (Tầng 2: Master bấm phê duyệt thực thi hành động).
        Ký bằng Ed25519 trên Canonical JSON bao quát toàn bộ ngữ cảnh thực thi.
        Enforce trước khi ký: expires_at tuyệt đối không vượt quá lease_expires_at.
        """
        now = time.time()
        if ttl_seconds is not None:
            expires_at = now + ttl_seconds
        else:
            expires_at = lease_expires_at

        # Signer Pre-Signature Enforce: Không thể ký approval sống lâu hơn lease
        if expires_at > lease_expires_at:
            raise ValueError(
                f"Signer Policy Error: approval expires_at ({expires_at:.2f}) cannot exceed lease_expires_at ({lease_expires_at:.2f})."
            )

        canonical_payload = {
            "action": action,
            "element_ref": str(element_ref or ""),
            "expires_at": expires_at,
            "hwnd": hwnd,
            "lease_expires_at": lease_expires_at,
            "lease_id": lease_id,
            "nonce": nonce,
            "proc_name": proc_name,
            "scroll_direction": str(scroll_direction or ""),
            "scroll_steps": scroll_steps,
            "scroll_unit": str(scroll_unit or ""),
            "session_id": session_id,
            "target_pid": target_pid,
            "text_payload": text_payload,
            "worker_generation": worker_generation
        }
        canonical_bytes = canonical_serialize(canonical_payload)
        sig_bytes = self._private_key.sign(canonical_bytes)
        
        approval_token_data = {
            "canonical_payload": canonical_payload,
            "signature": base64.b64encode(sig_bytes).decode("utf-8")
        }
        return base64.urlsafe_b64encode(json.dumps(approval_token_data).encode("utf-8")).decode("utf-8")

    def create_master_activation_token(
        self,
        session_id: str,
        target_hwnd: int,
        caller_id: str = "master_desktop_ui",
        ttl_seconds: float = 60.0
    ) -> str:
        """
        Ký phát hành Master One-Shot Activation Token ràng buộc cứng target_hwnd và session (Finding 2).
        Enforce TTL trong khoảng an toàn 1.0s đến 300.0s.
        """
        if ttl_seconds < 1.0 or ttl_seconds > 300.0:
            raise ValueError(f"Signer Error: ttl_seconds must be between 1.0s and 300.0s, got {ttl_seconds}")

        now = time.time()
        nonce = f"act_{uuid.uuid4().hex[:12]}"
        payload = {
            "caller_id": caller_id,
            "expires_at": now + ttl_seconds,
            "issued_at": now,
            "nonce": nonce,
            "scope": "master_mutation_activation",
            "session_id": session_id,
            "target_hwnd": int(target_hwnd),
        }
        canonical_bytes = canonical_serialize(payload)
        sig = self._private_key.sign(canonical_bytes)
        token_data = {
            "payload": payload,
            "signature": base64.b64encode(sig).decode("utf-8")
        }
        return base64.urlsafe_b64encode(json.dumps(token_data).encode("utf-8")).decode("utf-8")
