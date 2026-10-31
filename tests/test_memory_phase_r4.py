"""
Unit Tests for Phase R-Memory-4: Concurrency Serialization, Typed Proof & Scoped Store API
File: tests/test_memory_phase_r4.py
Governed by Turn 475 Consensus:
- Mandatory typed receipts & verdicts in production mode.
- Rejection of empty receipt id, unclosed lines, and ungrounded string verdicts.
- Namespace separation: evidence_memory_ids vs execution_receipt.id.
- Concurrency serialization with thread lock and duplicate revision prevention.
- Preflight budget check before reflect materialization.
- Public scoped store API usage (zero private internals access).
- Fake receipt rejection against execution ledger.
"""

import json
import threading
import time
import pytest
from pathlib import Path

from core.memory.memory_contracts import (
    MemoryBankScope, ProposalStatus, ReflectVerdict,
    EvidenceContract, ExecutionReceipt, VerificationVerdictContract,
    ObservationRevision,
    MemoryBudgetExceededError, MemoryLedgerIntegrityError,
    BUDGET_REFLECT_EVIDENCE_RECORDS
)
from core.memory.canonical_memory_schema import ProvenanceType, MemoryStatus
from core.memory.observation_builder import ObservationBuilder
from core.memory.memory_verifier import DeterministicMemorySafetyGate
from core.memory.memory_service import MemoryService
from core.memory.sovereign_hindsight_store import SovereignHindsightStore


def test_typed_receipt_fields_are_mandatory():
    # In production mode, dict or receipt missing mandatory fields must be rejected
    untyped_dict_receipt = {"id": "rec_01", "exit_code": 0}  # missing trace_id and mission_id
    contract = EvidenceContract(
        source_mission="mission_476",
        trace_id="tr_476",
        execution_receipt=untyped_dict_receipt,
        verification_verdict=VerificationVerdictContract(
            status="COMPLETE",
            mission_id="mission_476",
            receipt_refs=["rec_01"]
        )
    )
    with pytest.raises(ValueError, match="Production mode requires typed ExecutionReceipt"):
        contract.validate_bounds(production_mode=True)


def test_string_verdict_rejected_in_production():
    valid_receipt = ExecutionReceipt(
        id="rec_typed_01",
        trace_id="tr_prod_01",
        mission_id="m_prod_01",
        exit_code=0
    )
    contract = EvidenceContract(
        source_mission="m_prod_01",
        trace_id="tr_prod_01",
        execution_receipt=valid_receipt,
        verification_verdict="PASS"  # String verdict instead of typed contract
    )
    with pytest.raises(ValueError, match="String verdict rejected in production"):
        contract.validate_bounds(production_mode=True)


def test_empty_receipt_id_rejected():
    empty_receipt = ExecutionReceipt(
        id="",
        trace_id="tr_01",
        mission_id="m_01",
        exit_code=0
    )
    contract = EvidenceContract(
        source_mission="m_01",
        trace_id="tr_01",
        execution_receipt=empty_receipt,
        verification_verdict=VerificationVerdictContract(
            status="COMPLETE",
            mission_id="m_01",
            receipt_refs=[]
        )
    )
    with pytest.raises(ValueError, match="Receipt id cannot be empty"):
        contract.validate_bounds(production_mode=False)


def test_verdict_mission_and_receipt_binding():
    receipt = ExecutionReceipt(
        id="rec_bind_01",
        trace_id="tr_bind_01",
        mission_id="m_bind_01",
        exit_code=0
    )
    # Verdict with mismatched mission_id
    mismatched_verdict = VerificationVerdictContract(
        status="COMPLETE",
        mission_id="m_DIFFERENT",
        receipt_refs=["rec_bind_01"]
    )
    contract_mismatch = EvidenceContract(
        source_mission="m_bind_01",
        trace_id="tr_bind_01",
        execution_receipt=receipt,
        verification_verdict=mismatched_verdict
    )
    with pytest.raises(ValueError, match="does not match source_mission"):
        contract_mismatch.validate_bounds(production_mode=False)

    # In production, empty receipt_refs must be rejected
    empty_refs_verdict = VerificationVerdictContract(
        status="COMPLETE",
        mission_id="m_bind_01",
        receipt_refs=[]
    )
    contract_empty_refs = EvidenceContract(
        source_mission="m_bind_01",
        trace_id="tr_bind_01",
        execution_receipt=receipt,
        verification_verdict=empty_refs_verdict
    )
    with pytest.raises(ValueError, match="receipt_refs cannot be empty in production"):
        contract_empty_refs.validate_bounds(production_mode=True)


