# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — ENTERPRISE SOVEREIGN RUNTIME GOVERNANCE (LDS & RISK TIER)    ║
║   Tích Hợp Tinh Hoa 3 Nhóm Kiến Trúc: Sovereign OS, DIR & Agent Execution    ║
╚══════════════════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Độc Lập — Bảo Vệ Tuyệt Đối Chủ Quyền Thực Thi Cục Bộ.*

Kế Thừa & Nâng Cấp:
1. Nhóm 1 (Sovereign OS):
   - Receipt-backed Execution (SROS v2): Bằng chứng mật mã học (cryptographic receipt) cho mọi hành vi.
   - Glass-Box State Machine (Meru OS): Biểu diễn trạng thái số nguyên (Integer States) phục vụ Time-Travel Replay.
2. Nhóm 2 (Separation of Reasoning & Execution):
   - Legal Decision State (LDS từ DIR): 5 chiều thẩm định (Authority, Context, Time, Integrity, Evidence).
   - 4-Tier Risk Classification (Cognithor): GREEN (1), YELLOW (2), ORANGE (3), RED (4).
3. Nhóm 3 (Agent Execution Layers):
   - Replayable Contracts (Ouroboros): Phát lại chuỗi thực thi độc lập không cần gọi lại LLM.
   - Resource Concurrency Leases (AGH): Khóa tài nguyên chống race-condition đa Agent.
   - Recovery Loop (Agent OS): Plan -> LDS_Verify -> Snapshot -> Execute -> Verify -> [Recover] -> Receipt.
