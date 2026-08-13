"""
JKAI ZENITH AI OS — EVIDENCE PROVENANCE SCHEMA v2.2 (Constitution I3, I8, I9, I10, I11)
File: core/os/cognition/evidence_ledger_v2.py
"""
from __future__ import annotations
import logging, time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional

logger = logging.getLogger("jkai.cognition.evidence_ledger_v2")

class VerificationStatus(str, Enum):
    CANDIDATE = "CANDIDATE"
    VERIFIED   = "VERIFIED"
    FALSIFIED  = "FALSIFIED"

class EvidenceStrength(str, Enum):
    NONE     = "NONE"
    WEAK     = "WEAK"
    MODERATE = "MODERATE"
    STRONG   = "STRONG"

class ConclusionStrength(str, Enum):
    UNRESOLVED = "UNRESOLVED"
    LOW        = "LOW"
    MEDIUM     = "MEDIUM"
    HIGH       = "HIGH"

class BeliefStatus(str, Enum):
    ACTIVE       = "ACTIVE"
    WEAKENED     = "WEAKENED"
    CONFIRMED    = "CONFIRMED"
    CONTRADICTED = "CONTRADICTED"
    FALSIFIED    = "FALSIFIED"
    RETIRED      = "RETIRED"

class FSMState(str, Enum):
    CREATED                  = "CREATED"
    ADMITTED                 = "ADMITTED"
    UNDERSTANDING            = "UNDERSTANDING"
    PLANNING                 = "PLANNING"
    EXECUTING                = "EXECUTING"
    OBSERVING                = "OBSERVING"
    REASSESSING              = "REASSESSING"
    WAITING_FOR_EVIDENCE     = "WAITING_FOR_EVIDENCE"
    LOW_CONFIDENCE_CONCLUSION= "LOW_CONFIDENCE_CONCLUSION"
    VERIFYING                = "VERIFYING"
    COMPLETED                = "COMPLETED"
    RECOVERY                 = "RECOVERY"
    FAILED                   = "FAILED"

@dataclass
class EvidenceRecord:
    evidence_id:          str
    source_id:            str
    claim_id:             str
    description:          str
    timestamp:            float  = field(default_factory=time.time)
    extraction_method:    str    = "auto"
    verification_method:  str    = "unverified"
    independence_cluster: str    = "CL_DEFAULT"
    credibility:          float  = 0.5
    relevance:            float  = 0.5
    freshness:            float  = 1.0
    supports:             List[str] = field(default_factory=list)
    contradicts:          List[str] = field(default_factory=list)
    verification_status:  VerificationStatus = VerificationStatus.CANDIDATE
    provenance:           str    = ""

    @property
    def evidence_strength(self) -> EvidenceStrength:
        score = (self.credibility*0.4 + self.relevance*0.3 + self.freshness*0.2 +
                 (0.1 if self.verification_status == VerificationStatus.VERIFIED else 0.0))
        if score >= 0.75: return EvidenceStrength.STRONG
        if score >= 0.50: return EvidenceStrength.MODERATE
        if score >  0.0:  return EvidenceStrength.WEAK
        return EvidenceStrength.NONE

@dataclass
class Claim:
    claim_id:   str
    text:       str
    source_id:  str
    dimension:  str  = "general"
    normalized: bool = False

@dataclass
class Belief:
    belief_id:       str
    hypothesis:      str
    confidence:      float
    evidence_for:    List[str] = field(default_factory=list)
    evidence_against:List[str] = field(default_factory=list)
    status:          BeliefStatus = BeliefStatus.ACTIVE
    revision_reason: str   = ""
    created_at:      float = field(default_factory=time.time)
    updated_at:      float = field(default_factory=time.time)

