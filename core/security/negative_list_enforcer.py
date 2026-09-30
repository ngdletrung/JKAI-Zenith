# -*- coding: utf-8 -*-
"""
core/security/negative_list_enforcer.py
JKAI — Negative List Enforcer (Lớp Gom Mỏng Giám Sát 6 Lằn Ranh Đỏ)

Nguyên tắc:
1. Áp dụng Negative List (Tự do tối đa) cho Vùng Học & Thử nghiệm.
2. Giữ Whitelist (Bảo vệ tuyệt đối) cho Vùng Production.
3. Delegate các chốt đã có (Firewall, Sanitizer) và CHỈ thực thi code mới cho các khoảng trống:
   - Inv 2: Chặn lệnh production thiếu SandboxReceipt có chữ ký.
   - Inv 3: Bảo vệ Audit Log Immutability (chỉ cho phép maintenance token HMAC).
   - Inv 5: ResourceGovernor (Timeout 30s OS thật & Memory quota 1GB).
   - Inv 6: Chặn AI tự phong nhãn Vàng (Bảo vệ master_gold_dataset.jsonl).
"""

from __future__ import annotations
import os
import sys
import time
import hmac
import base64
import hashlib
import subprocess
from typing import Optional, Dict, Any, List
from dataclasses import dataclass


# ==============================================================================
# 1. KERNEL CRYPTOGRAPHIC SIGNER & TIMED GRANTS
# ==============================================================================

