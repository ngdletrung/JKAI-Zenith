# -*- coding: utf-8 -*-
"""
Unit test suite cho Tool Registry & Governance Engine
"""

import pytest
from core.kernel.tool_registry import ToolRegistry, ToolDefinition, RiskLevel, ExecutionMode


class TestToolRegistry:
    """Kiểm tra chức năng đăng ký, truy vấn, phân quyền và kiểm soát rủi ro Tool."""

    def test_register_and_resolve_tool(self):
        reg = ToolRegistry()
        tool = ToolDefinition(
            name="OFFICE_EXCEL_BUILDER",
            version="1.0.0",
            description="Tạo file Excel",
            risk=RiskLevel.LOW,
            permissions=("file:write",),
            timeout=30,
            schema={},
            deterministic=True,
            side_effects=True,
            idempotent=True,
            max_retries=2,
            allowed_sources=("FAST_PIPELINE",),
            execution_mode=ExecutionMode.SYNC
        )
        reg.register(tool)
        
        # Resolve by name
        resolved = reg.resolve("OFFICE_EXCEL_BUILDER")
        assert resolved is not None
        assert resolved.name == "OFFICE_EXCEL_BUILDER"
        assert resolved.version == "1.0.0"

        # Resolve by version
        resolved_v = reg.resolve("OFFICE_EXCEL_BUILDER", "1.0.0")
        assert resolved_v is not None

    def test_filter_by_risk_level(self):
        reg = ToolRegistry()
        t1 = ToolDefinition(
            name="SAFE_READ", version="1.0", description="read",
            risk=RiskLevel.LOW, permissions=("file:read",), timeout=5, schema={},
            deterministic=True, side_effects=False, idempotent=True, max_retries=1,
            allowed_sources=("ALL",), execution_mode=ExecutionMode.SYNC
        )
        t2 = ToolDefinition(
            name="SHELL_EXEC", version="1.0", description="exec",
            risk=RiskLevel.CRITICAL, permissions=("os:exec",), timeout=10, schema={},
            deterministic=False, side_effects=True, idempotent=False, max_retries=0,
            allowed_sources=("MASTER_ONLY",), execution_mode=ExecutionMode.SYNC
        )
        reg.register(t1)
        reg.register(t2)

        low_risk = reg.list_tools(filter_risk=RiskLevel.LOW)
        assert len(low_risk) == 1
        assert low_risk[0].name == "SAFE_READ"

        crit_risk = reg.list_tools(filter_risk=RiskLevel.CRITICAL)
        assert len(crit_risk) == 1
        assert crit_risk[0].name == "SHELL_EXEC"

    def test_permission_check(self):
        reg = ToolRegistry()
        tool = ToolDefinition(
            name="SECURE_QUERY", version="1.0", description="query",
            risk=RiskLevel.LOW, permissions=("db:read", "cache:read"), timeout=5, schema={},
            deterministic=True, side_effects=False, idempotent=True, max_retries=1,
            allowed_sources=("ALL",), execution_mode=ExecutionMode.SYNC
        )
        reg.register(tool)

        assert reg.has_permission("SECURE_QUERY", "db:read") is True
        assert reg.has_permission("SECURE_QUERY", "os:exec") is False
        assert reg.has_permission("UNKNOWN_TOOL", "db:read") is False
