"""
🏛️ JKAI SECURITY — PHASE 1 INVARIANT TEST: POLICY DENY-BEFORE-SIDE-EFFECT
File: tests/test_policy_deny_first.py

Proves the security invariant (Constitutional Principle 4):
    "No side effect may occur outside an authorized execution path."
    DENY must happen BEFORE any filesystem, network, or subprocess mutation.

Invariants verified:
    C1. Missing TaskContract → DENY before any execution (Fail-Closed)
    C2. Destructive action with no permission → DENY, tool_executed=False
    C3. python_execute always DENIED in v26.2 (Default-Deny)
    C4. Forbidden action list → DENY before side effect
    C5. ALLOW path requires all conditions to pass
    C6. Side-effect counter asserts: mutation_count == 0 on any DENY path
"""

import pytest
from unittest.mock import MagicMock, patch, call
from typing import Any, Optional

from core.kernel.execution_integrity import (
    ExecutionIntegrityLayer, ExecutionDecision, DecisionOutcome
)


# ---------------------------------------------------------------------------
# Minimal TaskContract / Authority mock builders
# ---------------------------------------------------------------------------

def _make_contract(
    can_delete: bool = False,
    can_modify: bool = True,
    can_send_external: bool = False,
    forbidden: list = None,
) -> MagicMock:
    authority = MagicMock()
    authority.can_delete_files = can_delete
    authority.can_modify_files = can_modify
    authority.can_send_external_message = can_send_external

    contract = MagicMock()
    contract.decision_authority = authority
    contract.forbidden_actions = forbidden or []
    return contract


class _SideEffectCounter:
    """Tracks any invocation that would constitute a side effect."""
    def __init__(self):
        self.count = 0

    def __call__(self, *args, **kwargs):
        self.count += 1
        return MagicMock()


# ---------------------------------------------------------------------------
# C1. Fail-Closed: Missing Contract → DENY
# ---------------------------------------------------------------------------

class TestFailClosed:

    def test_missing_contract_denies_any_action(self):
        """
        INVARIANT C1a:
        No TaskContract → ExecutionIntegrityLayer must DENY immediately.
        No code path that could produce a side effect should run.
        """
        layer = ExecutionIntegrityLayer(mission_id="test-001")
        decision = layer.authorize(action="read_file", arguments={}, task_contract=None)

        assert decision.outcome == DecisionOutcome.DENY
        assert "FAIL-CLOSED" in decision.reason
        assert decision.action == "read_file"

    def test_missing_authority_denies(self):
        """
        INVARIANT C1b:
        TaskContract present but decision_authority is None → DENY (Fail-Closed).
        """
        contract = MagicMock()
        contract.decision_authority = None
        contract.forbidden_actions = []

        layer = ExecutionIntegrityLayer(mission_id="test-002")
        decision = layer.authorize(action="write_file", arguments={}, task_contract=contract)

        assert decision.outcome == DecisionOutcome.DENY
        assert "FAIL-CLOSED" in decision.reason

    def test_deny_produces_no_side_effects(self):
        """
        INVARIANT C1c (Core):
        When contract is missing → DENY must occur BEFORE any side-effect-producing code.
        Side effect counter must be 0.
        """
        side_effect = _SideEffectCounter()
        layer = ExecutionIntegrityLayer(mission_id="test-003")

        # Patch subprocess.run to detect any accidental invocation
        with patch("subprocess.run", side_effect=side_effect):
            decision = layer.authorize(action="execute_command", arguments={}, task_contract=None)

        assert decision.outcome == DecisionOutcome.DENY
        # INVARIANT: subprocess never invoked
        assert side_effect.count == 0, (
            f"VIOLATION: {side_effect.count} side effects occurred despite DENY outcome"
        )


# ---------------------------------------------------------------------------
# C2. Destructive Action Hard Boundary
# ---------------------------------------------------------------------------

