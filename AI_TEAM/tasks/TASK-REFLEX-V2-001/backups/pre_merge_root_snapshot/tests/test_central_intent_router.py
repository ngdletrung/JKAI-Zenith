# -*- coding: utf-8 -*-
"""
Unit test suite cho Central Intent Router v4.0 (Semantic Fallback, Compound Parser & Active Learning)
"""

import pytest
from core.os.routing.intent_router import CentralIntentRouter, IntentMode, ActionType, intent_router
from core.os.routing.semantic_fallback import semantic_fallback_engine
from core.os.routing.compound_parser import compound_intent_parser
from core.os.routing.active_learner import active_learning_engine


class TestCentralIntentRouterV4:
    """Kiểm tra toàn diện các đột phá v4.0: Semantic Fallback, Compound Intents & Active Learning."""

    def test_math_priority_addition(self):
        decision = intent_router.route("15 + 35 bằng mấy ?")
        assert decision.mode == IntentMode.MATH
        assert "50" in decision.math_result

    def test_math_with_parentheses(self):
        decision = intent_router.route("tính (3 + 5) * 2")
        assert decision.mode == IntentMode.MATH
        assert "16" in decision.math_result

    def test_math_percentage(self):
        decision = intent_router.route("tính 15% của 200000")
        assert decision.mode == IntentMode.MATH
        assert "30,000" in decision.math_result

    def test_social_query_greeting(self):
        decision = intent_router.route("bạn thấy hôm nay thế nào ?")
        assert decision.mode == IntentMode.SOCIAL
        assert decision.role == "RECEPTIONIST"
        assert decision.max_turns == 0

    def test_office_query_excel_create(self):
        decision = intent_router.route("Tạo file excel báo cáo doanh thu tháng 8 kèm biểu đồ")
        assert decision.mode == IntentMode.OFFICE
        assert decision.role == "CODE_EXECUTOR"
        assert decision.action_type == ActionType.CREATE

    def test_office_action_type_update(self):
        decision = intent_router.route("Sửa file excel báo cáo tài chính năm 2026")
        assert decision.mode == IntentMode.OFFICE
        assert decision.action_type == ActionType.UPDATE

    def test_compound_intent_multitag(self):
        # Câu phức hợp kết hợp cả tạo file Excel và phân tích sâu
        decision = intent_router.route("Tạo file excel doanh thu và phân tích so sánh chi tiết")
        assert decision.is_compound is True
        assert "OFFICE" in decision.tags
        assert "ANALYSIS" in decision.tags

    def test_semantic_fallback_paraphrase(self):
        # Câu không có từ khóa cứng trong office.yaml nhưng có ý nghĩa văn phòng
        decision = intent_router.route("lập trang tính bảng lương nhân viên chi tiết")
        assert decision.mode == IntentMode.OFFICE
        assert decision.confidence > 0.0

    def test_active_learning_recording(self):
        initial_count = len(active_learning_engine.recorded_queries)
        intent_router.route("vẽ biểu đồ đường cho báo cáo tài chính")
        assert len(active_learning_engine.recorded_queries) > initial_count

    def test_yaml_lexicons_loaded(self):
        assert len(intent_router.lexicons) >= 6
        assert "social" in intent_router.lexicons
        assert "office" in intent_router.lexicons
