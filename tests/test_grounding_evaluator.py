import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

import unittest
from core.utils.grounding_evaluator import scrub_secrets, evaluate_grounding

class TestGroundingEvaluator(unittest.TestCase):
    def test_scrub_secrets(self):
        raw = "API_KEY=sk-1234567890abcdef1234567890abcdef and password='mysecretpassword123'"
        clean = scrub_secrets(raw)
        self.assertNotIn("sk-1234567890abcdef1234567890abcdef", clean)
        self.assertIn("REDACTED", clean)

    def test_evaluate_grounding_clean(self):
        text = "```python\nprint('hello')\n```"
        score, report = evaluate_grounding(text)
        self.assertEqual(score, 1.0)
        self.assertTrue(report["valid"])

    def test_evaluate_grounding_unclosed_fence(self):
        text = "```python\nprint('hello')"
        score, report = evaluate_grounding(text)
        self.assertLess(score, 1.0)
        self.assertFalse(report["valid"])

if __name__ == "__main__":
    unittest.main()
