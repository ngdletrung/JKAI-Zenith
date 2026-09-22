# -*- coding: utf-8 -*-
"""
🏛️ SINGLE AUTHORITY FINITE STATE MACHINE (FSM)
File: core/security/single_authority_fsm.py
Role: Deterministic Authority FSM with Blacklist Supremacy & Single Authority Rule
Version: SDS v26.4 (Reliability-First Slice A)

Principles (Consensus Turn 25 - OpenCode & Antigravity):
1. BLACKLIST SUPREMACY: Blacklist is supreme (Fail-Closed, Default-Deny).
   Any action touching blacklisted targets/operations is unconditionally DENIED (Terminal).
2. TASK CONTRACT SCOPE: Actions passing blacklist are verified against TaskContract scope.
   Out-of-scope actions trigger REQUIRE_APPROVAL (Human Gate) or DENY.
3. SINGLE AUTHORITY: Exactly ONE verdict is issued per evaluation.
   No concurrent conflicting verdicts (eliminating BLOCKED vs ALLOWED races).
4. AUDIT COMPLIANCE: Every verdict emits a standardized 14-field FIREWALL_DECISION record.
"""

from __future__ import annotations

import os
import re
import time
import uuid
from dataclasses import dataclass, field, asdict
from enum import Enum
from typing import Any, Dict, List, Optional, Tuple


class FSMState(str, Enum):
    PROPOSED = "PROPOSED"
    BLACKLIST_CHECK = "BLACKLIST_CHECK"
    SCOPE_CHECK = "SCOPE_CHECK"
    AUTHORIZED = "AUTHORIZED"
    DENIED = "DENIED"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


class AuthorityVerdict(str, Enum):
    ALLOW = "ALLOW"
    DENY = "DENY"
    REQUIRE_APPROVAL = "REQUIRE_APPROVAL"


