"""
🏛️ JKAI KERNEL — PHASE 1 INVARIANT TEST: MISSION REPLAY DETERMINISM
File: tests/test_mission_replay.py

Proves the Event Sourcing invariant:
    State(t) + Events[0:t] = State(t)

Must hold after:
    - Sequential replay of events from scratch
    - Crash simulation → snapshot restore → partial replay

Invariants verified:
    B1. reduce_state(events_0_to_t) == reduce_state(events_0_to_k) + reduce_state(events_k_to_t)
    B2. SnapshotEngine.save + load + get_latest_state returns identical MissionState
    B3. Node state transitions are always valid (no invalid state jumps)
    B4. Mission cancellation cascades correctly to all active nodes
"""

import pytest
import tempfile
import os
from datetime import datetime

from core.kernel.models import (
    MissionEvent, EventType, MissionContext, MissionPlan, MissionNode, MissionEdge,
    MissionNodeState,
)
from core.kernel.mission_state_machine import (
    MissionState, reduce_state, validate_node_transition, InvalidNodeStateTransition
)
from core.kernel.snapshot_engine import SnapshotEngine
from core.kernel.event_store import EventStore


# ---------------------------------------------------------------------------
# Helpers to build test events
# ---------------------------------------------------------------------------

def _mission_id() -> str:
    return "test-mission-replay-001"


def _make_event(mission_id: str, event_type: EventType, payload: dict) -> MissionEvent:
    return MissionEvent(
        mission_id=mission_id,
        event_type=event_type,
        payload=payload,
    )


def _build_two_node_plan(node_a_id: str, node_b_id: str) -> dict:
    """Returns a minimal 2-node DAG plan dict compatible with MissionPlan."""
    return {
        "nodes": {
            node_a_id: {
                "id": node_a_id, "name": "step_A", "capability": "web_search",
                "state": "PENDING", "input_context_keys": [], "params": {},
                "retries_count": 0, "max_retries": 3,
            },
            node_b_id: {
                "id": node_b_id, "name": "step_B", "capability": "write_file",
                "state": "PENDING", "input_context_keys": [], "params": {},
                "retries_count": 0, "max_retries": 3,
            },
        },
        "edges": [{"source": node_a_id, "target": node_b_id}],
        "metadata": {},
    }


# ---------------------------------------------------------------------------
# B1. Sequential Replay Determinism
# ---------------------------------------------------------------------------

class TestSequentialReplayDeterminism:

    def test_full_replay_produces_correct_final_state(self):
        """
        INVARIANT B1a:
        Replaying all events from scratch must produce the correct final MissionState.
        reduce_state([e1, e2, ..., eN]) must always yield the same result.
        """
        mid = _mission_id()
        node_a = "node-a-001"
        node_b = "node-b-001"

        plan_payload = _build_two_node_plan(node_a, node_b)
        context_payload = {
            "context": {
                "goal": "Test goal",
                "constraints": [],
                "preferences": {},
                "world_state": {},
                "policies": [],
            }
        }

        events = [
            _make_event(mid, EventType.MISSION_CREATED, context_payload),
            _make_event(mid, EventType.PLANNER_FINISHED, {"plan": plan_payload}),
            _make_event(mid, EventType.NODE_SCHEDULED, {"node_id": node_a}),
            _make_event(mid, EventType.NODE_STARTED, {"node_id": node_a}),
            _make_event(mid, EventType.NODE_COMPLETED, {"node_id": node_a, "output": {"result": "ok"}}),
            _make_event(mid, EventType.NODE_STARTED, {"node_id": node_b}),
            _make_event(mid, EventType.NODE_COMPLETED, {"node_id": node_b, "output": {"file": "written"}}),
            _make_event(mid, EventType.MISSION_COMPLETED, {}),
        ]

        # Replay 1
        state_run1 = reduce_state(mid, events)
        # Replay 2 — must be identical (determinism invariant)
        state_run2 = reduce_state(mid, events)

        assert state_run1.status == "COMPLETED"
        assert state_run1.plan.nodes[node_a].state == MissionNodeState.SUCCESS
        assert state_run1.plan.nodes[node_b].state == MissionNodeState.SUCCESS
        # Determinism: two replays produce identical states
        assert state_run1.model_dump() == state_run2.model_dump()

    def test_partial_replay_from_base_state_equals_full_replay(self):
        """
        INVARIANT B1b (Snapshot Optimization):
        reduce_state(events[k:N], base_state=S_k) == reduce_state(events[0:N])

        This proves snapshot-based incremental replay is correct.
        """
        mid = "test-partial-replay-002"
        node_a = "pa-node-001"
        node_b = "pa-node-002"

        plan_payload = _build_two_node_plan(node_a, node_b)
        context_payload = {"context": {"goal": "Partial replay test", "constraints": [],
                                        "preferences": {}, "world_state": {}, "policies": []}}

        all_events = [
            _make_event(mid, EventType.MISSION_CREATED, context_payload),
            _make_event(mid, EventType.PLANNER_FINISHED, {"plan": plan_payload}),
            _make_event(mid, EventType.NODE_SCHEDULED, {"node_id": node_a}),
            _make_event(mid, EventType.NODE_STARTED, {"node_id": node_a}),
            _make_event(mid, EventType.NODE_COMPLETED, {"node_id": node_a, "output": {"r": "done"}}),
            _make_event(mid, EventType.NODE_STARTED, {"node_id": node_b}),
            _make_event(mid, EventType.NODE_COMPLETED, {"node_id": node_b, "output": {"f": "ok"}}),
            _make_event(mid, EventType.MISSION_COMPLETED, {}),
        ]

        # Simulate snapshot at k=4 (after NODE_COMPLETED for node_a)
        k = 4
        base_state = reduce_state(mid, all_events[:k])
        remaining_events = all_events[k:]

        # Partial replay from base_state
        state_partial = reduce_state(mid, remaining_events, base_state=base_state)
        # Full replay from scratch
        state_full = reduce_state(mid, all_events)

        # INVARIANT: Both must produce identical final state
        assert state_partial.status == state_full.status
        assert (state_partial.plan.nodes[node_a].state ==
                state_full.plan.nodes[node_a].state)
        assert (state_partial.plan.nodes[node_b].state ==
                state_full.plan.nodes[node_b].state)

    def test_empty_events_returns_initial_state(self):
        """INVARIANT B1c: reduce_state([]) returns pristine MissionState."""
        mid = "empty-events-003"
        state = reduce_state(mid, [])
        assert state.mission_id == mid
        assert state.status == "CREATED"
        assert state.plan is None


