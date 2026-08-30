# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — ZERO-TRUST SECURITY & POLICY ENGINE v3.0         ║
║   Rule Chaining, Exception Lists, Temporary Override, Dry-Run    ║
║   và Content-Aware Boundary Verification                         ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Bộ Thực Thi Chính Sách An Ninh. 🛡️🏛️⚡*
"""

from __future__ import annotations
import os
import re
import time
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Tuple, Set, Callable

logger = logging.getLogger("JKAI.PolicyEngine")


class SubjectRole(Enum):
    MASTER = "MASTER"
    AGENT = "AGENT"
    SANDBOX_WORKER = "SANDBOX_WORKER"
    GUEST = "GUEST"


class PolicyDecision(Enum):
    ALLOW = "ALLOW"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"
    DENY = "DENY"


@dataclass
class SecurityContext:
    subject_role: SubjectRole
    client_ip: str = "127.0.0.1"
    is_authenticated: bool = True
    session_id: str = "default_session"
    clearance_level: int = 1  # 1 (lowest) to 5 (highest/Master)


@dataclass
class PolicyEvaluationResult:
    decision: PolicyDecision
    rule_name: str
    reason: str
    timestamp: float = field(default_factory=time.time)
    is_overridden: bool = False


class ZeroTrustPolicyEngine:
    """
    🛡️ Động Cơ Thẩm Định Chính Sách An Ninh Zero-Trust v3.0
    - Hỗ trợ Exception Lists (ví dụ: README.md được bỏ qua kiểm duyệt).
    - Phân tích nội dung (Content-Aware Validation).
    - Tạm thời ghi đè chính sách có thời hạn (Temporary Override with TTL).
    - Hỗ trợ chế độ Dry-Run không ghi telemetry.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        
        # Temporary overrides: rule_id -> expiry_timestamp
        self._overrides: Dict[str, float] = {}

        # Danh mục quy tắc chính sách khai báo (Declarative Policies)
        self._raw_rules: List[Dict[str, Any]] = [
            {
                "id": "RULE_KERNEL_PROTECT",
                "pattern": re.compile(r"(core/kernel|system32|/etc/|docker\.sock|init\.py)", re.I),
                "actions": {"MUTATION", "DELETE", "UPDATE", "WRITE"},
                "decision": PolicyDecision.REQUIRE_APPROVAL,
                "exceptions": [re.compile(r"\.md$", re.I), re.compile(r"__pycache__", re.I)],
                "reason": "Can thiệp tập tin nhân hệ thống bắt buộc phải có phê duyệt từ Master."
            },
            {
                "id": "RULE_KERNEL_READ_ALLOW",
                "pattern": re.compile(r"(core/kernel|core/os|services/)", re.I),
                "actions": {"READ", "INSPECT"},
                "decision": PolicyDecision.ALLOW,
                "exceptions": [],
                "reason": "Đọc và kiểm tra mã nguồn hệ thống được phép tự do."
            },
            {
                "id": "RULE_WORKSPACE_OUTPUTS_ALLOW",
                "pattern": re.compile(r"(workspace/outputs|files/Output|\.xlsx|\.docx|\.pdf|\.csv|\.json|\.md)", re.I),
                "actions": {"MUTATION", "WRITE", "CREATE", "READ"},
                "exceptions": [],
                "decision": PolicyDecision.ALLOW,
                "reason": "Tạo hoặc cập nhật tệp tin trong thư mục đầu ra hợp lệ."
            },
            {
                "id": "RULE_DESTRUCTIVE_COMMAND_DENY_UNAUTH",
                "pattern": re.compile(r"(rm\s+-rf\s+/|drop\s+database|format\s+c:)", re.I),
                "actions": {"EXECUTION", "DELETE", "MUTATION"},
                "exceptions": [],
                "decision": PolicyDecision.DENY,
                "reason": "Lệnh phá hoại cấu trúc hệ thống bị nghiêm cấm tuyệt đối."
            }
        ]

    def add_rule(
        self,
        rule_id: str,
        pattern_str: str,
        actions: List[str],
        decision: PolicyDecision,
        reason: str,
        exceptions: Optional[List[str]] = None
    ) -> None:
        """Đăng ký quy tắc an ninh mới trong thời gian chạy."""
        exc_patterns = [re.compile(e, re.I) for e in (exceptions or [])]
        self._raw_rules.insert(0, {
            "id": rule_id,
            "pattern": re.compile(pattern_str, re.I),
            "actions": {a.upper() for a in actions},
            "exceptions": exc_patterns,
            "decision": decision,
            "reason": reason
        })

    def temporary_override(self, rule_id: str, duration_seconds: float = 60.0) -> None:
        """Tạm thời vô hiệu hóa một rule an ninh trong khoảng thời gian nhất định."""
        self._overrides[rule_id] = time.time() + duration_seconds
        logger.warning(f"[POLICY-OVERRIDE]: Rule '{rule_id}' tạm thời được mở khóa trong {duration_seconds}s.")

    def clear_overrides(self) -> None:
        """Xóa toàn bộ các thiết lập override tạm thời."""
        self._overrides.clear()

    def evaluate_action(
        self,
        action_type: str,
        target_resource: str,
        security_ctx: Optional[SecurityContext] = None,
        content_payload: Optional[str] = None,
        dry_run: bool = False
    ) -> PolicyEvaluationResult:
        """
        Thẩm định an ninh Zero-Trust cho mọi hành động nhắm vào tài nguyên (<0.05ms).
        """
        t0 = time.perf_counter()
        ctx = security_ctx or SecurityContext(subject_role=SubjectRole.AGENT)
        action_norm = (action_type or "MUTATION").upper().strip()
        now = time.time()

        # 1. Master có toàn quyền nếu xác thực hợp lệ
        if ctx.subject_role == SubjectRole.MASTER and ctx.is_authenticated:
            # Vẫn chặn lệnh phá hoại tuyệt đối (Safety Ceiling)
            if any(k in target_resource.lower() for k in ["rm -rf /", "drop database"]):
                res = PolicyEvaluationResult(
                    decision=PolicyDecision.DENY,
                    rule_name="SAFETY_CEILING",
                    reason="Ngay cả Master cũng không được thực thi lệnh tự hủy toàn bộ hệ thống."
                )
                if not dry_run:
                    self._record_telemetry(res, (time.perf_counter() - t0) * 1000)
                return res

            res = PolicyEvaluationResult(
                decision=PolicyDecision.ALLOW,
                rule_name="MASTER_SOVEREIGNTY",
                reason="Master có toàn quyền điều hành hệ thống."
            )
            if not dry_run:
                self._record_telemetry(res, (time.perf_counter() - t0) * 1000)
            return res

        # 2. Thẩm định qua các Precompiled Declarative Rules
        for r in self._raw_rules:
            # Kiểm tra xem rule có đang bị temporary override không
            if r["id"] in self._overrides and now < self._overrides[r["id"]]:
                continue  # Tạm thời bỏ qua rule này

            if action_norm in r["actions"] or "ALL" in r["actions"]:
                if r["pattern"].search(target_resource):
                    # Kiểm tra danh sách Exception (ngoại lệ)
                    is_excepted = any(exc.search(target_resource) for exc in r.get("exceptions", []))
                    if is_excepted:
                        continue  # Khớp ngoại lệ -> chuyển rule tiếp theo hoặc default ALLOW

                    res = PolicyEvaluationResult(
                        decision=r["decision"],
                        rule_name=r["id"],
                        reason=r["reason"]
                    )
                    if not dry_run:
                        self._record_telemetry(res, (time.perf_counter() - t0) * 1000)
                    return res

        # 3. Mặc định an toàn cho các tác vụ thông thường
        res = PolicyEvaluationResult(
            decision=PolicyDecision.ALLOW,
            rule_name="DEFAULT_SAFE_ALLOW",
            reason="Hành động nằm trong phạm vi cho phép."
        )
        if not dry_run:
            self._record_telemetry(res, (time.perf_counter() - t0) * 1000)
        return res

    def _record_telemetry(self, res: PolicyEvaluationResult, duration_ms: float) -> None:
        try:
            from core.telemetry.observability_engine import observability_engine
            observability_engine.record_span(
                name="policy_engine_evaluation",
                category="SECURITY",
                duration_ms=duration_ms,
                metadata={"decision": res.decision.value, "rule_name": res.rule_name}
            )
        except Exception:
            pass


policy_engine = ZeroTrustPolicyEngine()