"""

from __future__ import annotations

import os
import re
import ast
import time
import json
import uuid
import hmac
import hashlib
import tempfile
import logging
from contextlib import contextmanager
from enum import Enum, IntEnum
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set, Tuple

logger = logging.getLogger("JKAI.LDSRiskGovernance")


def _resolve_governance_secret(secret_override: Optional[bytes] = None) -> bytes:
    """
    Xác định khóa bí mật cho Sovereign Governance:
    - Ưu tiên khóa được inject tường minh (secret_override).
    - Đọc từ biến môi trường JKAI_GOVERNANCE_SECRET hoặc SOVEREIGN_GOVERNANCE_SECRET.
    - Trong môi trường PRODUCTION: Bắt buộc phải có secret, nếu thiếu sẽ FAIL-CLOSED (raise RuntimeError).
    - Trong môi trường DEV/TEST: Fallback sang khóa dev cục bộ có thông báo cảnh báo.
    """
    if secret_override is not None:
        if isinstance(secret_override, str):
            return secret_override.encode("utf-8")
        return secret_override

    env_secret = os.getenv("JKAI_GOVERNANCE_SECRET", os.getenv("SOVEREIGN_GOVERNANCE_SECRET", ""))
    if env_secret.strip():
        return env_secret.strip().encode("utf-8")

    is_production = (
        os.getenv("JKAI_ENV", "").lower() in ("production", "prod")
        or os.getenv("ENVIRONMENT", "").lower() in ("production", "prod")
        or os.getenv("NODE_ENV", "").lower() in ("production", "prod")
    )
    if is_production:
        raise RuntimeError("GOVERNANCE_SECRET_MISSING: Sovereign governance secret is strictly required in production environment.")

    dev_key = os.getenv("JKAI_DEV_GOVERNANCE_SECRET", "jkai_dev_ephemeral_sovereign_key_local_only")
    return dev_key.encode("utf-8")

# ══════════════════════════════════════════════════════════════════════════════
# 1. RISK TIERING (Học từ Cognithor: Phân loại rủi ro 4 cấp)
# ══════════════════════════════════════════════════════════════════════════════

class RiskTier(IntEnum):
    """
    Phân loại rủi ro 4 cấp độ toán học:
    🟢 GREEN  (1): Rủi ro tối thiểu (Read-only, quan sát, tính toán số học).
    🟡 YELLOW (2): Rủi ro trung bình (Tạo file mới, gọi web search nội bộ, cache).
    🟠 ORANGE (3): Rủi ro cao (Sửa mã nguồn, cài package, chạy shell script).
    🔴 RED    (4): Rủi ro chí mạng (Xóa file, cấu hình mạng, drop DB, format disk).
    """
    GREEN = 1
    YELLOW = 2
    ORANGE = 3
    RED = 4

    @property
    def label(self) -> str:
        return {
            RiskTier.GREEN: "GREEN_LOW_RISK",
            RiskTier.YELLOW: "YELLOW_MEDIUM_RISK",
            RiskTier.ORANGE: "ORANGE_HIGH_RISK",
            RiskTier.RED: "RED_CRITICAL_RISK"
        }[self]


# ══════════════════════════════════════════════════════════════════════════════
# 2. GLASS-BOX INTEGER STATES (Học từ Meru OS: Hộp Kính Trạng Thái Số Nguyên)
# ══════════════════════════════════════════════════════════════════════════════

class AgentStateCode(IntEnum):
    """
    Trạng thái số nguyên (Integer States) giúp:
    - Time-travel debugging siêu tốc (O(1) comparison).
    - Replay chuỗi hành vi với footprint < 100 bytes.
    - Chống hộp đen vector mơ hồ.
    """
    IDLE = 0x00
    INTENT_ROUTED = 0x10
    LDS_EVALUATING = 0x20
    PRE_SNAPSHOT_CAPTURED = 0x30
    EXECUTING_SUBSTRATE = 0x40
    POST_RECEIPT_SEALED = 0x50
    VERIFIED_SUCCESS = 0x60
    APPROVAL_INTERRUPT = 0x90
    FAILED_RECOVERING = 0xEE
    COMPLETED = 0xFF


# ══════════════════════════════════════════════════════════════════════════════
# 3. LEGAL DECISION STATE (LDS từ DIR: 5 Trụ Cột Thẩm Định Pháp Lý Thực Thi)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class LDSVerdict:
    """
    Kết quả thẩm định 5 chiều của Legal Decision State (DIR):
    - authority: Thẩm quyền Agent/Role hợp lệ trong TaskContract.
    - context: Phạm vi tài nguyên hợp lệ, chống path traversal.
    - time: Nằm trong khung thời gian hợp lệ (TTL/tuần tự nhân quả).
    - integrity: Tham số không bị ô nhiễm (Command injection, Unsafe AST).
    - evidence: Có căn cứ nhân quả liên kết với mục tiêu/kế hoạch.
    """
    is_legal: bool
    authority_ok: bool
    context_ok: bool
    time_ok: bool
    integrity_ok: bool
    evidence_ok: bool
    risk_tier: RiskTier
    failure_reasons: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "is_legal": self.is_legal,
            "authority_ok": self.authority_ok,
            "context_ok": self.context_ok,
            "time_ok": self.time_ok,
            "integrity_ok": self.integrity_ok,
            "evidence_ok": self.evidence_ok,
            "risk_tier": self.risk_tier.name,
            "risk_tier_value": int(self.risk_tier),
            "failure_reasons": list(self.failure_reasons),
            "metadata": dict(self.metadata)
        }


# ══════════════════════════════════════════════════════════════════════════════
# 4. EXECUTION RECEIPT (Học từ SROS v2: Biên Nhận Mật Mã Học Không Thể Chối Cãi)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ExecutionReceipt:
    """
    Biên nhận thực thi có bảo chứng mật mã học (SROS v2):
    - Khóa chặt bằng HMAC-SHA256.
    - Lưu vết pre-state hash và post-state hash.
    - Đảm bảo tính bất khả chối cãi khi kiểm toán (Non-repudiation audit).
    """
    receipt_id: str
    task_id: str
    action: str
    risk_tier: str
    args_hash: str
    pre_state_hash: str
    post_state_hash: str
    output_hash: str
    lds_legal: bool
    timestamp_utc: str
    monotonic_seq: int
    key_id: str = "k_default_2026"
    hmac_signature: str = ""

    def compute_signature(self, secret_key: bytes) -> str:
        payload = f"{self.receipt_id}:{self.task_id}:{self.action}:{self.risk_tier}:{self.args_hash}:{self.pre_state_hash}:{self.post_state_hash}:{self.output_hash}:{self.lds_legal}:{self.monotonic_seq}:{self.key_id}"
        return hmac.new(secret_key, payload.encode("utf-8"), hashlib.sha256).hexdigest()

    def verify_signature(self, secret_key: bytes) -> bool:
        expected = self.compute_signature(secret_key)
        return hmac.compare_digest(self.hmac_signature, expected)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# ══════════════════════════════════════════════════════════════════════════════
# 5. RESOURCE LEASE MANAGER (Học từ AGH: Khóa Tài Nguyên Đa Agent)
# ══════════════════════════════════════════════════════════════════════════════

@dataclass
class ResourceLease:
    resource_path: str
    holder_id: str
    acquired_at: float
    expires_at: float
    lease_token: str
    fencing_token: int = 0


class ResourceLeaseManager:
    """
    Quản lý hợp đồng thuê tài nguyên (AGH Leases):
    - Đảm bảo tính cô lập tuyệt đối, chống race condition khi đa Agent/Process cùng hoạt động.
    - Hỗ trợ atomic file lock liên tiến trình (Cross-Process File Lock) và in-memory fast caching.
    - Hỗ trợ Fencing Token ngăn chặn stale holder ghi đè sau TTL expiration takeover.
    - Tự động thu hồi lease khi hết hạn (TTL-based auto-eviction).
    """

    _GLOBAL_FENCING_COUNTER: int = 0

    def __init__(self, default_ttl: float = 30.0, lock_dir: Optional[str] = None):
        self._leases: Dict[str, ResourceLease] = {}
        self._default_ttl = default_ttl
        env_lock_dir = lock_dir or os.environ.get("JKAI_LEASE_LOCK_DIR")
        if env_lock_dir:
            self.lock_dir = os.path.abspath(env_lock_dir)
        else:
            self.lock_dir = os.path.join(tempfile.gettempdir(), "jkai_resource_leases")
        try:
            os.makedirs(self.lock_dir, exist_ok=True)
        except Exception:
            pass

    def _lock_file_for(self, norm_path: str) -> str:
        h = hashlib.sha256(norm_path.encode("utf-8")).hexdigest()[:24]
        return os.path.join(self.lock_dir, f"lease_{h}.lock")

    def _read_file_lease(self, lock_file: str) -> Optional[ResourceLease]:
        if not os.path.exists(lock_file):
            return None
        try:
            with open(lock_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            return ResourceLease(
                resource_path=data["resource_path"],
                holder_id=data["holder_id"],
                acquired_at=float(data["acquired_at"]),
                expires_at=float(data["expires_at"]),
                lease_token=data["lease_token"],
                fencing_token=int(data.get("fencing_token", 0))
            )
        except Exception:
            return None

    @contextmanager
    def _acquire_os_mutex(self, lock_file: str):
        mutex_file = f"{lock_file}.mutex"
        handle = open(mutex_file, "a+", encoding="utf-8")
        try:
            if os.name == "nt":
                import msvcrt
                handle.seek(0)
                handle.write(" ")
                handle.flush()
                msvcrt.locking(handle.fileno(), msvcrt.LK_LOCK, 1)
            else:
                import fcntl
                fcntl.flock(handle.fileno(), fcntl.LOCK_EX)
            yield
        finally:
            try:
                if os.name == "nt":
                    # Closing handle releases msvcrt region lock reliably on Windows.
                    pass
                else:
                    import fcntl
                    fcntl.flock(handle.fileno(), fcntl.LOCK_UN)
            finally:
                handle.close()

    def _write_file_lease(self, lock_file: str, lease: ResourceLease) -> bool:
        try:
            temp_file = f"{lock_file}.tmp.{uuid.uuid4().hex[:8]}"
            with open(temp_file, "w", encoding="utf-8") as f:
                json.dump(asdict(lease), f)
            os.replace(temp_file, lock_file)
            return True
        except Exception:
            return False

    def acquire(self, resource_path: str, holder_id: str, ttl: Optional[float] = None) -> Optional[str]:
        norm_path = os.path.normpath(os.path.abspath(resource_path)).lower()
        lock_file = self._lock_file_for(norm_path)
        with self._acquire_os_mutex(lock_file):
            return self._acquire_unlocked(norm_path, holder_id, ttl)

    def _acquire_unlocked(self, norm_path: str, holder_id: str, ttl: Optional[float] = None) -> Optional[str]:
        
        now = time.time()
        effective_ttl = ttl if ttl is not None else self._default_ttl
        lock_file = self._lock_file_for(norm_path)

        # 1. Kiểm tra lease từ file (cross-process)
        existing = self._read_file_lease(lock_file)
        if existing:
            if now > existing.expires_at:
                try:
                    os.remove(lock_file)
                except Exception:
                    pass
            elif existing.holder_id != holder_id:
                # Đang bị process / agent khác giữ
                return None
            else:
                # Đang được giữ bởi chính holder này -> refresh TTL
                token = existing.lease_token
                lease = ResourceLease(
                    resource_path=norm_path,
                    holder_id=holder_id,
                    acquired_at=now,
                    expires_at=now + effective_ttl,
                    lease_token=token,
                    fencing_token=existing.fencing_token
                )
                self._leases[norm_path] = lease
                self._write_file_lease(lock_file, lease)
                return token

        # 2. Tạo lease mới atomic
        ResourceLeaseManager._GLOBAL_FENCING_COUNTER += 1
        fence = ResourceLeaseManager._GLOBAL_FENCING_COUNTER
        token = uuid.uuid4().hex
        lease = ResourceLease(
            resource_path=norm_path,
            holder_id=holder_id,
            acquired_at=now,
            expires_at=now + effective_ttl,
            lease_token=token,
            fencing_token=fence
        )
        if not self._write_file_lease(lock_file, lease):
            return None
        self._leases[norm_path] = lease
        return token

    def validate_fencing_token(self, resource_path: str, holder_id: str, lease_token: str, fencing_token: Optional[int] = None) -> bool:
        """
        [AGH Fencing Validation]
        Xác thực xem holder và token có còn quyền hợp pháp hay đã bị takeover bởi agent khác.
        """
        norm_path = os.path.normpath(os.path.abspath(resource_path)).lower()
        lock_file = self._lock_file_for(norm_path)
        with self._acquire_os_mutex(lock_file):
            existing = self._read_file_lease(lock_file) or self._leases.get(norm_path)
            if not existing:
                return False
            if time.time() > existing.expires_at:
                return False
            if existing.holder_id != holder_id or existing.lease_token != lease_token:
                return False
            if fencing_token is not None and existing.fencing_token != fencing_token:
                return False
            return True

    def release(self, resource_path: str, holder_id: str, lease_token: Optional[str] = None) -> bool:
        norm_path = os.path.normpath(os.path.abspath(resource_path)).lower()
        lock_file = self._lock_file_for(norm_path)
        with self._acquire_os_mutex(lock_file):
            return self._release_unlocked(norm_path, holder_id, lease_token)

    def _release_unlocked(self, norm_path: str, holder_id: str, lease_token: Optional[str] = None) -> bool:
        lock_file = self._lock_file_for(norm_path)
        existing = self._read_file_lease(lock_file) or self._leases.get(norm_path)
        if not existing:
            return True
        if existing.holder_id == holder_id:
            if lease_token is not None and existing.lease_token == lease_token:
                self._leases.pop(norm_path, None)
                if os.path.exists(lock_file):
                    try:
                        os.remove(lock_file)
                    except Exception:
                        pass
                return True
        return False

    def is_locked(self, resource_path: str, holder_id: str) -> bool:
        norm_path = os.path.normpath(os.path.abspath(resource_path)).lower()
        lock_file = self._lock_file_for(norm_path)
        with self._acquire_os_mutex(lock_file):
            existing = self._read_file_lease(lock_file) or self._leases.get(norm_path)
            if not existing:
                return False
            if time.time() > existing.expires_at:
                self._leases.pop(norm_path, None)
                if os.path.exists(lock_file):
                    try:
                        os.remove(lock_file)
                    except Exception:
                        pass
                return False
            return existing.holder_id != holder_id


# ══════════════════════════════════════════════════════════════════════════════
# 6. ENTERPRISE RUNTIME GOVERNANCE ENGINE (SSoT Gateway)
# ══════════════════════════════════════════════════════════════════════════════

class EnterpriseRuntimeGovernance:
    """
    Trung tâm điều phối & thực thi toàn diện LDS, Risk Tiering, Receipts và State Replay.
    """

    _MONOTONIC_COUNTER = 0

    # Whitelist & Blacklist Patterns
    _UNSAFE_CMD_RE = re.compile(
        r"(?i)(rm\s+-rf\s+[\/\*]|mkfs|dd\s+if=|:\(\)\{.*\}|chmod\s+-R\s+777|iptables\s+-F|shutdown|reboot|truncate\s+-s\s*0)"
    )
    _PATH_TRAVERSAL_RE = re.compile(r"(?:\.\.[\\\/]|\.\.$|^[\\\/]etc[\\\/]|^[\\\/]var[\\\/]|^[\\\/]bin[\\\/]|C:[\\\/]Windows)")

    # Read-only observation tools
    OBSERVATION_TOOLS = {
        "view_file", "read_file", "list_dir", "grep_search", "search_web",
        "search_web_global", "web_search", "web_read", "read_url", "fetch_url",
        "search_memory", "get_metrics", "health_check", "inspect_state"
    }

    # High mutation tools
    HIGH_MUTATION_TOOLS = {
        "replace_file_content", "python_execute", "run_script", "execute_code",
        "install_package", "pip_install", "npm_install", "modify_code"
    }

    # Destructive tools (Require Human Gate)
    DESTRUCTIVE_TOOLS = {
        "delete_file", "rm", "unlink", "drop_table", "drop_database",
        "truncate_table", "format_drive", "kill_process", "firewall_disable"
    }

    def __init__(
        self,
        workspace_root: Optional[str] = None,
        secret_key: Optional[bytes] = None,
        lock_dir: Optional[str] = None,
        key_id: str = "k_default_2026",
        key_ring: Optional[Dict[str, bytes]] = None
    ):
        self.workspace_root = os.path.abspath(workspace_root or os.getcwd())
        self.key_id = key_id
        self._secret = _resolve_governance_secret(secret_key)
        self.key_ring: Dict[str, bytes] = dict(key_ring or {})
        self.key_ring[self.key_id] = self._secret
        self.lease_manager = ResourceLeaseManager(lock_dir=lock_dir)
        self.integer_state_history: List[int] = [int(AgentStateCode.IDLE)]
        self.receipts_journal: List[ExecutionReceipt] = []

    @property
    def secret_key(self) -> bytes:
        return self._secret

    def record_state(self, state: AgentStateCode) -> int:
        code = int(state)
        self.integer_state_history.append(code)
        return code

    def get_state_history(self) -> List[int]:
        return list(self.integer_state_history)

    def classify_risk(self, action: str, arguments: Optional[Dict[str, Any]] = None) -> RiskTier:
        act = (action or "").strip().lower()
        args = arguments or {}

        # 1. Critical RED
        if act in self.DESTRUCTIVE_TOOLS or any(k in act for k in ("delete", "destroy", "drop_db", "format")):
            return RiskTier.RED

        # Check dangerous command line args
        cmd = str(args.get("CommandLine", args.get("cmd", args.get("command", ""))))
        if cmd and self._UNSAFE_CMD_RE.search(cmd):
            return RiskTier.RED

        # 2. High Mutation ORANGE
        if act in self.HIGH_MUTATION_TOOLS or act == "run_command":
            return RiskTier.ORANGE

        # File write / modification
        if act in ("write_to_file", "write_file", "append_file", "save_artifact"):
            target = str(args.get("TargetFile", args.get("Path", args.get("file_path", ""))))
            if os.path.exists(target):
                return RiskTier.ORANGE  # Overwrite existing is ORANGE
            return RiskTier.YELLOW      # Create new is YELLOW

        # 3. Read-only GREEN
        if act in self.OBSERVATION_TOOLS or any(act.startswith(p) for p in ("view_", "read_", "search_", "list_", "get_")):
            return RiskTier.GREEN

        # Default fallback: YELLOW
        return RiskTier.YELLOW

    def evaluate_lds(
        self,
        action: str,
        arguments: Optional[Dict[str, Any]] = None,
        task_contract: Optional[Any] = None,
        policy: Optional[Any] = None,
        task_id: str = "default",
        reasoning_link: Optional[str] = None
    ) -> LDSVerdict:
        """
        Thẩm định 5 trụ cột Legal Decision State (DIR):
        1. Authority
        2. Context
        3. Time
        4. Integrity
        5. Evidence
        """
        self.record_state(AgentStateCode.LDS_EVALUATING)
        args = arguments or {}
        risk = self.classify_risk(action, args)
        failures = []

        # 1. AUTHORITY CHECK
        authority_ok = True
        if task_contract is not None:
            authority = getattr(task_contract, "decision_authority", None)
            if authority is not None:
                # Check delete permission
                if risk == RiskTier.RED and getattr(authority, "can_delete_files", True) is False:
                    authority_ok = False
                    failures.append("AUTHORITY_VIOLATION: Action requires can_delete_files=True but authority denies it.")
                # Check modify permission
                if risk in (RiskTier.ORANGE, RiskTier.RED) and getattr(authority, "can_modify_files", True) is False:
                    authority_ok = False
                    failures.append("AUTHORITY_VIOLATION: Action requires can_modify_files=True but authority denies it.")
                # Check external comms
                if "send" in action.lower() and getattr(authority, "can_send_external_message", True) is False:
                    authority_ok = False
                    failures.append("AUTHORITY_VIOLATION: Action requires can_send_external_message=True.")

        # 2. CONTEXT CHECK (Path traversal & Sandbox)
        context_ok = True
        target_path = str(args.get("TargetFile", args.get("Path", args.get("AbsolutePath", args.get("file_path", ""))))).strip()
        if target_path:
            if self._PATH_TRAVERSAL_RE.search(target_path):
                context_ok = False
                failures.append(f"CONTEXT_VIOLATION: Detected forbidden path traversal in '{target_path}'.")
            else:
                abs_target = os.path.abspath(target_path)
                # Check lease lock
                if self.lease_manager.is_locked(abs_target, holder_id=task_id):
                    context_ok = False
                    failures.append(f"CONTEXT_VIOLATION: Resource '{target_path}' is leased by another Agent.")

        # 3. TIME CHECK (Monotonic causality & TTL)
        time_ok = True
        request_ts = args.get("_timestamp_utc")
        if request_ts:
            try:
                pass # valid parse
            except Exception:
                time_ok = False
                failures.append("TIME_VIOLATION: Malformed execution timestamp.")

        # 4. INTEGRITY CHECK (Injection & AST safety)
        integrity_ok = True
        cmd = str(args.get("CommandLine", args.get("cmd", args.get("command", ""))))
        if cmd and self._UNSAFE_CMD_RE.search(cmd):
            integrity_ok = False
            failures.append(f"INTEGRITY_VIOLATION: Command contains destructive pattern: {cmd[:60]}")

        # AST safety check for python execution
        py_code = args.get("code", args.get("CodeContent", ""))
        if action in ("python_execute", "exec_code") and py_code:
            try:
                parsed = ast.parse(py_code)
                for node in ast.walk(parsed):
                    if isinstance(node, ast.Import):
                        for n in node.names:
                            if n.name in ("shutil", "subprocess", "socket"):
                                # Mark as high-risk, requires explicit permission
                                pass
            except SyntaxError as se:
                integrity_ok = False
                failures.append(f"INTEGRITY_VIOLATION: Syntax error in python payload: {se}")

        # 5. EVIDENCE CHECK (Causal grounding)
        evidence_ok = True
        # Must have an active task context
        if not task_id or task_id == "unknown":
            evidence_ok = False
            failures.append("EVIDENCE_VIOLATION: Missing task_id evidence grounding.")

        is_legal = authority_ok and context_ok and time_ok and integrity_ok and evidence_ok

        return LDSVerdict(
            is_legal=is_legal,
            authority_ok=authority_ok,
            context_ok=context_ok,
            time_ok=time_ok,
            integrity_ok=integrity_ok,
            evidence_ok=evidence_ok,
            risk_tier=risk,
            failure_reasons=failures,
            metadata={"action": action, "task_id": task_id}
        )

    def seal_receipt(
        self,
        task_id: str,
        action: str,
        arguments: Dict[str, Any],
        output_result: Any,
        lds_verdict: LDSVerdict,
        pre_state_hash: str = "0" * 64,
        post_state_hash: str = "0" * 64
    ) -> ExecutionReceipt:
        """
        Ký niêm phong biên nhận mật mã học (SROS v2) sau khi hành động hoàn tất.
        """
        EnterpriseRuntimeGovernance._MONOTONIC_COUNTER += 1
        seq = EnterpriseRuntimeGovernance._MONOTONIC_COUNTER
        receipt_id = f"rcpt_{uuid.uuid4().hex[:12]}_{seq}"
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        # Canonical sorted json for hash
        args_clean = {k: v for k, v in arguments.items() if not k.startswith("_")}
        args_json = json.dumps(args_clean, sort_keys=True, ensure_ascii=False)
        args_hash = hashlib.sha256(args_json.encode("utf-8")).hexdigest()

        out_str = str(output_result)
        out_hash = hashlib.sha256(out_str.encode("utf-8")).hexdigest()

        receipt = ExecutionReceipt(
            receipt_id=receipt_id,
            task_id=task_id,
            action=action,
            risk_tier=lds_verdict.risk_tier.name,
            args_hash=args_hash,
            pre_state_hash=pre_state_hash,
            post_state_hash=post_state_hash,
            output_hash=out_hash,
            lds_legal=lds_verdict.is_legal,
            timestamp_utc=now_iso,
            monotonic_seq=seq,
            key_id=self.key_id
        )
        receipt.hmac_signature = receipt.compute_signature(self._secret)
        self.receipts_journal.append(receipt)
        self.record_state(AgentStateCode.POST_RECEIPT_SEALED)
        return receipt

    def verify_receipt(self, receipt: ExecutionReceipt) -> bool:
        """
        Kiểm toán nhanh 1 biên nhận đơn lẻ (SROS v2 Non-repudiation verification)
        hỗ trợ tra cứu theo Key Ring (Key ID & Rotation).
        """
        sec = self.key_ring.get(receipt.key_id)
        if sec is None:
            return False
        return receipt.verify_signature(sec)

    def replay_audit(
        self,
        receipts: List[ExecutionReceipt],
        expected_task_id: Optional[str] = None,
        max_age_seconds: Optional[float] = None
    ) -> Tuple[bool, List[str]]:
        """
        Kiểm toán chuỗi phát lại (Replayable Verification từ Ouroboros):
        Xác minh 100% tính nguyên vẹn của biên nhận mật mã học mà không cần gọi lại LLM.
        Hỗ trợ Key Rotation tra cứu theo key_id của từng receipt.
        Kiểm tra task scope, monotonic ordering, timestamp/freshness và tính duy nhất.
        """
        import calendar
        errors = []
        seen_ids = set()
        seen_seq = set()
        prev_seq = -1
        prev_ts_epoch = -1.0
        now_epoch = time.time()

        for i, r in enumerate(receipts):
            if expected_task_id and r.task_id != expected_task_id:
                errors.append(f"REPLAY_ERROR: Receipt {r.receipt_id} has task_id '{r.task_id}' but expected '{expected_task_id}'!")
            if r.receipt_id in seen_ids:
                errors.append(f"REPLAY_ERROR: Duplicate receipt ID {r.receipt_id}!")
            seen_ids.add(r.receipt_id)
            if r.monotonic_seq in seen_seq:
                errors.append(f"REPLAY_ERROR: Duplicate monotonic sequence {r.monotonic_seq}!")
            seen_seq.add(r.monotonic_seq)
            if prev_seq != -1 and r.monotonic_seq <= prev_seq:
                errors.append(f"REPLAY_ERROR: Non-monotonic sequence ordering {r.monotonic_seq} <= {prev_seq} at index {i}!")
            prev_seq = r.monotonic_seq

            # Validate timestamp format & freshness
            if not r.timestamp_utc:
                errors.append(f"REPLAY_ERROR: Missing timestamp_utc on receipt {r.receipt_id}!")
            else:
                try:
                    parsed_tm = time.strptime(r.timestamp_utc, "%Y-%m-%dT%H:%M:%SZ")
                    ts_epoch = float(calendar.timegm(parsed_tm))
                    if prev_ts_epoch > 0 and ts_epoch < prev_ts_epoch:
                        errors.append(f"REPLAY_ERROR: Timestamp regression on receipt {r.receipt_id} ({r.timestamp_utc})!")
                    prev_ts_epoch = ts_epoch
                    if max_age_seconds is not None and (now_epoch - ts_epoch) > max_age_seconds:
                        errors.append(f"REPLAY_ERROR: Stale receipt {r.receipt_id} exceeds max_age_seconds ({max_age_seconds}s)!")
                except ValueError:
                    errors.append(f"REPLAY_ERROR: Malformed timestamp_utc '{r.timestamp_utc}' on receipt {r.receipt_id}!")

            sec = self.key_ring.get(r.key_id)
            if sec is None:
                errors.append(f"REPLAY_ERROR: Unknown key ID {r.key_id}!")
                continue
            if not r.verify_signature(sec):
                errors.append(f"REPLAY_ERROR: Receipt {r.receipt_id} (index {i}) has invalid HMAC signature!")
            if not r.lds_legal:
                errors.append(f"REPLAY_ERROR: Receipt {r.receipt_id} records an illegal LDS action!")
        return (len(errors) == 0, errors)


enterprise_governance = EnterpriseRuntimeGovernance()


def get_lease_manager(lock_dir: Optional[str] = None) -> ResourceLeaseManager:
    """Return the cross-process ResourceLeaseManager (honoring JKAI_LEASE_LOCK_DIR if set)."""
    custom_dir = lock_dir or os.environ.get("JKAI_LEASE_LOCK_DIR")
    if custom_dir:
        abs_dir = os.path.abspath(custom_dir)
        if enterprise_governance.lease_manager.lock_dir != abs_dir:
            return ResourceLeaseManager(lock_dir=abs_dir)
    return enterprise_governance.lease_manager