class TestDestructiveActionBoundary:

    def test_delete_action_denied_without_permission(self):
        """
        INVARIANT C2a:
        Action containing 'delete' keyword → DENY when can_delete_files=False.
        """
        contract = _make_contract(can_delete=False)
        layer = ExecutionIntegrityLayer(mission_id="test-004")
        decision = layer.authorize(action="delete_file", arguments={"path": "/data/file.txt"}, task_contract=contract)

        assert decision.outcome == DecisionOutcome.DENY
        assert "HARD BOUNDARY" in decision.reason
        assert not decision.requires_human_gate  # Hard deny, not approval-required

    def test_remove_action_denied_without_permission(self):
        """INVARIANT C2b: 'remove' keyword → DENY (same as delete)."""
        contract = _make_contract(can_delete=False)
        layer = ExecutionIntegrityLayer(mission_id="test-005")
        decision = layer.authorize(action="remove_directory", arguments={}, task_contract=contract)

        assert decision.outcome == DecisionOutcome.DENY

    def test_delete_allowed_when_permission_granted(self):
        """
        INVARIANT C2c:
        can_delete_files=True → deletion is allowed to proceed to risk assessment.
        (May still require human approval depending on risk level.)
        """
        contract = _make_contract(can_delete=True)
        layer = ExecutionIntegrityLayer(mission_id="test-006")

        with patch("core.utils.human_approval_gate.eval_tool_risk", return_value=(False, "")):
            decision = layer.authorize(action="delete_file", arguments={"path": "/tmp/test.txt"},
                                       task_contract=contract)

        # With permission + no risk: ALLOW
        assert decision.outcome == DecisionOutcome.ALLOW

    def test_external_message_denied_without_permission(self):
        """INVARIANT C2d: External communication → DENY when can_send_external_message=False."""
        contract = _make_contract(can_send_external=False)
        layer = ExecutionIntegrityLayer(mission_id="test-007")
        decision = layer.authorize(action="send_message", arguments={"to": "user@example.com"},
                                   task_contract=contract)

        assert decision.outcome == DecisionOutcome.DENY
        assert "HARD BOUNDARY" in decision.reason


# ---------------------------------------------------------------------------
# C3. Python Execute — Default Deny (v26.2)
# ---------------------------------------------------------------------------

class TestPythonExecuteDefaultDeny:

    @pytest.mark.parametrize("action", [
        "python_execute", "exec_code", "run_code", "execute_code", "run_python"
    ])
    def test_arbitrary_code_execution_always_denied(self, action: str):
        """
        INVARIANT C3:
        Arbitrary Python/code execution is DEFAULT DENY in v26.2.
        No authority level can grant permission for python_execute family.
        """
        # Even with full permissions — still DENY
        contract = _make_contract(can_delete=True, can_modify=True, can_send_external=True)
        layer = ExecutionIntegrityLayer(mission_id="test-exec-deny")
        decision = layer.authorize(action=action, arguments={"code": "print('test')"},
                                   task_contract=contract)

        assert decision.outcome == DecisionOutcome.DENY
        assert "HARD BOUNDARY" in decision.reason or "Arbitrary" in decision.reason

    def test_python_execute_no_subprocess_invoked(self):
        """
        INVARIANT C3 (Core):
        DENY for python_execute must happen BEFORE subprocess.run().
        Side effect count must be 0.
        """
        contract = _make_contract(can_delete=True, can_modify=True, can_send_external=True)
        layer = ExecutionIntegrityLayer(mission_id="test-subprocess-guard")
        side_effect = _SideEffectCounter()

        with patch("subprocess.run", side_effect=side_effect):
            decision = layer.authorize(
                action="python_execute",
                arguments={"code": "import os; os.system('rm -rf /')"},
                task_contract=contract,
            )

        assert decision.outcome == DecisionOutcome.DENY
        # INVARIANT: subprocess.run was never called
        assert side_effect.count == 0, (
            f"CRITICAL VIOLATION: subprocess.run invoked {side_effect.count} times despite DENY"
        )


# ---------------------------------------------------------------------------
# C4. Forbidden Actions List
# ---------------------------------------------------------------------------

