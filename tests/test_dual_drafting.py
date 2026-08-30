# -*- coding: utf-8 -*-
"""
Unit test suite cho DualDraftingEngine & StepPreWarmer
"""

import pytest
from core.planning.dual_drafter import PlanCoverageValidator, parse_plan_json


class TestDualDrafting:
    """Kiểm tra độ chính xác của Validator và cơ chế bóc tách kế hoạch."""

    def test_coverage_validator_approves_comprehensive_plan(self):
        validator = PlanCoverageValidator()
        goal = "Xây dựng hệ thống phân tích dữ liệu bán hàng và xuất file Excel"
        steps = [
            {"id": "step_1", "description": "Khảo sát và thu thập dữ liệu bán hàng", "type": "recon"},
            {"id": "step_2", "description": "Thực thi phân tích dữ liệu bán hàng và tạo file Excel", "type": "execute"},
            {"id": "step_3", "description": "Kiểm định file Excel xuất ra có đủ dữ liệu", "type": "verify"}
        ]
        res = validator.evaluate_draft(goal, steps)
        assert res["approved"] is True
        assert res["quality_score"] >= 0.70
        assert res["has_execute"] is True
        assert res["has_verify"] is True

    def test_coverage_validator_rejects_empty_plan(self):
        validator = PlanCoverageValidator()
        res = validator.evaluate_draft("Mục tiêu bất kỳ", [])
        assert res["approved"] is False
        assert res["score"] == 0.0

    def test_parse_plan_json_with_json_block(self):
        raw = (
            "Dưới đây là kế hoạch:\n"
            "```json\n"
            "{\"steps\": [{\"id\": \"s1\", \"description\": \"Bước 1\", \"type\": \"recon\"}]}\n"
            "```"
        )
        plan = parse_plan_json(raw, "Test")
        assert "steps" in plan
        assert len(plan["steps"]) == 1
        assert plan["steps"][0]["id"] == "s1"

    def test_parse_plan_json_fallback_with_bullet_points(self):
        raw = (
            "Kế hoạch gồm các bước:\n"
            "- 1. Thu thập thông tin mạng\n"
            "- 2. Tổng hợp dữ liệu thành báo cáo\n"
            "- 3. Kiểm tra chất lượng"
        )
        plan = parse_plan_json(raw, "Test")
        assert "steps" in plan
        assert len(plan["steps"]) == 3
