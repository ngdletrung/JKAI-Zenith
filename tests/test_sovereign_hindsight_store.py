"""
Unit Tests for Sovereign Hindsight Memory Store (Retain, Recall, Reflect)
File: tests/test_sovereign_hindsight_store.py
"""

import pytest
from core.memory.canonical_memory_schema import ProvenanceType, MemoryStatus
from core.memory.sovereign_hindsight_store import (
    SovereignHindsightStore, MemoryBankType
)


def test_retain_and_bank_isolation():
    store = SovereignHindsightStore()

    # Retain in bank_master_disposition
    r1 = store.retain(
        bank_id=MemoryBankType.MASTER_DISPOSITION.value,
        claim="Master LeeTrung yêu cầu giao tiếp tiếng Việt chuẩn mực.",
        source="master_chat",
        provenance=ProvenanceType.VERIFIED,
        confidence=1.0
    )
    assert r1.status == MemoryStatus.ACTIVE
    assert r1.provenance == ProvenanceType.VERIFIED

    # Retain in bank_system_world
    r2 = store.retain(
        bank_id=MemoryBankType.SYSTEM_WORLD.value,
        claim="Cụm AI Executor lắng nghe tại cổng 8000.",
        source="docker_compose",
        provenance=ProvenanceType.VERIFIED,
        confidence=0.9
    )

    # Verify strict bank isolation: recalling master disposition cannot see system world
    recalled_master = store.recall(
        bank_id=MemoryBankType.MASTER_DISPOSITION.value,
        query="cổng 8000"
    )
    assert len(recalled_master) == 0

    recalled_system = store.recall(
        bank_id=MemoryBankType.SYSTEM_WORLD.value,
        query="cổng 8000"
    )
    assert len(recalled_system) == 1
    assert recalled_system[0].id == r2.id


def test_recall_token_ceiling_and_provenance_filter():
    store = SovereignHindsightStore()
    bank_id = MemoryBankType.VERIFIED_EXPERIENCE.value

    # 1. Add RAW record (should be ignored by recall)
    store.retain(
        bank_id=bank_id,
        claim="Chạy tool bash thất bại không rõ nguyên nhân",
        source="raw_log",
        provenance=ProvenanceType.RAW
    )

    # 2. Add VERIFIED record
    v1 = store.retain(
        bank_id=bank_id,
        claim="Tool BROWSER_CONTROL cần URL hợp lệ để chụp ảnh màn hình.",
        source="execution_receipt",
        provenance=ProvenanceType.VERIFIED,
        confidence=0.95
    )

    # 3. Add long VERIFIED record to test token ceiling
    v2 = store.retain(
        bank_id=bank_id,
        claim="Khi lập trình web cần chú ý các cổng kết nối và không dùng lệnh in print rác để thay thế mã nguồn thực thụ.",
        source="post_mortem",
        provenance=ProvenanceType.VERIFIED,
        confidence=0.90
    )

    results = store.recall(bank_id=bank_id, query="chụp ảnh màn hình BROWSER_CONTROL", token_budget=60, top_k=2)
    assert len(results) >= 1
    assert all(r.provenance == ProvenanceType.VERIFIED for r in results)
    assert v1.id in [r.id for r in results]


def test_reflect_offline_safeguard_and_conflict_resolution():
    store = SovereignHindsightStore()
    bank_id = MemoryBankType.SYSTEM_WORLD.value

    # Rule 1: reflect cannot be executed by MODEL
    with pytest.raises(PermissionError) as exc_info:
        store.reflect(bank_id=bank_id, verifier_actor="MODEL")
    assert "[SAFEGUARD-BREACH]" in str(exc_info.value)

    # Rule 2: Conflict resolution during reflect
    r_old = store.retain(
        bank_id=bank_id,
        claim="Docker port 8000 is True",
        source="old_config",
        provenance=ProvenanceType.VERIFIED,
        confidence=0.7,
        scope="port_binding"
    )

    r_new = store.retain(
        bank_id=bank_id,
        claim="Docker port 8000 is False",
        source="new_config",
        provenance=ProvenanceType.VERIFIED,
        confidence=0.95,
        scope="port_binding"
    )

    # One of them should be marked conflicted upon retain
    assert r_old.status == MemoryStatus.CONFLICTED or r_new.status == MemoryStatus.CONFLICTED

    # Execute offline reflect by OFFLINE_AUDITOR
    audit_res = store.reflect(bank_id=bank_id, verifier_actor="OFFLINE_AUDITOR")
    assert audit_res["conflict_resolved_count"] == 1
    assert r_old.status == MemoryStatus.SUPERSEDED
    assert r_new.status == MemoryStatus.ACTIVE
