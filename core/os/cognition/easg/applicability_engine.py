"""
core/os/cognition/easg/applicability_engine.py
EASG — Evidence Applicability Engine with Two-Tier Evaluation (Hard Gates + Soft Scoring).

Enforces:
1. Hard Gate != Score: Soft scores cannot bribe or bypass hard violations.
2. 4-State Output: APPLICABLE, INAPPLICABLE, UNKNOWN, CONDITIONAL.
3. Hierarchy: VALID != APPLICABLE != AUTHORIZED.
"""

from __future__ import annotations
from typing import Dict, List, Optional
from core.os.cognition.easg.models import (
    ApplicabilityState,
    CandidateEvidence,
    EvidenceApplicabilityProfile,
    HardGateResult,
    HardGateStatus,
    SourceTier,
)
from core.os.cognition.easg.provenance_engine import provenance_engine
from core.os.cognition.easg.policy_gate import policy_gate
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec


class EvidenceApplicabilityEngine:
    """Evaluates candidate evidence against hard boundary gates and soft ranking dimensions."""

    def evaluate_applicability(
        self,
        candidate: CandidateEvidence,
        mission: CanonicalMissionSpec,
        required_department: Optional[str] = None,
        target_organization: str = "HueIC",
        allow_conditional: bool = True,
        target_criterion_purpose: Optional[str] = None,
    ) -> EvidenceApplicabilityProfile:
        ev_id = f"ev_{candidate.candidate_id}"

        # 0. Register Lineage & Clustering
        lineage, cluster_id = provenance_engine.register_and_cluster(candidate)

        # ── TIER 1: HARD GATES EVALUATION ──
        passed_gates: List[str] = []
        failed_gates: List[str] = []
        conditions: List[str] = []

        # Gate 1: Provenance Legitimacy (No LLM Synthesis)
        if candidate.source_tier == SourceTier.LLM_SYNTHESIZED_TEXT:
            failed_gates.append("GATE_PROVENANCE_FAIL (LLM synthesized text cannot be admitted as ground truth)")
        else:
            passed_gates.append("GATE_PROVENANCE_PASS")

        # Gate 2: Temporal Expiration
        if candidate.is_expired or candidate.effective_year < 2025:
            failed_gates.append(f"GATE_TEMPORAL_EXPIRED (Effective year {candidate.effective_year} < 2025)")
        else:
            passed_gates.append("GATE_TEMPORAL_PASS")

        # Gate 3: Department / Scope Gate
        if required_department and candidate.department:
            if required_department.lower() != candidate.department.lower():
                failed_gates.append(f"GATE_SCOPE_MISMATCH (Required: '{required_department}', Candidate: '{candidate.department}')")
            else:
                passed_gates.append("GATE_SCOPE_PASS")
        elif required_department and not candidate.department:
            # Ambiguity -> Condition required
            conditions.append(f"Requires confirmation that policy applies to '{required_department}'")

        # Gate 4: Jurisdiction Gate
        is_internal_mission = any(k in mission.raw_goal.lower() for k in ["quy chế", "quy định", "nội bộ", "trường", "hueic"])
        is_technical_criterion = target_criterion_purpose and any(k in target_criterion_purpose.lower() for k in ["tech", "api", "standard", "driver", "code"])
        
        if is_internal_mission and not is_technical_criterion:
            if candidate.jurisdiction.lower() in [target_organization.lower(), "internal"]:
                passed_gates.append("GATE_JURISDICTION_PASS")
            elif candidate.source_tier == SourceTier.EXTERNAL_UNTRUSTED_BLOG:
                failed_gates.append("GATE_JURISDICTION_UNTRUSTED_BLOG_FOR_INTERNAL_POLICY")
            elif candidate.source_tier == SourceTier.EXTERNAL_OFFICIAL_DOCS:
                # External docs can be used as comparative reference or technical specification
                passed_gates.append("GATE_JURISDICTION_PASS (External official doc for technical reference)")
            else:
                conditions.append(f"Requires validation against {target_organization} internal jurisdiction")
        else:
            # For technical tasks or technical criteria, official external docs pass jurisdiction
            passed_gates.append("GATE_JURISDICTION_PASS")

        # Determine Hard Gate Status
        if len(failed_gates) > 0:
            hard_status = HardGateStatus.FAIL
            app_state = ApplicabilityState.INAPPLICABLE
        elif len(conditions) > 0:
            if allow_conditional:
                hard_status = HardGateStatus.CONDITIONAL
                app_state = ApplicabilityState.CONDITIONAL
            else:
                hard_status = HardGateStatus.UNKNOWN
                app_state = ApplicabilityState.UNKNOWN
        else:
            hard_status = HardGateStatus.PASS
            app_state = ApplicabilityState.APPLICABLE

        hard_result = HardGateResult(
            status=hard_status,
            passed_gates=passed_gates,
            failed_gates=failed_gates,
            conditions_required=conditions,
            failure_details="; ".join(failed_gates) if failed_gates else None
        )

        # ── TIER 2: SOFT SCORING (Only for non-failed candidates) ──
        authority = 0.5
        if candidate.source_tier == SourceTier.INTERNAL_MASTER_DIRECTIVE:
            authority = 1.00
        elif candidate.source_tier == SourceTier.INTERNAL_ORGANIZATION_POLICY:
            authority = 0.95
        elif candidate.source_tier == SourceTier.EXTERNAL_OFFICIAL_DOCS:
            authority = 0.90
        elif candidate.source_tier == SourceTier.EXTERNAL_ACADEMIC_PEER_REVIEWED:
            authority = 0.85
        elif candidate.source_tier == SourceTier.EXTERNAL_VENDOR_KB:
            authority = 0.80
        elif candidate.source_tier == SourceTier.EXTERNAL_COMMUNITY_VERIFIED:
            authority = 0.60
        elif candidate.source_tier == SourceTier.EXTERNAL_UNTRUSTED_BLOG:
            authority = 0.20
        elif candidate.source_tier == SourceTier.LLM_SYNTHESIZED_TEXT:
            authority = 0.00

        freshness = 1.0 if candidate.effective_year >= 2026 else (0.8 if candidate.effective_year == 2025 else 0.1)
        specificity = 1.0 if candidate.department else 0.7

        if hard_status == HardGateStatus.FAIL:
            overall_ranking = 0.0
        elif hard_status == HardGateStatus.UNKNOWN:
            overall_ranking = 0.3
        elif hard_status == HardGateStatus.CONDITIONAL:
            overall_ranking = authority * 0.7
        else:
            overall_ranking = round((authority * 0.5) + (freshness * 0.3) + (specificity * 0.2), 3)

        # ── TIER 3: POLICY USAGE AUTHORIZATION GATE ──
        is_auth, auth_denial_reason = policy_gate.evaluate_usage_authorization(candidate, mission)

        role = "QUARANTINED"
        if hard_status == HardGateStatus.FAIL or not is_auth:
            role = "REJECTED"
        elif hard_status == HardGateStatus.CONDITIONAL:
            role = "CONDITIONAL"
        elif hard_status == HardGateStatus.PASS:
            role = "PRIMARY_AUTHORITY" if overall_ranking >= 0.80 else "SUPPORTING"

        return EvidenceApplicabilityProfile(
            evidence_id=ev_id,
            candidate_id=candidate.candidate_id,
            source_tier=candidate.source_tier,
            applicability_state=app_state,
            hard_gate_result=hard_result,
            authority_score=authority,
            freshness_score=freshness,
            specificity_score=specificity,
            overall_ranking_score=overall_ranking,
            policy_authorized=is_auth,
            policy_restriction_reason=auth_denial_reason,
            primary_role=role,
            bound_criteria=[]
        )


applicability_engine = EvidenceApplicabilityEngine()
