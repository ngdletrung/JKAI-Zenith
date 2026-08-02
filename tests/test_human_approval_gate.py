import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from core.utils.human_approval_gate import eval_tool_risk, create_approval_interrupt

class TestHumanApprovalGate(unittest.TestCase):
    def test_low_risk_command(self):
        req, reason = eval_tool_risk("run_command", {"command": "ls -la"})
        self.assertFalse(req)

    def test_high_risk_rm_command(self):
        req, reason = eval_tool_risk("run_command", {"command": "rm -rf /tmp/test"})
        self.assertTrue(req)
        self.assertIn("High-risk command execution pattern", reason)

    def test_high_risk_env_file_edit(self):
        req, reason = eval_tool_risk("replace_file_content", {"path": "/project/.env"})
        self.assertTrue(req)
        self.assertIn("Modification of critical system file", reason)

    def test_create_approval_interrupt(self):
        payload = create_approval_interrupt("task_123", "run_command", {"command": "del file.txt"}, "Testing interrupt")
        self.assertEqual(payload["status"], "INTERRUPTED_AWAITING_APPROVAL")
        self.assertTrue(payload["requires_approval"])

if __name__ == "__main__":
    unittest.main()
