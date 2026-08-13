"""
JKAI ZENITH AI OS — MISSION STATE v2 & BELIEF ENGINE
File: core/os/cognition/mission_state_v2.py

Triển khai ImmutableMission, MutableRuntimeState, BeliefEngine và EvidenceLedger.
Bảo toàn tính bất biến của Mission & Invariants theo hợp đồng P0-1.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Dict, List, Optional, Set


class BeliefStatus(str, Enum):
    ACTIVE = "ACTIVE"
    WEAKENED = "WEAKENED"
    CONFIRMED = "CONFIRMED"
    CONTRADICTED = "CONTRADICTED"
    RETIRED = "RETIRED"


@dataclass(frozen=True)
class ImmutableMission:
    """Immutable Mission Definition — Cannot be mutated during runtime execution."""
    mission_id: str
    goal: str
    original_goal: str
    constraints: List[str] = field(default_factory=list)
    invariants: List[str] = field(default_factory=list)
    success_criteria: List[str] = field(default_factory=list)


@dataclass
class EvidenceItem:
    evidence_id: str
    description: str
    source: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class Belief:
    belief_id: str
    hypothesis: str
    confidence: float
    evidence_for: List[str] = field(default_factory=list)
    evidence_against: List[str] = field(default_factory=list)
    status: BeliefStatus = BeliefStatus.ACTIVE
    revision_reason: str = ""
    created_at: float = field(default_factory=time.time)
    updated_at: float = field(default_factory=time.time)


@dataclass
class EvidenceLedger:
    items: Dict[str, EvidenceItem] = field(default_factory=dict)

    def add_evidence(self, evidence_id: str, description: str, source: str, **kwargs) -> EvidenceItem:
        item = EvidenceItem(evidence_id=evidence_id, description=description, source=source, metadata=kwargs)
        self.items[evidence_id] = item
        return item


@dataclass
class MutableRuntimeState:
    """Mutable Runtime State — Tracks beliefs, topology history, budgets, and observations."""
    mission_id: str
    current_topology: str = "FAST"
    topology_history: List[str] = field(default_factory=lambda: ["FAST"])
    beliefs: Dict[str, Belief] = field(default_factory=dict)
    evidence_ledger: EvidenceLedger = field(default_factory=EvidenceLedger)
    execution_history: List[Dict[str, Any]] = field(default_factory=list)
    budgets: Dict[str, float] = field(default_factory=lambda: {
        "wall_clock": 90.0,
        "tool_calls": 15,
        "errors": 3,
        "mutations": 5
    })

    def transition_topology(self, new_topology: str, reason: str = "") -> None:
        """Bounded Topology Transition: updates current topology while preserving topology history."""
        self.current_topology = new_topology
        self.topology_history.append(new_topology)

    def update_belief(self, belief_id: str, confidence: float, new_status: Optional[BeliefStatus] = None, reason: str = "") -> None:
        if belief_id in self.beliefs:
            b = self.beliefs[belief_id]
            b.confidence = confidence
            if new_status:
                b.status = new_status
            if reason:
                b.revision_reason = reason
            b.updated_at = time.time()