# ---------------------------------------------------------------------------
# B2. Snapshot Engine — Save → Load → Replay Invariant
# ---------------------------------------------------------------------------

class TestSnapshotEngineInvariant:

    def test_save_load_snapshot_preserves_state(self):
        """
        INVARIANT B2a:
        save_snapshot(state) followed by load_snapshot() returns an equivalent state.
        """
        mid = "snapshot-test-004"
        node_a = "snap-node-a"
        node_b = "snap-node-b"

        plan_payload = _build_two_node_plan(node_a, node_b)
        context_payload = {"context": {"goal": "Snapshot test", "constraints": [],
                                        "preferences": {}, "world_state": {}, "policies": []}}

        events_before_snapshot = [
            _make_event(mid, EventType.MISSION_CREATED, context_payload),
            _make_event(mid, EventType.PLANNER_FINISHED, {"plan": plan_payload}),
            _make_event(mid, EventType.NODE_SCHEDULED, {"node_id": node_a}),
            _make_event(mid, EventType.NODE_STARTED, {"node_id": node_a}),
            _make_event(mid, EventType.NODE_COMPLETED, {"node_id": node_a, "output": {"x": 1}}),
        ]

        state_at_snapshot = reduce_state(mid, events_before_snapshot)

        with tempfile.TemporaryDirectory() as tmpdir:
            engine = SnapshotEngine(base_dir=tmpdir)
            last_event = events_before_snapshot[-1]
            engine.save_snapshot(state_at_snapshot, last_event.event_id, last_event.timestamp)

            restored_state, restored_event_id, restored_ts = engine.load_snapshot(mid)

        assert restored_state is not None
        assert restored_state.mission_id == mid
        assert restored_state.status == state_at_snapshot.status
        assert restored_event_id == last_event.event_id
        assert restored_state.plan.nodes[node_a].state == MissionNodeState.SUCCESS
        assert restored_state.plan.nodes[node_b].state == MissionNodeState.PENDING

    def test_full_snapshot_cycle_get_latest_state(self):
        """
        INVARIANT B2b:
        SnapshotEngine.get_latest_state() == reduce_state(all_events)
        after snapshot + new events appended.
        """
        mid = "snapshot-cycle-005"
        node_a = "sc-node-a"
        node_b = "sc-node-b"

        plan_payload = _build_two_node_plan(node_a, node_b)
        context_payload = {"context": {"goal": "Snapshot cycle", "constraints": [],
                                        "preferences": {}, "world_state": {}, "policies": []}}

        all_events = [
            _make_event(mid, EventType.MISSION_CREATED, context_payload),
            _make_event(mid, EventType.PLANNER_FINISHED, {"plan": plan_payload}),
            _make_event(mid, EventType.NODE_SCHEDULED, {"node_id": node_a}),
            _make_event(mid, EventType.NODE_STARTED, {"node_id": node_a}),
            _make_event(mid, EventType.NODE_COMPLETED, {"node_id": node_a, "output": {}}),
            _make_event(mid, EventType.NODE_STARTED, {"node_id": node_b}),
            _make_event(mid, EventType.NODE_COMPLETED, {"node_id": node_b, "output": {}}),
            _make_event(mid, EventType.MISSION_COMPLETED, {}),
        ]

        with tempfile.TemporaryDirectory() as tmpdir:
            # Write events to EventStore
            store = EventStore(tmpdir)
            for ev in all_events:
                store.append_event(ev)

            # Snapshot at midpoint
            snap_engine = SnapshotEngine(base_dir=tmpdir, event_store=store)
            k = 4
            base = reduce_state(mid, all_events[:k])
            snap_engine.save_snapshot(base, all_events[k - 1].event_id, all_events[k - 1].timestamp)

            # get_latest_state must replay the rest and return final state
            final = snap_engine.get_latest_state(mid)
            expected = reduce_state(mid, all_events)

        assert final.status == expected.status
        assert final.plan.nodes[node_a].state == expected.plan.nodes[node_a].state
        assert final.plan.nodes[node_b].state == expected.plan.nodes[node_b].state


