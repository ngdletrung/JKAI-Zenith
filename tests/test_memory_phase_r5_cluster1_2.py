"""
Unit Tests for Phase R-Memory-5: Cluster 1 & Cluster 2
File: tests/test_memory_phase_r5_cluster1_2.py
Governed by Turn 477 & Turn 480 SOP V5.0 Swarm Track B:
- Cluster 1: Production Default-Deny Boundary (ProductionMemoryService default-deny, string verdict rejection).
- Cluster 2: Mandatory Execution Ledger Binding & Hash Verification (exit_code, trace_id, mission_id, artifact_hash).
- Cluster 4: Conflicting evidence namespace rejection.
"""

import pytest
from core.memory.memory_contracts import (
    MemoryBankScope, ProposalStatus, EvidenceContract,
    ExecutionReceipt, VerificationVerdictContract
)
from core.memory.observation_builder import ObservationBuilder
from core.memory.memory_verifier import DeterministicMemorySafetyGate
from core.memory.memory_service import MemoryService, ProductionMemoryService
from core.memory.sovereign_hindsight_store import SovereignHindsightStore


def test_default_production_path_rejects_string_verdict():
    """Cluster 1: Production path rejects untyped string verdict and enforces VerificationVerdictContract."""
    service = ProductionMemoryService()
    assert service.production_mode is True

    receipt = ExecutionReceipt(
        id="rec_p1",
        trace_id="tr_p1",
        mission_id="m_p1",
        exit_code=0,
        artifact_hash="sha256_art1"
    )

    # In production, passing string verdict 'PASS' must be rejected
    contract = EvidenceContract(
        source_mission="m_p1",
        trace_id="tr_p1",
        execution_receipt=receipt,
        verification_verdict="PASS"
    )

    res = service.retain_observation(
        bank=MemoryBankScope.VERIFIED_EXPERIENCE,
        claim="Production claim with string verdict",
        source_mission="m_p1",
        evidence_contract=contract
    )

    assert res["success"] is False
    assert "String verdict rejected in production" in res["reason"]
    assert res["status"] == ProposalStatus.REJECTED.value


def test_missing_execution_ledger_blocks_verified_experience():
    """Cluster 2: In production mode, retaining into VERIFIED_EXPERIENCE without execution ledger is blocked."""
    service = ProductionMemoryService(execution_ledger=None)

    receipt = ExecutionReceipt(
        id="rec_p2",
        trace_id="tr_p2",
        mission_id="m_p2",
        exit_code=0,
        artifact_hash="sha256_art2"
    )
    verdict = VerificationVerdictContract(
        status="COMPLETE",
        mission_id="m_p2",
        receipt_refs=["rec_p2"]
    )
    contract = EvidenceContract(
        source_mission="m_p2",
        trace_id="tr_p2",
        execution_receipt=receipt,
        verification_verdict=verdict
    )

    res = service.retain_observation(
        bank=MemoryBankScope.VERIFIED_EXPERIENCE,
        claim="Verified execution without ledger backing",
        source_mission="m_p2",
        evidence_contract=contract
    )

    assert res["success"] is False
    assert "EXECUTION_LEDGER_MANDATORY" in res["reason"]


