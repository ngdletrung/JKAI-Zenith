# -*- coding: utf-8 -*-
"""
tests/test_capability_and_typo_queries.py
Kiểm chứng tính năng nhận diện câu hỏi năng lực & chuẩn hóa lỗi gõ tiếng Việt:
1. Câu hỏi 'bạn có tính năng ai-browse ah' định tuyến FAST META_INTROSPECTION.
2. Câu hỏi 'bạn có điều khỉ được trang web' tự động sửa chính tả thành 'điều khiển' và định tuyến FAST META_INTROSPECTION.
3. Câu lệnh trực tiếp 'hãy mở trang web...' vẫn được phân tuyến chuẩn sang BROWSER execution.
"""
import unittest
import pytest
from core.os.routing.intent_router import intent_router, IntentMode
from core.kernel.tool_arbiter import tool_arbiter, ToolDomain


class TestCapabilityQuestions(unittest.TestCase):
    def test_capability_questions_all(self):
        """Mọi câu hỏi về năng lực hệ thống phải về META_INTROSPECTION / RECEPTIONIST, tuyệt đối không vào DEEP/CODING."""
        prompts = [
            "bạn có tính năng ai-browse ah",
            "bạn có tính năng ai browse không",
            "hệ thống có chức năng ai-browser không ạ",
            "bạn có điều khỉ được trang web",
            "bạn có điều khiển được trang web không",
            "bạn có thể điều khiển máy tính không",
            "bạn có làm được việc điều khiển trình duyệt không",
        ]
        for prompt in prompts:
            with self.subTest(prompt=prompt):
                decision = intent_router.route(prompt)
                self.assertEqual(decision.mode, IntentMode.META_INTROSPECTION)
                self.assertEqual(decision.role, "RECEPTIONIST")
                self.assertIn("CAPABILITY", decision.tags)
                self.assertGreaterEqual(decision.confidence, 0.95)

    def test_typo_dieu_khi_is_normalized(self):
        """Lỗi gõ 'điều khỉ' phải được xử lý chính xác như 'điều khiển'."""
        prompt = "bạn có điều khỉ được trang web"
        decision = intent_router.route(prompt)
        self.assertEqual(decision.mode, IntentMode.META_INTROSPECTION)
        self.assertEqual(decision.role, "RECEPTIONIST")

    def test_direct_action_command_still_executes_browser(self):
        """Câu lệnh thực thi trực tiếp 'hãy mở...' không bị nhầm thành câu hỏi năng lực."""
        prompt = "hãy mở trang web news.ycombinator.com và click vào nút new"
        verdict = tool_arbiter.arbitrate(prompt)
        self.assertEqual(verdict.primary_domain, ToolDomain.BROWSER)
        self.assertTrue(verdict.is_visual_required)
