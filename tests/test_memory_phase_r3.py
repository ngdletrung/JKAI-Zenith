"""
Unit Tests for Phase R-Memory-3: Memory Hardening, Integrity Verification & Grounded Reflection
File: tests/test_memory_phase_r3.py
Governed by Turn 473 Consensus:
- Strict EvidenceContract binding (trace_id, mission_id, exit_code==0, verdict bound to receipt).
- Master disposition provenance (MASTER_AUTHORED, never empirically VERIFIED).
- Persistent ledger fails closed on corruption, tampering, or revision gaps.
- Durable single-record append with fsync.
- Separation of operation_status and semantic verdict.
- Reflect topic grounding, evidence cap (<=6), and token budget (<=384).
- Evidence ID existence and bank ownership resolution.
"""

import json
import pytest
from core.memory.memory_contracts import (
    MemoryBankScope, ProposalStatus, ReflectVerdict,
    EvidenceContract, ExecutionReceipt, VerificationVerdictContract,
    MemoryBudgetExceededError, MemoryLedgerIntegrityError
)
from core.memory.canonical_memory_schema import ProvenanceType
from core.memory.observation_builder import ObservationBuilder
from core.memory.memory_verifier import DeterministicMemorySafetyGate
from core.memory.memory_service import MemoryService
from core.memory.sovereign_hindsight_store import SovereignHindsightStore


def test_rejects_fake_receipt_shape():
    # Receipt with exit_code != 0
    bad_receipt = ExecutionReceipt(
        id="rec_01",
        trace_id="tr_01",
        mission_id="m_01",
        exit_code=1,  # FAILED execution
        output="Command failed with error"
    )
    contract = EvidenceContract(
        source_mission="m_01",
        trace_id="tr_01",
        execution_receipt=bad_receipt,
        verification_verdict="PASS"
    )
    with pytest.raises(ValueError, match="exit_code must be 0"):
        contract.validate_bounds()


def test_receipt_trace_mission_binding():
    # Mismatched trace_id
    receipt_mismatch = ExecutionReceipt(
        id="rec_02",
        trace_id="tr_OTHER",
        mission_id="m_02",
        exit_code=0
    )
    contract = EvidenceContract(
        source_mission="m_02",
        trace_id="tr_EXPECTED",
        execution_receipt=receipt_mismatch,
        verification_verdict="PASS"
    )
    with pytest.raises(ValueError, match="does not match contract trace_id"):
        contract.validate_bounds()


def test_verdict_must_be_complete_and_receipt_bound():
    receipt = ExecutionReceipt(
        id="rec_03",
        trace_id="tr_03",
        mission_id="m_03",
        exit_code=0
    )
    # Verdict not bound to receipt ID
    verdict_unbound = VerificationVerdictContract(
        status="COMPLETE",
        mission_id="m_03",
        receipt_refs=["rec_SOME_OTHER_RECEIPT"]
    )
    contract = EvidenceContract(
        source_mission="m_03",
        trace_id="tr_03",
        execution_receipt=receipt,
        verification_verdict=verdict_unbound
    )
    with pytest.raises(ValueError, match="does not contain receipt ID"):
        contract.validate_bounds()


def test_master_disposition_uses_non_empirical_provenance():
    service = MemoryService()
    res = service.retain_observation(
        bank=MemoryBankScope.MASTER_DISPOSITION,
        claim="Master prefers dark mode and concise summaries",
        source_mission="mission_pref",
        authorized_by_master=True
    )
    assert res["success"] is True
    assert res["provenance"] == ProvenanceType.MASTER_AUTHORED.value
    assert res["provenance"] != ProvenanceType.VERIFIED.value


def test_corrupt_ledger_fails_closed(tmp_path):
    ledger = tmp_path / "corrupt_ledger.jsonl"
    ledger.write_text("NOT_VALID_JSON\n", encoding="utf-8")

    with pytest.raises(MemoryLedgerIntegrityError, match="MEMORY_LEDGER_INTEGRITY_FAILURE"):
        ObservationBuilder(ledger_file=ledger)


def test_tampered_revision_hash_detected(tmp_path):
    ledger = tmp_path / "tampered_ledger.jsonl"
    builder = ObservationBuilder(ledger_file=ledger)
    rev = builder.append_revision("obs_t", "Original Claim")

    # Manually tamper with the ledger line (alter claim without updating hash)
    raw_lines = ledger.read_text(encoding="utf-8").splitlines()
    data = json.loads(raw_lines[0])
    data["claim"] = "TAMPERED CLAIM"
    ledger.write_text(json.dumps(data) + "\n", encoding="utf-8")

    # New builder must detect hash mismatch and fail closed
    with pytest.raises(MemoryLedgerIntegrityError, match="Hash mismatch"):
        ObservationBuilder(ledger_file=ledger)


