"""
Unit Tests for Phase R-Memory-2: Deterministic Safety Gate & Semantic Evidence Governance
File: tests/test_memory_phase_r2.py
Governed by Turn 469 & Turn 471 Consensus:
- Mandatory Evidence Contract for VERIFIED_EXPERIENCE (receipt + verdict + trace_id).
- Master Authority vs Empirical Truth separation.
- Deterministic Token Budgets (retain input <= 512, claim <= 256).
- Entity (<= 32) and Relation (<= 64) limit enforcement.
- Cross-bank evidence reference blocking.
- Full payload SHA-256 hash chaining & persistence across process restarts.
- Semantic Reflect Verdicts (SUPPORTED, CONFLICTED, INSUFFICIENT_EVIDENCE).
"""

import pytest
from core.memory.memory_contracts import (
    MemoryBankScope, ProposalStatus, ReflectVerdict,
    EvidenceContract, MemoryBudgetExceededError,
    MemoryEntityLimitExceededError, MemoryRelationLimitExceededError
)
from core.memory.observation_builder import ObservationBuilder
from core.memory.memory_verifier import DeterministicMemorySafetyGate
from core.memory.memory_service import MemoryService
from core.memory.sovereign_hindsight_store import SovereignHindsightStore


def test_verified_experience_requires_evidence_contract():
    service = MemoryService()

    # Attempt retention to VERIFIED_EXPERIENCE without EvidenceContract
    res_fail = service.retain_observation(
        bank=MemoryBankScope.VERIFIED_EXPERIENCE,
        claim="Docker build succeeded after adding cache mount",
        source_mission="mission_build_01"
    )
    assert res_fail["success"] is False
    assert "EVIDENCE_CONTRACT_REQUIRED" in res_fail["reason"]
    assert res_fail["status"] == ProposalStatus.REJECTED.value

    # Retention with valid EvidenceContract
    contract = EvidenceContract(
        source_mission="mission_build_01",
        trace_id="trace_dk_99",
        execution_receipt={"exit_code": 0, "build_time_sec": 4.2},
        verification_verdict="PASS",
        evidence_records=[]
    )
    res_pass = service.retain_observation(
        bank=MemoryBankScope.VERIFIED_EXPERIENCE,
        claim="Docker build succeeded after adding cache mount",
        source_mission="mission_build_01",
        evidence_contract=contract
    )
    assert res_pass["success"] is True
    assert res_pass["status"] == ProposalStatus.VERIFIED_EXPERIENCE.value



def test_master_authority_does_not_equal_empirical_verification():
    """
    Master authority authorizes policy/disposition mutation,
    but cannot bypass empirical verification requirement for verified experience.
    """
    service = MemoryService()

    # Master authority cannot bypass EvidenceContract for VERIFIED_EXPERIENCE
    res = service.retain_observation(
        bank=MemoryBankScope.VERIFIED_EXPERIENCE,
        claim="Tool execution succeeded on production without test run",
        source_mission="mission_prod",
        authorized_by_master=True  # Master says yes, but no evidence contract!
    )
    assert res["success"] is False
    assert "EVIDENCE_CONTRACT_REQUIRED" in res["reason"]

    # Master authority DOES allow updating MASTER_DISPOSITION
    res_master = service.retain_observation(
        bank=MemoryBankScope.MASTER_DISPOSITION,
        claim="Master mandates: Vietnamese communication in all user chats",
        source_mission="mission_policy",
        authorized_by_master=True
    )
    assert res_master["success"] is True
    assert res_master["status"] == ProposalStatus.APPROVED_OBSERVATION.value


def test_input_budget_enforcement():
    builder = ObservationBuilder()

    # Create an evidence payload that blows past the 512-token input ceiling
    huge_payload = {"records": [f"log_entry_detail_data_point_{i} " * 15 for i in range(40)]}

    with pytest.raises(MemoryBudgetExceededError, match="BLOCKED_MEMORY_BUDGET"):
        builder.create_proposal(
            target_bank=MemoryBankScope.SYSTEM_WORLD,
            claim="Subsystem port status",
            source_mission="mission_audit",
            evidence_payload=huge_payload
        )


