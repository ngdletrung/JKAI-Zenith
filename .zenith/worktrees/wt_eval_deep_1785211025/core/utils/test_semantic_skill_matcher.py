import sys
import unittest
from pathlib import Path

# Add root directory to sys.path
PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

sys.stdout.reconfigure(encoding='utf-8')

from core.utils.semantic_skill_matcher import get_matcher
from core.utils.ingress_skill_gate import enrich_goal_with_deck

class TestSemanticSkillMatcher(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.matcher = get_matcher()

    def test_true_positives(self):
        cases = [
            ("sua loi IndexError trong main.py", "DEBUGGING_AND_ERROR_RECOVERY"),
            ("review code nay", "CODE_REVIEW_AND_QUALITY"),
            ("bao mat API key", "SECURITY_AND_HARDENING"),
            ("viet dac ta cho feature moi", "SPEC_DRIVEN_DEVELOPMENT"),
            ("tinh loc y tuong du an", "IDEA_REFINE"),
            ("viet unit test cho module login", "TEST_DRIVEN_DEVELOPMENT"),
            ("toi muon thiet ke API", "API_AND_INTERFACE_DESIGN"),
            ("tối ưu ram cpu", "PERFORMANCE_OPTIMIZATION"),
            ("làm sao dọn dẹp code rác", "DEPRECATION_AND_MIGRATION"),
            ("chay devtools kiem tra memory leak", "BROWSER_TESTING_WITH_DEVTOOLS")
        ]

        print("\n=== RUNNING TRUE POSITIVE TESTS ===")
        for goal, expected_skill in cases:
            matches = self.matcher.match(goal, top_k=1, min_score=0.40)
            self.assertTrue(len(matches) > 0, f"Failed to match any skill for goal: '{goal}'")
            best_match = matches[0]
            print(f"Goal: '{goal:35}' -> Matched: {best_match.skill_id:30} (score={best_match.score:.3f})")
            self.assertEqual(best_match.skill_id, expected_skill, f"Goal '{goal}' matched {best_match.skill_id} instead of {expected_skill}")

    def test_true_negatives(self):
        cases = [
            "hello, hom nay the nao",
            "chao ban",
            "thoi tiet hom nay",
            "an gi hom nay",
            "how is the weather"
        ]

        print("\n=== RUNNING TRUE NEGATIVE TESTS ===")
        for goal in cases:
            matches = self.matcher.match(goal, top_k=1, min_score=0.40)
            if matches:
                print(f"Goal: '{goal:35}' -> Matched: {matches[0].skill_id} (score={matches[0].score:.3f}) [FALSE POSITIVE!]")
            else:
                print(f"Goal: '{goal:35}' -> No match [OK]")
            self.assertEqual(len(matches), 0, f"Goal '{goal}' should not match any skill, but matched {matches[0].skill_id if matches else ''}")

    def test_enrichment_pipeline(self):
        print("\n=== RUNNING ENRICHMENT PIPELINE TESTS ===")
        goal = "sua loi IndexError trong main.py"
        enriched, ids, warn = enrich_goal_with_deck(goal)
        print(f"Original: '{goal}'")
        print(f"Enriched: '{enriched[:120]}...'")
        print(f"Matched IDs: {ids}")
        self.assertIn("DEBUGGING_AND_ERROR_RECOVERY", ids)
        self.assertIn("<ZENITH_SKILL_ACTIVATED>", enriched)

if __name__ == "__main__":
    unittest.main()
