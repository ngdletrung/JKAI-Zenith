# -*- coding: utf-8 -*-
"""
core/governance/confidence_policy.py
JKAI Zenith - Kernel Policy for Uncalibrated Confidence (ADR 0003)
Enforces fail-closed safety gating on uncalibrated confidence outputs.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional

# UNFITTED placeholders — see ADR 0003. Do not cite as calibrated.
THETA_READ_FIT_PLACEHOLDER: float = 0.70
THETA_READ_UNCAL_FIT_PLACEHOLDER: float = 0.85
THETA_MUT_FIT_PLACEHOLDER: float = 0.90
THETA_IRREV_FIT_PLACEHOLDER: float = 0.95


class ActionClass(str, Enum):
    READ = "READ"
    MUTATE_REVERSIBLE = "MUTATE_REVERSIBLE"
    MUTATE_IRREVERSIBLE = "MUTATE_IRREVERSIBLE"


class PolicyVerdict(str, Enum):
    AUTHORIZE = "AUTHORIZE"
    ESCALATE_TO_TIER3 = "ESCALATE_TO_TIER3"
    REJECT = "REJECT"


@dataclass(frozen=True)
class PolicyDecision:
    verdict: PolicyVerdict
    reason: str
    action_class: ActionClass
    threshold_used: Optional[float]
    backend_calibration_state: str


def decide(
    packet: Any,
    action_class: ActionClass,
    backend_calibration_state: str,
    tier3_concurred: Optional[bool] = None,
) -> PolicyDecision:
    """
    Apply ADR 0003 policy table.

    tier3_concurred: required for MUTATE_IRREVERSIBLE. None means Tier 3 has
    not yet run; caller must run it before this decision is final.
    """
    calibrated = (backend_calibration_state == "calibrated")
    conf = packet.confidence

    if action_class == ActionClass.READ:
        threshold = THETA_READ_FIT_PLACEHOLDER if calibrated else THETA_READ_UNCAL_FIT_PLACEHOLDER
        if conf >= threshold:
            return PolicyDecision(
                PolicyVerdict.AUTHORIZE,
                f"READ: confidence {conf:.3f} >= {threshold}",
                action_class, threshold, backend_calibration_state,
            )
        return PolicyDecision(
            PolicyVerdict.ESCALATE_TO_TIER3,
            f"READ: confidence {conf:.3f} < {threshold}",
            action_class, threshold, backend_calibration_state,
        )

    if action_class == ActionClass.MUTATE_REVERSIBLE:
        if not calibrated:
            return PolicyDecision(
                PolicyVerdict.ESCALATE_TO_TIER3,
                "MUTATE_REVERSIBLE with uncalibrated backend: always escalate",
                action_class, None, backend_calibration_state,
            )
        if conf >= THETA_MUT_FIT_PLACEHOLDER:
            return PolicyDecision(
                PolicyVerdict.AUTHORIZE,
                f"MUTATE_REVERSIBLE: confidence {conf:.3f} >= {THETA_MUT_FIT_PLACEHOLDER}",
                action_class, THETA_MUT_FIT_PLACEHOLDER, backend_calibration_state,
            )
        return PolicyDecision(
            PolicyVerdict.ESCALATE_TO_TIER3,
            f"MUTATE_REVERSIBLE: confidence {conf:.3f} < {THETA_MUT_FIT_PLACEHOLDER}",
            action_class, THETA_MUT_FIT_PLACEHOLDER, backend_calibration_state,
        )

    # MUTATE_IRREVERSIBLE
    if not calibrated:
        return PolicyDecision(
            PolicyVerdict.ESCALATE_TO_TIER3,
            "MUTATE_IRREVERSIBLE with uncalibrated backend: always escalate",
            action_class, None, backend_calibration_state,
        )
    if conf < THETA_IRREV_FIT_PLACEHOLDER:
        return PolicyDecision(
            PolicyVerdict.ESCALATE_TO_TIER3,
            f"MUTATE_IRREVERSIBLE: confidence {conf:.3f} < {THETA_IRREV_FIT_PLACEHOLDER}",
            action_class, THETA_IRREV_FIT_PLACEHOLDER, backend_calibration_state,
        )
    if tier3_concurred is None:
        return PolicyDecision(
            PolicyVerdict.ESCALATE_TO_TIER3,
            "MUTATE_IRREVERSIBLE: Tier 3 concurrence not yet obtained",
            action_class, THETA_IRREV_FIT_PLACEHOLDER, backend_calibration_state,
        )
    if tier3_concurred is False:
        return PolicyDecision(
            PolicyVerdict.REJECT,
            "MUTATE_IRREVERSIBLE: Tier 3 disagrees with Tier 2",
            action_class, THETA_IRREV_FIT_PLACEHOLDER, backend_calibration_state,
        )
    return PolicyDecision(
        PolicyVerdict.AUTHORIZE,
        "MUTATE_IRREVERSIBLE: confidence and Tier 3 concurrence satisfied",
        action_class, THETA_IRREV_FIT_PLACEHOLDER, backend_calibration_state,
    )
