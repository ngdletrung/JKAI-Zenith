"""
Unit Tests for Phase R-Memory-5: Cluster 3 & Cluster 4
File: tests/test_memory_phase_r5_cluster3_4.py
Governed by Turn 477, Turn 479 & Turn 481 Consensus:
- Cluster 3: Process-safe Writer (Real Multi-Process Appends, OS Lock) & Quarantine Artifact.
- Cluster 4: Bounded Reflect Pipeline & Read Safety (No Write Mutation Side-Effects, Count Preflight).
"""

import os
import json
import time
import multiprocessing
import pytest
from pathlib import Path

from core.memory.memory_contracts import (
    MemoryBankScope, MemoryLedgerIntegrityError, MemoryBudgetExceededError,
    BUDGET_REFLECT_EVIDENCE_RECORDS
)
from core.memory.canonical_memory_schema import MemoryStatus, ProvenanceType
from core.memory.observation_builder import ObservationBuilder
from core.memory.sovereign_hindsight_store import SovereignHindsightStore
from core.memory.memory_service import MemoryService


def _worker_append(ledger_path_str: str, worker_id: int, count: int):
    """Worker function executed in separate real OS processes."""
    ledger_file = Path(ledger_path_str)
    builder = ObservationBuilder(ledger_file=ledger_file)
    for i in range(count):
        builder.append_revision(
            observation_id=f"obs_proc_{worker_id}",
            claim=f"Process {worker_id} observation revision step {i}",
            provenance="VERIFIED"
        )
        time.sleep(0.005)


def test_cross_process_append_serialization(tmp_path):
    """Cluster 3: Real multi-process concurrent append serialization."""
    ledger_file = tmp_path / "cross_process_ledger.jsonl"
    
    # 2 concurrent worker processes appending to same ledger
    num_workers = 2
    items_per_worker = 5
    processes = []
    for wid in range(num_workers):
        p = multiprocessing.Process(
            target=_worker_append,
            args=(str(ledger_file), wid, items_per_worker)
        )
        processes.append(p)
        p.start()

    for p in processes:
        p.join(timeout=20)
        assert p.exitcode == 0

    assert ledger_file.exists()
    lines = ledger_file.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == num_workers * items_per_worker

    # Verify that a fresh ObservationBuilder can load and verify full ledger without error
    builder = ObservationBuilder(ledger_file=ledger_file)
    for wid in range(num_workers):
        revs = builder.get_revisions(f"obs_proc_{wid}")
        assert len(revs) == items_per_worker
        assert [r.revision for r in revs] == list(range(1, items_per_worker + 1))


def test_partial_line_quarantine_artifact(tmp_path):
    """Cluster 3: Quarantine artifact creation on partial/unclosed trailing line."""
    ledger_file = tmp_path / "quarantine_test_ledger.jsonl"
    builder = ObservationBuilder(ledger_file=ledger_file)
    builder.append_revision("obs_valid", "Valid initial revision")

    # Append corrupted trailing line without closing newline
    corrupted_tail = b'{"observation_id": "obs_truncated", "revision": 2, "claim": "Incom'
    with open(ledger_file, "ab") as f:
        f.write(corrupted_tail)

    quarantine_path = ledger_file.with_name(ledger_file.name + ".quarantine")
    assert not quarantine_path.exists()

    # Attempting to load must fail closed and generate quarantine artifact
    with pytest.raises(MemoryLedgerIntegrityError) as excinfo:
        ObservationBuilder(ledger_file=ledger_file)

    # 1. Quarantine artifact exists alongside ledger
    assert quarantine_path.exists()
    # 2. Corrupted tail bytes strictly preserved in quarantine file
    assert quarantine_path.read_bytes() == corrupted_tail
    # 3. Quarantine resolved path is mentioned in exception
    assert str(quarantine_path.resolve()) in str(excinfo.value)
    # 4. Original ledger was not silently truncated
    assert ledger_file.read_bytes().endswith(corrupted_tail)


def test_count_scoped_records_before_retrieval():
    """Cluster 4: count_scoped_records fast preflight without allocating full objects."""
    store = SovereignHindsightStore()
    
    # Empty count
    assert store.count_scoped_records("bank_test") == 0

    # Add records
    store.retain("bank_test", "PostgreSQL database configuration", "m1")
    store.retain("bank_test", "Redis cache configuration", "m2")
    store.retain("bank_test", "Docker daemon configuration", "m3")

    assert store.count_scoped_records("bank_test") == 3
    assert store.count_scoped_records("bank_test", topic="PostgreSQL") == 1
    assert store.count_scoped_records("bank_test", topic="Redis") == 1
    assert store.count_scoped_records("bank_test", topic="Kubernetes") == 0


def test_reading_unknown_bank_has_no_write_side_effect():
    """Cluster 4: Querying non-existent bank leaves internal state untouched."""
    store = SovereignHindsightStore()
    unknown_bank = "bank_completely_unknown_999"

    assert unknown_bank not in store.banks

    res_list = store.list_scoped_records(unknown_bank)
    assert res_list == []
    assert unknown_bank not in store.banks

    res_resolve = store.resolve_evidence(unknown_bank, "mem_xyz")
    assert res_resolve is None
    assert unknown_bank not in store.banks

    res_count = store.count_scoped_records(unknown_bank)
    assert res_count == 0
    assert unknown_bank not in store.banks


def test_store_reflect_receives_bounded_records_only(monkeypatch):
    """Cluster 4: store.reflect receives only bounded target records, not whole bank."""
    store = SovereignHindsightStore()
    service = MemoryService(store=store)

    # Add 4 records under topic "Network" and 3 under topic "Storage"
    for i in range(4):
        store.retain(
            bank_id=MemoryBankScope.SYSTEM_WORLD.value,
            claim=f"Network interface eth{i} configured",
            source="net_mission",
            provenance=ProvenanceType.VERIFIED,
            evidence_refs=[f"ev_net_{i}"]
        )
    for j in range(3):
        store.retain(
            bank_id=MemoryBankScope.SYSTEM_WORLD.value,
            claim=f"Storage volume vol{j} mounted",
            source="storage_mission",
            provenance=ProvenanceType.VERIFIED,
            evidence_refs=[f"ev_vol_{j}"]
        )

    received_target_records = None
    original_store_reflect = store.reflect

    def spy_store_reflect(*args, **kwargs):
        nonlocal received_target_records
        received_target_records = kwargs.get("target_records")
        return original_store_reflect(*args, **kwargs)

    monkeypatch.setattr(store, "reflect", spy_store_reflect)

    # Reflect on topic "Network"
    res = service.reflect(
        bank=MemoryBankScope.SYSTEM_WORLD,
        offline_mode=True,
        topic="Network"
    )

    assert res["operation_status"] == "SUCCEEDED"
    assert received_target_records is not None
    # Must only contain the 4 network records, NOT all 7 records in the bank
    assert len(received_target_records) == 4
    for r in received_target_records:
        assert "Network interface" in r.claim
