# -*- coding: utf-8 -*-
"""
Unit test suite cho ZenithPromptAssembler v5.0 (PromptParams & Context Orchestrator)
"""

import os
import sys
import pytest

# Thêm services/ai-brain vào sys.path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "ai-brain"))
from prompt_assembler import ZenithPromptAssembler, PromptParams
from core.os.routing.intent_router import IntentMode


class TestZenithPromptAssemblerV5:
    """Kiểm tra độ chính xác của PromptParams và điều phối ngữ cảnh v5.0."""

    def test_get_prompt_params_multitag(self):
        params = ZenithPromptAssembler.get_prompt_params("Viết python script phân tích dữ liệu")
        assert isinstance(params, PromptParams)
        assert params.task_type == "CODING"
        assert "CODING" in params.tags
        assert "ANALYSIS" in params.tags
        assert params.mode == IntentMode.CODING

    def test_get_prompt_params_max_turns_allocation(self):
        # 1. Social -> max_turns = 0
        social_p = ZenithPromptAssembler.get_prompt_params("Chào bạn, bạn khỏe không ?")
        assert social_p.max_turns == 0
        assert social_p.mode == IntentMode.SOCIAL

        # 2. Office -> max_turns = 1
        office_p = ZenithPromptAssembler.get_prompt_params("Tạo file excel báo cáo doanh thu")
        assert office_p.max_turns == 1
        assert office_p.action_type == "CREATE"

        # 3. Realtime -> max_turns = 3
        realtime_p = ZenithPromptAssembler.get_prompt_params("Giá vàng hôm nay bao nhiêu ?")
        assert realtime_p.max_turns == 3
        assert realtime_p.need_web is True

        # 4. Reasoning -> max_turns = 5
        reasoning_p = ZenithPromptAssembler.get_prompt_params("Phân tích so sánh hai mô hình")
        assert reasoning_p.max_turns == 5

    def test_assemble_context_injects_action_type(self):
        extra = {}
        sys_p, user_p = ZenithPromptAssembler.assemble_prompt(
            goal="Sửa file excel báo cáo tài chính",
            manifesto="Test Manifesto",
            skills_dna="Test Skills",
            kb_context="Test KB",
            extra_context=extra
        )
        assert extra.get("action_type") == "UPDATE"
        assert extra.get("mode") == "OFFICE"
        assert isinstance(sys_p, str)

    def test_classify_task_backward_compatibility(self):
        task_type = ZenithPromptAssembler.classify_task("Viết hàm tính fibonacci bằng Python")
        assert task_type == "CODING"