# ---------------------------------------------------------------------------
# B3. Node State Transition Validity
# ---------------------------------------------------------------------------

class TestNodeStateTransitionValidity:

    def test_valid_transitions_do_not_raise(self):
        """INVARIANT B3a: Documented valid transitions must never raise."""
        valid_transitions = [
            (MissionNodeState.PENDING, MissionNodeState.RUNNING),
            (MissionNodeState.RUNNING, MissionNodeState.SUCCESS),
            (MissionNodeState.RUNNING, MissionNodeState.FAILED),
            (MissionNodeState.RUNNING, MissionNodeState.PAUSED),
            (MissionNodeState.PAUSED, MissionNodeState.RUNNING),
            (MissionNodeState.FAILED, MissionNodeState.PENDING),  # Retry
        ]
        for src, tgt in valid_transitions:
            validate_node_transition("test_node", src, tgt)  # Must not raise

    def test_invalid_transitions_raise(self):
        """INVARIANT B3b: Undocumented state jumps must ALWAYS raise InvalidNodeStateTransition."""
        invalid_transitions = [
            (MissionNodeState.PENDING, MissionNodeState.SUCCESS),  # Skip RUNNING
            (MissionNodeState.CANCELLED, MissionNodeState.RUNNING),  # Terminal → active
            (MissionNodeState.SUCCESS, MissionNodeState.RUNNING),  # Backwards (not in ALLOWED)
        ]
        for src, tgt in invalid_transitions:
            with pytest.raises(InvalidNodeStateTransition):
                validate_node_transition("test_node", src, tgt)

    def test_same_state_transition_is_noop(self):
        """INVARIANT B3c: Transitioning to same state is always a no-op (idempotent)."""
        for state in MissionNodeState:
            validate_node_transition("node", state, state)  # Must never raise


# ---------------------------------------------------------------------------
# B4. Mission Cancellation Cascade
# ---------------------------------------------------------------------------

class TestMissionCancellationCascade:

    def test_cancel_mission_cancels_all_active_nodes(self):
        """
        INVARIANT B4:
        MISSION_CANCELLED event must cascade and set all PENDING/RUNNING/PAUSED nodes
        to CANCELLED. Terminal nodes (SUCCESS, FAILED, CANCELLED) must not be touched.
        """
        mid = "cancel-cascade-006"
        node_a = "cc-node-a"
        node_b = "cc-node-b"
        node_c = "cc-node-c"

        plan_payload = {
            "nodes": {
                node_a: {"id": node_a, "name": "done_node", "capability": "web_search",
                         "state": "SUCCESS", "input_context_keys": [], "params": {},
                         "retries_count": 0, "max_retries": 3},
                node_b: {"id": node_b, "name": "running_node", "capability": "compute",
                         "state": "PENDING", "input_context_keys": [], "params": {},
                         "retries_count": 0, "max_retries": 3},
                node_c: {"id": node_c, "name": "pending_node", "capability": "write_file",
                         "state": "PENDING", "input_context_keys": [], "params": {},
                         "retries_count": 0, "max_retries": 3},
            },
            "edges": [{"source": node_a, "target": node_b}, {"source": node_b, "target": node_c}],
            "metadata": {},
        }
        context_payload = {"context": {"goal": "Cancel test", "constraints": [],
                                        "preferences": {}, "world_state": {}, "policies": []}}

        events = [
            _make_event(mid, EventType.MISSION_CREATED, context_payload),
            _make_event(mid, EventType.PLANNER_FINISHED, {"plan": plan_payload}),
            _make_event(mid, EventType.MISSION_CANCELLED, {}),
        ]

        state = reduce_state(mid, events)

        assert state.status == "CANCELLED"
        # SUCCESS node must remain SUCCESS (terminal, not touched)
        assert state.plan.nodes[node_a].state == MissionNodeState.SUCCESS
        # PENDING nodes must be CANCELLED
        assert state.plan.nodes[node_b].state == MissionNodeState.CANCELLED
        assert state.plan.nodes[node_c].state == MissionNodeState.CANCELLED
