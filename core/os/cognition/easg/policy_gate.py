"""
core/os/cognition/easg/policy_gate.py
EASG — Evidence Usage Authorization & Policy Gate.

Enforces:
Applicable Evidence != Authorized Evidence.
Restricts confidential, wrong-tenant, or policy-prohibited evidence from influencing Belief.
"""

from __future__ import annotations
from typing import Optional, Tuple
from core.os.cognition.easg.models import CandidateEvidence
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec


class PolicyGate:
    """Usage authorization gate evaluating tenant, confidentiality, and organizational policies."""

    def evaluate_usage_authorization(
        self,
        candidate: CandidateEvidence,
        mission: CanonicalMissionSpec,
        requesting_tenant_id: str = "default_tenant",
        allow_confidential: bool = False,
    ) -> Tuple[bool, Optional[str]]:
        # 1. Tenant Isolation
        if candidate.tenant_id != requesting_tenant_id and candidate.tenant_id != "global":
            return False, f"SECURITY_DENIAL: Cross-tenant access violation (candidate_tenant={candidate.tenant_id}, mission_tenant={requesting_tenant_id})"

        # 2. Confidentiality Level Gate
        if candidate.confidentiality_level in ["RESTRICTED", "TOP_SECRET"] and not allow_confidential:
            return False, f"SECURITY_DENIAL: Evidence has confidentiality '{candidate.confidentiality_level}' but mission is unclassified."

        # 3. Laundered Evidence Block
        if candidate.lineage and candidate.lineage.is_laundered:
            return False, "SECURITY_DENIAL: Evidence failed provenance check (Laundered derivation detected)."

        return True, None


policy_gate = PolicyGate()
