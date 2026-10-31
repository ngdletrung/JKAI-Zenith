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
    risk_tier: Optional[str] = None
    lds_verdict: Optional[Dict[str, Any]] = None


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
    receipt: Optional[Dict[str, Any]] = None
    risk_tier: Optional[str] = None
    lds_verdict: Optional[Dict[str, Any]] = None

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
    # NOTE: must contain BOTH "search_web*" and "web_search" canonical forms.
    OBSERVATION_TOOL_PREFIXES = [
        "search_web", "search_web_global", "web_search", "websearch", "read_url", "fetch_url", "view_file",
        "search_memory", "execute_skill", "search", "read", "fetch", "lookup",
        "web_read", "browser_observe", "browser_act", "browser_extract", "browser_action", "browser_control",
    ]

    # Word-boundary destructive intent (fixes "rm" matching "form"/"performance").
    # "rm" alone only counts as standalone word or "rm -rf"/"rmdir".
    _DESTRUCTIVE_RE = None

    @classmethod
    def _destructive_re(cls):
        import re as _re
        if cls._DESTRUCTIVE_RE is None:
            cls._DESTRUCTIVE_RE = _re.compile(
                r"(?i)\b(delete|remove|unlink|rmdir|drop\s+database|truncate\s+table|xoa)\b|\brm\b\s*-rf?\b"
            )
        return cls._DESTRUCTIVE_RE

    def is_observation_tool(self, action: str) -> bool:
        """Returns True if this tool is an observation/read-only tool (Fail-Open eligible)."""
        act = action.lower().strip()
        return any(act.startswith(prefix) or act == prefix for prefix in self.OBSERVATION_TOOL_PREFIXES)

    # Backwards-compatible alias
    _is_observation_tool = is_observation_tool

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
        act_lower = (action or "").lower()
        args_str = str(args).lower()

        raw_action = action
        try:
            from core.kernel.tool_contracts import (
                ToolContractRegistry, is_known_tool, looks_like_sentence_tool,
                ALLOWED_TOOL_NAMES,
            )
            canon = ToolContractRegistry.get_canonical_name(action or "")
            if looks_like_sentence_tool(action or ""):
                hint = ", ".join(ALLOWED_TOOL_NAMES)
                return ExecutionDecision(
                    outcome=DecisionOutcome.DENY,
                    reason=(
                        f"CONTRACT_VIOLATION: Unknown tool '{action}'. "
                        f"Must use one canonical tool name in field 'tool'. "
                        f"Allowed: {hint}. "
                        f"Map CODE_EXECUTION->run_command, OMNI_SEARCH_ENGINE/SEARCH_WEB_GLOBAL->web_search, "
                        f"create_file->write_to_file. Step IDs (auto_code_01, plan_*) are NOT tools."
                    ),
                    action=action,
                )
            if canon is not None:
                # Normalize known aliases to canonical for downstream checks.
                action = canon
                act_lower = action.lower()
            # [FIX-41310c-2] Auto-repair web_search missing query from sibling args.
            if canon == "web_search":
                q = args.get("query") or args.get("Query") or args.get("q") or args.get("pattern")
                if not q or not str(q).strip():
                    fallback = None
                    for _k in ("topic", "keyword", "term", "question", "goal", "description", "input"):
                        _v = args.get(_k) or args.get(_k.capitalize())
                        if isinstance(_v, str) and len(_v.strip()) >= 3:
                            fallback = _v.strip()[:300]
                            break
                    if fallback:
                        args = dict(args)
                        args["query"] = fallback
                        args_str = str(args).lower()
        except ImportError:
            pass

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
        if fsm_verdict == AuthorityVerdict.DENY:
            log_structured_event(
                message=fsm_reason,
                tool_name=action,
                authority_decision="DENY",
                error_code="FSM_AUTHORITY_DENY",
                trace_id=self.fsm.trace_id,
                extra={"target": str(args.get("file_path") or args.get("TargetFile") or "")}
            )
            return ExecutionDecision(
                outcome=DecisionOutcome.DENY,
                reason=fsm_reason,
                action=action
            )

        if fsm_verdict == AuthorityVerdict.REQUIRE_APPROVAL:
            target_path = args.get("file_path", args.get("TargetFile", args.get("path", "")))
            interrupt_id = str(uuid.uuid4())
            log_structured_event(
                message=fsm_reason,
                tool_name=action,
                authority_decision="REQUIRE_APPROVAL",
                trace_id=self.fsm.trace_id,
                extra={"interrupt_id": interrupt_id, "target": str(target_path)}
            )
            return ExecutionDecision(
                outcome=DecisionOutcome.REQUIRE_APPROVAL,
                reason=fsm_reason,
                action=action,
                target=str(target_path),
                requires_human_gate=True,
                interrupt_id=interrupt_id
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
            # A. Deletion Check — canonical tool membership + word-boundary intent.
            # FIX-41310c: old `any(k in act_lower)` matched "rm" inside "form"/"performance".
            is_delete_tool = act_lower in {"delete_file", "remove_file", "rm", "rmdir", "unlink"}
            is_delete_intent = bool(self._destructive_re().search(act_lower + " " + args_str))
            is_delete_req = is_delete_tool or is_delete_intent
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
        # 4. LEGAL DECISION STATE (DIR LDS) & COGNITHOR RISK TIERING
        # ---------------------------------------------------------------------
        try:
            from core.kernel.lds_risk_governance import enterprise_governance, RiskTier, AgentStateCode
            lds_v = enterprise_governance.evaluate_lds(
                action=raw_action or action,
                arguments=args,
                task_contract=task_contract,
                policy=effective_snapshot,
                task_id=self.mission_id
            )
        except Exception as lds_err:
            logger.debug("[LDS-EVAL] Fallback: %s", lds_err)
            lds_v = None

        if lds_v is not None and not lds_v.is_legal:
            fail_msg = "; ".join(lds_v.failure_reasons)
            logger.warning(f"[LDS-DENIED] Action '{action}' failed LDS verification: {fail_msg}")
            return ExecutionDecision(
                outcome=DecisionOutcome.DENY,
                reason=f"LEGAL_DECISION_STATE_DENIAL: {fail_msg}",
                action=action,
                risk_tier=lds_v.risk_tier.name,
                lds_verdict=lds_v.to_dict()
            )

        target_path = args.get("file_path", args.get("TargetFile", args.get("path", "")))
        requires_approval, gate_reason = eval_tool_risk(action, args)
        if lds_v is not None and lds_v.risk_tier == RiskTier.RED:
            requires_approval = True
            gate_reason = gate_reason or f"COGNITHOR_RED_GATE: Critical risk action '{action}' requires explicit human authorization." 

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
                interrupt_id=interrupt_id,
                risk_tier=lds_v.risk_tier.name if lds_v else None,
                lds_verdict=lds_v.to_dict() if lds_v else None
            )

        # ---------------------------------------------------------------------
        # 5. ALLOW EXECUTION & ISSUE SIGNED EXECUTION GRANT
        # ---------------------------------------------------------------------
        snap_id = getattr(effective_snapshot, "snapshot_id", "snap_default")
        grant = issue_execution_grant(
            mission_id=self.mission_id,
            snapshot_id=snap_id,
            tool_name=raw_action or action,
            tool_args=args,
            ttl_seconds=300.0
        )
        log_structured_event(
            message="Execution authorized by Execution Integrity Layer with signed grant.",
            tool_name=raw_action or action,
            authority_decision="ALLOW",
            trace_id=self.fsm.trace_id,
            extra={"grant_id": getattr(grant, "grant_id", "")}
        )
        return ExecutionDecision(
            outcome=DecisionOutcome.ALLOW,
            reason="Execution authorized by Execution Integrity Layer with signed grant.",
            action=raw_action or action,
            grant=grant.to_dict(),
            risk_tier=lds_v.risk_tier.name if lds_v else None,
            lds_verdict=lds_v.to_dict() if lds_v else None
        )

    def seal_execution_receipt(
        self,
        action: str,
        arguments: Dict[str, Any],
        output: Any,
        lds_verdict: Optional[Any] = None,
        task_id: Optional[str] = None,
        pre_state_hash: str = "0" * 64,
        post_state_hash: str = "0" * 64
    ) -> Any:
        """
        [SROS v2 / Sovereign Enterprise Governance]
        Niêm phong biên nhận mật mã học (ExecutionReceipt) sau khi hành động đã thực thi trên substrate.
        """
        try:
            from core.kernel.lds_risk_governance import enterprise_governance, LDSVerdict, RiskTier
            eff_task_id = task_id or self.mission_id
            verdict = lds_verdict
            if verdict is None:
                verdict = enterprise_governance.evaluate_lds(
                    action=action,
                    arguments=arguments,
                    task_id=eff_task_id
                )
            elif isinstance(verdict, dict):
                risk_tier_name = verdict.get("risk_tier", "YELLOW")
                try:
                    rt = RiskTier[risk_tier_name]
                except KeyError:
                    rt = RiskTier.YELLOW
                verdict = LDSVerdict(
                    is_legal=verdict.get("is_legal", True),
                    authority_ok=verdict.get("authority_ok", True),
                    context_ok=verdict.get("context_ok", True),
                    time_ok=verdict.get("time_ok", True),
                    integrity_ok=verdict.get("integrity_ok", True),
                    evidence_ok=verdict.get("evidence_ok", True),
                    risk_tier=rt,
                    failure_reasons=verdict.get("failure_reasons", []),
                    metadata=verdict.get("metadata", {})
                )

            receipt = enterprise_governance.seal_receipt(
                task_id=eff_task_id,
                action=action,
                arguments=arguments,
                output_result=output,
                lds_verdict=verdict,
                pre_state_hash=pre_state_hash,
                post_state_hash=post_state_hash
            )
            return receipt
        except Exception as e:
            logger.error("[RECEIPT-SEAL-ERROR] Failed to seal execution receipt: %s", e)
            raise RuntimeError("FAIL-CLOSED: execution receipt sealing failed") from e
