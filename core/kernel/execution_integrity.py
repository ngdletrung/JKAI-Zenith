# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/kernel/execution_integrity.py
# - Role: Execution Integrity Layer — Security Boundary & Hard Authority Gateway
# - Ownership: Master LeeTrung
# - Status: Active | Version: SDS v26.2 (Execution Integrity & Grounded Cognition)
#
# [WORKING PRINCIPLES]:
# 1. Structural authority is not execution authority (Prompt instructions != Hard boundary).
# 2. 3-State Decision: ALLOW, DENY, REQUIRE_APPROVAL.
# 3. Fail-Closed Invariant: Malformed, missing, or unknown authority -> DENY or REQUIRE_APPROVAL.
# 4. No side effect may occur outside an authorized execution path.
#    (Constitutional Principle 4 — covers Tool, File, Network, Subprocess, External Message)
# -----------------------------------------------------------------------------

import logging
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from core.utils.human_approval_gate import eval_tool_risk, create_approval_interrupt
import uuid

logger = logging.getLogger("JKAI.ExecutionIntegrity")


class DecisionOutcome(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class ExecutionDecision(BaseModel):
    """Structured authority decision — runtime verdict on a proposed tool action."""
    outcome: DecisionOutcome
    reason: str
    action: str
    target: Optional[str] = None
    requires_human_gate: bool = False
    interrupt_id: Optional[str] = None


class ExecutionResult(BaseModel):
    """
    Structured execution result returned by executor_gateway.execute_tool().
    Replaces raw string returns so callers never need to parse "[EXECUTION-DENIED]:...".

    Invariants:
    - DENY  → tool_executed=False, result=None
    - REQUIRE_APPROVAL → tool_executed=False, result=None, interrupt_id set
    - ALLOW → tool_executed=True, result=<tool output>
    """
    outcome: DecisionOutcome
    tool_executed: bool
    result: Optional[Any] = None       # Tool output on ALLOW; None on DENY/APPROVAL
    reason: str = ""
    interrupt_id: Optional[str] = None
    action: str = ""

    def __str__(self) -> str:
        """Backward-compatible string form — returns tool output or denial message."""
        if self.outcome == DecisionOutcome.ALLOW:
            return str(self.result) if self.result is not None else ""
        if self.outcome == DecisionOutcome.REQUIRE_APPROVAL:
            return (
                f"[APPROVAL-REQUIRED]: Tool '{self.action}' requires human approval "
                f"before execution. InterruptID={self.interrupt_id}. Reason: {self.reason}"
            )
        return f"[EXECUTION-DENIED]: {self.reason}"


class ExecutionIntegrityLayer:
    """
    Execution Integrity Layer (v26.2)
    Acts as the hard security boundary between LLM Intent/Tool Proposal and Tool Execution.
    Enforces TaskContract, DecisionAuthority, CognitivePolicy, and Risk Gates.

    Constitutional Principle 4: No side effect may occur outside an authorized execution path.
    """

    DESTRUCTIVE_KEYWORDS = ["delete", "rm", "xoa", "unlink", "drop", "truncate", "remove"]
    EXTERNAL_COMM_KEYWORDS = ["email", "send_message", "webhook", "publish", "post_to", "send_external"]
    MODIFY_KEYWORDS = ["write", "replace", "modify", "update", "edit", "append"]
    # Arbitrary code execution is DENIED completely in v26.2.
    # python_execute is a meta-capability (file/network/subprocess/env) — not a single action.
    # Default-deny; a proper sandboxed execution environment is a future phase.
    PYTHON_EXECUTE_KEYWORDS = ["python_execute", "exec_code", "run_code", "execute_code", "run_python"]

    def __init__(self, mission_id: str):
        self.mission_id = mission_id

    def authorize(
        self,
        action: str,
        arguments: Optional[Dict[str, Any]] = None,
        task_contract: Optional[Any] = None,
        policy: Optional[Any] = None,
        world_state: Optional[Any] = None
    ) -> ExecutionDecision:
        """
        Evaluates a proposed tool action against TaskContract authority and risk policy.
        Returns ExecutionDecision (ALLOW, DENY, REQUIRE_APPROVAL).
        FAILS CLOSED if contract or authority is missing/invalid.
        """
        args = arguments or {}
        act_lower = action.lower()
        args_str = str(args).lower()

        # ---------------------------------------------------------------------
        # FAIL-CLOSED INVARIANT CHECK: Missing Contract or Authority
        # ---------------------------------------------------------------------
        if not task_contract:
            logger.warning(f"Fail-closed triggered for action={action}: TaskContract missing.")
            return ExecutionDecision(
                outcome=DecisionOutcome.DENY,
                reason="FAIL-CLOSED: TaskContract is missing or unverified.",
                action=action
            )

        authority = getattr(task_contract, "decision_authority", None)
        if not authority:
            logger.warning(f"Fail-closed triggered for action={action}: DecisionAuthority missing.")
            return ExecutionDecision(
                outcome=DecisionOutcome.DENY,
                reason="FAIL-CLOSED: DecisionAuthority scope is missing or unverified.",
                action=action
            )

        # ---------------------------------------------------------------------
        # HARD AUTHORITY BOUNDARY CHECKS
        # ---------------------------------------------------------------------
        # 1. Deletion Check
        is_delete_req = any(k in act_lower or k in args_str for k in self.DESTRUCTIVE_KEYWORDS)
        if is_delete_req:
            can_delete = getattr(authority, "can_delete_files", False)
            if not can_delete:
                logger.info(f"Execution HARD DENIED for action={action}: can_delete_files=False.")
                return ExecutionDecision(
                    outcome=DecisionOutcome.DENY,
                    reason="HARD BOUNDARY DENIAL: DecisionAuthority forbids file deletion (can_delete_files=False).",
                    action=action
                )

        # 2. External Communication Check
        is_comm_req = any(k in act_lower or k in args_str for k in self.EXTERNAL_COMM_KEYWORDS)
        if is_comm_req:
            can_send = getattr(authority, "can_send_external_message", False)
            if not can_send:
                logger.info(f"Execution HARD DENIED for action={action}: can_send_external_message=False.")
                return ExecutionDecision(
                    outcome=DecisionOutcome.DENY,
                    reason="HARD BOUNDARY DENIAL: DecisionAuthority forbids external communication (can_send_external_message=False).",
                    action=action
                )

        # 3. Modification Check
        is_modify_req = any(k in act_lower for k in self.MODIFY_KEYWORDS)
        if is_modify_req:
            can_mod = getattr(authority, "can_modify_files", True)
            if not can_mod:
                logger.info(f"Execution HARD DENIED for action={action}: can_modify_files=False.")
                return ExecutionDecision(
                    outcome=DecisionOutcome.DENY,
                    reason="HARD BOUNDARY DENIAL: DecisionAuthority forbids file modification (can_modify_files=False).",
                    action=action
                )

        # 4. Arbitrary Python / Code Execution Check (v26.2 Default-Deny)
        is_python_req = any(k in act_lower for k in self.PYTHON_EXECUTE_KEYWORDS)
        if is_python_req:
            logger.info(f"Execution HARD DENIED for action={action}: Arbitrary Python execution is disabled in v26.2.")
            return ExecutionDecision(
                outcome=DecisionOutcome.DENY,
                reason="HARD BOUNDARY DENIAL: Arbitrary Python code execution is disabled in v26.2 (Default-Deny meta-capability).",
                action=action
            )

        # ---------------------------------------------------------------------
        # FORBIDDEN ACTIONS CHECK (Contract Level)
        # ---------------------------------------------------------------------
        forbidden = getattr(task_contract, "forbidden_actions", [])
        for forb in forbidden:
            if forb.lower() in act_lower or forb.lower() in args_str:
                return ExecutionDecision(
                    outcome=DecisionOutcome.DENY,
                    reason=f"CONTRACT DENIAL: Action matches forbidden_action rule '{forb}'.",
                    action=action
                )

        # ---------------------------------------------------------------------
        # RISK ASSESSMENT & HUMAN APPROVAL GATE INTERRUPT
        # ---------------------------------------------------------------------
        target_path = args.get("file_path", args.get("TargetFile", args.get("path", "")))
        requires_approval, gate_reason = eval_tool_risk(action, args)

        if requires_approval:
            # Escalates to Human Approval Gate (HITL)
            interrupt_id = str(uuid.uuid4())
            interrupt = create_approval_interrupt(
                task_id=self.mission_id,
                tool_name=action,
                args=args,
                reason=gate_reason or f"Action '{action}' involves high-risk operation requiring explicit approval."
            )
            interrupt["interrupt_id"] = interrupt_id
            logger.info(f"Execution REQUIRE_APPROVAL triggered for action={action}: Interrupt ID={interrupt_id}")
            return ExecutionDecision(
                outcome=DecisionOutcome.REQUIRE_APPROVAL,
                reason=f"HUMAN APPROVAL REQUIRED: {gate_reason or 'Risk level is HIGH for action ' + repr(action)}.",
                action=action,
                target=target_path,
                requires_human_gate=True,
                interrupt_id=interrupt_id
            )

        # ---------------------------------------------------------------------
        # ALLOW EXECUTION
        # ---------------------------------------------------------------------
        return ExecutionDecision(
            outcome=DecisionOutcome.ALLOW,
            reason="Execution authorized by Execution Integrity Layer.",
            action=action
        )