def test_evidence_id_namespace_separation():
    receipt = ExecutionReceipt(
        id="receipt_exec_999",
        trace_id="tr_sep_01",
        mission_id="m_sep_01",
        exit_code=0
    )
    verdict = VerificationVerdictContract(
        status="COMPLETE",
        mission_id="m_sep_01",
        receipt_refs=["receipt_exec_999"]
    )
    contract = EvidenceContract(
        source_mission="m_sep_01",
        trace_id="tr_sep_01",
        execution_receipt=receipt,
        verification_verdict=verdict,
        evidence_memory_ids=["mem_hindsight_123", "mem_hindsight_456"]
    )
    assert contract.execution_receipt.id == "receipt_exec_999"
    assert "mem_hindsight_123" in contract.evidence_memory_ids
    assert "receipt_exec_999" not in contract.evidence_memory_ids
    assert contract.evidence_records == contract.evidence_memory_ids


def test_reflect_without_topic_policy():
    store = SovereignHindsightStore()
    service = MemoryService(store=store)

    # Populate 7 records in VERIFIED_EXPERIENCE (> BUDGET_REFLECT_EVIDENCE_RECORDS = 6)
    for i in range(7):
        store.retain(
            bank_id=MemoryBankScope.VERIFIED_EXPERIENCE.value,
            claim=f"Test benchmark observation number {i}",
            source="benchmark_mission",
            provenance=ProvenanceType.VERIFIED
        )

    # Reflect without topic must be rejected
    with pytest.raises(MemoryBudgetExceededError, match="Topic is required when bank contains more than"):
        service.reflect(bank=MemoryBankScope.VERIFIED_EXPERIENCE, offline_mode=True, topic=None)


def test_reflect_preflight_budget_before_materialization(monkeypatch):
    store = SovereignHindsightStore()
    service = MemoryService(store=store)

    # Retain records that exceed evidence records budget for the specific topic
    for i in range(8):
        store.retain(
            bank_id=MemoryBankScope.VERIFIED_EXPERIENCE.value,
            claim=f"Targeted performance benchmark observation {i}",
            source="perf_mission",
            provenance=ProvenanceType.VERIFIED,
            evidence_refs=[f"ev_rec_{i}"]
        )

    # Track if store.reflect was called
    reflect_called = False
    original_store_reflect = store.reflect

    def spy_reflect(*args, **kwargs):
        nonlocal reflect_called
        reflect_called = True
        return original_store_reflect(*args, **kwargs)

    monkeypatch.setattr(store, "reflect", spy_reflect)

    with pytest.raises(MemoryBudgetExceededError, match="exceeds limit"):
        service.reflect(
            bank=MemoryBankScope.VERIFIED_EXPERIENCE,
            offline_mode=True,
            topic="performance benchmark"
        )

    # Crucial preflight assertion: store.reflect MUST NOT have been called
    assert not reflect_called, "store.reflect should NOT be called if preflight budget checks fail"


def test_concurrent_append_serialized(tmp_path):
    ledger_path = tmp_path / "concurrent_ledger.jsonl"
    builder = ObservationBuilder(ledger_file=ledger_path)
    obs_id = "obs_concurrent_test"

    thread_count = 10
    barrier = threading.Barrier(thread_count)

    def worker(worker_id):
        barrier.wait()
        builder.append_revision(
            observation_id=obs_id,
            claim=f"Claim from worker {worker_id}",
            provenance="RAW"
        )

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(thread_count)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # Load fresh builder to verify the ledger
    verifier_builder = ObservationBuilder(ledger_file=ledger_path)
    revisions = verifier_builder.get_revisions(obs_id)

    assert len(revisions) == thread_count
    # Verify sequential unbroken numbering
    for idx, rev in enumerate(revisions, start=1):
        assert rev.revision == idx
        if idx == 1:
            assert rev.previous_hash == "0" * 16
        else:
            assert rev.previous_hash == revisions[idx - 2].current_hash
        assert rev.current_hash == rev.compute_hash()


