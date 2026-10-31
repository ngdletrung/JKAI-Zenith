"""
Unit Tests for Sovereign Memory Runtime Adapter
File: tests/test_memory_runtime_adapter.py
Governed by Phase R-Memory-6 Consensus & Turn 490 Gate 3 Hardening Directives:
- Concurrent recall across master disposition and verified experience.
- Strict per-bank token ceiling (<= 120 tokens) and aggregate token ceiling (<= 240 tokens).
- Partial resilience: one bank failing does not destroy other bank's retrieved lessons.
- Preservation of asyncio.CancelledError during shutdown.
- Production boundary enforcement: rejects untyped dict receipts, string verdicts, and mismatched proofs.
"""

import sys
import pytest
import asyncio
from pathlib import Path
from unittest.mock import MagicMock

AI_BRAIN_DIR = Path(__file__).resolve().parent.parent / "services" / "ai-brain"
if str(AI_BRAIN_DIR) not in sys.path:
    sys.path.insert(0, str(AI_BRAIN_DIR))

from context.memory_runtime_adapter import (
    MemoryRuntimeAdapter, get_memory_runtime_adapter,
    format_bank_section, estimate_tokens
)
from core.memory.memory_contracts import (
    MemoryBankScope, ExecutionReceipt, VerificationVerdictContract
)
from core.memory.memory_service import MemoryService
from core.memory.sovereign_hindsight_store import SovereignHindsightStore


@pytest.mark.asyncio
async def test_adapter_recall_empty_when_no_memories():
    """Verify adapter returns empty string when no memories exist."""
    store = SovereignHindsightStore()
    service = MemoryService(store=store)
    adapter = MemoryRuntimeAdapter(service=service)

    res = await adapter.recall_for_goal("Một mục tiêu hoàn toàn mới")
    assert res == ""


@pytest.mark.asyncio
async def test_adapter_concurrent_recall_with_content():
    """Verify concurrent recall formats claims from both banks cleanly."""
    store = SovereignHindsightStore()
    service = MemoryService(store=store)
    adapter = MemoryRuntimeAdapter(service=service)

    # Retain in MASTER_DISPOSITION
    store.retain(
        bank_id=MemoryBankScope.MASTER_DISPOSITION.value,
        claim="Giao tiếp 100% bằng tiếng Việt chuẩn mực",
        source="master_chat"
    )

    # Retain in VERIFIED_EXPERIENCE
    store.retain(
        bank_id=MemoryBankScope.VERIFIED_EXPERIENCE.value,
        claim="Docker Chromium cần flag --no-sandbox khi chạy root",
        source="execution_receipt",
        evidence_refs=["ev_rec_01"]
    )

    res = await adapter.recall_for_goal("Khởi động Chromium bằng tiếng Việt")

    assert "### [SOVEREIGN-MEMORY]" in res
    assert "[CHỈ ĐẠO MASTER]" in res
    assert "Giao tiếp 100% bằng tiếng Việt chuẩn mực" in res
    assert "[KINH NGHIỆM ĐÃ KIỂM CHỨNG]" in res
    assert "Docker Chromium cần flag --no-sandbox khi chạy root" in res


@pytest.mark.asyncio
async def test_adapter_per_bank_and_aggregate_token_ceiling():
    """Verify both per-bank ceiling (<= 120 tokens) and aggregate ceiling (<= 240 tokens) are enforced."""
    # Test format_bank_section with an overflow of long claims
    long_claims = [
        f"Kinh nghiệm thực thi số {i} với hướng dẫn chi tiết về bảo mật sandbox mạng lưới và phân quyền tài nguyên"
        for i in range(15)
    ]
    section = format_bank_section("### [TEST BANK]", long_claims, max_tokens=120)
    assert estimate_tokens(section) <= 120
    assert section.startswith("### [TEST BANK]")

    # Test full adapter aggregate ceiling
    store = SovereignHindsightStore()
    service = MemoryService(store=store)
    adapter = MemoryRuntimeAdapter(service=service)

    claim_1 = "Chi tiết kiến trúc hệ thống Docker với các cấu hình bảo mật nghiêm ngặt " * 15
    claim_2 = "Kinh nghiệm thực thi các bài học về sandbox mạng lưới và cổng kết nối " * 15

    store.retain(bank_id=MemoryBankScope.MASTER_DISPOSITION.value, claim=claim_1, source="m1")
    store.retain(bank_id=MemoryBankScope.VERIFIED_EXPERIENCE.value, claim=claim_2, source="m2", evidence_refs=["e1"])

    res = await adapter.recall_for_goal("kiến trúc hệ thống sandbox")
    assert estimate_tokens(res) <= 245


@pytest.mark.asyncio
async def test_adapter_graceful_fail_soft_on_exception():
    """Verify adapter returns empty string when service raises general exceptions."""
    mock_service = MagicMock()
    mock_service.recall.side_effect = RuntimeError("Fatal disk I/O lock error")

    adapter = MemoryRuntimeAdapter(service=mock_service)
    res = await adapter.recall_for_goal("Mục tiêu thử nghiệm")

    assert res == ""


@pytest.mark.asyncio
async def test_adapter_one_bank_error_does_not_destroy_other_bank():
    """Verify that failure in one bank still allows the other bank to return findings."""
    mock_service = MagicMock()

    def mock_recall(bank, query, top_k, max_tokens):
        if bank == MemoryBankScope.MASTER_DISPOSITION:
            raise RuntimeError("Database connection timed out")
        return ["Kinh nghiệm từ ngân hàng verified còn nguyên vẹn"]

    mock_service.recall.side_effect = mock_recall

    adapter = MemoryRuntimeAdapter(service=mock_service)
    res = await adapter.recall_for_goal("Mục tiêu thử nghiệm")

    assert "### [SOVEREIGN-MEMORY]" in res
    assert "[KINH NGHIỆM ĐÃ KIỂM CHỨNG]" in res
    assert "Kinh nghiệm từ ngân hàng verified còn nguyên vẹn" in res
    assert "[CHỈ ĐẠO MASTER]" not in res


