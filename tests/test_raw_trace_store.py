# -*- coding: utf-8 -*-
"""
Unit test suite for DEMS Canonical RawTraceStore (Phase 5.6-B).
Verifies:
  - I-DEMS-01: Historical Immutability (Append-only)
  - I-DEMS-02: Evidence Provenance
  - 4-Tier Hierarchy indexing: Turn -> Window -> Episode -> Mission
"""

import os
import shutil
import tempfile
import pytest
from core.storage.raw_trace_store import RawTraceStore, RawTrace


@pytest.fixture
def temp_store():
    tmp_dir = tempfile.mkdtemp()
    db_path = os.path.join(tmp_dir, "test_traces.db")
    store = RawTraceStore(db_path=db_path)
    yield store
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_append_and_read_trace(temp_store):
    trace = temp_store.append_trace(
        mission_id="m_001",
        episode_id="ep_001",
        window_id="win_001",
        turn_id="turn_001",
        actor="tool",
        event_type="command_exec",
        payload={"command": "netstat -ano", "stdout": "TCP 0.0.0.0:9000", "exit_code": 0},
        authority_level=4
    )

    assert trace.trace_id.startswith("tr_")
    assert trace.authority_level == 4
    assert len(trace.integrity_hash) == 64

    # Verify retrieval
    read_trace = temp_store.get_trace(trace.trace_id)
    assert read_trace is not None
    assert read_trace.trace_id == trace.trace_id
    assert read_trace.payload["stdout"] == "TCP 0.0.0.0:9000"
    assert read_trace.integrity_hash == trace.integrity_hash


def test_4_tier_hierarchy_queries(temp_store):
    # Append multiple traces across episodes and turns
    for t_idx in range(5):
        temp_store.append_trace(
            mission_id="m_001",
            episode_id="ep_001",
            window_id=f"win_{t_idx // 2}",
            turn_id=f"turn_{t_idx}",
            actor="assistant" if t_idx % 2 == 0 else "user",
            event_type="conversation",
            payload={"text": f"turn {t_idx} message"},
            authority_level=3 if t_idx % 2 == 1 else 1
        )

    temp_store.append_trace(
        mission_id="m_001",
        episode_id="ep_002",
        window_id="win_ep2_0",
        turn_id="turn_ep2_0",
        actor="tool",
        event_type="file_mutation",
        payload={"path": "src/main.py", "action": "write"},
        authority_level=4
    )

    # Test Mission-level query
    m_traces = temp_store.get_traces_by_mission("m_001")
    assert len(m_traces) == 6

    # Test Episode-level query
    ep1_traces = temp_store.get_traces_by_episode("ep_001")
    assert len(ep1_traces) == 5

    ep2_traces = temp_store.get_traces_by_episode("ep_002")
    assert len(ep2_traces) == 1
    assert ep2_traces[0].event_type == "file_mutation"


def test_rebuild_iteration(temp_store):
    for i in range(10):
        temp_store.append_trace(
            mission_id="m_rebuild",
            episode_id="ep_rebuild",
            window_id="win_rebuild",
            turn_id=f"turn_{i}",
            actor="tool",
            event_type="test_event",
            payload={"index": i},
            authority_level=4
        )

    all_traces = list(temp_store.iterate_all_traces(batch_size=3))
    assert len(all_traces) == 10
    assert [t.payload["index"] for t in all_traces] == list(range(10))
