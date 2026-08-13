"""
JKAI ZENITH AI OS — EXECUTION GOVERNOR
File: core/os/cognition/execution_governor.py

Determines ExecutionPolicy and ExecutionTopology from TaskProfile.
Separates Topology Decision from Model Mapping (handled by AMG v2).
"""

from __future__ import annotations
from enum import Enum
from dataclasses import dataclass
from typing import Dict, Any, Optional

from core.os.cognition.task_profiler import TaskProfile


class ExecutionTopology(str, Enum):
    REFLEX = "REFLEX"                # Minimal cognition (Capability lookup, Direct Math, Social)
    SINGLE_AGENT = "SINGLE_AGENT"    # FAST Mode: 1 Cognitive Actor (multi-step, multi-file autonomous loop)
    MULTI_AGENT = "MULTI_AGENT"      # DEEP Mode: Multi-Agent Ensemble (Planner, DAG Waves, Council, Verifiers)


@dataclass
class ExecutionPolicy:
    """Governance execution policy determined by the Execution Governor."""
    topology: ExecutionTopology
    user_facing_mode: str            # REFLEX, FAST, DEEP
    requires_policy_gate: bool = False
    requires_worktree: bool = False
    estimated_cognitive_budget: float = 1.0
    reason: str = ""


def govern_execution(profile: TaskProfile, requested_mode: str = "fast") -> ExecutionPolicy:
    """
    Decides ExecutionPolicy based on multi-dimensional TaskProfile signals.
    """
    # Override for High Risk / System Destructive Commands -> Mandatory MULTI_AGENT (DEEP) + Policy Gate
    if profile.risk >= 0.8 or "HIGH_RISK_DESTRUCTIVE_COMMAND" in profile.reason_codes:
        return ExecutionPolicy(
            topology=ExecutionTopology.MULTI_AGENT,
            user_facing_mode="DEEP",
            requires_policy_gate=True,
            requires_worktree=True,
            estimated_cognitive_budget=5.0,
            reason="High risk or system mutation requires Multi-Agent Governance and Policy Gate."
        )

    # Master yêu cầu DEEP tường minh -> Multi-Agent Ensemble
    if requested_mode in ("deep", "deliberative"):
        return ExecutionPolicy(
            topology=ExecutionTopology.MULTI_AGENT,
            user_facing_mode="DEEP",
            requires_policy_gate=(profile.risk > 0.3),
            requires_worktree=True,
            estimated_cognitive_budget=4.0,
            reason="Master explicitly requested DEEP (Multi-Agent Ensemble Mode)."
        )

    # Architectural Audit / Multi-file action with low confidence -> MULTI_AGENT (DEEP)
    if "MULTI_FILE_AUDIT_ACTION" in profile.reason_codes or (profile.mutation_scope == "MULTI_FILE" and profile.confidence_score < 0.8):
        return ExecutionPolicy(
            topology=ExecutionTopology.MULTI_AGENT,
            user_facing_mode="DEEP",
            requires_policy_gate=False,
            requires_worktree=True,
            estimated_cognitive_budget=3.5,
            reason="Architectural Audit / Multi-file scope with confidence < 0.8 assigned to MULTI_AGENT (DEEP)."
        )

    # Reflex signals
    if "CAPABILITY_QUERY" in profile.reason_codes or "GREETING_SOCIAL" in profile.reason_codes:
        return ExecutionPolicy(
            topology=ExecutionTopology.REFLEX,
            user_facing_mode="REFLEX",
            requires_worktree=False,
            reason="Capability query or social greeting mapped to Zero-Cognition REFLEX."
        )

    return ExecutionPolicy(
        topology=ExecutionTopology.SINGLE_AGENT,
        user_facing_mode="FAST",
        requires_worktree=(profile.mutation_scope != "NONE"),
        estimated_cognitive_budget=2.0,
        reason="Default: SINGLE_AGENT (FAST) — 1 autonomous model handles trajectory, multi-tool & multi-file via tool loop."
    )


def escalate_policy(current_policy: ExecutionPolicy, reason: str = "") -> ExecutionPolicy:
    """
    Mid-Flight Topology Escalation Primitive:
    Escalates an existing policy (e.g. FAST -> DEEP) during active execution.
    """
    return ExecutionPolicy(
        topology=ExecutionTopology.MULTI_AGENT,
        user_facing_mode="DEEP",
        requires_policy_gate=current_policy.requires_policy_gate,
        requires_worktree=True,
        estimated_cognitive_budget=max(4.0, current_policy.estimated_cognitive_budget + 2.0),
        reason=f"Mid-flight escalation triggered: {reason or 'Scope expansion detected'}"
    )