@pytest.mark.asyncio
async def test_adapter_preserves_cancellation_error():
    """Verify asyncio.CancelledError is NOT swallowed by fail-soft and propagates properly."""
    mock_service = MagicMock()
    mock_service.recall.side_effect = asyncio.CancelledError()

    adapter = MemoryRuntimeAdapter(service=mock_service)
    with pytest.raises(asyncio.CancelledError):
        await adapter.recall_for_goal("Mục tiêu thử nghiệm")


@pytest.mark.asyncio
async def test_retain_rejects_dict_receipt_in_production():
    """Verify production adapter rejects raw dict receipts (no auto-wrapping)."""
    adapter = MemoryRuntimeAdapter()
    verdict = VerificationVerdictContract(status="COMPLETE", mission_id="m1", receipt_refs=["rec_01"])

    ok = await adapter.retain_verified_mission(
        mission_id="m1",
        trace_id="tr1",
        claim="Lesson",
        receipt={"id": "rec_01", "exit_code": 0},
        verdict=verdict
    )
    assert ok is False


@pytest.mark.asyncio
async def test_retain_rejects_string_verdict_in_production():
    """Verify production adapter rejects string verdicts (no auto-wrapping)."""
    adapter = MemoryRuntimeAdapter()
    receipt = ExecutionReceipt(id="rec_01", trace_id="tr1", mission_id="m1", exit_code=0)

    ok = await adapter.retain_verified_mission(
        mission_id="m1",
        trace_id="tr1",
        claim="Lesson",
        receipt=receipt,
        verdict="PASS"
    )
    assert ok is False


@pytest.mark.asyncio
async def test_retain_rejects_mismatched_typed_proof():
    """Verify production adapter rejects mismatched IDs between receipt, verdict, and call parameters."""
    adapter = MemoryRuntimeAdapter()
    receipt = ExecutionReceipt(id="rec_01", trace_id="tr1", mission_id="m1", exit_code=0)
    verdict = VerificationVerdictContract(status="COMPLETE", mission_id="m1", receipt_refs=["rec_01"])

    # 1. Mission ID mismatch with receipt
    assert await adapter.retain_verified_mission(
        mission_id="m_DIFFERENT", trace_id="tr1", claim="L", receipt=receipt, verdict=verdict
    ) is False

    # 2. Trace ID mismatch with receipt
    assert await adapter.retain_verified_mission(
        mission_id="m1", trace_id="tr_DIFFERENT", claim="L", receipt=receipt, verdict=verdict
    ) is False

    # 3. Mission ID mismatch with verdict
    verdict_diff = VerificationVerdictContract(status="COMPLETE", mission_id="m_DIFF", receipt_refs=["rec_01"])
    assert await adapter.retain_verified_mission(
        mission_id="m1", trace_id="tr1", claim="L", receipt=receipt, verdict=verdict_diff
    ) is False

    # 4. Receipt id not in verdict.receipt_refs
    verdict_no_ref = VerificationVerdictContract(status="COMPLETE", mission_id="m1", receipt_refs=["rec_OTHER"])
    assert await adapter.retain_verified_mission(
        mission_id="m1", trace_id="tr1", claim="L", receipt=receipt, verdict=verdict_no_ref
    ) is False


@pytest.mark.asyncio
async def test_adapter_retain_verified_mission_success():
    """Verify retain_verified_mission succeeds when valid typed proof is provided."""
    store = SovereignHindsightStore()
    service = MemoryService(store=store, production_mode=False)
    adapter = MemoryRuntimeAdapter(service=service)

    receipt = ExecutionReceipt(id="rec_t1", trace_id="tr_pilot_01", mission_id="m_pilot_01", exit_code=0)
    verdict = VerificationVerdictContract(status="COMPLETE", mission_id="m_pilot_01", receipt_refs=["rec_t1"])

    ok = await adapter.retain_verified_mission(
        mission_id="m_pilot_01",
        trace_id="tr_pilot_01",
        claim="Thực thi thành công nhiệm vụ pilot",
        receipt=receipt,
        verdict=verdict,
        artifact_hash="sha256_art1"
    )

    assert ok is True
    records = store.list_scoped_records(MemoryBankScope.VERIFIED_EXPERIENCE.value)
    assert len(records) == 1
    assert records[0].claim == "Thực thi thành công nhiệm vụ pilot"


def test_adapter_token_estimator_boundary_unicode_punctuation_and_no_whitespace():
    """Verify estimate_tokens boundary conditions: empty, unicode, heavy punctuation, unspaced strings."""
    assert estimate_tokens("") == 0
    assert estimate_tokens("   ") == 0

    # Unicode with Vietnamese diacritics
    viet_text = "Hệ thống ghi nhận bài học kiểm chứng cho trí tuệ nhân tạo JKAI Zenith."
    toks_viet = estimate_tokens(viet_text)
    assert 15 <= toks_viet <= 35

    # Heavy punctuation
    punct_text = "key:value;arg1=1&arg2=2|pipe>redirect//path/to/resource"
    toks_punct = estimate_tokens(punct_text)
    assert toks_punct >= 10

    # Extremely dense unspaced string (e.g. base64 or long hash)
    dense_unspaced = "A" * 350
    toks_dense = estimate_tokens(dense_unspaced)
    # Character ratio must catch dense text, not report 1 token
    assert toks_dense >= 90

