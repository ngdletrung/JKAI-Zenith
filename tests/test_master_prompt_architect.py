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
        # Biến thể MID
        prompt_mid = master_prompt_architect.build_master_system_prompt(role="RECEPTIONIST", task_type="CHAT", prompt_variant="MID")
        self.assertIn("JKAI Zenith", prompt_mid)
        self.assertIn("RECEPTIONIST", prompt_mid)
        self.assertIn("LIVE TIME ANCHOR", prompt_mid)

        # Biến thể FULL
        prompt_full = master_prompt_architect.build_master_system_prompt(role="RECEPTIONIST", task_type="CHAT", prompt_variant="FULL")
        self.assertIn("JKAI Zenith", prompt_full)
        self.assertIn("Master LeeTrung", prompt_full)
        self.assertIn("Live Spatio-Temporal Anchor", prompt_full)

if __name__ == "__main__":
    unittest.main()