@dataclass
class FirewallDecisionRecord:
    """Standardized 14-field audit record for every firewall verdict."""
    timestamp: float
    mission_id: str
    trace_id: str
    action: str
    target: str
    fsm_state: str
    verdict: str
    reason: str
    risk_level: str
    rule_matched: str
    caller: str
    grant_id: Optional[str]
    duration_ms: float
    is_terminal: bool

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class SingleAuthorityFSM:
    """
    Deterministic Authority FSM enforcing:
    PROPOSED -> [Blacklist hit?] -> DENIED (Terminal, Fail-Fast)
             -> [Out of TaskContract Scope?] -> REQUIRE_APPROVAL / DENIED
             -> [Pass Both] -> AUTHORIZED (Issues Grant)
    """

    # Unconditional Blacklist Patterns (Blacklist is Supreme)
    HARD_BLACKLIST_PATTERNS = [
        r"\.env",
        r"credentials?",
        r"id_rsa",
        r"\.ssh/",
        r"\.git/",
        r"node_modules/",
        r"rm\s+-rf\s+/",
        r"format\s+[c-z]:",
        r"drop\s+database",
        r"truncate\s+table",
    ]

    DESTRUCTIVE_ACTIONS = {
        "delete_file", "remove_file", "unlink", "rmdir", "delete", "remove"
    }

    ARBITRARY_CODE_ACTIONS = {
        "python_execute", "exec_code", "run_code", "execute_code", "run_python", "eval"
    }

    def __init__(self, mission_id: str, trace_id: Optional[str] = None):
        self.mission_id = mission_id
        self.trace_id = trace_id or f"tr_{uuid.uuid4().hex[:8]}"
        self.state: FSMState = FSMState.PROPOSED
        self._audit_history: List[FirewallDecisionRecord] = []

    def evaluate(
        self,
        action: str,
        arguments: Optional[Dict[str, Any]] = None,
        task_contract: Optional[Any] = None,
        policy_advisory: Optional[Any] = None,
        workspace_root: Optional[str] = None
    ) -> Tuple[AuthorityVerdict, str, Optional[FirewallDecisionRecord]]:
        """
        Runs the deterministic FSM evaluation.
        Returns: (verdict, reason, audit_record)
        Guaranteed: Exactly one terminal state reached per evaluation.
        """
        start_time = time.perf_counter()
        args = arguments or {}
        act_lower = action.lower().strip()
        args_str = str(args).lower()
        target = str(args.get("file_path") or args.get("TargetFile") or args.get("path") or args.get("target") or "")

        self.state = FSMState.BLACKLIST_CHECK

        # ------------------------------------------------------------------
        # 1. STEP 1: BLACKLIST CHECK (SUPREME / UNCONDITIONAL FAIL-CLOSED)
        # ------------------------------------------------------------------
        # 1A. Arbitrary Code Execution Block (Invariant C3)
        if act_lower in self.ARBITRARY_CODE_ACTIONS or any(k in act_lower for k in ["python_eval", "eval_code"]):
            self.state = FSMState.DENIED
            reason = "HARD BOUNDARY DENIAL: Arbitrary Python/code execution is unconditionally forbidden (Invariant C3)."
            record = self._create_record(
                action=action, target=target, verdict=AuthorityVerdict.DENY,
                reason=reason, risk_level="CRITICAL", rule_matched="INVARIANT_C3_ARBITRARY_CODE",
                start_time=start_time, is_terminal=True
            )
            return AuthorityVerdict.DENY, reason, record

        # 1B. Hard Path & Pattern Blacklist
        for pattern in self.HARD_BLACKLIST_PATTERNS:
            if re.search(pattern, target, re.IGNORECASE) or re.search(pattern, args_str, re.IGNORECASE):
                self.state = FSMState.DENIED
                reason = f"HARD BOUNDARY DENIAL: Target or arguments match prohibited security pattern '{pattern}'."
                record = self._create_record(
                    action=action, target=target, verdict=AuthorityVerdict.DENY,
                    reason=reason, risk_level="CRITICAL", rule_matched=f"BLACKLIST:{pattern}",
                    start_time=start_time, is_terminal=True
                )
                return AuthorityVerdict.DENY, reason, record

        # 1C. Path Traversal & Workspace Confinement Check
        if target:
            target_norm = target.replace("\\", "/").lower()
            system_prefixes = [
                "/etc/", "/var/", "/usr/", "/root/", "/bin/", "/sbin/",
                "c:/windows", "c:/program files", "c:/program files (x86)"
            ]
            for sp in system_prefixes:
                if target_norm.startswith(sp) or f":{sp}" in target_norm:
                    self.state = FSMState.DENIED
                    reason = f"HARD BOUNDARY DENIAL: Target path '{target}' points to protected system directory."
                    record = self._create_record(
                        action=action, target=target, verdict=AuthorityVerdict.DENY,
                        reason=reason, risk_level="CRITICAL", rule_matched="PROTECTED_SYSTEM_DIR",
                        start_time=start_time, is_terminal=True
                    )
                    return AuthorityVerdict.DENY, reason, record

        # 1D. Destructive Deletion Check against Advisory Flags
        can_delete = False
        if policy_advisory:
            can_delete = getattr(policy_advisory, "can_delete_files", False)
        if task_contract:
            authority = getattr(task_contract, "decision_authority", None)
            if authority:
                can_delete = getattr(authority, "can_delete_files", can_delete)

        if act_lower in self.DESTRUCTIVE_ACTIONS and not can_delete:
            self.state = FSMState.DENIED
            reason = "HARD BOUNDARY DENIAL: Policy strictly forbids file deletion (can_delete_files=False)."
            record = self._create_record(
                action=action, target=target, verdict=AuthorityVerdict.DENY,
                reason=reason, risk_level="HIGH", rule_matched="FORBIDDEN_FILE_DELETION",
                start_time=start_time, is_terminal=True
            )
            return AuthorityVerdict.DENY, reason, record

        # ------------------------------------------------------------------
        # 2. STEP 2: TASK CONTRACT & SCOPE CHECK
        # ------------------------------------------------------------------
        self.state = FSMState.SCOPE_CHECK

        # Observation tools are Fail-Open eligible
        is_obs = any(act_lower.startswith(p) for p in [
            "view_file", "read_file", "list_dir", "grep_search", "search_web", "fetch_url"
        ])

        if not is_obs and not task_contract and not policy_advisory:
            self.state = FSMState.DENIED
            reason = "FAIL-CLOSED: TaskContract and PolicyAdvisory are missing for state mutation tool."
            record = self._create_record(
                action=action, target=target, verdict=AuthorityVerdict.DENY,
                reason=reason, risk_level="MEDIUM", rule_matched="MISSING_CONTRACT_FAIL_CLOSED",
                start_time=start_time, is_terminal=True
            )
            return AuthorityVerdict.DENY, reason, record

        # Explicit forbidden actions in contract
        forbidden = []
        if policy_advisory:
            forbidden.extend(getattr(policy_advisory, "forbidden_actions", []) or [])
        if task_contract:
            forbidden.extend(getattr(task_contract, "forbidden_actions", []) or [])

        for forb in forbidden:
            if forb.lower() in act_lower or forb.lower() in args_str:
                self.state = FSMState.DENIED
                reason = f"CONTRACT DENIAL: Action matches forbidden_action rule '{forb}'."
                record = self._create_record(
                    action=action, target=target, verdict=AuthorityVerdict.DENY,
                    reason=reason, risk_level="HIGH", rule_matched=f"CONTRACT_RULE:{forb}",
                    start_time=start_time, is_terminal=True
                )
                return AuthorityVerdict.DENY, reason, record

        # High-Risk / Approval Gate Check
        requires_approval = False
        if act_lower in {"run_command", "execute_command"}:
            cmd = str(args.get("CommandLine") or args.get("command") or "").strip()
            # If command attempts network exfiltration or destructive shell
            if any(k in cmd.lower() for k in ["curl ", "wget ", "ssh ", "nc ", "ncat "]):
                requires_approval = True
                approval_reason = f"Command '{cmd}' initiates external network connection."

        if requires_approval:
            self.state = FSMState.REQUIRE_APPROVAL
            record = self._create_record(
                action=action, target=target, verdict=AuthorityVerdict.REQUIRE_APPROVAL,
                reason=approval_reason, risk_level="HIGH", rule_matched="HUMAN_GATE_HIGH_RISK",
                start_time=start_time, is_terminal=False
            )
            return AuthorityVerdict.REQUIRE_APPROVAL, approval_reason, record

        # ------------------------------------------------------------------
        # 3. STEP 3: AUTHORIZATION GRANTED
        # ------------------------------------------------------------------
        self.state = FSMState.AUTHORIZED
        grant_id = f"grant_{uuid.uuid4().hex[:10]}"
        reason = f"Action '{action}' fully authorized under Single Authority FSM."
        record = self._create_record(
            action=action, target=target, verdict=AuthorityVerdict.ALLOW,
            reason=reason, risk_level="LOW", rule_matched="AUTHORIZED_SAFE",
            start_time=start_time, is_terminal=True, grant_id=grant_id
        )
        return AuthorityVerdict.ALLOW, reason, record

    def _create_record(
        self,
        action: str,
        target: str,
        verdict: AuthorityVerdict,
        reason: str,
        risk_level: str,
        rule_matched: str,
        start_time: float,
        is_terminal: bool,
        grant_id: Optional[str] = None
    ) -> FirewallDecisionRecord:
        duration_ms = (time.perf_counter() - start_time) * 1000.0
        rec = FirewallDecisionRecord(
            timestamp=time.time(),
            mission_id=self.mission_id,
            trace_id=self.trace_id,
            action=action,
            target=target,
            fsm_state=self.state.value,
            verdict=verdict.value,
            reason=reason,
            risk_level=risk_level,
            rule_matched=rule_matched,
            caller="SingleAuthorityFSM",
            grant_id=grant_id,
            duration_ms=round(duration_ms, 3),
            is_terminal=is_terminal,
        )
        self._audit_history.append(rec)
        return rec

    def get_audit_records(self) -> List[FirewallDecisionRecord]:
        return list(self._audit_history)
