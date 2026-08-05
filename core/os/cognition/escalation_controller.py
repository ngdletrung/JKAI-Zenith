"""
JKAI ZENITH AI OS — ESCALATION CONTROLLER
File: core/os/cognition/escalation_controller.py

Manages dynamic runtime escalation (SINGLE_AGENT -> MULTI_AGENT) and 
de-escalation (MULTI_AGENT -> SINGLE_AGENT) based on observed execution feedback.
"""

from __future__ import annotations
from dataclasses import dataclass
from typing import Dict, Any, Optional

from core.os.cognition.execution_governor import ExecutionPolicy, ExecutionTopology


@dataclass
class EscalationDecision:
    escalated: bool
    new_topology: ExecutionTopology
    user_facing_mode: str
    reason: str


def evaluate_runtime_escalation(
    current_policy: ExecutionPolicy,
    observed_feedback: Dict[str, Any]
) -> EscalationDecision:
    """
    Evaluates whether runtime feedback requires topology escalation or de-escalation.
    """
    uncertainty = observed_feedback.get("uncertainty", 0.0)
    unexpected_failures = observed_feedback.get("unexpected_failures", 0)
    cross_module_dependencies = observed_feedback.get("cross_module_dependencies", False)

    # Escalation: SINGLE_AGENT (FAST) -> MULTI_AGENT (DEEP)
    if current_policy.topology == ExecutionTopology.SINGLE_AGENT:
        if uncertainty > 0.7 or unexpected_failures >= 2 or cross_module_dependencies:
            return EscalationDecision(
                escalated=True,
                new_topology=ExecutionTopology.MULTI_AGENT,
                user_facing_mode="DEEP",
                reason=f"Runtime feedback triggered escalation: uncertainty={uncertainty:.2f}, failures={unexpected_failures}."
            )

    # De-escalation: MULTI_AGENT (DEEP) -> SINGLE_AGENT (FAST)
    if current_policy.topology == ExecutionTopology.MULTI_AGENT:
        if observed_feedback.get("root_cause_is_deterministic", False) and uncertainty < 0.2:
            return EscalationDecision(
                escalated=True,
                new_topology=ExecutionTopology.SINGLE_AGENT,
                user_facing_mode="FAST",
                reason="Root cause found to be simple & deterministic. De-escalated to SINGLE_AGENT (FAST)."
            )

    return EscalationDecision(
        escalated=False,
        new_topology=current_policy.topology,
        user_facing_mode=current_policy.user_facing_mode,
        reason="No topology change required."
    )
