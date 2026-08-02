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
    outcome: DecisionOutcome
    reason: str
    action: str
    target: Optional[str] = None
    requires_human_gate: bool = False
    interrupt_id: Optional[str] = None


class ExecutionIntegrityLayer:
    """
    Execution Integrity Layer (v26.2)
    Acts as the hard security boundary between LLM Intent/Tool Proposal and Tool Execution.
    Enforces TaskContract, DecisionAuthority, CognitivePolicy, and Risk Gates.
    """

    DESTRUCTIVE_KEYWORDS = ["delete", "rm", "xóa", "unlink", "drop", "truncate", "remove"]
    EXTERNAL_COMM_KEYWORDS = ["email", "send_message", "webhook", "publish", "post_to", "send_external"]
    MODIFY_KEYWORDS = ["write", "replace", "modify", "update", "edit", "append"]

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
