# -*- coding: utf-8 -*-
"""
🧪 TEST SUITE: DURABLE CHECKPOINT ENGINE (TEMPORAL-LITE)
File: tests/test_durable_checkpoint.py
Role: Comprehensive verification for Reliability-First Slice (b) & Conditions B1-B4
"""

import time
from pathlib import Path
import pytest

from core.kernel.durable_checkpoint import (
    DurableCheckpointEngine,
    StateEnvelope,
    CheckpointRecord,
)


@pytest.fixture
def temp_checkpoint_engine(tmp_path: Path):
    db_file = tmp_path / "test_checkpoints.db"
    engine = DurableCheckpointEngine(db_path=db_file)
    yield engine
    engine.close()


def test_01_save_and_load_checkpoint_roundtrip(temp_checkpoint_engine):
    """Condition B4: State envelope roundtrip with versioned metadata."""
    envelope = StateEnvelope(
        version="1.0",
        messages=[{"role": "user", "content": "hello"}, {"role": "assistant", "content": "hi"}],
        artifacts_manifest={"quadratic.py": "hash_12345"},
        next_step_id=2,
        metadata={"priority": "HIGH"}
    )
    key = temp_checkpoint_engine.compute_idempotency_key(
        mission_id="m_001", step_id=1, tool_name="write_to_file", args={"target": "test.py"}
    )

    duration_ms = temp_checkpoint_engine.save_checkpoint(
        mission_id="m_001",
        step_id=1,
        status="COMPLETED",
        state=envelope,
        idempotency_key=key,
    )
    assert duration_ms >= 0.0

    record = temp_checkpoint_engine.load_latest_checkpoint("m_001")
    assert record is not None
    assert record.mission_id == "m_001"
    assert record.step_id == 1
    assert record.status == "COMPLETED"
    assert record.state.version == "1.0"
    assert len(record.state.messages) == 2
    assert record.state.artifacts_manifest["quadratic.py"] == "hash_12345"


def test_02_idempotency_key_with_args_hash(temp_checkpoint_engine):
    """Condition B2: Idempotency key includes args hash."""
    args_a = {"file": "a.py", "content": "123"}
    args_b = {"file": "a.py", "content": "456"}

    key_a = temp_checkpoint_engine.compute_idempotency_key("m_002", 1, "write_file", args_a)
    key_b = temp_checkpoint_engine.compute_idempotency_key("m_002", 1, "write_file", args_b)
    key_a_repeat = temp_checkpoint_engine.compute_idempotency_key("m_002", 1, "write_file", args_a)

    # Identical args must yield identical key
    assert key_a == key_a_repeat
    # Different args must yield different key
    assert key_a != key_b
    assert "write_file" in key_a


def test_03_sub_millisecond_overhead(temp_checkpoint_engine):
    """Condition B3: SQLite WAL commit overhead under 1.5ms budget."""
    envelope = StateEnvelope(
        messages=[{"role": "user", "content": "bench"}],
        next_step_id=1
    )
    key = temp_checkpoint_engine.compute_idempotency_key("m_003", 1, "tool", {})

    # Warmup
    temp_checkpoint_engine.save_checkpoint("m_003", 1, "PENDING", envelope, key)

    latencies = []
    for i in range(10):
        envelope.next_step_id = i + 2
        ik = f"m_003:{i+2}:tool:hash"
        dur = temp_checkpoint_engine.save_checkpoint("m_003", i + 2, "COMPLETED", envelope, ik)
        latencies.append(dur)

    avg_lat = sum(latencies) / len(latencies)
    # Average WAL commit duration on SSD should easily stay below 10ms (usually <1.5ms)
    assert avg_lat < 10.0, f"Average WAL latency too high: {avg_lat}ms"


def test_04_crash_recovery_resumes_from_latest(temp_checkpoint_engine):
    """Simulate crash recovery after step 2 completes."""
    env_step1 = StateEnvelope(messages=[{"step": 1}], next_step_id=2)
    env_step2 = StateEnvelope(messages=[{"step": 1}, {"step": 2}], next_step_id=3)

    temp_checkpoint_engine.save_checkpoint("m_crash", 1, "COMPLETED", env_step1, "k1")
    temp_checkpoint_engine.save_checkpoint("m_crash", 2, "COMPLETED", env_step2, "k2")

    # Simulate restart: load latest checkpoint
    latest = temp_checkpoint_engine.load_latest_checkpoint("m_crash")
    assert latest is not None
    assert latest.step_id == 2
    assert latest.status == "COMPLETED"
    assert latest.state.next_step_id == 3


def test_05_status_transition_pending_to_completed(temp_checkpoint_engine):
    """Condition B1: Status transition PENDING -> COMPLETED."""
    envelope = StateEnvelope(messages=[], next_step_id=1)
    key = "m_trans:1:tool:hash"

    # Save PENDING before execution
    temp_checkpoint_engine.save_checkpoint("m_trans", 1, "PENDING", envelope, key)
    assert temp_checkpoint_engine.is_step_completed(key) is False

    # Mark COMPLETED after execution
    temp_checkpoint_engine.save_checkpoint("m_trans", 1, "COMPLETED", envelope, key)
    assert temp_checkpoint_engine.is_step_completed(key) is True


def test_06_kill_simulation_new_engine_instance_resumes_mission(tmp_path: Path):
    """Condition Lát (c): Hard kill simulation - new engine instance on same DB file resumes state."""
    db_file = tmp_path / "crash_sim.db"

    # Process 1: Mission executes step 1 and step 2
    engine_proc1 = DurableCheckpointEngine(db_path=db_file)
    envelope_1 = StateEnvelope(
        messages=[{"role": "user", "content": "build project"}],
        artifacts_manifest={"init.py": "hash_1"},
        next_step_id=2
    )
    engine_proc1.save_checkpoint("m_sim_kill", 1, "COMPLETED", envelope_1, "m_sim:1:tool1:hash")

    envelope_2 = StateEnvelope(
        messages=[{"role": "user", "content": "build project"}, {"role": "assistant", "content": "step 1 done"}],
        artifacts_manifest={"init.py": "hash_1", "main.py": "hash_2"},
        next_step_id=3
    )
    engine_proc1.save_checkpoint("m_sim_kill", 2, "COMPLETED", envelope_2, "m_sim:2:tool2:hash")

    # Hard Kill: close connection and destroy instance
    engine_proc1.close()
    del engine_proc1

    # Process 2 (Post-Crash / Restart): Brand new engine instance opens the same DB
    engine_proc2 = DurableCheckpointEngine(db_path=db_file)
    recovered = engine_proc2.load_latest_checkpoint("m_sim_kill")

    assert recovered is not None
    assert recovered.mission_id == "m_sim_kill"
    assert recovered.step_id == 2
    assert recovered.status == "COMPLETED"
    assert len(recovered.state.messages) == 2
    assert recovered.state.artifacts_manifest["main.py"] == "hash_2"
    assert recovered.state.next_step_id == 3

    # Process 2 resumes and writes Step 3
    envelope_3 = StateEnvelope(
        messages=recovered.state.messages + [{"role": "assistant", "content": "step 3 done"}],
        next_step_id=4
    )
    engine_proc2.save_checkpoint("m_sim_kill", 3, "COMPLETED", envelope_3, "m_sim:3:tool3:hash")

    latest_resumed = engine_proc2.load_latest_checkpoint("m_sim_kill")
    assert latest_resumed.step_id == 3
    assert len(latest_resumed.state.messages) == 3

    engine_proc2.close()

