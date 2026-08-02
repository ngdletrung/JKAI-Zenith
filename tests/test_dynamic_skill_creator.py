import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
import unittest
from core.kernel.dynamic_skill_creator import dynamic_skill_creator

class TestDynamicSkillCreator(unittest.TestCase):
    def test_create_dynamic_skill(self):
        sample_code = """# Dynamic Skill Logic
def run_custom_audit(data=None):
    return {"status": "success", "audit": "Passed dynamic code audit"}
"""
        res = dynamic_skill_creator.create_skill(
            skill_name="test_dynamic_audit",
            description="Thao tác kiểm toán động",
            python_code=sample_code,
            category="TEST"
        )
        self.assertEqual(res["status"], "success")
        self.assertEqual(res["skill_name"], "test_dynamic_audit")
        self.assertTrue(os.path.exists(res["skill_dir"]))

if __name__ == "__main__":
    unittest.main()
