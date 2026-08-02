# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: tests/test_benchmark_integration_v21.py
# - Role: Benchmark v2.1 — Integration & Bypass-Resistance Proof Suite
# - Ownership: Master LeeTrung
# - Status: Active | Version: SDS v26.2 (Execution Integrity Runtime Enforcement)
# -----------------------------------------------------------------------------

import os
import sys
import asyncio
import unittest
from unittest.mock import AsyncMock, MagicMock, patch

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../services/ai-brain')))

from core.kernel.execution_integrity import DecisionOutcome, ExecutionDecision, ExecutionResult
from core.kernel.task_contract_store import (
    set_active_contract,
    get_active_contract,
    clear_contract,
    clear_task
)
from prompt_engine.task_contract import TaskContract, DecisionAuthority
from receptionist.executor_gateway import ExecutorGateway, ExecutionRequest


class TestBenchmarkIntegrationV21(unittest.IsolatedAsyncioTestCase):
    """
    Benchmark v2.1 Verification Suite.
    Proves that Execution Integrity Layer is runtime-enforced, bypass-resistant, and fail-closed.
    """

    def setUp(self):
        self.mock_http_client = AsyncMock()
        self.gateway = ExecutorGateway(http_client=self.mock_http_client)

    def tearDown(self):
        clear_task("task_A")
        clear_task("task_B")
        clear_task("task_test")
        clear_task("task_spoofed")

    # =========================================================================
    # Group A: 3-State Authority Proof
    # =========================================================================
    async def test_A1_deny_proof(self):
        """A1: DENY proof — when authority forbids action, DENY is returned and HTTP executor call count is 0."""
        task_id = "task_A"
        contract = TaskContract(
            objective="Cleanup work",
            decision_authority=DecisionAuthority(can_delete_files=False)
        )
        set_active_contract(task_id, contract)

        req = ExecutionRequest(
            trace_id="tr_a1",
            capability_token={},
            tool_name="delete_file",
            tool_args={"TargetFile": "important.docx"}
        )

        res = await self.gateway.execute_tool(req, task_id=task_id)

        self.assertIsInstance(res, ExecutionResult)
        self.assertEqual(res.outcome, DecisionOutcome.DENY)
        self.assertFalse(res.tool_executed)
        self.assertIn("can_delete_files=False", res.reason)
        # HTTP executor MUST NOT have been called
        self.assertEqual(self.mock_http_client.post.call_count, 0)

    async def test_A2_require_approval_proof(self):
        """A2: REQUIRE_APPROVAL proof — high-risk action halts, returns interrupt_id, HTTP call count is 0."""
        task_id = "task_A"
        contract = TaskContract(
            objective="Update config",
            decision_authority=DecisionAuthority(can_modify_files=True)
        )
        set_active_contract(task_id, contract)

        req = ExecutionRequest(
            trace_id="tr_a2",
            capability_token={},
            tool_name="write_file",
            tool_args={"file_path": ".env", "content": "SECRET=123"}
        )

        res = await self.gateway.execute_tool(req, task_id=task_id)

        self.assertIsInstance(res, ExecutionResult)
        self.assertEqual(res.outcome, DecisionOutcome.REQUIRE_APPROVAL)
        self.assertFalse(res.tool_executed)
        self.assertIsNotNone(res.interrupt_id)
        # HTTP executor MUST NOT have been called
        self.assertEqual(self.mock_http_client.post.call_count, 0)

    async def test_A3_allow_proof(self):
        """A3: ALLOW proof — safe action proceeds, returns ALLOW, and HTTP executor is called 1 time."""
        task_id = "task_A"
        contract = TaskContract(
            objective="Read data",
            decision_authority=DecisionAuthority(can_modify_files=True)
        )
        set_active_contract(task_id, contract)

        # Mock HTTP response from executor
        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "output": "File content mock"}
        self.mock_http_client.post.return_value = mock_response

        with patch("core.utils.registry.registry.get_service_url", return_value="http://mock-executor"):
            req = ExecutionRequest(
                trace_id="tr_a3",
                capability_token={},
                tool_name="read_file",
                tool_args={"file_path": "report.pdf"}
            )
            res = await self.gateway.execute_tool(req, task_id=task_id)

            self.assertIsInstance(res, ExecutionResult)
            self.assertEqual(res.outcome, DecisionOutcome.ALLOW)
            self.assertTrue(res.tool_executed)
            self.assertEqual(res.result, "File content mock")
            # HTTP executor MUST have been called exactly 1 time
            self.assertEqual(self.mock_http_client.post.call_count, 1)

    # =========================================================================
    # Group B: Bypass Resistance & Contract Isolation Proof
    # =========================================================================
    async def test_B1_subprocess_bypass_closed(self):
        """B1: Subprocess bypass test — arbitrary python execution in ReAct loop is DENIED, subprocess NEVER called."""
        from core.kernel.cognitive_react_loop import CognitiveReActLoop
        react = CognitiveReActLoop(max_turns=1)

        task_id = "task_A"
        contract = TaskContract(
            objective="ReAct turn",
            decision_authority=DecisionAuthority(can_modify_files=True)
        )
        set_active_contract(task_id, contract)

        with patch("core.utils.engine.engine.call_chat", new_callable=AsyncMock) as mock_llm:
            # LLM attempts code block action to execute python
            mock_llm.return_value = "Thought: I will run Python code\n```python\nimport os; os.remove('important.docx')\n```"
            
            with patch("subprocess.run") as mock_subproc:
                res = await react.run_loop("Goal", task_id=task_id)

                # Subprocess MUST NOT be invoked
                self.assertEqual(mock_subproc.call_count, 0)
                trajectory = res.get("trajectory", [])
                self.assertTrue(len(trajectory) > 0)
                obs = trajectory[0].get("observation", "")
                self.assertIn("EXECUTION-DENIED", obs)
                self.assertIn("subprocess_invoked\": false", obs)

    async def test_B2_executor_gateway_wire_denial(self):
        """B2: Direct gateway invocation with delete action is blocked BEFORE any side effect."""
        task_id = "task_A"
        contract = TaskContract(
            objective="Audit mode",
            decision_authority=DecisionAuthority(can_delete_files=False)
        )
        set_active_contract(task_id, contract)

        req = ExecutionRequest(
            trace_id="tr_b2",
            capability_token={},
            tool_name="delete_file",
            tool_args={"file_path": "system.log"}
        )

        res = await self.gateway.execute_tool(req, task_id=task_id)

        self.assertEqual(res.outcome, DecisionOutcome.DENY)
        self.assertFalse(res.tool_executed)
        self.assertEqual(self.mock_http_client.post.call_count, 0)

    async def test_B3_fail_closed_missing_contract(self):
        """B3: Missing contract fail-closed test — calling execute_tool without registering a contract returns DENY."""
        task_id = "task_no_contract"

        req = ExecutionRequest(
            trace_id="tr_b3",
            capability_token={},
            tool_name="read_file",
            tool_args={"file_path": "doc.txt"}
        )

        res = await self.gateway.execute_tool(req, task_id=task_id)

        self.assertEqual(res.outcome, DecisionOutcome.DENY)
        self.assertFalse(res.tool_executed)
        self.assertIn("FAIL-CLOSED", res.reason)
        self.assertEqual(self.mock_http_client.post.call_count, 0)

    async def test_B4_contract_isolation_and_lifetime(self):
        """
        B4: Contract Isolation & Lifetime Proof.
        - Task A (can_delete=False) vs Task B (can_delete=True) isolation
        - Spoofing protection: LLM passing task_id in args cannot override runtime task_id
        - Lifetime: clear_contract(task_id) → immediate DENY on next attempt
        """
        # 1. Isolation: Task A (False) vs Task B (True)
        set_active_contract("task_A", TaskContract(objective="A", decision_authority=DecisionAuthority(can_delete_files=False)))
        set_active_contract("task_B", TaskContract(objective="B", decision_authority=DecisionAuthority(can_delete_files=True)))

        req_del = ExecutionRequest(trace_id="tr_iso", capability_token={}, tool_name="delete_file", tool_args={"file": "x.txt"})

        res_a = await self.gateway.execute_tool(req_del, task_id="task_A")
        self.assertEqual(res_a.outcome, DecisionOutcome.DENY)

        mock_response = MagicMock()
        mock_response.json.return_value = {"status": "success", "output": "deleted"}
        self.mock_http_client.post.return_value = mock_response

        with patch("core.utils.registry.registry.get_service_url", return_value="http://mock-executor"):
            res_b = await self.gateway.execute_tool(req_del, task_id="task_B")
            self.assertEqual(res_b.outcome, DecisionOutcome.ALLOW)

        # 2. Spoofing protection: LLM passes task_id="task_B" in tool_args, but runtime passes task_id="task_A"
        req_spoof = ExecutionRequest(
            trace_id="tr_spf",
            capability_token={},
            tool_name="delete_file",
            tool_args={"task_id": "task_B", "file": "x.txt"} # spoofed task_id in args
        )
        res_spoof = await self.gateway.execute_tool(req_spoof, task_id="task_A") # trusted runtime task_id
        self.assertEqual(res_spoof.outcome, DecisionOutcome.DENY) # Must use trusted task_A authority (False)

        # 3. Lifetime: Clear contract for task_B → next call for task_B must DENY
        clear_contract("task_B")
        res_b_after = await self.gateway.execute_tool(req_del, task_id="task_B")
        self.assertEqual(res_b_after.outcome, DecisionOutcome.DENY)

    # =========================================================================
    # Group C: Adversarial Hardening (Approval Binding & Replay Protection)
    # =========================================================================
    async def test_C1_approval_replay_protection(self):
        """C1: Approval Replay Protection — interrupt ID generated for Task A cannot be bound or accepted for Task B."""
        task_id_a = "task_A"
        task_id_b = "task_B"

        set_active_contract(task_id_a, TaskContract(objective="A", decision_authority=DecisionAuthority(can_modify_files=True)))
        set_active_contract(task_id_b, TaskContract(objective="B", decision_authority=DecisionAuthority(can_modify_files=True)))

        # Task A triggers high-risk write -> REQUIRE_APPROVAL
        req_a = ExecutionRequest(trace_id="tr_c1a", capability_token={}, tool_name="write_file", tool_args={"file_path": ".env"})
        res_a = await self.gateway.execute_tool(req_a, task_id=task_id_a)

        self.assertEqual(res_a.outcome, DecisionOutcome.REQUIRE_APPROVAL)
        interrupt_id_a = res_a.interrupt_id

        # Attempt to use Task A's interrupt payload for Task B
        req_b = ExecutionRequest(
            trace_id="tr_c1b",
            capability_token={"replayed_interrupt_id": interrupt_id_a},
            tool_name="write_file",
            tool_args={"file_path": ".env"}
        )
        res_b = await self.gateway.execute_tool(req_b, task_id=task_id_b)

        # Task B MUST still trigger its own REQUIRE_APPROVAL with a NEW unique interrupt_id (no replay bypass)
        self.assertEqual(res_b.outcome, DecisionOutcome.REQUIRE_APPROVAL)
        self.assertNotEqual(res_b.interrupt_id, interrupt_id_a)
        self.assertEqual(self.mock_http_client.post.call_count, 0)

    async def test_C2_approval_mutation_protection(self):
        """C2: Approval Action Mutation Protection — changing action from write_file to delete_file generates distinct decisions."""
        task_id = "task_A"
        set_active_contract(task_id, TaskContract(objective="A", decision_authority=DecisionAuthority(can_modify_files=True, can_delete_files=False)))

        req_write = ExecutionRequest(trace_id="tr_c2", capability_token={}, tool_name="write_file", tool_args={"file_path": ".env"})
        res_write = await self.gateway.execute_tool(req_write, task_id=task_id)

        # write_file on .env triggers REQUIRE_APPROVAL
        self.assertEqual(res_write.outcome, DecisionOutcome.REQUIRE_APPROVAL)

        # Mutating action to delete_file must trigger HARD DENY (not approval)
        req_del = ExecutionRequest(trace_id="tr_c2", capability_token={}, tool_name="delete_file", tool_args={"file_path": ".env"})
        res_del = await self.gateway.execute_tool(req_del, task_id=task_id)

        self.assertEqual(res_del.outcome, DecisionOutcome.DENY)
        self.assertIn("can_delete_files=False", res_del.reason)


if __name__ == "__main__":
    unittest.main()