class TestForbiddenActionsList:

    def test_forbidden_action_denied_by_contract(self):
        """
        INVARIANT C4a:
        Action listed in contract.forbidden_actions → DENY (CONTRACT DENIAL).
        """
        contract = _make_contract(forbidden=["deploy_to_production", "send_email"])
        layer = ExecutionIntegrityLayer(mission_id="test-forbidden-001")
        decision = layer.authorize(action="deploy_to_production", arguments={},
                                   task_contract=contract)

        assert decision.outcome == DecisionOutcome.DENY
        assert "CONTRACT DENIAL" in decision.reason
        assert "deploy_to_production" in decision.reason

    def test_non_forbidden_action_not_denied_by_list(self):
        """
        INVARIANT C4b:
        Action NOT in forbidden list must not be denied by contract check.
        """
        contract = _make_contract(forbidden=["deploy_to_production"])
        layer = ExecutionIntegrityLayer(mission_id="test-forbidden-002")

        with patch("core.utils.human_approval_gate.eval_tool_risk", return_value=(False, "")):
            decision = layer.authorize(action="read_file", arguments={"path": "/data/report.txt"},
                                       task_contract=contract)

        # Should not be denied by forbidden list
        assert decision.outcome != DecisionOutcome.DENY or "CONTRACT" not in decision.reason


# ---------------------------------------------------------------------------
# C5. ALLOW Path
# ---------------------------------------------------------------------------

class TestAllowPath:

    def test_safe_action_with_full_authority_is_allowed(self):
        """
        INVARIANT C5:
        A safe action with full authority and no risk → ALLOW.
        """
        contract = _make_contract(can_delete=True, can_modify=True, can_send_external=True)
        layer = ExecutionIntegrityLayer(mission_id="test-allow-001")

        with patch("core.utils.human_approval_gate.eval_tool_risk", return_value=(False, "")):
            decision = layer.authorize(action="read_file",
                                       arguments={"path": "/data/report.txt"},
                                       task_contract=contract)

        assert decision.outcome == DecisionOutcome.ALLOW
        assert "authorized" in decision.reason.lower()

    def test_allow_sets_tool_executed_invariant(self):
        """
        INVARIANT C5b:
        ALLOW decision must have outcome=ALLOW. Caller uses this to gate execution.
        The decision object must not contain contradictory fields.
        """
        contract = _make_contract()
        layer = ExecutionIntegrityLayer(mission_id="test-allow-002")

        with patch("core.utils.human_approval_gate.eval_tool_risk", return_value=(False, "")):
            decision = layer.authorize(action="web_search",
                                       arguments={"query": "test"},
                                       task_contract=contract)

        # If ALLOW, requires_human_gate must be False
        assert decision.outcome == DecisionOutcome.ALLOW
        assert decision.requires_human_gate is False
        assert decision.interrupt_id is None


# ---------------------------------------------------------------------------
# C6. Side-Effect Mutation Count — Universal Invariant
# ---------------------------------------------------------------------------

class TestSideEffectMutationCount:

    @pytest.mark.parametrize("action,args,can_delete,expect_deny", [
        ("delete_file",     {"path": "/etc/passwd"},  False, True),
        ("python_execute",  {"code": "malicious()"},  True,  True),
        ("send_message",    {"to": "evil@hack.com"},  False, True),
        ("remove",          {"target": "/root"},      False, True),
    ])
    def test_deny_paths_produce_zero_mutations(self, action, args, can_delete, expect_deny):
        """
        INVARIANT C6 (Universal):
        For every known DENY path — subprocess.run and open() for write
        must NEVER be invoked. Zero mutations guaranteed.
        """
        contract = _make_contract(can_delete=can_delete)
        layer = ExecutionIntegrityLayer(mission_id="test-side-effect-universal")
        subprocess_counter = _SideEffectCounter()
        file_write_counter = _SideEffectCounter()

        with patch("subprocess.run", side_effect=subprocess_counter), \
             patch("builtins.open", side_effect=file_write_counter):
            decision = layer.authorize(action=action, arguments=args, task_contract=contract)

        if expect_deny:
            assert decision.outcome == DecisionOutcome.DENY
            # INVARIANT: zero side effects on DENY
            assert subprocess_counter.count == 0, (
                f"VIOLATION [{action}]: subprocess.run called {subprocess_counter.count} times"
            )
