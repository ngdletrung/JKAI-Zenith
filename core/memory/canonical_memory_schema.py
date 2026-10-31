"""
JKAI Canonical Memory Schema, Provenance, Expiry & Conflict Detection Engine
File: core/memory/canonical_memory_schema.py

Triển khai tiêu chuẩn Phase R4 theo Cương lĩnh của Master LeeTrung:
- Schema memory chuẩn: id, claim, source, provenance, verified_by, verified_at, valid_from, valid_to, confidence, evidence_refs, scope, status.
- Phân loại Provenance: RAW, HYPOTHESIS, VERIFIED, DEPRECATED.
- Kiểm soát thời hạn hiệu lực (Freshness & Expiry).
- Phát hiện mâu thuẫn (Conflict Detection) giữa các tri thức cùng phạm vi.
- Đo lường chất lượng bộ nhớ: provenance_coverage, stale_memory_rate, contradiction_rate.
"""

import time
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field, asdict


class ProvenanceType(str, Enum):
    RAW = "RAW"                     # Dữ liệu thu thập thô, chưa qua kiểm chứng
    HYPOTHESIS = "HYPOTHESIS"       # Giả thuyết do model đề xuất
    VERIFIED = "VERIFIED"           # Tri thức đã được Verifier hoặc vật lý xác thực
    DEPRECATED = "DEPRECATED"       # Tri thức cũ, đã hết hiệu lực hoặc bị thay thế
    MASTER_AUTHORED = "MASTER_AUTHORED" # Chỉ thị / quan điểm do Master ban hành
    MASTER_APPROVED = "MASTER_APPROVED" # Đề xuất được Master phê duyệt



class MemoryStatus(str, Enum):
    ACTIVE = "ACTIVE"
    EXPIRED = "EXPIRED"
    CONFLICTED = "CONFLICTED"
    SUPERSEDED = "SUPERSEDED"


@dataclass
class CanonicalMemoryRecord:
    """Bản ghi bộ nhớ chuẩn hóa theo đặc tả của Master LeeTrung."""
    id: str
    claim: str
    source: str
    provenance: ProvenanceType
    verified_by: Optional[str] = None
    verified_at: Optional[str] = None
    valid_from: str = field(default_factory=lambda: time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()))
    valid_to: Optional[str] = None
    confidence: float = 1.0
    evidence_refs: List[str] = field(default_factory=list)
    counter_evidence_refs: List[str] = field(default_factory=list)
    scope: str = "workspace"
    status: MemoryStatus = MemoryStatus.ACTIVE

    def is_expired(self, current_time_iso: Optional[str] = None) -> bool:
        if not self.valid_to:
            return False
        now_iso = current_time_iso or time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        return now_iso > self.valid_to

    def mark_conflicted(self, counter_claim_id: str):
        self.status = MemoryStatus.CONFLICTED
        self.counter_evidence_refs.append(counter_claim_id)

    def mark_superseded(self):
        self.status = MemoryStatus.SUPERSEDED
        self.provenance = ProvenanceType.DEPRECATED

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["provenance"] = self.provenance.value
        d["status"] = self.status.value
        return d


class ConflictDetector:
    """Phát hiện mâu thuẫn tri thức giữa các bản ghi cùng phạm vi áp dụng (scope)."""
    @staticmethod
    def detect_scope_conflict(existing: CanonicalMemoryRecord, candidate: CanonicalMemoryRecord) -> bool:
        if existing.scope != candidate.scope:
            return False
        if existing.id == candidate.id:
            return False

        # Kiểm tra xung đột logic đơn giản hoặc phủ định
        claim_a = existing.claim.lower().strip()
        claim_b = candidate.claim.lower().strip()

        # Ví dụ: "X is True" vs "X is False", hoặc "not"
        is_direct_negation = (
            f"not {claim_a}" in claim_b or
            f"not {claim_b}" in claim_a or
            (claim_a.endswith("true") and claim_b.endswith("false")) or
            (claim_a.endswith("false") and claim_b.endswith("true"))
        )
        return is_direct_negation


class MemoryRetrievalFilter:
    """Bộ lọc truy xuất thông minh bảo đảm Provenance, Freshness và chống rò rỉ mâu thuẫn."""
    def __init__(self, records: Optional[List[CanonicalMemoryRecord]] = None):
        self.records: List[CanonicalMemoryRecord] = records or []

    def add_record(self, record: CanonicalMemoryRecord):
        # Kiểm tra mâu thuẫn trước khi nạp
        for existing in self.records:
            if existing.status == MemoryStatus.ACTIVE and ConflictDetector.detect_scope_conflict(existing, record):
                # Phát hiện mâu thuẫn: bản ghi có confidence thấp hơn hoặc cũ hơn bị đánh dấu CONFLICTED
                if existing.confidence >= record.confidence:
                    record.mark_conflicted(existing.id)
                else:
                    existing.mark_conflicted(record.id)
        self.records.append(record)

    def retrieve_verified(self, scope: Optional[str] = None) -> List[CanonicalMemoryRecord]:
        """Chỉ truy xuất những tri thức ACTIVE, VERIFIED và chưa hết hạn."""
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        candidates = []
        for r in self.records:
            if scope and r.scope != scope:
                continue
            if r.is_expired(now_iso):
                r.status = MemoryStatus.EXPIRED
                continue
            if r.status == MemoryStatus.ACTIVE and r.provenance == ProvenanceType.VERIFIED:
                candidates.append(r)
        return candidates

    def compute_quality_metrics(self) -> Dict[str, float]:
        """Đo lường độ tin cậy của bộ nhớ: provenance_coverage, stale_rate, contradiction_rate."""
        total = len(self.records)
        if total == 0:
            return {"total_records": 0, "provenance_coverage_pct": 0.0}

        verified_count = sum(1 for r in self.records if r.provenance == ProvenanceType.VERIFIED)
        stale_count = sum(1 for r in self.records if r.status == MemoryStatus.EXPIRED or r.provenance == ProvenanceType.DEPRECATED)
        conflicted_count = sum(1 for r in self.records if r.status == MemoryStatus.CONFLICTED)

        return {
            "total_records": float(total),
            "provenance_coverage_pct": round((verified_count / total) * 100.0, 2),
            "stale_memory_rate_pct": round((stale_count / total) * 100.0, 2),
            "contradiction_rate_pct": round((conflicted_count / total) * 100.0, 2)
        }
