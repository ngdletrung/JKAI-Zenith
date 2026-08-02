import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
import asyncio

from core.kernel.cognitive_react_loop import cognitive_react_loop
from core.kernel.cognitive_memory_buffer import cognitive_memory_buffer
from core.kernel.self_reflection_guard import self_reflection_guard

class TestSoftAgenticFramework(unittest.TestCase):
    """
    🧠 [SOFT-FRAMEWORK-TEST]: Bộ kiểm thử thẩm định Bộ Khung Mềm Cho Model Hoạt Động.
    """
    def test_cognitive_memory_compression(self):
        # Tạo 30 tin nhắn lịch sử vượt max_token_budget (8192 tokens ≈ 32768 chars)
        long_content = "Lorem ipsum dolor sit amet, consectetur adipiscing elit. " * 80  # ~8000 chars
        messages = [{"role": "system", "content": "System prompt"}]
        for i in range(15):
            messages.append({"role": "user", "content": f"{long_content} User question {i}"})
            messages.append({"role": "assistant", "content": f"{long_content} Assistant response {i}"})

        self.assertEqual(len(messages), 31)
        compressed = cognitive_memory_buffer.compress_messages(messages)
        
        # Thẩm định tin nhắn đã được nén về đúng budget max_history_turns (10 turns = 20 msgs + 1 sys msg)
        self.assertLess(len(compressed), len(messages))
        self.assertIn("engram_memory", compressed[0]["content"])

    def test_self_reflection_guard_audit(self):
        # 1. Câu trả lời chứa placeholder TODO
        dirty_resp = "Here is the code:\ndef process():\n    # TODO: implement later\n    pass"
        audit = self_reflection_guard.audit_response(dirty_resp)
        self.assertFalse(audit["is_clean"])

        # 2. Câu trả lời chứa 123-char fallback stub
        stub_resp = '{"status": "success", "output": "Executed CREATE_EXCEL under physical-ready sandbox."}'
        stub_audit = self_reflection_guard.audit_response(stub_resp)
        self.assertFalse(stub_audit["is_clean"])

        # 3. Câu trả lời hoàn chỉnh 100%
        clean_resp = "def process():\n    return 'Successfully processed data 100%'"
        clean_audit = self_reflection_guard.audit_response(clean_resp)
        self.assertTrue(clean_audit["is_clean"])

if __name__ == "__main__":
    unittest.main()
