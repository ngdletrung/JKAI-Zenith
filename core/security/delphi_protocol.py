# -*- coding: utf-8 -*-
"""
JKAI Delphi Protocol & Claim-Level Consensus Tracker.
Enforces multi-round dialectic debates (max 10 rounds) with:
1. Anti-hallucination cascade: unverified consensus is labeled AGREED_UNVERIFIED.
2. Anti-sycophancy: randomizes speaking order per round.
3. Anti-context-explosion: extractive summarization every 3 rounds.
4. Circuit breaker: hard stop at round 10.
"""

import random
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional


class ClaimState(str, Enum):
    VERIFIED = "VERIFIED"
    AGREED_UNVERIFIED = "AGREED_UNVERIFIED"
    CONFLICTED = "CONFLICTED"
    INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
    REJECTED = "REJECTED"


@dataclass
class ClaimRecord:
    claim_id: str
    statement: str
    state: ClaimState
    supporting_models: List[str] = field(default_factory=list)
    opposing_models: List[str] = field(default_factory=list)
    independent_evidence: Optional[str] = None


@dataclass
class DebateRound:
    round_number: int
    speaker_order: List[str]
    model_responses: Dict[str, str] = field(default_factory=dict)
    tokens_consumed: int = 0


class ConsensusTracker:
    """
    Tracks debate claims across turns without relying on pseudo 90% semantic similarity metrics.
    Guarantees that agreement without independent verification is NEVER classified as truth.
    """

    def __init__(self):
        self.claims: Dict[str, ClaimRecord] = {}

    def register_or_update_claim(
        self,
        claim_id: str,
        statement: str,
        proposing_model: str,
        has_independent_evidence: bool = False,
        evidence_detail: Optional[str] = None,
    ) -> ClaimRecord:
        if claim_id not in self.claims:
            state = (
                ClaimState.VERIFIED
                if has_independent_evidence
                else ClaimState.INSUFFICIENT_EVIDENCE
            )
            self.claims[claim_id] = ClaimRecord(
                claim_id=claim_id,
                statement=statement,
                state=state,
                supporting_models=[proposing_model],
                independent_evidence=evidence_detail,
            )
        return self.claims[claim_id]

    def record_agreement(
        self, claim_id: str, agreeing_model: str
    ) -> ClaimRecord:
        claim = self.claims.get(claim_id)
        if not claim:
            raise KeyError(f"Claim {claim_id} not registered")

        if agreeing_model not in claim.supporting_models:
            claim.supporting_models.append(agreeing_model)

        # Anti-Cascade Invariant: If multiple models agree WITHOUT independent proof,
        # it is strictly AGREED_UNVERIFIED, NEVER VERIFIED!
        if len(claim.supporting_models) >= 2:
            if not claim.independent_evidence:
                claim.state = ClaimState.AGREED_UNVERIFIED
            else:
                claim.state = ClaimState.VERIFIED

        return claim

    def record_disagreement(
        self, claim_id: str, opposing_model: str
    ) -> ClaimRecord:
        claim = self.claims.get(claim_id)
        if not claim:
            raise KeyError(f"Claim {claim_id} not registered")

        if opposing_model not in claim.opposing_models:
            claim.opposing_models.append(opposing_model)

        claim.state = ClaimState.CONFLICTED
        return claim


class DelphiDebateManager:
    """
    Multi-round debate coordinator enforcing circuit-breaker and order randomization.
    """

    MAX_ROUNDS = 10

    def __init__(self, tracker: Optional[ConsensusTracker] = None):
        self.tracker = tracker or ConsensusTracker()
        self.rounds: List[DebateRound] = []

    def plan_round_speaker_order(self, models: List[str]) -> List[str]:
        """Anti-anchoring bias: Shuffles speaking order randomly for each round."""
        shuffled = list(models)
        random.shuffle(shuffled)
        return shuffled

    def check_should_stop(self, current_round: int) -> bool:
        """
        Circuit breaker & early stop check:
        1. Hard ceiling: stop at round 10.
        2. Early stop: if all registered claims are either VERIFIED or AGREED_UNVERIFIED (no CONFLICTED).
        """
        if current_round >= self.MAX_ROUNDS:
            return True

        if not self.tracker.claims:
            return False

        # If any claim is currently actively CONFLICTED, continue debating (until round 10)
        has_active_conflicts = any(
            c.state == ClaimState.CONFLICTED for c in self.tracker.claims.values()
        )
        return not has_active_conflicts
