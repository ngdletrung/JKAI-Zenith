# -*- coding: utf-8 -*-
"""
Unit test suite cho Shadow Dry-Run, DiffBuilder và ImpactAnalyzer (Phase 4)
"""

import pytest
import asyncio
from core.kernel.shadow_dry_run import DiffBuilder, ImpactAnalyzer, shadow_runner


class TestShadowDryRun:
    """Kiểm tra chức năng Shadow Dry-Run, Diff Preview và Impact Analysis."""

    def test_diff_builder_creates_unified_diff(self):
        orig = "def old_fn():\n    return 1\n"
        mod = "def new_fn():\n    return 2\n"
        diff = DiffBuilder.create_text_diff(orig, mod, "test.py")
        assert "--- a/test.py" in diff
        assert "+++ b/test.py" in diff
        assert "-def old_fn():" in diff
        assert "+def new_fn():" in diff

    def test_diff_builder_no_change(self):
        orig = "same content"
        diff = DiffBuilder.create_text_diff(orig, orig)
        assert "Không có thay đổi" in diff

    def test_impact_analyzer_destructive_command(self):
        impact = ImpactAnalyzer.analyze_action("Xóa bỏ vĩnh viễn bảng dữ liệu database", ["db.sqlite"])
        assert impact.risk_level == "CRITICAL"
        assert impact.action_type == "DESTRUCTIVE_MUTATION"

    def test_impact_analyzer_config_change(self):
        impact = ImpactAnalyzer.analyze_action("Thay đổi file cấu hình .env và secret", [".env"])
        assert impact.risk_level == "HIGH"
        assert impact.requires_service_restart is True

    def test_impact_analyzer_file_creation(self):
        impact = ImpactAnalyzer.analyze_action("Tạo file báo cáo Excel doanh thu", ["report.xlsx"])
        assert impact.risk_level == "LOW"
        assert impact.action_type == "FILE_CREATION_OR_UPDATE"

    @pytest.mark.asyncio
    async def test_shadow_runner_executes_within_timeout(self):
        res = await shadow_runner.run_shadow_dry_run(
            action_desc="Tạo file Excel",
            task_id="test_task",
            proposal_id="prop_123",
            original_content="a = 1\n",
            target_content="a = 2\n",
            filename="calc.py"
        )
        assert res.dry_run_success is True
        assert res.execution_time_ms < 500.0
        assert "calc.py" in res.diff_preview
        assert res.impact.risk_level == "LOW"