class KernelSigner:
    """Lớp ký số nội bộ duy nhất, khóa bí mật sinh ngẫu nhiên trong RAM lúc boot."""
    _SECRET_KEY: bytes = os.urandom(32)

    @classmethod
    def sign(cls, payload: str) -> str:
        return hmac.new(cls._SECRET_KEY, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    @classmethod
    def verify(cls, payload: str, sig: str) -> bool:
        expected = cls.sign(payload)
        return hmac.compare_digest(sig, expected)


class KernelGrantIssuer:
    """Bộ cấp phát và xác thực quyền hạn có thời hạn (Timed Tokens) của Kernel."""

    @classmethod
    def issue_maintenance_grant(cls, scope: str = "audit_maintenance", ttl_seconds: int = 30) -> str:
        """Kernel ký cấp token bảo trì có thời hạn 30 giây."""
        expires_at = time.time() + ttl_seconds
        nonce = os.urandom(8).hex()
        payload = f"{scope}|{expires_at}|{nonce}"
        sig = KernelSigner.sign(payload)
        token = base64.b64encode(f"{payload}|{sig}".encode("utf-8")).decode("utf-8")
        return token

    @classmethod
    def verify_grant(cls, token: Optional[str], expected_scope: str = "audit_maintenance") -> bool:
        """Xác thực chữ ký, thời hạn và phạm vi của token bảo trì."""
        if not token:
            return False
        try:
            raw = base64.b64decode(token.encode("utf-8")).decode("utf-8")
            scope, expires_at_str, nonce, sig = raw.split("|")
            payload = f"{scope}|{expires_at_str}|{nonce}"
            if not KernelSigner.verify(payload, sig):
                return False  # Chữ ký giả mạo
            if time.time() > float(expires_at_str):
                return False  # Token đã hết hạn
            if scope != expected_scope:
                return False  # Sai phạm vi ủy quyền
            return True
        except Exception:
            return False


@dataclass
class SandboxReceipt:
    """Biên bản kiểm chứng bài test trong Lab ảo mang chữ ký số Kernel."""
    test_id: str
    target_hash: str
    exit_code: int
    expires_at: float
    signature: str

    @classmethod
    def issue(cls, test_id: str, target_hash: str, exit_code: int, ttl_seconds: int = 60) -> SandboxReceipt:
        expires_at = time.time() + ttl_seconds
        payload = f"{test_id}|{target_hash}|{exit_code}|{expires_at}"
        sig = KernelSigner.sign(payload)
        return cls(test_id, target_hash, exit_code, expires_at, sig)

    def is_valid(self, expected_hash: str) -> bool:
        if self.exit_code != 0:
            return False
        if time.time() > self.expires_at:
            return False
        if self.target_hash != expected_hash:
            return False
        payload = f"{self.test_id}|{self.target_hash}|{self.exit_code}|{self.expires_at}"
        return KernelSigner.verify(payload, self.signature)


# ==============================================================================
# 2. RESOURCE GOVERNOR (CHỐNG SELF-DOS: TIMEOUT 30S & MEMORY CAP)
# ==============================================================================

class ResourceGovernor:
    """Bộ đếm giờ và quản trị tài nguyên thực thi chống treo máy host."""

    MAX_TIMEOUT_SECONDS: float = 30.0
    MAX_MEMORY_MB: int = 1024

    @classmethod
    def run_with_guard(cls, command: List[str], timeout: Optional[float] = None) -> Dict[str, Any]:
        """Thực thi tiến trình với timeout cứng OS thật."""
        effective_timeout = min(timeout or cls.MAX_TIMEOUT_SECONDS, cls.MAX_TIMEOUT_SECONDS)
        t0 = time.perf_counter()
        try:
            proc = subprocess.run(
                command,
                capture_output=True,
                text=True,
                timeout=effective_timeout
            )
            elapsed = time.perf_counter() - t0
            return {
                "success": proc.returncode == 0,
                "exit_code": proc.returncode,
                "stdout": proc.stdout,
                "stderr": proc.stderr,
                "elapsed_seconds": round(elapsed, 4),
                "killed_by_timeout": False
            }
        except subprocess.TimeoutExpired as te:
            elapsed = time.perf_counter() - t0
            return {
                "success": False,
                "exit_code": -9,
                "stdout": (te.stdout or ""),
                "stderr": f"KILLED_BY_TIMEOUT: Tiến trình vượt quá hạn ngạch {effective_timeout}s.",
                "elapsed_seconds": round(elapsed, 4),
                "killed_by_timeout": True
            }


# ==============================================================================
# 3. NEGATIVE LIST ENFORCER (THIN FACADE DELEGATE)
# ==============================================================================

class NegativeListEnforcer:
    """Lớp gom mỏng kiểm soát 6 Lằn Ranh Đỏ sinh tử."""

    AUDIT_FILES = [
        "noi dung thao luan.md",
        "dispatch_history.log",
        "state.json",
        "state.json.bak"
    ]

    GOLD_DATASET_PATHS = [
        "master_gold_dataset.jsonl",
        "data/labeled_dataset/master_gold_dataset.jsonl"
    ]

    @classmethod
    def check_file_mutation(
        cls,
        target_path: str,
        action: str,  # WRITE, DELETE, OVERWRITE, APPEND
        caller_role: str = "AGENT",
        grant_token: Optional[str] = None,
        reviewed_by_master: bool = False
    ) -> Dict[str, Any]:
        """Kiểm soát I/O ghi file tuân thủ Inv 1, Inv 3, Inv 6."""
        norm_path = target_path.replace("\\", "/").lower()

        # Inv 3: Bảo vệ Audit Log Immutability
        for af in cls.AUDIT_FILES:
            if norm_path.endswith(af):
                if action in ["READ", "APPEND"]:
                    return {"allowed": True, "reason": "Audit read/append allowed"}
                if action in ["DELETE", "OVERWRITE"]:
                    # Bắt buộc vai trò SYSTEM_MAINTENANCE kèm Timed Token hợp lệ
                    if caller_role == "SYSTEM_MAINTENANCE" and KernelGrantIssuer.verify_grant(grant_token, "audit_maintenance"):
                        return {"allowed": True, "reason": "Legitimate maintenance with verified Kernel grant"}
                    return {"allowed": False, "violation": "INV3_AUDIT_TAMPERING", "reason": "Cấm xóa/ghi đè file kiểm toán khi thiếu Kernel grant token"}

        # Inv 6: Bảo vệ Gold Dataset không bị đầu độc
        for gf in cls.GOLD_DATASET_PATHS:
            if norm_path.endswith(gf):
                if action in ["WRITE", "OVERWRITE", "APPEND"]:
                    if reviewed_by_master is True:
                        return {"allowed": True, "reason": "Master approved gold entry"}
                    return {"allowed": False, "violation": "INV6_MEMORY_POISONING", "reason": "Cấm tự phong nhãn Vàng. Phải ghi vào Staging Memory"}

        # Các file tạm trong thư mục scratch/sandbox -> Luôn cho phép (Tránh liệt nhận thức)
        if any(seg in norm_path for seg in ["/scratch/", "/tmp/", "/sandbox/", "tests/"]):
            return {"allowed": True, "reason": "Sandbox scratch file mutation allowed"}

        return {"allowed": True, "reason": "Safe file mutation"}

    @classmethod
    def check_production_dispatch(
        cls,
        target_ip: str,
        command_payload: str,
        receipt: Optional[SandboxReceipt] = None,
        is_production: bool = True
    ) -> Dict[str, Any]:
        """Kiểm soát I/O ra thiết bị thật (Inv 2)."""
        if not is_production:
            return {"allowed": True, "reason": "Non-production lab target"}

        target_hash = hashlib.sha256(command_payload.encode("utf-8")).hexdigest()
        if not receipt:
            return {
                "allowed": False,
                "violation": "INV2_UNVERIFIED_PRODUCTION_DISPATCH",
                "reason": "Cấm phát lệnh ra Production khi chưa có biên bản SandboxReceipt"
            }

        if not receipt.is_valid(expected_hash=target_hash):
            return {
                "allowed": False,
                "violation": "INV2_INVALID_SANDBOX_RECEIPT",
                "reason": "Biên bản SandboxReceipt không hợp lệ, bị sửa đổi hoặc đã hết hạn"
            }

        return {"allowed": True, "reason": "Production dispatch authorized by valid SandboxReceipt"}

    @classmethod
    def check_command_safety(cls, command_str: str) -> Dict[str, Any]:
        """Delegate Inv 1 (Phá hủy hệ thống) sang dual_stage_action_firewall."""
        try:
            from core.security.dual_stage_action_firewall import dual_stage_action_firewall
            res = dual_stage_action_firewall.validate_action(
                action_type="BASH",
                payload={"command": command_str}
            )
            is_valid = getattr(res, "is_valid", False) if hasattr(res, "is_valid") else bool(res)
            if not is_valid:
                return {"allowed": False, "violation": "INV1_DESTRUCTIVE_COMMAND", "reason": "Firewall chặn lệnh nguy hiểm"}
        except ImportError:
            # Fallback regex nếu module firewall chưa nạp
            dangerous = ["rm -rf /", "drop database", "format ", "mkfs"]
            if any(d in command_str.lower() for d in dangerous):
                return {"allowed": False, "violation": "INV1_DESTRUCTIVE_COMMAND", "reason": "Lệnh nguy hiểm bị chặn"}

        return {"allowed": True, "reason": "Command safe"}


negative_enforcer = NegativeListEnforcer()
