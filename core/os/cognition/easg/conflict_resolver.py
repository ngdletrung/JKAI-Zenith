"""
core/os/cognition/easg/conflict_resolver.py
EASG — Multi-Criterion Conflict Resolver (Non-Winner-Takes-All).

Enforces:
Conflict != Winner-Takes-All.
Resolves sources on a per-SuccessCriterion basis and preserves comparative evidence.
"""

from __future__ import annotations
from typing import Dict, List, Optional, Tuple
from core.os.cognition.easg.models import (
    ApplicabilityState,
    CandidateEvidence,
    EvidenceApplicabilityProfile,
    EvidenceUsageRecord,
    SourceTier,
)
from core.os.cognition.easg.evidence_usage import evidence_usage_manager
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec


class EvidenceConflictResolver:
    """Multi-criterion conflict resolver mapping evidence to specific criteria."""

    def resolve_for_criterion(
        self,
        criterion_id: str,
        criterion_purpose: str,
        profiles: List[EvidenceApplicabilityProfile],
        candidates_map: Dict[str, CandidateEvidence],
        mission: CanonicalMissionSpec,
    ) -> Tuple[Optional[EvidenceApplicabilityProfile], Optional[EvidenceUsageRecord]]:
        # Filter eligible profiles (APPLICABLE or CONDITIONAL with policy authorization)
        eligible = [
            p for p in profiles 
            if p.applicability_state in [ApplicabilityState.APPLICABLE, ApplicabilityState.CONDITIONAL] and p.policy_authorized
        ]
        rejected = [
            p for p in profiles 
            if p.applicability_state not in [ApplicabilityState.APPLICABLE, ApplicabilityState.CONDITIONAL] or not p.policy_authorized
        ]

        if not eligible:
            return None, None

        # Purpose-driven criterion prioritization
        if "compliance" in criterion_purpose.lower() or "quy chế" in criterion_purpose.lower():
            # Internal policy prioritized for internal compliance criterion
            eligible.sort(key=lambda p: (
                1.0 if p.source_tier in [SourceTier.INTERNAL_MASTER_DIRECTIVE, SourceTier.INTERNAL_ORGANIZATION_POLICY] else 0.0,
                p.overall_ranking_score
            ), reverse=True)
        elif "technical_standard" in criterion_purpose.lower() or "api" in criterion_purpose.lower():
            # Official docs prioritized for technical API standards
            eligible.sort(key=lambda p: (
                1.0 if p.source_tier == SourceTier.EXTERNAL_OFFICIAL_DOCS else 0.0,
                p.overall_ranking_score
            ), reverse=True)
        else:
            eligible.sort(key=lambda p: p.overall_ranking_score, reverse=True)

        selected = eligible[0]
        selected.bound_criteria.append(criterion_id)
        alternatives = [p.evidence_id for p in eligible[1:]]

        usage_record = evidence_usage_manager.create_usage_record(
            selected_profile=selected,
            candidates_map=candidates_map,
            mission=mission,
            criterion_id=criterion_id,
            alternatives=alternatives,
            rejected_profiles=rejected
        )

        return selected, usage_record

    def resolve_and_audit(
        self,
        profiles: List[EvidenceApplicabilityProfile],
        candidates_map: Dict[str, CandidateEvidence],
        mission: CanonicalMissionSpec,
        criterion_id: str = "CRIT-001",
    ) -> Tuple[Optional[EvidenceApplicabilityProfile], Optional[EvidenceUsageRecord]]:
        """Convenience alias for single-criterion resolution."""
        return self.resolve_for_criterion(
            criterion_id=criterion_id,
            criterion_purpose="general",
            profiles=profiles,
            candidates_map=candidates_map,
            mission=mission
        )


conflict_resolver = EvidenceConflictResolver()
