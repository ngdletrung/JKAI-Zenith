# -*- coding: utf-8 -*-
"""
Integration test suite for DEMS Full Pipeline (Phase 5.6-G).
Verifies:
  - 0 Token Compaction
  - Raw Trace -> Evidence -> Claim -> Belief flow
  - Derived Index Rebuilder (I-DEMS-07)
  - Fast-path verification
"""

import os
import shutil
import tempfile
import pytest
import asyncio

from core.storage.raw_trace_store import RawTraceStore
from core.governor.claim_ledger import ClaimLedger, ClaimScope, ClaimStatus
from core.governor.belief_governor import BeliefGovernor
from core.kernel.compaction import CompactionEngine
from core.tools.dems_rebuilder import DemsIndexRebuilder
from core.kernel.world_model import TypedWorldGraph


@pytest.fixture
def clean_dems_env():
    tmp_dir = tempfile.mkdtemp()
    trace_db = os.path.join(tmp_dir, "traces.db")
    claim_db = os.path.join(tmp_dir, "claims.db")

    trace_store = RawTraceStore(db_path=trace_db)
    clm_ledger = ClaimLedger(db_path=claim_db)
    gov = BeliefGovernor(ledger=clm_ledger)
    graph = TypedWorldGraph()
    reb = DemsIndexRebuilder(trace_store=trace_store, claim_led=clm_ledger, world_graph=graph)

    yield trace_store, clm_ledger, gov, reb
    shutil.rmtree(tmp_dir, ignore_errors=True)


def test_dems_closed_loop_flow(clean_dems_env):
    trace_store, clm_ledger, gov, reb = clean_dems_env

    # 1. User asks question -> trace appended
    t1 = trace_store.append_trace(
        mission_id="m_e2e_01",
        episode_id="ep_01",
        window_id="win_01",
        turn_id="turn_01",
        actor="user",
        event_type="prompt",
        payload={"query": "Kiểm tra port service redis"},
        authority_level=3
    )

    # 2. Tool executes command -> raw observation trace appended
    t2 = trace_store.append_trace(
        mission_id="m_e2e_01",
        episode_id="ep_01",
        window_id="win_01",
        turn_id="turn_02",
        actor="tool",
        event_type="command_exec",
        payload={"service": "redis", "predicate": "port", "stdout": "6379", "exit_code": 0},
        authority_level=4,
        parent_trace_id=t1.trace_id
    )

    # 3. Claim created from trace
    claim = clm_ledger.register_claim(
        subject="redis",
        predicate="port",
        object_val="6379",
        scope=ClaimScope.RUNTIME,
        evidence_id=f"ev_{t2.trace_id}",
        authority_level=t2.authority_level
    )
    assert claim.status == ClaimStatus.ACTIVE

    # 4. Belief resolved without LLM
    belief = gov.resolve_belief(
        subject="redis",
        predicate="port",
        scope=ClaimScope.RUNTIME,
        mission_id="m_e2e_01"
    )

    assert belief.status == ClaimStatus.ACTIVE
    assert belief.effective_object == "6379"
    assert belief.confidence >= 0.85
    assert belief.evidence_debt is None


@pytest.mark.asyncio
async def test_zero_token_compaction():
    engine = CompactionEngine(token_limit=100, threshold=0.5)
    history = [
        {"role": "system", "content": "System prompt"},
        {"role": "user", "content": "Goal: Optimize DB queries"},
        {"role": "assistant", "content": "Let me check the logs"},
        {"role": "user", "content": "Observation: Found slow query on users table took 2500ms"},
        {"role": "assistant", "content": "Let me check indexes"},
        {"role": "user", "content": "Observation: Index missing on email column"},
        {"role": "assistant", "content": "I will create index"},
        {"role": "user", "content": "Observation: Successfully created index idx_users_email in 45ms"},
        {"role": "assistant", "content": "FINAL_ANSWER: Done"},
    ]

    # Compact with fast heuristic (0 token LLM)
    condensed = await engine.condense(history, task_id="test_compaction", use_fast_heuristic=True)
    assert len(condensed) > 0
    # Data DNA / Vital facts preserved
    full_text = " ".join([str(m["content"]) for m in condensed])
    assert "users" in full_text or "index" in full_text or "45ms" in full_text or "2500ms" in full_text


def test_rebuilder_recovers_claims_from_traces(clean_dems_env):
    trace_store, clm_ledger, gov, reb = clean_dems_env

    # Populate traces
    trace_store.append_trace(
        mission_id="m_rec",
        episode_id="ep_rec",
        window_id="win_rec",
        turn_id="turn_rec_1",
        actor="tool",
        event_type="command_exec",
        payload={"service": "postgres", "predicate": "port", "stdout": "5432"},
        authority_level=4
    )

    res = reb.rebuild_all()
    assert res["status"] == "SUCCESS"
    assert res["total_traces_scanned"] == 1
    assert res["rebuilt_claims"] == 1

    # Verify claim can be retrieved from rebuilt state
    claims = clm_ledger.get_claims_by_predicate("postgres", "port")
    assert len(claims) == 1
    assert claims[0].object_val == "5432"
