"""
Unit Tests for Phase R4: Canonical Memory Schema, Provenance, Expiry & Conflict Detection
File: tests/test_canonical_memory_schema.py
"""

import pytest
import time
from core.memory.canonical_memory_schema import (
    ProvenanceType,
    MemoryStatus,
    CanonicalMemoryRecord,
    ConflictDetector,
    MemoryRetrievalFilter
)


def test_canonical_memory_record_initialization():
    """Bảo đảm Record chứa đầy đủ 12 trường dữ liệu theo Cương lĩnh của Master."""
    rec = CanonicalMemoryRecord(
        id="mem-001",
        claim="Postgres chạy tại port 5432 trên mạng ai-network",
        source="docker-compose.yml",
        provenance=ProvenanceType.VERIFIED,
        verified_by="PHYSICAL_PORT_PROBE",
        verified_at="2026-10-18T10:00:00Z",
        valid_from="2026-10-18T10:00:00Z",
        valid_to="2026-12-31T23:59:59Z",
        confidence=0.98,
        evidence_refs=["receipt_123"],
        scope="network_infrastructure",
        status=MemoryStatus.ACTIVE
    )
    d = rec.to_dict()
    assert d["id"] == "mem-001"
    assert d["provenance"] == "VERIFIED"
    assert d["confidence"] == 0.98
    assert d["verified_by"] == "PHYSICAL_PORT_PROBE"
    assert d["status"] == "ACTIVE"


def test_memory_expiry_check():
    """Bảo đảm cơ chế kiểm tra hết hạn (Freshness & Expiry)."""
    rec_active = CanonicalMemoryRecord(
        id="mem-002",
        claim="API token tạm thời",
        source="vault",
        provenance=ProvenanceType.VERIFIED,
        valid_to="2099-01-01T00:00:00Z"
    )
    assert rec_active.is_expired() is False

    rec_expired = CanonicalMemoryRecord(
        id="mem-003",
        claim="Phiên đăng nhập cũ",
        source="session_cache",
        provenance=ProvenanceType.VERIFIED,
        valid_to="2020-01-01T00:00:00Z"
    )
    assert rec_expired.is_expired() is True


def test_conflict_detection_and_marking():
    """Bảo đảm phát hiện mâu thuẫn giữa 2 tri thức cùng phạm vi."""
    rec1 = CanonicalMemoryRecord(
        id="mem-004",
        claim="VRAM RX 6600 limit is 8192 MB",
        source="gpu_spec",
        provenance=ProvenanceType.VERIFIED,
        confidence=0.95,
        scope="hardware"
    )
    rec2 = CanonicalMemoryRecord(
        id="mem-005",
        claim="not VRAM RX 6600 limit is 8192 MB",
        source="unverified_forum",
        provenance=ProvenanceType.HYPOTHESIS,
        confidence=0.30,
        scope="hardware"
    )

    filter_engine = MemoryRetrievalFilter()
    filter_engine.add_record(rec1)
    filter_engine.add_record(rec2)

    # Bản ghi rec2 có confidence thấp hơn bị đánh dấu CONFLICTED
    assert rec2.status == MemoryStatus.CONFLICTED
    assert rec1.id in rec2.counter_evidence_refs
    assert rec1.status == MemoryStatus.ACTIVE


def test_memory_retrieval_filter_drops_deprecated_and_unverified():
    """Bộ lọc chỉ trả về tri thức VERIFIED và ACTIVE, loại bỏ RAW, HYPOTHESIS, EXPIRED."""
    r_verified = CanonicalMemoryRecord(
        id="mem-101",
        claim="Đường dẫn lưu ảnh chụp là /workspace/eye_*.png",
        source="browser_actuator",
        provenance=ProvenanceType.VERIFIED
    )
    r_raw = CanonicalMemoryRecord(
        id="mem-102",
        claim="Có thể dùng tool xyz",
        source="user_chat",
        provenance=ProvenanceType.RAW
    )
    r_expired = CanonicalMemoryRecord(
        id="mem-103",
        claim="Dữ liệu năm ngoái",
        source="old_db",
        provenance=ProvenanceType.VERIFIED,
        valid_to="2021-01-01T00:00:00Z"
    )

    filter_engine = MemoryRetrievalFilter([r_verified, r_raw, r_expired])
    verified_results = filter_engine.retrieve_verified()

    assert len(verified_results) == 1
    assert verified_results[0].id == "mem-101"


def test_memory_quality_metrics_calculation():
    """Đo lường độ bao phủ Provenance, tỷ lệ tri thức cũ và tỷ lệ mâu thuẫn."""
    r1 = CanonicalMemoryRecord(id="m1", claim="c1", source="s1", provenance=ProvenanceType.VERIFIED)
    r2 = CanonicalMemoryRecord(id="m2", claim="c2", source="s2", provenance=ProvenanceType.VERIFIED)
    r3 = CanonicalMemoryRecord(id="m3", claim="c3", source="s3", provenance=ProvenanceType.RAW)
    r4 = CanonicalMemoryRecord(id="m4", claim="c4", source="s4", provenance=ProvenanceType.DEPRECATED, status=MemoryStatus.EXPIRED)

    filter_engine = MemoryRetrievalFilter([r1, r2, r3, r4])
    metrics = filter_engine.compute_quality_metrics()

    assert metrics["total_records"] == 4.0
    assert metrics["provenance_coverage_pct"] == 50.0  # 2/4
    assert metrics["stale_memory_rate_pct"] == 25.0    # 1/4
