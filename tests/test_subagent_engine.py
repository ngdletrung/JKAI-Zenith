import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from core.kernel.subagent_engine import subagent_engine

class TestSubagentEngine(unittest.TestCase):
    def test_define_subagent(self):
        res = subagent_engine.define_subagent(
            name="code_reviewer",
            role="Code Quality Auditor",
            system_prompt="You are an expert Python code reviewer."
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["name"], "code_reviewer")
        self.assertIn("code_reviewer", subagent_engine.definitions)

    def test_send_inter_agent_message(self):
        subagent_engine.define_subagent(
            name="tester",
            role="Test Engineer",
            system_prompt="You write unit tests."
        )
        msg_res = subagent_engine.send_message("sub_12345", "Please review PR #42")
        self.assertIn("status", msg_res)

if __name__ == "__main__":
    unittest.main()
