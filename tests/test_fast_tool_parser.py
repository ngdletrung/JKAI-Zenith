# -*- coding: utf-8 -*-
"""
Unit test suite cho Fast Tool Parser (Hỗ trợ 3 format Tool Call)
"""

import pytest
from core.os.cognition.fast_tool_parser import extract_tool_calls_lexical


class TestFastToolParser:
    """Kiểm tra khả năng trích xuất Tool Call đa định dạng từ các model LLM."""

    def test_extract_tool_calls_action_arguments(self):
        content = "Tôi sẽ tra cứu:\nAction: search_memory\nArguments: {\"query\": \"tỷ giá USD\"}"
        calls = extract_tool_calls_lexical(content)
        assert len(calls) == 1
        assert calls[0]["function"]["name"] == "search_memory"
        assert "tỷ giá USD" in calls[0]["function"]["arguments"]

    def test_extract_tool_calls_action_function_syntax(self):
        content = "Action: OFFICE_SUITE_MASTER(action='create_excel', filename='report.xlsx')"
        calls = extract_tool_calls_lexical(content)
        assert len(calls) == 1
        assert calls[0]["function"]["name"] == "OFFICE_SUITE_MASTER"
        assert "create_excel" in calls[0]["function"]["arguments"]

    def test_extract_tool_calls_markdown_json_block(self):
        content = (
            "Dưới đây là công cụ cần gọi:\n"
            "```json\n"
            "{\n"
            "  \"name\": \"SEARCH_WEB_GLOBAL\",\n"
            "  \"parameters\": {\"query\": \"giá vàng hôm nay\"}\n"
            "}\n"
            "```"
        )
        calls = extract_tool_calls_lexical(content)
        assert len(calls) == 1
        assert calls[0]["function"]["name"] == "SEARCH_WEB_GLOBAL"
        assert "giá vàng hôm nay" in calls[0]["function"]["arguments"]
