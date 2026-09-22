# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/kernel/execution_integrity.py
# - Role: Execution Integrity Layer — Security Boundary & Hard Authority Gateway
# - Ownership: Master LeeTrung
# - Status: Active | Version: SDS v26.3 (Immutable Policy Snapshot & HMAC Grants)
#
# [WORKING PRINCIPLES]:
# 1. Structural authority is not execution authority (Prompt instructions != Hard boundary).
# 2. 3-State Decision: ALLOW, DENY, REQUIRE_APPROVAL.
# 3. Fail-Closed Invariant: Malformed, missing, or unknown authority -> DENY or REQUIRE_APPROVAL.
# 4. No side effect may occur outside an authorized execution path (JKAI-BND-001).
# -----------------------------------------------------------------------------

from __future__ import annotations

import logging
import uuid
from enum import Enum
from typing import Dict, Any, Optional, List
from pydantic import BaseModel

from core.utils.human_approval_gate import eval_tool_risk, create_approval_interrupt
from core.kernel.policy_snapshot import PolicySnapshot, ExecutionGrant, issue_execution_grant
from core.security.single_authority_fsm import SingleAuthorityFSM, AuthorityVerdict, FirewallDecisionRecord
from core.observability.structured_logger import log_structured_event

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
    grant: Optional[Dict[str, Any]] = None   # Serialized ExecutionGrant if ALLOW


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
    Execution Integrity Layer (v26.3)
    Acts as the hard security boundary between LLM Intent/Tool Proposal and Tool Execution.
    Enforces PolicySnapshot, TaskContract, DecisionAuthority, and Risk Gates.

    Constitutional Invariant (JKAI-BND-001):
    No execution-capable operation may reach an execution substrate without a valid ExecutionGrant.
    """

    DESTRUCTIVE_KEYWORDS = ["delete", "rm", "xoa", "unlink", "drop", "truncate", "remove"]
    EXTERNAL_COMM_KEYWORDS = ["email", "send_message", "webhook", "publish", "post_to", "send_external"]
    MODIFY_KEYWORDS = ["write", "replace", "modify", "update", "edit", "append"]
    PYTHON_EXECUTE_KEYWORDS = ["python_execute", "exec_code", "run_code", "execute_code", "run_python"]

    # Observation tools: FAIL-OPEN (Safe to allow read-only)
    # Mutation/Execution tools: FAIL-CLOSED (Require explicit PolicySnapshot/TaskContract)
    OBSERVATION_TOOL_PREFIXES = [
        "search_web", "search_web_global", "read_url", "fetch_url", "view_file",
        "search_memory", "execute_skill", "search", "read", "fetch", "lookup",
    ]

    def _is_observation_tool(self, action: str) -> bool:
        """Returns True if this tool is an observation/read-only tool (Fail-Open eligible)."""
        act = action.lower().strip()
        return any(act.startswith(prefix) or act == prefix for prefix in self.OBSERVATION_TOOL_PREFIXES)

    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self.fsm = SingleAuthorityFSM(mission_id=mission_id)

    def authorize(
        self,
        action: str,
        arguments: Optional[Dict[str, Any]] = None,
        task_contract: Optional[Any] = None,
        policy: Optional[Any] = None,
        snapshot: Optional[PolicySnapshot] = None,
        world_state: Optional[Any] = None
    ) -> ExecutionDecision:
        """
        Evaluates a proposed tool action against PolicySnapshot, TaskContract, and Risk Policy.
        Returns ExecutionDecision (ALLOW with ExecutionGrant, DENY, REQUIRE_APPROVAL).
        FAILS CLOSED if contract or authority is missing/invalid for mutation tools.
        Enforces Single Authority Rule and Blacklist Supremacy via SingleAuthorityFSM.
        """
        args = arguments or {}
        act_lower = action.lower()
        args_str = str(args).lower()

        # [RELIABILITY-FIRST SLICE A] Step 0: Single Authority FSM Hard Blacklist Check
        effective_snapshot = snapshot
        if not effective_snapshot and policy and isinstance(policy, PolicySnapshot):
            effective_snapshot = policy

        fsm_verdict, fsm_reason, fsm_record = self.fsm.evaluate(
            action=action,
            arguments=args,
            task_contract=task_contract,
            policy_advisory=effective_snapshot
        )
        if fsm_verdict == AuthorityVerdict.DENY and "HARD BOUNDARY" in fsm_reason:
            log_structured_event(
                message=fsm_reason,
                tool_name=action,
                authority_decision="DENY",
                error_code="HARD_BOUNDARY_DENIAL",
                trace_id=self.fsm.trace_id,
                extra={"target": str(args.get("file_path") or args.get("TargetFile") or "")}
            )
            return ExecutionDecision(
                outcome=DecisionOutcome.DENY,
                reason=fsm_reason,
                action=action
            )

        # ---------------------------------------------------------------------
        # 1. DUAL SECURITY POLICY & CONTRACT ADMISSION
        # ---------------------------------------------------------------------
        if not task_contract and not effective_snapshot:
            logger.warning(f"Fail-closed triggered for action={action}: PolicySnapshot/TaskContract missing.")
            log_structured_event(
                message="FAIL-CLOSED: PolicySnapshot/TaskContract is missing or unverified.",
                tool_name=action,
                authority_decision="DENY",
                error_code="MISSING_CONTRACT",
                trace_id=self.fsm.trace_id
            )
            return ExecutionDecision(
                outcome=DecisionOutcome.DENY,
                reason="FAIL-CLOSED: PolicySnapshot/TaskContract is missing or unverified.",
                action=action
            )

        authority = getattr(task_contract, "decision_authority", None) if task_contract else None
        if not authority and not effective_snapshot:
            if self._is_observation_tool(action):
                grant = issue_execution_grant(
                    mission_id=self.mission_id,
                    snapshot_id="default_obs",
                    tool_name=action,
                    tool_args=args
                )
                return ExecutionDecision(
                    outcome=DecisionOutcome.ALLOW,
                    reason="FAIL-OPEN: Observation tool allowed without DecisionAuthority (Dual Security Policy).",
                    action=action,
                    grant=grant.to_dict()
                )
            logger.warning(f"Fail-closed triggered for action={action}: DecisionAuthority missing.")
            return ExecutionDecision(
                outcome=DecisionOutcome.DENY,
                reason="FAIL-CLOSED: DecisionAuthority scope is missing or unverified.",
                action=action
            )

        can_delete = getattr(effective_snapshot, "can_delete_files", getattr(authority, "can_delete_files", False))
        can_send = getattr(effective_snapshot, "can_send_external_message", getattr(authority, "can_send_external_message", False))
        can_modify = getattr(effective_snapshot, "can_modify_files", getattr(authority, "can_modify_files", True))
        can_shell = getattr(effective_snapshot, "can_execute_shell", getattr(authority, "can_execute_shell", False))

        # ---------------------------------------------------------------------
        # 2. HARD AUTHORITY BOUNDARY CHECKS
        # ---------------------------------------------------------------------
        # Nếu là công cụ quan sát/đọc (Observation / Search / Read), không chặn bởi từ khóa tìm kiếm
        if not self._is_observation_tool(action):
            # A. Deletion Check
            is_delete_req = any(k in act_lower for k in self.DESTRUCTIVE_KEYWORDS) or any(k in args_str for k in ["delete_file", "remove_file", "rmdir", "unlink"])
            if is_delete_req and not can_delete:
                logger.info(f"Execution HARD DENIED for action={action}: can_delete_files=False.")
                return ExecutionDecision(
                    outcome=DecisionOutcome.DENY,
                    reason="HARD BOUNDARY DENIAL: PolicySnapshot forbids file deletion (can_delete_files=False).",
                    action=action
                )

            # B. External Communication Check
            is_comm_req = any(k in act_lower for k in self.EXTERNAL_COMM_KEYWORDS)
            if is_comm_req and not can_send:
                logger.info(f"Execution HARD DENIED for action={action}: can_send_external_message=False.")
                return ExecutionDecision(
                    outcome=DecisionOutcome.DENY,
                    reason="HARD BOUNDARY DENIAL: PolicySnapshot forbids external communication (can_send_external_message=False).",
                    action=action
                )

        # C. Modification Check
        is_modify_req = any(k in act_lower for k in self.MODIFY_KEYWORDS)
        if is_modify_req and not can_modify:
            logger.info(f"Execution HARD DENIED for action={action}: can_modify_files=False.")
            return ExecutionDecision(
                outcome=DecisionOutcome.DENY,
                reason="HARD BOUNDARY DENIAL: PolicySnapshot forbids file modification (can_modify_files=False).",
                action=action
            )


        # D. Arbitrary Python / Code Execution Check
        # 🔒 [INVARIANT C3 — ABSOLUTE DENY]: Arbitrary code execution is NEVER permitted
        # regardless of PolicySnapshot or any authority level. This is a hard constitutional boundary.
        is_python_req = any(k in act_lower for k in self.PYTHON_EXECUTE_KEYWORDS)
        if is_python_req:
            logger.info(f"Execution HARD DENIED for action={action}: Arbitrary code execution is an absolute boundary.")
            return ExecutionDecision(
                outcome=DecisionOutcome.DENY,
                reason="HARD BOUNDARY DENIAL: Arbitrary Python/code execution is unconditionally forbidden (Invariant C3).",
                action=action
            )


        # ---------------------------------------------------------------------
        # 3. FORBIDDEN ACTIONS CHECK
        # ---------------------------------------------------------------------
        forbidden = list(getattr(effective_snapshot, "forbidden_actions", []) or [])
        if task_contract:
            forbidden.extend(getattr(task_contract, "forbidden_actions", []) or [])
        for forb in forbidden:
            if forb.lower() in act_lower or forb.lower() in args_str:
                return ExecutionDecision(
                    outcome=DecisionOutcome.DENY,
                    reason=f"CONTRACT DENIAL: Action matches forbidden_action rule '{forb}'.",
                    action=action
                )

        # ---------------------------------------------------------------------
        # 4. RISK ASSESSMENT & HUMAN APPROVAL GATE INTERRUPT
        # ---------------------------------------------------------------------
        target_path = args.get("file_path", args.get("TargetFile", args.get("path", "")))
        requires_approval, gate_reason = eval_tool_risk(action, args)

        if requires_approval:
            interrupt_id = str(uuid.uuid4())
            interrupt = create_approval_interrupt(
                task_id=self.mission_id,
                tool_name=action,
                args=args,
                reason=gate_reason or f"Action '{action}' involves high-risk operation requiring explicit approval."
            )
            interrupt["interrupt_id"] = interrupt_id
            logger.info(f"Execution REQUIRE_APPROVAL triggered for action={action}: Interrupt ID={interrupt_id}")
            log_structured_event(
                message=f"HUMAN APPROVAL REQUIRED: {gate_reason}",
                tool_name=action,
                authority_decision="REQUIRE_APPROVAL",
                trace_id=self.fsm.trace_id,
                extra={"interrupt_id": interrupt_id, "target": str(target_path)}
            )
            return ExecutionDecision(
                outcome=DecisionOutcome.REQUIRE_APPROVAL,
                reason=f"HUMAN APPROVAL REQUIRED: {gate_reason or 'Risk level is HIGH for action ' + repr(action)}.",
                action=action,
                target=target_path,
                requires_human_gate=True,
                interrupt_id=interrupt_id
            )

        # ---------------------------------------------------------------------
        # 5. ALLOW EXECUTION & ISSUE SIGNED EXECUTION GRANT
        # ---------------------------------------------------------------------
        snap_id = getattr(effective_snapshot, "snapshot_id", "snap_default")
        grant = issue_execution_grant(
            mission_id=self.mission_id,
            snapshot_id=snap_id,
            tool_name=action,
            tool_args=args,
            ttl_seconds=300.0
        )
        log_structured_event(
            message="Execution authorized by Execution Integrity Layer with signed grant.",
            tool_name=action,
            authority_decision="ALLOW",
            trace_id=self.fsm.trace_id,
            extra={"grant_id": getattr(grant, "grant_id", "")}
        )
        return ExecutionDecision(
            outcome=DecisionOutcome.ALLOW,
            reason="Execution authorized by Execution Integrity Layer with signed grant.",
            action=action,
            grant=grant.to_dict()
        )