class EvidenceLedger:
    """Append-only epistemic history (I3). Correlated source detection. Sufficiency gate (I8,I11)."""

    def __init__(self) -> None:
        self._records: Dict[str,EvidenceRecord] = {}
        self._claims:  Dict[str,Claim]          = {}
        self._beliefs: Dict[str,Belief]         = {}
        self._belief_revision_log: List[Dict[str,Any]] = []

    def add_evidence(self, record: EvidenceRecord) -> None:
        if record.evidence_id in self._records:
            logger.warning("[EvidenceLedger] Duplicate %s ignored (I3)", record.evidence_id)
            return
        self._records[record.evidence_id] = record

    def add_claim(self, claim: Claim) -> None:
        self._claims[claim.claim_id] = claim

    def update_belief(self, belief: Belief, new_confidence: float,
                      new_status: Optional[BeliefStatus], trigger_evidence: List[str], reason: str) -> Belief:
        """I9: confidence increase only on ΔVerifiedEvidence>0. I10: always emit BELIEF_REVISED."""
        old_confidence = belief.confidence
        verified_delta = sum(1 for eid in trigger_evidence
                             if self._records.get(eid, EvidenceRecord("","","","")).verification_status
                                == VerificationStatus.VERIFIED)
        if new_confidence > old_confidence and verified_delta == 0:
            logger.warning("[I9-VIOLATION] Confidence increase blocked %s: %.2f→%.2f (0 VerifiedEvidence)",
                           belief.belief_id, old_confidence, new_confidence)
            new_confidence = old_confidence
        belief.confidence = new_confidence
        if new_status: belief.status = new_status
        belief.revision_reason = reason
        belief.updated_at = time.time()
        event = {"event":"BELIEF_REVISED","belief_id":belief.belief_id,"before":old_confidence,
                 "after":new_confidence,"trigger_evidence":trigger_evidence,"reason":reason,
                 "timestamp":belief.updated_at}
        self._belief_revision_log.append(event)
        logger.info("[I10-TELEMETRY] %s", event)
        return belief

    def count_independent_evidence(self, claim_id: str) -> int:
        clusters = {r.independence_cluster for r in self._records.values()
                    if claim_id in r.supports and r.verification_status != VerificationStatus.FALSIFIED}
        return len(clusters)

    def evidence_sufficiency(self, claim_id: str) -> Dict[str,Any]:
        supporting    = [r for r in self._records.values() if claim_id in r.supports
                         and r.verification_status != VerificationStatus.FALSIFIED]
        contradicting = [r for r in self._records.values() if claim_id in r.contradicts]
        ind = self.count_independent_evidence(claim_id)
        if not supporting: max_s = EvidenceStrength.NONE
        else:
            verified = [r for r in supporting if r.verification_status == VerificationStatus.VERIFIED]
            verified_count = len(verified)
            # If verified evidence exists, assess strength based on best verified source
            if verified_count >= 1:
                best_verified_cred = max(r.credibility for r in verified)
                if ind >= 2 and best_verified_cred >= 0.8: max_s = EvidenceStrength.STRONG
                elif ind >= 1 and best_verified_cred >= 0.7: max_s = EvidenceStrength.MODERATE
                else: max_s = EvidenceStrength.WEAK
            else:
                avg_cred = sum(r.credibility for r in supporting) / len(supporting)
                if ind >= 3 and avg_cred >= 0.70: max_s = EvidenceStrength.MODERATE
                elif ind >= 2 and avg_cred >= 0.55: max_s = EvidenceStrength.WEAK
                else: max_s = EvidenceStrength.WEAK
        contradiction_level = len(contradicting) / max(len(supporting), 1)
        return {"claim_id":claim_id,"supporting_count":len(supporting),"independent_clusters":ind,
                "evidence_strength":max_s.value,"contradiction_level":round(contradiction_level,2),
                "sufficient": max_s in (EvidenceStrength.MODERATE, EvidenceStrength.STRONG)
                              and contradiction_level < 0.4}

    @property
    def belief_revision_log(self): return list(self._belief_revision_log)
    @property
    def all_evidence(self): return dict(self._records)
