import sys, os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../services/ai-brain')))

import unittest
from prompt_engine.cognitive_context_compiler import CognitiveContextCompiler
from prompt_engine.task_contract import TaskContract, DecisionAuthority, CompletionStatus
from prompt_engine.cognitive_policy import CognitivePolicy
from prompt_engine.master_prompt_architect import MasterPromptArchitect


class TestCognitiveContextCompilerV261(unittest.TestCase):
    """
    Test suite updated to v26.1.
    Covers: structure, budget, MPA integration, 9 distinct modes,
    provenance tagging, compiled_context_snapshot_diff, and Decision Authority.
    """

    def setUp(self):
        self.mission_id = "test_compiler_mission_001"
        self.compiler = CognitiveContextCompiler(self.mission_id)

    # ------------------------------------------------------------------
    # Original 3 tests — unchanged
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # NEW v26.1 — Test: all 9 cognitive modes produce distinct directives
    # ------------------------------------------------------------------
    def test_nine_modes_all_distinct(self):
        """Each mode must produce a unique, non-fallback directive."""
        MODES = [
            "REACTIVE", "ANALYTICAL", "PLANNING", "EXECUTION",
            "DEBUGGING", "REFLECTION", "RECOVERY", "LEARNING", "EXPLORATION"
        ]
        outputs = {}
        for mode in MODES:
            out = self.compiler.compile(cognitive_mode=mode, max_context_chars=1000)
            self.assertIn("<mode_directive", out, f"mode_directive missing for {mode}")
            self.assertIn(mode, out, f"{mode} not found in its own compiled output")
            outputs[mode] = out

        # Each mode output must be distinct from every other
        seen = list(outputs.values())
        for i, m in enumerate(MODES):
            for j, n in enumerate(MODES):
                if i != j:
                    self.assertNotEqual(
                        outputs[m], outputs[n],
                        f"Modes {m} and {n} produced identical output — possible fallback collision"
                    )

    # ------------------------------------------------------------------
    # NEW v26.1 — Test: provenance tags present on all key sections
    # ------------------------------------------------------------------
    def test_provenance_tags(self):
        """All major sections must carry a source= provenance attribute."""
        compiled = self.compiler.compile(
            role="RECEPTIONIST",
            cognitive_mode="ANALYTICAL",
            max_context_chars=4000
        )
        self.assertIn('source="system_kernel"', compiled,  "identity missing provenance")
        self.assertIn('source="UCWS"',          compiled,  "world_state missing provenance")
        self.assertIn('source="policy_engine"', compiled,  "cognitive_policy missing provenance")
        self.assertIn('source="adaptive_mode"', compiled,  "mode_directive missing provenance")

    # ------------------------------------------------------------------
    # NEW v26.1 — Test: compiled_context_snapshot_diff present per cycle
    # ------------------------------------------------------------------
    def test_compiled_context_snapshot_diff(self):
        """After a second compile the diff tag must appear in world_state."""
        # Compile once to seed the snapshot
        self.compiler.compile(cognitive_mode="REACTIVE", max_context_chars=2000)
        # Compile again — now diff should be non-empty
        second = self.compiler.compile(cognitive_mode="ANALYTICAL", max_context_chars=2000)
        self.assertIn("<compiled_context_snapshot_diff>", second,
                      "compiled_context_snapshot_diff tag missing after second cycle")

    # ------------------------------------------------------------------
    # NEW v26.1 — Test: Decision Authority rendered in task_contract
    # ------------------------------------------------------------------
    def test_decision_authority_rendered(self):
        contract = TaskContract(
            objective="Safe audit",
            decision_authority=DecisionAuthority(
                can_modify_files=True,
                can_delete_files=False,
                can_send_external_message=False
            ),
            completion_status=CompletionStatus(
                required=["audit_report.pdf"],
                validated_evidence=[]
            )
        )
        compiled = self.compiler.compile(
            role="RECEPTIONIST",
            cognitive_mode="EXECUTION",
            contract=contract,
            max_context_chars=4000
        )
        # Decision Authority is rendered as JSON inside <decision_authority> tag
        self.assertIn('"can_modify_files": true',  compiled)
        self.assertIn('"can_delete_files": false',  compiled)
        self.assertIn('"can_send_external_message": false', compiled)
        self.assertIn("audit_report.pdf",            compiled)

    # ------------------------------------------------------------------
    # NEW v26.1 — Test: task_contract source tag
    # ------------------------------------------------------------------
    def test_task_contract_source_tag(self):
        contract = TaskContract(objective="Verify deployment")
        compiled = self.compiler.compile(
            role="RECEPTIONIST", cognitive_mode="PLANNING",
            contract=contract, max_context_chars=4000
        )
        self.assertIn('source="execution_contract"', compiled,
                      "task_contract provenance tag missing")


if __name__ == "__main__":
    unittest.main()
