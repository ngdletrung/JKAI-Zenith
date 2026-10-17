# -*- coding: utf-8 -*-
"""
JKAI Centralized Egress Gate (JKAI Discuss Protocol v1.0).
Provides deterministic centralized policy control over any payload leaving
the local machine, enforcing dual killswitches, mission authority, and
pre-send payload scrubbing.
"""

import os
from dataclasses import dataclass
from typing import Any, Dict, Optional

from core.security.pii_scrubber import PIIScrubber

# Mission-scoped discuss authorization set (prevents process-global env race conditions)
_AUTHORIZED_DISCUSS_MISSIONS: set[str] = set()


def authorize_discuss_mission(mission_id: str) -> None:
    """Grants temporary egress authorization strictly scoped to a single mission_id."""
    if mission_id:
        _AUTHORIZED_DISCUSS_MISSIONS.add(mission_id)


def revoke_discuss_mission(mission_id: str) -> None:
    """Revokes mission-scoped egress authorization immediately upon completion."""
    if mission_id:
        _AUTHORIZED_DISCUSS_MISSIONS.discard(mission_id)


@dataclass
class EgressDecision:
    allowed: bool
    reason: str
    sanitized_prompt: str = ""
    is_local_only: bool = True
    target_models: Optional[list] = None


class CentralizedEgressGate:
    """
    Centralized Gateway for Egress Control.
    Enforces the Invariant: No payload leaves the local machine unless
    explicitly authorized by Master and filtered by deterministic scrubbers.
    """

    def __init__(self, scrubber: Optional[PIIScrubber] = None):
        self.scrubber = scrubber or PIIScrubber()

    def inspect_and_authorize(self, payload: Dict[str, Any]) -> EgressDecision:
        """
        Inspects request payload and validates permission against policy.
        """
        if not isinstance(payload, dict):
            return EgressDecision(
                allowed=False,
                reason="invalid_payload_format",
                is_local_only=True,
            )

        mode = payload.get("mode", "fast")
        allow_cloud = payload.get("allow_cloud", False)
        prompt = payload.get("prompt", "")
        target_models = payload.get("target_models", [])
        mission_id = payload.get("mission_id", "default_mission")

        # 1. Routine Non-Discuss Tasks are ALWAYS Local-Only
        if mode != "discuss":
            return EgressDecision(
                allowed=False,
                reason="mode_not_discuss",
                is_local_only=True,
                sanitized_prompt=prompt,
            )

        # 2. Mission Flag Enforcement: Must have explicit allow_cloud flag
        if not allow_cloud:
            return EgressDecision(
                allowed=False,
                reason="mission_cloud_not_permitted",
                is_local_only=True,
                sanitized_prompt=prompt,
            )

        # 3. Dual Killswitch Invariant Check
        # JKAI_LOCAL_ONLY stays 1 as sovereign baseline.
        # Egress requires either mission-scoped authorization OR explicit JKAI_DISCUSS_ALLOWED=1.
        discuss_env = os.getenv("JKAI_DISCUSS_ALLOWED", "0").strip() == "1"
        mission_scoped_ok = mission_id in _AUTHORIZED_DISCUSS_MISSIONS
        if not (discuss_env or mission_scoped_ok):
            return EgressDecision(
                allowed=False,
                reason="discuss_switch_disabled",
                is_local_only=True,
                sanitized_prompt=prompt,
            )

        # 4. Prior Reverse-Solicitation Alert Check: Block follow-up leaks if mission flagged
        from core.security.data_leak_guard import data_leak_guard
        if data_leak_guard.has_active_alert(mission_id):
            return EgressDecision(
                allowed=False,
                reason="reverse_solicitation_alert_active",
                is_local_only=True,
                sanitized_prompt=prompt,
            )

        # 5. Canary Token Scan: Absolute block if internal canary token found
        from core.security.canary_guard import canary_guard
        canary_found = canary_guard.scan(prompt)
        if canary_found:
            return EgressDecision(
                allowed=False,
                reason="canary_leak_blocked",
                is_local_only=True,
                sanitized_prompt=prompt,
            )

        # 6. Active Mosaic Prevention: Check accumulation across rounds
        from core.security.context_canary import context_canary, RiskLevel
        mosaic_result = context_canary.check_accumulation(mission_id, prompt)
        if mosaic_result.risk_level == RiskLevel.HIGH:
            return EgressDecision(
                allowed=False,
                reason="mosaic_accumulation_limit_exceeded",
                is_local_only=True,
                sanitized_prompt=prompt,
            )

        # 7. Deterministic Pre-send Sanitization
        sanitized = self.sanitize_final_payload(prompt)

        # 8. Passed all safety tiers
        return EgressDecision(
            allowed=True,
            reason="authorized",
            sanitized_prompt=sanitized,
            is_local_only=False,
            target_models=target_models,
        )

    def sanitize_final_payload(self, text: str) -> str:
        """Applies deterministic scrubbing to strip paths, IPs, keys, and PII."""
        if not text:
            return ""
        return self.scrubber.mask(text)


egress_gate = CentralizedEgressGate()
