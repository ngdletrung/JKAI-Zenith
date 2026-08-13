"""
core/os/cognition/easg/evidence_usage.py
EASG — Evidence Usage Manager & Epistemic Audit Trail Generator.

Answers Master's question:
"Why was this specific evidence selected for this Success Criterion?"
"""

from __future__ import annotations
import hashlib
import time
from typing import Dict, List, Optional
from core.os.cognition.easg.models import (
    CandidateEvidence,
    EvidenceApplicabilityProfile,
    EvidenceUsageRecord,
)
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec


class EvidenceUsageManager:
    """Creates and tracks Evidence Usage Records."""

    def create_usage_record(
        self,
        selected_profile: EvidenceApplicabilityProfile,
        candidates_map: Dict[str, CandidateEvidence],
        mission: CanonicalMissionSpec,
        criterion_id: str,
        alternatives: List[str],
        rejected_profiles: List[EvidenceApplicabilityProfile],
    ) -> EvidenceUsageRecord:
        cand = candidates_map.get(selected_profile.candidate_id)
        owner = cand.provenance_owner if cand else "Unknown"
        cluster_id = cand.get_lineage().root_cluster_id if cand else "unknown_cluster"

        record_id = f"eur_{hashlib.sha256(f'{selected_profile.evidence_id}:{criterion_id}:{time.time()}'.encode()).hexdigest()[:12]}"

        rejected_reasons = []
        for p in rejected_profiles:
            reason = p.hard_gate_result.failure_details or p.policy_restriction_reason or "Lower ranking score"
            rejected_reasons.append({
                "evidence_id": p.evidence_id,
                "reason": reason,
                "hard_status": p.hard_gate_result.status.value
            })

        return EvidenceUsageRecord(
            record_id=record_id,
            mission_id=mission.mission_id,
            selected_evidence_id=selected_profile.evidence_id,
            used_for_criterion=criterion_id,
            reason_for_use=(
                f"Passed all Hard Gates with ranking score {selected_profile.overall_ranking_score} "
                f"from verified owner '{owner}' ({selected_profile.source_tier.value})"
            ),
            authority_level=selected_profile.primary_role,
            applicability_state=selected_profile.applicability_state.value,
            ranking_score=selected_profile.overall_ranking_score,
            cluster_id=cluster_id,
            alternatives_considered=alternatives,
            rejected_sources=rejected_reasons
        )


evidence_usage_manager = EvidenceUsageManager()
