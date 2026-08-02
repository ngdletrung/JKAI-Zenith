import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'services', 'ai-brain')))
import unittest

from prompt_engine.master_prompt_architect import master_prompt_architect

class TestMasterPromptArchitect(unittest.TestCase):
    def setUp(self):
        from core.guardrails.rules_loader import invalidate_cache
        invalidate_cache()

    def test_build_master_system_prompt(self):
        prompt = master_prompt_architect.build_master_system_prompt(role="RECEPTIONIST", task_type="CHAT")
        self.assertIn("JKAI Zenith", prompt)
        self.assertIn("Master LeeTrung", prompt)
        self.assertIn("Project Rules", prompt)
        self.assertIn("Behavioral Directives", prompt)
        self.assertIn("Task Mode: CHAT", prompt)
        self.assertIn("Response Format", prompt)
        self.assertIn(".jkairules.json", prompt)

if __name__ == "__main__":
    unittest.main()
