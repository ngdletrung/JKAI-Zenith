import sys, os, unittest
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../services/ai-brain')))

from core.kernel.execution_integrity import ExecutionIntegrityLayer, DecisionOutcome, ExecutionDecision
from prompt_engine.task_contract import TaskContract, DecisionAuthority
from prompt_engine.cognitive_context_compiler import CognitiveContextCompiler
from core.os.ucws import reduce_world_state, get_ucws


class TestExecutionIntegrityLayer(unittest.TestCase):
    """
    Test suite for v26.2 Execution Integrity Layer & Context Projection Invariants.
    Verifies:
      1. Hard boundary DENY when can_delete_files=False
      2. Hard boundary DENY when can_send_external_message=False
      3. REQUIRE_APPROVAL for high-risk operations
      4. Fail-Closed invariant on missing/malformed contract or authority
      5. Context Projection recoverable invariant for entities, relationships, and causality
    """

    def setUp(self):
        self.mission_id = "test_integrity_mission_001"
        self.integrity = ExecutionIntegrityLayer(self.mission_id)
        self.compiler  = CognitiveContextCompiler(self.mission_id)

    # -------------------------------------------------------------------------
    # Fail-Closed Invariant Tests
    # -------------------------------------------------------------------------
    def test_fail_closed_missing_contract(self):
        """Action must be DENIED if task_contract is missing."""
        decision = self.integrity.authorize("delete_file", {"file_path": "/tmp/a.txt"}, task_contract=None)
        self.assertEqual(decision.outcome, DecisionOutcome.DENY)
        self.assertIn("FAIL-CLOSED", decision.reason)

    def test_fail_closed_missing_authority(self):
        """Action must be DENIED if decision_authority is missing."""
        contract = TaskContract(objective="Audit")
        contract.decision_authority = None
        decision = self.integrity.authorize("write_file", {"file_path": "/tmp/b.txt"}, task_contract=contract)
        self.assertEqual(decision.outcome, DecisionOutcome.DENY)
        self.assertIn("FAIL-CLOSED", decision.reason)

    # -------------------------------------------------------------------------
    # Hard Authority Boundary Tests
    # -------------------------------------------------------------------------
    def test_hard_deny_deletion(self):
        """Action 'delete' must be HARD DENIED when can_delete_files=False."""
        contract = TaskContract(
            objective="Cleanup",
            decision_authority=DecisionAuthority(can_delete_files=False, can_modify_files=True)
        )
        decision = self.integrity.authorize("delete_file", {"TargetFile": "draft.docx"}, task_contract=contract)
        self.assertEqual(decision.outcome, DecisionOutcome.DENY)
        self.assertIn("can_delete_files=False", decision.reason)

    def test_hard_deny_external_communication(self):
        """Action 'send_message' or 'email' must be HARD DENIED when can_send_external_message=False."""
        contract = TaskContract(
            objective="Notify customer",
            decision_authority=DecisionAuthority(can_send_external_message=False)
        )
        decision = self.integrity.authorize("send_email", {"recipient": "client@example.com"}, task_contract=contract)
        self.assertEqual(decision.outcome, DecisionOutcome.DENY)
        self.assertIn("can_send_external_message=False", decision.reason)

    def test_require_approval_for_high_risk(self):
        """High-risk actions (e.g. modifying .env or destructive bash) must trigger REQUIRE_APPROVAL."""
        contract = TaskContract(
            objective="System edit",
            decision_authority=DecisionAuthority(can_modify_files=True, can_delete_files=True)
        )
        decision = self.integrity.authorize("write_file", {"file_path": ".env"}, task_contract=contract)
        self.assertEqual(decision.outcome, DecisionOutcome.REQUIRE_APPROVAL)
        self.assertTrue(decision.requires_human_gate)
        self.assertIsNotNone(decision.interrupt_id)

    def test_allow_safe_read(self):
        """Safe read operations must be ALLOWED."""
        contract = TaskContract(
            objective="Read data",
            decision_authority=DecisionAuthority(can_modify_files=True)
        )
        decision = self.integrity.authorize("read_file", {"file_path": "report.pdf"}, task_contract=contract)
        self.assertEqual(decision.outcome, DecisionOutcome.ALLOW)

    # -------------------------------------------------------------------------
    # Context Projection Invariant Tests (Entities, Relationships, Causality)
    # -------------------------------------------------------------------------
    def test_context_projection_entities_recoverable(self):
        """UCWS entity attributes must be projected into model-visible compiled context."""
        ucws = get_ucws(self.mission_id)
        reduce_world_state(ucws, {
            "event_type": "ENTITY_ADDED",
            "payload": {
                "entity_id": "file:hop_dong_2026.docx",
                "data": {"name": "hop_dong_2026.docx", "type": "file", "status": "validated"}
            }
        })
        compiled = self.compiler.compile(cognitive_mode="ANALYTICAL", max_context_chars=4000)
        self.assertIn("hop_dong_2026.docx", compiled)
        self.assertIn("validated", compiled)

    def test_context_projection_relationships_recoverable(self):
        """UCWS relationships must be projected into model-visible compiled context."""
        ucws = get_ucws(self.mission_id)
        reduce_world_state(ucws, {
            "event_type": "RELATIONSHIP_LINKED",
            "payload": {
                "relation_key": "A_depends_B",
                "targets": ["file:B.docx"]
            }
        })
        compiled = self.compiler.compile(cognitive_mode="ANALYTICAL", max_context_chars=4000)
        self.assertIn("A_depends_B", compiled)
        self.assertIn("file:B.docx", compiled)

    def test_context_projection_causality_recoverable(self):
        """UCWS causality edges must be projected into model-visible compiled context."""
        ucws = get_ucws(self.mission_id)
        reduce_world_state(ucws, {
            "event_type": "CAUSALITY_RECORDED",
            "payload": {
                "cause": "validation_run_step_8",
                "effect": "document.status=validated",
                "confidence": 0.99
            }
        })
        compiled = self.compiler.compile(cognitive_mode="ANALYTICAL", max_context_chars=4000)
        self.assertIn("validation_run_step_8", compiled)
        self.assertIn("document.status=validated", compiled)


if __name__ == "__main__":
    unittest.main()