def test_revision_gap_detected(tmp_path):
    ledger = tmp_path / "gap_ledger.jsonl"
    builder = ObservationBuilder(ledger_file=ledger)
    rev1 = builder.append_revision("obs_g", "Rev 1 Claim")

    # Append revision 3 directly (skipping rev 2)
    fake_rev3 = {
        "observation_id": "obs_g",
        "revision": 3,
        "claim": "Rev 3 Claim",
        "supporting_memory_ids": [],
        "contradicting_memory_ids": [],
        "provenance": "RAW",
        "previous_hash": rev1.current_hash,
        "valid_from": "2026-10-18T10:00:00Z",
        "valid_to": None
    }
    # compute hash for fake rev3
    from core.memory.memory_contracts import ObservationRevision
    r3_obj = ObservationRevision(**fake_rev3)
    fake_rev3["current_hash"] = r3_obj.compute_hash()

    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(fake_rev3) + "\n")

    with pytest.raises(MemoryLedgerIntegrityError, match="Revision gap detected"):
        ObservationBuilder(ledger_file=ledger)


def test_append_is_durable_and_single_record(tmp_path):
    ledger = tmp_path / "durable_ledger.jsonl"
    builder = ObservationBuilder(ledger_file=ledger)

    rev = builder.append_revision("obs_d", "Durable claim text", provenance="VERIFIED")
    assert ledger.exists()

    lines = ledger.read_text(encoding="utf-8").strip().splitlines()
    assert len(lines) == 1
    loaded = json.loads(lines[0])
    assert loaded["observation_id"] == "obs_d"
    assert loaded["revision"] == 1
    assert loaded["claim"] == "Durable claim text"


def test_reflect_separates_operation_status_and_verdict():
    service = MemoryService()
    res = service.reflect(MemoryBankScope.SYSTEM_WORLD, offline_mode=True)
    assert res["operation_status"] == "SUCCEEDED"
    assert res["verdict"] in ["INSUFFICIENT_EVIDENCE", "SUPPORTED", "CONFLICTED"]
    # Guarantee no confusing "status": "COMPLETED" as semantic judgment
    assert res.get("status") != "COMPLETED"


def test_reflect_budget_and_topic_enforced():
    store = SovereignHindsightStore()
    service = MemoryService(store=store)

    # Add observations
    service.retain_observation(MemoryBankScope.SYSTEM_WORLD, "Docker port 8000 listening", "m_net")
    service.retain_observation(MemoryBankScope.SYSTEM_WORLD, "Postgres port 5432 listening", "m_db")

    # Topic filtering
    res_topic = service.reflect(MemoryBankScope.SYSTEM_WORLD, offline_mode=True, topic="Docker")
    assert len(res_topic["claims"]) == 1
    assert "Docker port 8000" in res_topic["claims"][0]

    # Overflow budget test (> 6 evidence records)
    records = store._ensure_bank(MemoryBankScope.SYSTEM_WORLD.value)
    records[0].evidence_refs = [f"ev_{i}" for i in range(10)]
    with pytest.raises(MemoryBudgetExceededError, match="BLOCKED_MEMORY_BUDGET"):
        service.reflect(MemoryBankScope.SYSTEM_WORLD, offline_mode=True)


def test_evidence_id_exists_and_same_bank():
    store = SovereignHindsightStore()
    service = MemoryService(store=store)

    # Retain a valid memory in WORLD
    rec_world = store.retain(
        bank_id=MemoryBankScope.SYSTEM_WORLD.value,
        claim="Existing world fact",
        source="m_init"
    )

    receipt = ExecutionReceipt(id="r1", trace_id="t1", mission_id="m1", exit_code=0)
    verdict = VerificationVerdictContract(status="COMPLETE", mission_id="m1", receipt_refs=["r1"])

    # 1. Non-existent evidence ID
    contract_missing = EvidenceContract(
        source_mission="m1",
        trace_id="t1",
        execution_receipt=receipt,
        verification_verdict=verdict,
        evidence_records=["mem_DOES_NOT_EXIST"]
    )
    res1 = service.retain_observation(
        bank=MemoryBankScope.VERIFIED_EXPERIENCE,
        claim="Execution tested with missing evidence",
        source_mission="m1",
        evidence_contract=contract_missing
    )
    assert res1["success"] is False
    assert "EVIDENCE_RECORD_NOT_FOUND" in res1["reason"]

    # 2. Evidence ID belonging to different bank (WORLD instead of VERIFIED_EXPERIENCE)
    contract_wrong_bank = EvidenceContract(
        source_mission="m1",
        trace_id="t1",
        execution_receipt=receipt,
        verification_verdict=verdict,
        evidence_records=[rec_world.id]
    )
    res2 = service.retain_observation(
        bank=MemoryBankScope.VERIFIED_EXPERIENCE,
        claim="Execution referencing world bank evidence",
        source_mission="m1",
        evidence_contract=contract_wrong_bank
    )
    assert res2["success"] is False
    assert "CROSS_BANK_LEAKAGE" in res2["reason"]


def test_reflect_grounding_rejects_unsupported_claim():
    store = SovereignHindsightStore()
    service = MemoryService(store=store)

    # Inject an active record in VERIFIED_EXPERIENCE without evidence_refs
    store.retain(
        bank_id=MemoryBankScope.VERIFIED_EXPERIENCE.value,
        claim="Ungrounded claim with no evidence",
        source="m_ungrounded",
        evidence_refs=[]  # empty evidence!
    )
    res = service.reflect(MemoryBankScope.VERIFIED_EXPERIENCE, offline_mode=True)
    assert res["verdict"] == ReflectVerdict.INSUFFICIENT_EVIDENCE.value
