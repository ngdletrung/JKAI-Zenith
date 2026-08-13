"""
JKAI ZENITH AI OS — SHARED COGNITIVE SUBSTRATE BRIDGE (PHASE 4 & 5)
File: core/os/cognition/substrate_bridge.py

Implements:
- EvidenceAdmissionGate (C3, D3, D13, D20): ADMIT / QUARANTINE / REJECT
- BeliefRevisionEngine (D22, D25, D28 CAS): Optimistic CAS versioning, Revocation graph
- SharedSubstrateBridge (D17): Mission-isolated cognitive state manager
"""

from __future__ import annotations
import logging
import time
import hashlib
from typing import Dict, List, Optional, Any, Tuple

from core.os.cognition.deep_schemas import (
    Observation,
    Claim,
    EvidenceRecord,
    EvidenceQualityVector,
    AdmissionStatus,
    BeliefState,
    BeliefRevision,
    BeliefFreshnessStatus,
    CriterionStatus
)
from core.os.cognition.event_model import event_store, emit_contract_violation

logger = logging.getLogger("jkai.cognition.substrate_bridge")


class EvidenceAdmissionGate:
    """Evaluates raw Observations/Claims before admission into the Evidence Ledger (C3)."""

    @staticmethod
    def evaluate(claim: Claim, observation: Observation, known_provenance: List[str]) -> Tuple[AdmissionStatus, str]:
        # Condition 1: Check provenance exists
        if not observation.source_id or observation.source_id.strip() == "":
            return AdmissionStatus.REJECT, "NULL_PROVENANCE_SOURCE"

        # Condition 2: Check credibility
        credibility = observation.metadata.get("credibility", 0.5)
        if credibility <= 0.0:
            return AdmissionStatus.REJECT, "ZERO_CREDIBILITY_SOURCE"

        # Condition 3: Check conflict / quarantine need
        if observation.metadata.get("quarantine_requested", False) or credibility < 0.3:
            return AdmissionStatus.QUARANTINE, "LOW_CREDIBILITY_REQUIRES_CORROBORATION"

        return AdmissionStatus.ADMIT, "VALID_PROVENANCE_AND_CREDIBILITY"


class BeliefRevisionEngine:
    """Manages versioned, CAS-guarded belief updates and revocation propagation (D22, D25, D28)."""

    @staticmethod
    def apply_revision(
        current_state: BeliefState,
        expected_cas_token: str,
        trigger_evidence_ids: List[str],
        hypotheses_delta: Dict[str, float],
        reason: str
    ) -> Tuple[bool, BeliefState, Optional[BeliefRevision]]:
        # Optimistic Concurrency Check (D28)
        if current_state.cas_token != expected_cas_token:
            logger.warning("[D28-CAS-CONFLICT] Expected token %s != Current %s", expected_cas_token, current_state.cas_token)
            return False, current_state, None

        prev_version = current_state.version
        new_version = prev_version + 1
        new_cas_token = hashlib.sha256(f"{current_state.mission_id}:{new_version}".encode()).hexdigest()[:16]

        # Update hypotheses
        updated_hypotheses = dict(current_state.hypotheses)
        for h_id, conf in hypotheses_delta.items():
            updated_hypotheses[h_id] = max(0.0, min(1.0, conf))

        event_id = f"rev_{current_state.mission_id}_{new_version}"
        rev = BeliefRevision(
            event_id=event_id,
            mission_id=current_state.mission_id,
            version=new_version,
            prev_version=prev_version,
            trigger_evidence_ids=trigger_evidence_ids,
            supporting_evidence_ids=trigger_evidence_ids,
            contradicting_evidence_ids=[],
            changed_hypotheses=hypotheses_delta,
            freshness_status=BeliefFreshnessStatus.FRESH,
            revision_reason=reason
        )

        new_state = BeliefState(
            mission_id=current_state.mission_id,
            version=new_version,
            cas_token=new_cas_token,
            hypotheses=updated_hypotheses,
            criterion_coverage=dict(current_state.criterion_coverage),
            staleness_map=dict(current_state.staleness_map),
            last_revision_event_id=event_id
        )

        # Log event in global event store
        event_store.append(
            aggregate_id=current_state.mission_id,
            event_type="BELIEF_REVISED",
            payload={
                "version": new_version,
                "prev_version": prev_version,
                "hypotheses_delta": hypotheses_delta,
                "reason": reason,
                "cas_token": new_cas_token
            }
        )

        return True, new_state, rev


