# -*- coding: utf-8 -*-
"""
Unit test suite cho ZeroTrustPolicyEngine v3.0
"""

import pytest
from core.security.policy_engine import (
    ZeroTrustPolicyEngine, policy_engine,
    SubjectRole, SecurityContext, PolicyDecision
)


class TestPolicyEngineV3:
    """Kiểm tra các quy tắc phân quyền chi tiết của Policy Engine v3.0."""

    def test_policy_kernel_read_allowed(self):
        # Đọc mã nguồn nhân hệ thống -> ALLOW
        ctx = SecurityContext(subject_role=SubjectRole.AGENT)
        res = policy_engine.evaluate_action("READ", "core/kernel/execution_integrity.py", ctx)
        assert res.decision == PolicyDecision.ALLOW

    def test_policy_kernel_mutation_requires_approval(self):
        # Ghi đè mã nguồn nhân hệ thống -> REQUIRE_APPROVAL
        ctx = SecurityContext(subject_role=SubjectRole.AGENT)
        res = policy_engine.evaluate_action("MUTATION", "core/kernel/execution_integrity.py", ctx)
        assert res.decision == PolicyDecision.REQUIRE_APPROVAL

    def test_policy_kernel_mutation_exception_readme_allowed(self):
        # Sửa file README.md trong kernel -> Khớp Exception -> ALLOW
        ctx = SecurityContext(subject_role=SubjectRole.AGENT)
        res = policy_engine.evaluate_action("MUTATION", "core/kernel/README.md", ctx)
        assert res.decision == PolicyDecision.ALLOW

    def test_policy_workspace_outputs_allow(self):
        # Ghi file đầu ra văn phòng -> ALLOW
        ctx = SecurityContext(subject_role=SubjectRole.AGENT)
        res = policy_engine.evaluate_action("CREATE", "workspace/outputs/bang_luong.xlsx", ctx)
        assert res.decision == PolicyDecision.ALLOW

    def test_policy_destructive_command_denied(self):
        # Lệnh phá hoại trái phép -> DENY
        ctx = SecurityContext(subject_role=SubjectRole.AGENT)
        res = policy_engine.evaluate_action("EXECUTION", "rm -rf /", ctx)
        assert res.decision == PolicyDecision.DENY

    def test_policy_master_sovereignty(self):
        # Master thao tác -> ALLOW
        ctx = SecurityContext(subject_role=SubjectRole.MASTER, is_authenticated=True)
        res = policy_engine.evaluate_action("MUTATION", "core/kernel/execution_integrity.py", ctx)
        assert res.decision == PolicyDecision.ALLOW

    def test_policy_temporary_override(self):
        # Tạm thời mở khóa rule kernel trong 10s
        policy_engine.temporary_override("RULE_KERNEL_PROTECT", duration_seconds=10.0)
        ctx = SecurityContext(subject_role=SubjectRole.AGENT)
        res = policy_engine.evaluate_action("MUTATION", "core/kernel/execution_integrity.py", ctx)
        assert res.decision == PolicyDecision.ALLOW
        # Dọn dẹp override để không ảnh hưởng test khác
        policy_engine.clear_overrides()

    def test_policy_dry_run_mode(self):
        # Chế độ dry-run không ghi nhận false alert
        ctx = SecurityContext(subject_role=SubjectRole.AGENT)
        res = policy_engine.evaluate_action("EXECUTION", "rm -rf /", ctx, dry_run=True)
        assert res.decision == PolicyDecision.DENY
