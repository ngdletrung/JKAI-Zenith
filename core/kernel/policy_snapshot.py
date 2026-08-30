# -*- coding: utf-8 -*-
"""
🏛️ IMMUTABLE POLICY SNAPSHOT & EXECUTION GRANT SPECIFICATION
File: core/kernel/policy_snapshot.py

Thực thi chuẩn an toàn JKAI-LAW-03 & JKAI-BND-001:
- PolicySnapshot: Chụp ảnh đóng băng toàn bộ quyền hạn, ngân sách, invariants khi Mission khởi tạo.
- ExecutionGrant: Thẻ cấp quyền thực thi có thời hạn (TTL) và chữ ký HMAC-SHA256, chỉ cấp bởi AuthorityGateway.
- No Grant -> No Execution (Fail-Closed).
"""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import time
import uuid
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional


# Khóa bí mật nội bộ giữa AI Brain (Authority Gateway) và AI Executor
_SHARED_EXECUTION_SECRET = os.getenv("JKAI_EXECUTION_SECRET", "jkai_zenith_sovereign_governance_secret_2026").encode("utf-8")


@dataclass(frozen=True)
class PolicySnapshot:
    """
    Ảnh chụp chính sách bất biến của một Mission.
    Sau khi tạo tại Mission Admission, cấm mọi hành vi tự ý sửa đổi (Immutable).
    """
    snapshot_id: str
    mission_id: str
    created_at: float
    expires_at: float
    can_modify_files: bool = True
    can_delete_files: bool = False
    can_send_external_message: bool = True
    can_execute_shell: bool = False
    allowed_paths: List[str] = field(default_factory=lambda: ["/app", "/workspace", "/mnt/user-data"])
    forbidden_actions: List[str] = field(default_factory=list)
    budget_max_turns: int = 12
    invariants: List[str] = field(default_factory=lambda: [
        "JKAI-LAW-01: Proof Before Claim",
        "JKAI-LAW-02: Delegation Cannot Create",
        "JKAI-LAW-03: Adaptation Cannot Mutate Constitution",
        "JKAI-LAW-04: Enforcement Before Declaration",
    ])
    snapshot_hash: str = ""

    def compute_hash(self) -> str:
        payload = f"{self.snapshot_id}:{self.mission_id}:{self.can_modify_files}:{self.can_delete_files}:{self.can_execute_shell}:{self.budget_max_turns}:{json.dumps(self.invariants, sort_keys=True)}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def create_policy_snapshot(
    mission_id: str,
    can_modify_files: bool = True,
    can_delete_files: bool = False,
    can_send_external_message: bool = True,
    can_execute_shell: bool = False,
    allowed_paths: Optional[List[str]] = None,
    forbidden_actions: Optional[List[str]] = None,
    ttl_seconds: float = 3600.0,
    budget_max_turns: int = 12,
) -> PolicySnapshot:
    """Khởi tạo PolicySnapshot bất biến cho Mission."""
    now = time.time()
    snapshot_id = f"snap_{uuid.uuid4().hex[:12]}"
    paths = allowed_paths if allowed_paths is not None else ["/app", "/workspace", "/mnt/user-data"]
    forbidden = forbidden_actions if forbidden_actions is not None else []
    
    pre_snap = PolicySnapshot(
        snapshot_id=snapshot_id,
        mission_id=mission_id,
        created_at=now,
        expires_at=now + ttl_seconds,
        can_modify_files=can_modify_files,
        can_delete_files=can_delete_files,
        can_send_external_message=can_send_external_message,
        can_execute_shell=can_execute_shell,
        allowed_paths=paths,
        forbidden_actions=forbidden,
        budget_max_turns=budget_max_turns,
    )
    computed_hash = pre_snap.compute_hash()
    
    # Tạo đối tượng hoàn chỉnh có hash
    return PolicySnapshot(
        snapshot_id=pre_snap.snapshot_id,
        mission_id=pre_snap.mission_id,
        created_at=pre_snap.created_at,
        expires_at=pre_snap.expires_at,
        can_modify_files=pre_snap.can_modify_files,
        can_delete_files=pre_snap.can_delete_files,
        can_send_external_message=pre_snap.can_send_external_message,
        can_execute_shell=pre_snap.can_execute_shell,
        allowed_paths=pre_snap.allowed_paths,
        forbidden_actions=pre_snap.forbidden_actions,
        budget_max_turns=pre_snap.budget_max_turns,
        invariants=pre_snap.invariants,
        snapshot_hash=computed_hash,
    )


