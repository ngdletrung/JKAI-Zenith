# -*- coding: utf-8 -*-
"""
🧪 TEST SUITE: SEMANTIC SKILL RUNTIME & DYNAMIC RETRIEVAL (MCP COMPLIANT)
Kiểm thử toàn diện:
1. Đăng ký và tuân thủ chuẩn MCP của Semantic Skill Manifest.
2. Khả năng truy xuất công cụ động theo ngữ cảnh (Dynamic Tool Retrieval).
3. Đánh chặn Anti-trigger (Tránh gọi tool bừa bãi khi không cần thiết).
4. Tiền kiểm tham số (Pre-flight validation) và tạo thông điệp tự sửa lỗi (Self-healing feedback).
"""

import pytest
from core.kernel.skill_manifest_schema import SemanticSkillManifest, SkillDomain
from core.kernel.semantic_skill_registry import semantic_skill_registry, SemanticSkillRegistry
from core.os.cognition.skill_retriever import DynamicSkillRetriever, skill_retriever


class TestSemanticSkillRuntime:

    def test_01_mcp_tool_definition_generation(self):
        """Manifest tạo ra định dạng MCP tool definition chuẩn xác."""
        manifest = semantic_skill_registry.get_manifest("SEARCH_WEB_GLOBAL")
        assert manifest is not None
        mcp_def = manifest.to_mcp_tool_def()

        assert mcp_def["type"] == "function"
        fn = mcp_def["function"]
        assert fn["name"] == "SEARCH_WEB_GLOBAL"
        assert "✅ [KHI NÀO NÊN DÙNG]" in fn["description"]
        assert "⛔ [KHI NÀO TUYỆT ĐỐI KHÔNG DÙNG]" in fn["description"]
        assert "query" in fn["parameters"]["properties"]
        assert "query" in fn["parameters"]["required"]

    def test_02_dynamic_retrieval_realtime_financial_intent(self):
        """Truy vấn giá vàng/tỷ giá thời gian thực -> Tự động nạp SEARCH_WEB_GLOBAL."""
        verdict = skill_retriever.retrieve_active_tools(
            query="Tình hình giá vàng hôm nay và tỷ giá USD thế nào?",
            top_k=2
        )
        selected_ids = [m.skill_id for m in verdict.selected_manifests]
        assert "SEARCH_WEB_GLOBAL" in selected_ids
        assert len(verdict.mcp_tools) <= 2

    def test_03_dynamic_retrieval_graph_correlation_intent(self):
        """Truy vấn phân tích đồ thị/mạng lưới quan hệ -> Nạp SKILL_DATA_48_GRAPH."""
        verdict = skill_retriever.retrieve_active_tools(
            query="Phân tích mạng lưới tương quan giữa FED, Địa chính trị và Giá vàng",
            top_k=2
        )
        selected_ids = [m.skill_id for m in verdict.selected_manifests]
        assert "SKILL_DATA_48_GRAPH" in selected_ids

    def test_04_anti_trigger_greeting_exclusion(self):
        """Câu chào hỏi xã giao -> Bị phạt điểm anti-trigger, không nạp SEARCH_WEB_GLOBAL."""
        verdict = skill_retriever.retrieve_active_tools(
            query="Xin chào JKAI, bạn có khỏe không?",
            top_k=2
        )
        selected_ids = [m.skill_id for m in verdict.selected_manifests]
        assert "SEARCH_WEB_GLOBAL" not in selected_ids

    def test_05_preflight_argument_validation_missing_query(self):
        """Gọi SEARCH_WEB_GLOBAL nhưng truyền thiếu 'query' -> Báo lỗi tiền kiểm."""
        is_valid, err_msg = skill_retriever.validate_tool_call(
            tool_name="SEARCH_WEB_GLOBAL",
            arguments={}
        )
        assert is_valid is False
        assert "Thiếu tham số bắt buộc 'query'" in err_msg

    def test_06_preflight_argument_validation_valid(self):
        """Gọi SEARCH_WEB_GLOBAL đầy đủ tham số -> Passed."""
        is_valid, err_msg = skill_retriever.validate_tool_call(
            tool_name="SEARCH_WEB_GLOBAL",
            arguments={"query": "giá vàng hôm nay"}
        )
        assert is_valid is True
        assert err_msg is None

    def test_07_graph_skill_argument_validation(self):
        """Gọi SKILL_DATA_48_GRAPH thiếu analysis_type -> Báo lỗi."""
        is_valid, err_msg = skill_retriever.validate_tool_call(
            tool_name="SKILL_DATA_48_GRAPH",
            arguments={"nodes": ["Vang", "USD"]}
        )
        assert is_valid is False
        assert "Thiếu tham số bắt buộc 'analysis_type'" in err_msg


if __name__ == "__main__":
    t = TestSemanticSkillRuntime()
    t.test_01_mcp_tool_definition_generation()
    t.test_02_dynamic_retrieval_realtime_financial_intent()
    t.test_03_dynamic_retrieval_graph_correlation_intent()
    t.test_04_anti_trigger_greeting_exclusion()
    t.test_05_preflight_argument_validation_missing_query()
    t.test_06_preflight_argument_validation_valid()
    t.test_07_graph_skill_argument_validation()
    print("ALL TESTS PASSED!")