def test_entity_and_relation_limit_enforcement():
    # Exceeding 32 entities
    excess_entities = [f"entity_{i}" for i in range(35)]
    contract_entities = EvidenceContract(
        source_mission="mission_graph",
        trace_id="tr_101",
        execution_receipt={"status": "ok"},
        verification_verdict="PASS",
        entities=excess_entities
    )
    with pytest.raises(MemoryEntityLimitExceededError, match="BLOCKED_MEMORY_ENTITY_LIMIT"):
        contract_entities.validate_bounds()

    # Exceeding 64 relations
    excess_relations = [{"from": f"e_{i}", "to": f"e_{i+1}", "rel": "link"} for i in range(70)]
    contract_relations = EvidenceContract(
        source_mission="mission_graph",
        trace_id="tr_102",
        execution_receipt={"status": "ok"},
        verification_verdict="PASS",
        relations=excess_relations
    )
    with pytest.raises(MemoryRelationLimitExceededError, match="BLOCKED_MEMORY_RELATION_LIMIT"):
        contract_relations.validate_bounds()


def test_cross_bank_evidence_leakage_blocked():
    builder = ObservationBuilder()

    # Contract attempting to reference master disposition record as evidence for verified experience
    contract_leaked = EvidenceContract(
        source_mission="mission_exploit",
        trace_id="tr_999",
        execution_receipt={"tamper": True},
        verification_verdict="PASS",
        evidence_records=["bank_master_disposition_rec_42"]
    )
    prop = builder.create_proposal(
        target_bank=MemoryBankScope.VERIFIED_EXPERIENCE,
        claim="Claim claiming master opinion as empirical proof",
        source_mission="mission_exploit",
        evidence_payload={},
        evidence_contract=contract_leaked
    )
    approved, reason = DeterministicMemorySafetyGate.verify_proposal(prop)
    assert approved is False
    assert "CROSS_BANK_LEAKAGE" in reason


def test_full_payload_hash_chaining_and_persistence_across_restarts(tmp_path):
    ledger = tmp_path / "persistent_revisions.jsonl"

    # Process Session 1
    builder1 = ObservationBuilder(ledger_file=ledger)
    obs_id = "obs_restart_test"

    rev1 = builder1.append_revision(obs_id, "Service port is 45278", provenance="RAW")
    assert rev1.revision == 1
    assert rev1.previous_hash == "0" * 16

    rev2 = builder1.append_revision(obs_id, "Service port upgraded to 45280", provenance="VERIFIED")
    assert rev2.revision == 2
    assert rev2.previous_hash == rev1.current_hash
    assert rev2.current_hash != rev1.current_hash

    # Simulate Process Restart: Process Session 2 reads the same ledger file
    builder2 = ObservationBuilder(ledger_file=ledger)
    reloaded_history = builder2.get_revisions(obs_id)
    assert len(reloaded_history) == 2
    assert reloaded_history[0].claim == "Service port is 45278"
    assert reloaded_history[1].claim == "Service port upgraded to 45280"

    # Append Revision 3 after restart: chaining must continue smoothly
    rev3 = builder2.append_revision(obs_id, "Service port pinned to 45280 permanently", provenance="VERIFIED")
    assert rev3.revision == 3
    assert rev3.previous_hash == rev2.current_hash


def test_semantic_reflect_verdicts():
    store = SovereignHindsightStore()
    service = MemoryService(store=store)

    # 1. INSUFFICIENT_EVIDENCE: empty bank
    res_empty = service.reflect(MemoryBankScope.SYSTEM_WORLD, offline_mode=True)
    assert res_empty["operation_status"] == "SUCCEEDED"
    assert res_empty["verdict"] == ReflectVerdict.INSUFFICIENT_EVIDENCE.value
    assert len(res_empty["claims"]) == 0


    # 2. SUPPORTED: retains clean verified observation
    service.retain_observation(
        bank=MemoryBankScope.SYSTEM_WORLD,
        claim="Chromium headless flag active on port 9222",
        source_mission="m_browser"
    )
    res_supported = service.reflect(MemoryBankScope.SYSTEM_WORLD, offline_mode=True)
    assert res_supported["verdict"] == ReflectVerdict.SUPPORTED.value
    assert "Chromium headless flag active on port 9222" in res_supported["claims"]

    # 3. CONFLICTED: manual injection of conflicted record
    rec = store.retain(
        bank_id=MemoryBankScope.SYSTEM_WORLD.value,
        claim="Chromium headless flag disabled on port 9222",
        source="m_browser_alt",
        confidence=0.5
    )
    # Mark conflicted directly
    rec.mark_conflicted("dummy_conflict_id")
    res_conflicted = service.reflect(MemoryBankScope.SYSTEM_WORLD, offline_mode=True)
    assert res_conflicted["verdict"] == ReflectVerdict.CONFLICTED.value