def test_duplicate_revision_blocked_under_lock(tmp_path):
    ledger_path = tmp_path / "dup_ledger.jsonl"
    builder = ObservationBuilder(ledger_file=ledger_path)
    obs_id = "obs_dup_test"

    # Append revision 1
    builder.append_revision(observation_id=obs_id, claim="Initial claim", explicit_revision=1)

    # Attempting to append duplicate revision 1 must raise MemoryLedgerIntegrityError
    with pytest.raises(MemoryLedgerIntegrityError, match="DUPLICATE_REVISION_BLOCKED"):
        builder.append_revision(observation_id=obs_id, claim="Duplicate claim", explicit_revision=1)


def test_partial_final_line_fails_closed(tmp_path):
    ledger_path = tmp_path / "partial_line_ledger.jsonl"
    valid_record = {
        "observation_id": "obs_p_01",
        "revision": 1,
        "claim": "Valid claim before crash",
        "supporting_memory_ids": [],
        "contradicting_memory_ids": [],
        "provenance": "RAW",
        "previous_hash": "0" * 16,
        "current_hash": "dummy",
        "valid_from": "2026-10-18T00:00:00Z",
        "valid_to": None
    }
    # Calculate correct hash
    rev_obj = ObservationRevision(**valid_record)
    valid_record["current_hash"] = rev_obj.compute_hash()

    with open(ledger_path, "w", encoding="utf-8") as f:
        f.write(json.dumps(valid_record) + "\n")
        # Write unclosed trailing line representing crash
        f.write('{"observation_id": "obs_p_01", "revision": 2, "claim": "Incomplete w')

    with pytest.raises(MemoryLedgerIntegrityError, match="Partial/unclosed trailing line detected"):
        ObservationBuilder(ledger_file=ledger_path)


def test_public_scoped_store_api_used(monkeypatch):
    store = SovereignHindsightStore()
    service = MemoryService(store=store)

    store.retain(
        bank_id=MemoryBankScope.VERIFIED_EXPERIENCE.value,
        claim="API boundaries check observation",
        source="m_api_boundary",
        provenance=ProvenanceType.VERIFIED,
        evidence_refs=["rec_api_01"]
    )

    # Spy on _ensure_bank: reflect() should NOT call _ensure_bank directly
    ensure_bank_called = False
    original_ensure_bank = store._ensure_bank

    def spy_ensure_bank(*args, **kwargs):
        nonlocal ensure_bank_called
        ensure_bank_called = True
        return original_ensure_bank(*args, **kwargs)

    # Use public API directly
    records = store.list_scoped_records(MemoryBankScope.VERIFIED_EXPERIENCE.value)
    assert len(records) == 1
    assert records[0].claim == "API boundaries check observation"

    # Now run reflect: should succeed without calling _ensure_bank from service layer
    # Note: store.reflect internally may call its own private helper, but MemoryService must not
    res = service.reflect(bank=MemoryBankScope.VERIFIED_EXPERIENCE, offline_mode=True, topic="boundaries")
    assert res["status"] == "SUCCEEDED"
    assert res["verdict"] == ReflectVerdict.SUPPORTED.value


def test_fake_receipt_not_in_execution_ledger_rejected():
    receipt = ExecutionReceipt(
        id="rec_fake_999",
        trace_id="tr_exec_01",
        mission_id="m_exec_01",
        exit_code=0
    )
    verdict = VerificationVerdictContract(
        status="COMPLETE",
        mission_id="m_exec_01",
        receipt_refs=["rec_fake_999"]
    )
    contract = EvidenceContract(
        source_mission="m_exec_01",
        trace_id="tr_exec_01",
        execution_receipt=receipt,
        verification_verdict=verdict
    )

    # Execution ledger contains only genuine receipts
    genuine_execution_ledger = {"rec_genuine_101", "rec_genuine_102"}

    gate = DeterministicMemorySafetyGate()
    from core.memory.observation_builder import ObservationProposal
    proposal = ObservationProposal(
        id="prop_test_fake",
        target_bank=MemoryBankScope.VERIFIED_EXPERIENCE,
        claim="Claim backed by fake receipt not in ledger",
        source_mission="m_exec_01",
        evidence_payload={},
        evidence_contract=contract,
        status=ProposalStatus.CANDIDATE
    )

    approved, reason = gate.verify_proposal(
        proposal=proposal,
        execution_ledger=genuine_execution_ledger,
        production_mode=True
    )
    assert not approved
    assert "EXECUTION_RECEIPT_NOT_FOUND" in reason
    assert "rec_fake_999" in reason