def test_typed_receipt_payload_matches_ledger():
    """Cluster 2: Receipt payload (trace_id, mission_id, exit_code) must strictly match resolved ledger."""
    ledger_records = {
        "rec_auth_01": ExecutionReceipt(
            id="rec_auth_01",
            trace_id="tr_legit",
            mission_id="m_legit",
            exit_code=0,
            artifact_hash="sha256_valid"
        )
    }

    service = ProductionMemoryService(execution_ledger=ledger_records)

    # 1. Mismatched trace_id in proposal
    spoofed_trace_receipt = ExecutionReceipt(
        id="rec_auth_01",
        trace_id="tr_SPOOFED",
        mission_id="m_legit",
        exit_code=0,
        artifact_hash="sha256_valid"
    )
    contract_spoof = EvidenceContract(
        source_mission="m_legit",
        trace_id="tr_SPOOFED",
        execution_receipt=spoofed_trace_receipt,
        verification_verdict=VerificationVerdictContract(
            status="COMPLETE",
            mission_id="m_legit",
            receipt_refs=["rec_auth_01"]
        )
    )

    res_spoof = service.retain_observation(
        bank=MemoryBankScope.VERIFIED_EXPERIENCE,
        claim="Spoofed trace proposal",
        source_mission="m_legit",
        evidence_contract=contract_spoof
    )
    assert res_spoof["success"] is False
    assert "EXECUTION_RECEIPT_MISMATCH: trace_id mismatch" in res_spoof["reason"]

    # 2. Mismatched mission_id
    spoofed_mission_receipt = ExecutionReceipt(
        id="rec_auth_01",
        trace_id="tr_legit",
        mission_id="m_OTHER",
        exit_code=0,
        artifact_hash="sha256_valid"
    )
    contract_mission = EvidenceContract(
        source_mission="m_OTHER",
        trace_id="tr_legit",
        execution_receipt=spoofed_mission_receipt,
        verification_verdict=VerificationVerdictContract(
            status="COMPLETE",
            mission_id="m_OTHER",
            receipt_refs=["rec_auth_01"]
        )
    )
    res_mission = service.retain_observation(
        bank=MemoryBankScope.VERIFIED_EXPERIENCE,
        claim="Spoofed mission proposal",
        source_mission="m_OTHER",
        evidence_contract=contract_mission
    )
    assert res_mission["success"] is False
    assert "EXECUTION_RECEIPT_MISMATCH: mission_id mismatch" in res_mission["reason"]


def test_conflicting_evidence_namespace_fields_rejected():
    """Cluster 4: Conflicting evidence_records and evidence_memory_ids must be rejected."""
    receipt = ExecutionReceipt(id="r_ns", trace_id="t_ns", mission_id="m_ns", exit_code=0)
    verdict = VerificationVerdictContract(status="COMPLETE", mission_id="m_ns", receipt_refs=["r_ns"])

    # Disagreeing lists
    with pytest.raises(ValueError, match="Conflicting evidence namespace"):
        EvidenceContract(
            source_mission="m_ns",
            trace_id="t_ns",
            execution_receipt=receipt,
            verification_verdict=verdict,
            evidence_records=["mem_alpha"],
            evidence_memory_ids=["mem_beta"]
        )


def test_execution_receipt_artifact_hash_binding():
    """Cluster 2: Artifact hash in proposal must match resolved ledger entry."""
    ledger_records = {
        "rec_hash_01": ExecutionReceipt(
            id="rec_hash_01",
            trace_id="tr_h1",
            mission_id="m_h1",
            exit_code=0,
            artifact_hash="sha256_golden_artifact"
        )
    }

    service = ProductionMemoryService(execution_ledger=ledger_records)

    # 1. Tampered artifact hash
    tampered_receipt = ExecutionReceipt(
        id="rec_hash_01",
        trace_id="tr_h1",
        mission_id="m_h1",
        exit_code=0,
        artifact_hash="sha256_tampered_artifact"
    )
    contract_tampered = EvidenceContract(
        source_mission="m_h1",
        trace_id="tr_h1",
        execution_receipt=tampered_receipt,
        verification_verdict=VerificationVerdictContract(
            status="COMPLETE",
            mission_id="m_h1",
            receipt_refs=["rec_hash_01"]
        )
    )

    res_tampered = service.retain_observation(
        bank=MemoryBankScope.VERIFIED_EXPERIENCE,
        claim="Tampered artifact hash proposal",
        source_mission="m_h1",
        evidence_contract=contract_tampered
    )
    assert res_tampered["success"] is False
    assert "artifact_hash mismatch" in res_tampered["reason"]

    # 2. Missing artifact hash in proposal
    missing_hash_receipt = ExecutionReceipt(
        id="rec_hash_01",
        trace_id="tr_h1",
        mission_id="m_h1",
        exit_code=0,
        artifact_hash=""
    )
    contract_missing = EvidenceContract(
        source_mission="m_h1",
        trace_id="tr_h1",
        execution_receipt=missing_hash_receipt,
        verification_verdict=VerificationVerdictContract(
            status="COMPLETE",
            mission_id="m_h1",
            receipt_refs=["rec_hash_01"]
        )
    )

    res_missing = service.retain_observation(
        bank=MemoryBankScope.VERIFIED_EXPERIENCE,
        claim="Missing artifact hash proposal",
        source_mission="m_h1",
        evidence_contract=contract_missing
    )
    assert res_missing["success"] is False
    assert "artifact_hash missing in proposal receipt" in res_missing["reason"]
