"""
core/os/cognition/adaptive_solver/belief_system.py
P0-1: Governed Belief Revision Engine for JKAI Zenith (Belief-Based Situational Intelligence).

Enforces:
- Explicit Belief States: HYPOTHESIS -> CONFIRMED | REFUTED | UNCERTAIN | SUPERSEDED.
- No Silent Hypothesis Drift: Every belief revision records previous statement, new statement, trigger evidence, and rationale.
- Epistemic Integrity: Belief revision directly drives Strategy Invalidation and Next Best Action selection.
"""

from __future__ import annotations
import enum
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


class BeliefStatus(str, enum.Enum):
    HYPOTHESIS = "HYPOTHESIS"   # Initial unverified assumption
    CONFIRMED = "CONFIRMED"     # Corroborated by empirical observation/test
    REFUTED = "REFUTED"         # Contradicted by physical reality
    UNCERTAIN = "UNCERTAIN"     # Ambiguous or contradictory evidence
    SUPERSEDED = "SUPERSEDED"   # Replaced by a more specific belief


@dataclass
class Belief:
    """Explicit epistemic belief held by JKAI regarding workspace/data/tools."""
    belief_id: str
    statement: str
    confidence: float = 0.50
    status: BeliefStatus = BeliefStatus.HYPOTHESIS
    supporting_evidence: List[str] = field(default_factory=list)
    refuting_evidence: List[str] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class BeliefRevisionEvent:
    """Immutable causal record of a belief transition."""
    revision_id: str
    belief_id: str
    old_statement: str
    new_statement: str
    old_status: BeliefStatus
    new_status: BeliefStatus
    trigger_evidence: str
    rationale: str
    timestamp: float = field(default_factory=time.time)


class BeliefRevisionEngine:
    """Maintains and evaluates JKAI's beliefs against empirical runtime evidence."""

    def __init__(self):
        self._beliefs: Dict[str, Belief] = {}
        self._revision_history: List[BeliefRevisionEvent] = []

    def register_belief(
        self,
        statement: str,
        initial_confidence: float = 0.60,
        belief_id: Optional[str] = None
    ) -> Belief:
        """Registers a new explicit hypothesis into the world state."""
        b_id = belief_id or f"BLF-{len(self._beliefs) + 1:03d}"
        belief = Belief(
            belief_id=b_id,
            statement=statement,
            confidence=initial_confidence,
            status=BeliefStatus.HYPOTHESIS
        )
        self._beliefs[b_id] = belief
        return belief

    def evaluate_observation(
        self,
        belief_id: str,
        observation: str,
        is_contradictory: bool,
        evidence_weight: float = 0.35
    ) -> Belief:
        """Evaluates an empirical observation against an existing belief."""
        belief = self._beliefs.get(belief_id)
        if not belief:
            raise KeyError(f"Belief '{belief_id}' not found in Belief System.")

        old_status = belief.status
        old_stmt = belief.statement

        if is_contradictory:
            belief.confidence = max(0.0, belief.confidence - evidence_weight)
            belief.refuting_evidence.append(observation)
            if belief.confidence <= 0.30:
                belief.status = BeliefStatus.REFUTED
            else:
                belief.status = BeliefStatus.UNCERTAIN
        else:
            belief.confidence = min(1.0, belief.confidence + evidence_weight)
            belief.supporting_evidence.append(observation)
            if belief.confidence >= 0.80:
                belief.status = BeliefStatus.CONFIRMED

        belief.updated_at = time.time()

        if belief.status != old_status:
            rev_event = BeliefRevisionEvent(
                revision_id=f"REV-{len(self._revision_history) + 1:04d}",
                belief_id=belief_id,
                old_statement=old_stmt,
                new_statement=belief.statement,
                old_status=old_status,
                new_status=belief.status,
                trigger_evidence=observation,
                rationale=f"Belief confidence shifted to {belief.confidence:.2f} based on observation: {observation}"
            )
            self._revision_history.append(rev_event)

        return belief

    def revise_belief(
        self,
        belief_id: str,
        new_statement: str,
        trigger_evidence: str,
        rationale: str,
        new_confidence: float = 0.85
    ) -> BeliefRevisionEvent:
        """Explicitly supersedes an old belief with a new refined belief."""
        old_belief = self._beliefs.get(belief_id)
        if not old_belief:
            raise KeyError(f"Belief '{belief_id}' not found in Belief System.")

        old_stmt = old_belief.statement
        old_status = old_belief.status

        old_belief.status = BeliefStatus.SUPERSEDED
        old_belief.updated_at = time.time()

        # Register successor belief
        new_id = f"{belief_id}_v2"
        new_belief = Belief(
            belief_id=new_id,
            statement=new_statement,
            confidence=new_confidence,
            status=BeliefStatus.CONFIRMED,
            supporting_evidence=[trigger_evidence]
        )
        self._beliefs[new_id] = new_belief

        rev_event = BeliefRevisionEvent(
            revision_id=f"REV-{len(self._revision_history) + 1:04d}",
            belief_id=belief_id,
            old_statement=old_stmt,
            new_statement=new_statement,
            old_status=old_status,
            new_status=BeliefStatus.SUPERSEDED,
            trigger_evidence=trigger_evidence,
            rationale=rationale
        )
        self._revision_history.append(rev_event)
        return rev_event

    def get_active_beliefs(self) -> List[Belief]:
        """Returns all non-superseded beliefs."""
        return [b for b in self._beliefs.values() if b.status != BeliefStatus.SUPERSEDED]

    def get_revision_history(self) -> List[BeliefRevisionEvent]:
        return list(self._revision_history)


belief_revision_engine = BeliefRevisionEngine()
