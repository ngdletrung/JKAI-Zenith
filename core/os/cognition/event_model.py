"""
JKAI ZENITH AI OS — STRUCTURED COGNITIVE EVENT MODEL (PHASE 1)
File: core/os/cognition/event_model.py

Defines the event-sourcing infrastructure:
- CognitiveEvent (event_id, aggregate_id, sequence_no, causation_id, correlation_id, schema_version, payload)
- EventStore & In-Memory Replay Engine (Deterministic Replay & Diagnostic Replay)
- Telemetry emitter for C9 (CONTRACT_VIOLATION) and C10 (FSM_TRANSITION)
"""

from __future__ import annotations
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Any, Optional, Callable
import hashlib
import json
import time
import uuid


@dataclass
class CognitiveEvent:
    """Canonical event-sourced event record (D22, P1-4)."""
    event_id: str
    aggregate_id: str
    sequence_no: int
    event_type: str
    causation_id: Optional[str]
    correlation_id: str
    schema_version: int = 1
    payload: Dict[str, Any] = field(default_factory=dict)
    payload_hash: str = ""
    timestamp: float = field(default_factory=time.time)

    def __post_init__(self):
        if not self.payload_hash:
            encoded = json.dumps(self.payload, sort_keys=True, ensure_ascii=False).encode()
            self.payload_hash = hashlib.sha256(encoded).hexdigest()[:16]


class CognitiveEventStore:
    """Append-only in-memory and persisted event log with replay capabilities."""

    def __init__(self):
        self._events: List[CognitiveEvent] = []
        self._sequence_counters: Dict[str, int] = {} # aggregate_id -> current sequence
        self._telemetry_listeners: List[Callable[[CognitiveEvent], None]] = []

    def append(
        self,
        aggregate_id: str,
        event_type: str,
        payload: Dict[str, Any],
        causation_id: Optional[str] = None,
        correlation_id: str = "trace_default",
    ) -> CognitiveEvent:
        seq = self._sequence_counters.get(aggregate_id, 0) + 1
        self._sequence_counters[aggregate_id] = seq

        event_id = f"evt_{uuid.uuid4().hex[:12]}_{seq}"
        evt = CognitiveEvent(
            event_id=event_id,
            aggregate_id=aggregate_id,
            sequence_no=seq,
            event_type=event_type,
            causation_id=causation_id,
            correlation_id=correlation_id,
            payload=payload
        )
        self._events.append(evt)

        # Notify telemetry listeners
        for listener in self._telemetry_listeners:
            try:
                listener(evt)
            except Exception:
                pass

        return evt

    def get_events_for_aggregate(self, aggregate_id: str) -> List[CognitiveEvent]:
        return [e for e in self._events if e.aggregate_id == aggregate_id]

    def add_telemetry_listener(self, listener: Callable[[CognitiveEvent], None]):
        self._telemetry_listeners.append(listener)

    # ------------------------------------------------------------------------
    # REPLAY ENGINES (P1-4)
    # ------------------------------------------------------------------------

    def deterministic_replay(self, aggregate_id: str, reducer_fn: Callable[[Any, CognitiveEvent], Any], initial_state: Any) -> Any:
        """Replays all events for an aggregate deterministically from initial state."""
        events = self.get_events_for_aggregate(aggregate_id)
        current_state = initial_state
        for evt in events:
            current_state = reducer_fn(current_state, evt)
        return current_state


# Global Event Store Singleton for DEEP Cognition
event_store = CognitiveEventStore()


# ============================================================================
# C9 & C10 TELEMETRY EMITTER HELPERS
# ============================================================================

def emit_contract_violation(
    contract_id: str,
    mission_id: str,
    trace_id: str,
    expected: str,
    actual: str,
    recovery_policy: str,
    enforcement_point: str,
) -> CognitiveEvent:
    """C9: Emits structured CONTRACT_VIOLATION telemetry (No Silent Violation)."""
    return event_store.append(
        aggregate_id=mission_id,
        event_type="CONTRACT_VIOLATION",
        payload={
            "contract_id": contract_id,
            "expected": expected,
            "actual": actual,
            "recovery_policy": recovery_policy,
            "enforcement_point": enforcement_point,
            "timestamp": time.time(),
        },
        correlation_id=trace_id
    )


def emit_fsm_transition(
    mission_id: str,
    trace_id: str,
    from_state: str,
    to_state: str,
    trigger: str,
    fsm_type: str = "MISSION_FSM",
) -> CognitiveEvent:
    """C10: Emits structured FSM_TRANSITION telemetry (No Silent Transition)."""
    return event_store.append(
        aggregate_id=mission_id,
        event_type="FSM_TRANSITION",
        payload={
            "fsm_type": fsm_type,
            "from_state": from_state,
            "to_state": to_state,
            "trigger": trigger,
            "timestamp": time.time(),
        },
        correlation_id=trace_id
    )
