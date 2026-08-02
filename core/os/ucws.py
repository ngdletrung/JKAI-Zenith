# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/os/ucws.py
# - Role: Universal Cognitive World State (UCWS) & Event Reducer
# - Ownership: Master LeeTrung
# - Status: Active | Version: SDS v25.0 (Cognitive OS Substrate)
#
# [WORKING PRINCIPLES]:
# 1. Decoupled State & Provenance: Current state vs Historical Evidence.
# 2. Immutable Versioning: State transitions occur strictly via W(N+1) = Reduce(W(N), Event).
# 3. Multi-dimensional Uncertainty: factual, state, causal, temporal, intent, execution.
# -----------------------------------------------------------------------------

import os
import json
import time
import logging
from typing import Dict, Any, List, Optional
from pydantic import BaseModel, Field

logger = logging.getLogger("JKAI.UCWS")


class CurrentState(BaseModel):
    entities: Dict[str, Any] = Field(default_factory=dict)
    relationships: Dict[str, Any] = Field(default_factory=dict)
    state: Dict[str, Any] = Field(default_factory=dict)


class Uncertainty(BaseModel):
    factual: float = 0.0
    state: float = 0.0
    causal: float = 0.0
    temporal: float = 0.0
    intent: float = 0.0
    execution: float = 0.0


class WorldProvenance(BaseModel):
    events: List[Dict[str, Any]] = Field(default_factory=list)
    causality_graph: List[Dict[str, Any]] = Field(default_factory=list)
    temporal_history: List[Dict[str, Any]] = Field(default_factory=list)


class UCWS(BaseModel):
    world_version: int = 100
    mission_id: str = "default_mission"
    current_state: CurrentState = Field(default_factory=CurrentState)
    uncertainty: Uncertainty = Field(default_factory=Uncertainty)
    provenance: WorldProvenance = Field(default_factory=WorldProvenance)
    last_updated: float = Field(default_factory=time.time)


_UCWS_REGISTRY: Dict[str, UCWS] = {}


def get_ucws(mission_id: str) -> UCWS:
    """Retrieves the Universal Cognitive World State for a mission."""
    if not mission_id:
        mission_id = "default_mission"
    if mission_id not in _UCWS_REGISTRY:
        _UCWS_REGISTRY[mission_id] = UCWS(mission_id=mission_id)
    return _UCWS_REGISTRY[mission_id]


def reduce_world_state(current: UCWS, event: Dict[str, Any]) -> UCWS:
    """
    State Reducer: Applies a Cognitive Event to transition WorldState from W(N) to W(N+1).
    W(N+1) = Reduce(W(N), Event)
    """
    current.world_version += 1
    current.last_updated = time.time()
    event_type = event.get("event_type", "UNKNOWN")
    payload = event.get("payload", {})

    # Record event in provenance event store
    event_entry = {
        "event_id": f"evt_{current.world_version}",
        "event_type": event_type,
        "world_version": current.world_version,
        "timestamp": current.last_updated,
        "payload": payload
    }
    current.provenance.events.append(event_entry)

    # State reducer logic
    if event_type == "ENTITY_ADDED" or event_type == "ENTITY_UPDATED":
        entity_id = payload.get("entity_id")
        if entity_id:
            current.current_state.entities[entity_id] = payload.get("data", {})
    elif event_type == "RELATIONSHIP_LINKED":
        rel_key = payload.get("relation_key")
        if rel_key:
            current.current_state.relationships[rel_key] = payload.get("targets", [])
    elif event_type == "STATE_CHANGED":
        current.current_state.state.update(payload)
    elif event_type == "CAUSALITY_RECORDED":
        causal_entry = {
            "world_version": current.world_version,
            "cause": payload.get("cause"),
            "action": payload.get("action"),
            "observation": payload.get("observation"),
            "effect": payload.get("effect"),
            "confidence": payload.get("confidence", 0.9)
        }
        current.provenance.causality_graph.append(causal_entry)
    elif event_type == "UNCERTAINTY_UPDATED":
        for k, v in payload.items():
            if hasattr(current.uncertainty, k):
                setattr(current.uncertainty, k, float(v))

    # Record delta in temporal history
    current.provenance.temporal_history.append({
        "world_version": current.world_version,
        "event_type": event_type,
        "summary": str(payload)[:200]
    })

    return current


def replay_world_state(mission_id: str, events: List[Dict[str, Any]]) -> UCWS:
    """Deterministic Replay: Reconstructs UCWS from a list of events."""
    replayed = UCWS(mission_id=mission_id)
    for evt in events:
        replayed = reduce_world_state(replayed, evt)
    return replayed