class SharedSubstrateBridge:
    """
    Unified, mission-isolated Cognitive Substrate Bridge for FAST v2.2 and DEEP v2.2.
    Ensures:
    1. Shared cognitive logic, isolated mission state (D17).
    2. No Observation -> Belief shortcut (C2).
    3. Causal Lineage Clustering (D13, D20).
    """

    def __init__(self):
        self._mission_beliefs: Dict[str, BeliefState] = {}
        self._mission_ledgers: Dict[str, Dict[str, EvidenceRecord]] = {}
        self._mission_claims: Dict[str, Dict[str, Claim]] = {}

    def get_or_create_mission_state(self, mission_id: str) -> Tuple[BeliefState, Dict[str, EvidenceRecord]]:
        if mission_id not in self._mission_beliefs:
            self._mission_beliefs[mission_id] = BeliefState(mission_id=mission_id)
            self._mission_ledgers[mission_id] = {}
            self._mission_claims[mission_id] = {}
        return self._mission_beliefs[mission_id], self._mission_ledgers[mission_id]

    def ingest_observation(
        self,
        mission_id: str,
        observation: Observation,
        extracted_claims: List[Claim]
    ) -> List[EvidenceRecord]:
        """Ingests Observation -> Extracts Claims -> Evidence Admission -> Updates Ledger."""
        belief_state, ledger = self.get_or_create_mission_state(mission_id)
        claims_map = self._mission_claims[mission_id]
        admitted_records: List[EvidenceRecord] = []

        for claim in extracted_claims:
            claims_map[claim.claim_id] = claim
            status, reason = EvidenceAdmissionGate.evaluate(claim, observation, [observation.source_id])

            # Collapse causal lineage (D13/D20)
            cluster_id = f"cl_{observation.source_id}"
            ev_id = f"ev_{hashlib.sha256((claim.claim_id + observation.source_id).encode()).hexdigest()[:12]}"

            quality = EvidenceQualityVector(
                reliability=observation.metadata.get("credibility", 0.7),
                provenance_score=1.0 if "primary" in observation.metadata.get("source_type", "") else 0.6,
                independence=1.0,
                freshness=1.0,
                directness=0.8,
                verification_level=1.0 if observation.metadata.get("verified", False) else 0.0
            )

            record = EvidenceRecord(
                evidence_id=ev_id,
                claim_id=claim.claim_id,
                source_id=observation.source_id,
                provenance_lineage=[observation.source_id, observation.agent_id],
                independence_cluster=cluster_id,
                quality=quality,
                admission_status=status,
                admission_reason=reason
            )

            if status == AdmissionStatus.ADMIT:
                ledger[ev_id] = record
                admitted_records.append(record)
                event_store.append(
                    aggregate_id=mission_id,
                    event_type="EVIDENCE_ADMITTED",
                    payload={"evidence_id": ev_id, "claim_id": claim.claim_id, "cluster": cluster_id}
                )
            elif status == AdmissionStatus.QUARANTINE:
                event_store.append(
                    aggregate_id=mission_id,
                    event_type="EVIDENCE_QUARANTINED",
                    payload={"evidence_id": ev_id, "reason": reason}
                )
            else:
                event_store.append(
                    aggregate_id=mission_id,
                    event_type="EVIDENCE_REJECTED",
                    payload={"claim_id": claim.claim_id, "reason": reason}
                )

        return admitted_records

    def revoke_evidence(self, mission_id: str, invalidated_evidence_id: str, new_proof_evidence_id: str) -> bool:
        """D25: Invalidate evidence without deletion, marking it REVOKED in event sourcing."""
        _, ledger = self.get_or_create_mission_state(mission_id)
        if invalidated_evidence_id in ledger:
            rec = ledger[invalidated_evidence_id]
            rec.revoked = True
            rec.invalidated_by = new_proof_evidence_id
            event_store.append(
                aggregate_id=mission_id,
                event_type="EVIDENCE_REVOKED",
                payload={"revoked_id": invalidated_evidence_id, "invalidated_by": new_proof_evidence_id}
            )
            return True
        return False


# Global substrate bridge instance
substrate_bridge = SharedSubstrateBridge()