@dataclass(frozen=True)
class ExecutionGrant:
    """
    Thẻ ủy quyền thực thi công cụ do Authority Gateway cấp.
    Chỉ có hiệu lực trong TTL ngắn và được ký bởi HMAC bí mật.
    """
    grant_id: str
    mission_id: str
    snapshot_id: str
    tool_name: str
    args_hash: str
    issued_at: float
    expires_at: float
    signature: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "grant_id": self.grant_id,
            "mission_id": self.mission_id,
            "snapshot_id": self.snapshot_id,
            "tool_name": self.tool_name,
            "args_hash": self.args_hash,
            "issued_at": self.issued_at,
            "expires_at": self.expires_at,
            "signature": self.signature,
        }


def issue_execution_grant(
    mission_id: str,
    snapshot_id: str,
    tool_name: str,
    tool_args: Dict[str, Any],
    ttl_seconds: float = 300.0,
) -> ExecutionGrant:
    """Phát hành ExecutionGrant có chữ ký HMAC-SHA256."""
    now = time.time()
    grant_id = f"grant_{uuid.uuid4().hex[:12]}"
    args_payload = json.dumps(tool_args or {}, sort_keys=True)
    args_hash = hashlib.sha256(args_payload.encode("utf-8")).hexdigest()
    expires_at = now + ttl_seconds

    sig_payload = f"{grant_id}:{mission_id}:{snapshot_id}:{tool_name}:{args_hash}:{expires_at}"
    signature = hmac.new(_SHARED_EXECUTION_SECRET, sig_payload.encode("utf-8"), hashlib.sha256).hexdigest()

    return ExecutionGrant(
        grant_id=grant_id,
        mission_id=mission_id,
        snapshot_id=snapshot_id,
        tool_name=tool_name,
        args_hash=args_hash,
        issued_at=now,
        expires_at=expires_at,
        signature=signature,
    )


def verify_execution_grant(
    grant_dict: Dict[str, Any],
    expected_tool: str,
    actual_args: Dict[str, Any],
) -> tuple[bool, str]:
    """
    Xác thực tính hợp lệ của ExecutionGrant trên service ai-executor.
    Trả về: (is_valid, reason).
    """
    if not grant_dict or not isinstance(grant_dict, dict):
        return False, "Thiếu hoặc sai cấu trúc ExecutionGrant (FAIL-CLOSED)."

    grant_id = grant_dict.get("grant_id")
    mission_id = grant_dict.get("mission_id")
    snapshot_id = grant_dict.get("snapshot_id")
    tool_name = grant_dict.get("tool_name")
    args_hash = grant_dict.get("args_hash")
    expires_at = grant_dict.get("expires_at", 0)
    signature = grant_dict.get("signature")

    if not all([grant_id, mission_id, snapshot_id, tool_name, args_hash, signature]):
        return False, "ExecutionGrant thiếu các trường bắt buộc."

    # 1. Kiểm tra hết hạn TTL
    if time.time() > float(expires_at):
        return False, f"ExecutionGrant {grant_id} đã hết hạn."

    # 2. Kiểm tra khớp tên Tool
    if tool_name != expected_tool:
        return False, f"ExecutionGrant cấp cho tool '{tool_name}' không khớp với '{expected_tool}'."

    # 3. Kiểm tra khớp mã băm đối số (Args integrity)
    args_payload = json.dumps(actual_args or {}, sort_keys=True)
    actual_args_hash = hashlib.sha256(args_payload.encode("utf-8")).hexdigest()
    if actual_args_hash != args_hash:
        return False, "Đối số thực thi không khớp với mã băm trong ExecutionGrant (Phát hiện can thiệp đối số)."

    # 4. Kiểm tra chữ ký HMAC
    sig_payload = f"{grant_id}:{mission_id}:{snapshot_id}:{tool_name}:{args_hash}:{expires_at}"
    expected_sig = hmac.new(_SHARED_EXECUTION_SECRET, sig_payload.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(signature, expected_sig):
        return False, "Chữ ký HMAC của ExecutionGrant không hợp lệ hoặc bị giả mạo."

    return True, "ExecutionGrant hợp lệ."
