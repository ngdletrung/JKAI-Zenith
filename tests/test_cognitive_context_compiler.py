import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../services/ai-brain')))

import unittest
from prompt_engine.cognitive_context_compiler import CognitiveContextCompiler
from prompt_engine.task_contract import TaskContract
from prompt_engine.cognitive_policy import CognitivePolicy
from prompt_engine.master_prompt_architect import MasterPromptArchitect


class TestCognitiveContextCompiler(unittest.TestCase):
    def setUp(self):
        self.mission_id = "test_compiler_mission_001"
        self.compiler = CognitiveContextCompiler(self.mission_id)

    def test_compile_structure(self):
        contract = TaskContract(
            objective="Compile report for PCCC",
            constraints=["Must finish within 60s"],
            forbidden_actions=["rm -rf"],
            success_criteria=["Report generated in PDF"],
            risk_level=0.2
        )
        compiled_text = self.compiler.compile(
            role="RECEPTIONIST",
            cognitive_mode="ANALYTICAL",
            contract=contract,
            max_context_chars=4000
        )
        self.assertIn("<identity", compiled_text)
        self.assertIn("ANALYTICAL", compiled_text)
        self.assertIn("<world_state", compiled_text)
        self.assertIn("<cognitive_policy", compiled_text)
        self.assertIn("<task_contract", compiled_text)
        self.assertIn("Compile report for PCCC", compiled_text)

    def test_context_budgeter(self):
        compiled_short = self.compiler.compile(
            role="RECEPTIONIST",
            cognitive_mode="REACTIVE",
            max_context_chars=300
        )
        self.assertTrue(len(compiled_short) <= 350)
        self.assertIn("Context Budget Capped", compiled_short)

    def test_master_prompt_architect_integration(self):
        mpa = MasterPromptArchitect()
        prompt = mpa.build_master_system_prompt(
            role="RECEPTIONIST",
            task_type="CHAT",
            task_id=self.mission_id,
            prompt_variant="LEAN"
        )
        self.assertIn("<identity", prompt)
        self.assertIn("<cognitive_policy>", prompt)


if __name__ == "__main__":
    unittest.main()
