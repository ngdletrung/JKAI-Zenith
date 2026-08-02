"""
Unit Tests: critic.py - Sentinel Fast-track & LLM Audit Logic
Kiểm thử cơ chế phê duyệt nhanh cho các kế hoạch đơn giản thưa Master.
"""
import os
import sys
import unittest
from unittest.mock import MagicMock, AsyncMock, patch

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "..", "services", "ai-brain"))


class TestCriticSentinelFastTrack(unittest.TestCase):
    """Test cơ chế Sentinel Fast-track trong critic.py thưa Master."""

    def _make_plan(self, steps: list, tool_calls: list = None) -> dict:
        """Tạo cấu trúc plan giả để test thưa Master."""
        plan_steps = []
        for i, desc in enumerate(steps):
            plan_steps.append({
                "step_id": i + 1,
                "description": desc,
                "tool_calls": tool_calls or []
            })
        return {"steps": plan_steps}

    def test_single_step_no_dangerous_tools_should_fasttrack(self):
        """Plan 1 bước, không dùng tool nguy hiểm -> fast-track thưa Master."""
        from critic import is_safe_for_fasttrack
        plan = self._make_plan(["Trả lời câu hỏi của Master"])
        self.assertTrue(is_safe_for_fasttrack(plan))

    def test_single_step_with_write_tool_should_not_fasttrack(self):
        """Plan 1 bước nhưng dùng write_file -> phải qua LLM thưa Master."""
        from critic import is_safe_for_fasttrack
        plan = self._make_plan(
            ["Ghi file config"],
            tool_calls=[{"tool": "write_file", "args": {}}]
        )
        self.assertFalse(is_safe_for_fasttrack(plan))

    def test_multi_step_plan_should_not_fasttrack(self):
        """Plan nhiều bước -> luôn phải qua LLM kiểm duyệt thưa Master."""
        from critic import is_safe_for_fasttrack
        plan = self._make_plan([
            "Tìm thông tin",
            "Phân tích dữ liệu",
            "Báo cáo kết quả"
        ])
        self.assertFalse(is_safe_for_fasttrack(plan))

    def test_single_step_with_shell_tool_should_not_fasttrack(self):
        """Plan 1 bước dùng shell tool -> phải qua LLM thưa Master."""
        from critic import is_safe_for_fasttrack
        plan = self._make_plan(
            ["Chạy lệnh terminal"],
            tool_calls=[{"tool": "run_shell", "args": {}}]
        )
        self.assertFalse(is_safe_for_fasttrack(plan))

    def test_empty_steps_should_fasttrack(self):
        """Plan rỗng (không có bước nào) -> fast-track thưa Master."""
        from critic import is_safe_for_fasttrack
        plan = {"steps": []}
        self.assertTrue(is_safe_for_fasttrack(plan))


class TestCriticHelpers(unittest.TestCase):
    """Test các hàm tiện ích trong critic.py thưa Master."""

    def test_plan_structure_validation(self):
        """Critic phải xử lý được plan có cấu trúc không chuẩn thưa Master."""
        try:
            from critic import is_safe_for_fasttrack
            # Plan thiếu key 'steps'
            self.assertTrue(is_safe_for_fasttrack({}))
            # Plan với steps không phải list
            self.assertTrue(is_safe_for_fasttrack({"steps": None}))
        except (ImportError, AttributeError):
            self.skipTest("critic.py chưa expose hàm is_safe_for_fasttrack")


if __name__ == "__main__":
    unittest.main()
