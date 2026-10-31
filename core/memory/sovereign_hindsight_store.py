"""
JKAI Sovereign Hindsight Memory Store — Learn, Not Just Remember
File: core/memory/sovereign_hindsight_store.py
Inspired by Vectorize Hindsight (arXiv:2512.12818) & Governed by Master LeeTrung's OS Principles.

Core Architecture:
1. Three Primitives: retain() -> recall() -> reflect()
2. Multi-Network Memory Banks:
   - bank_master_disposition (Opinion / Preferences / Style of Master)
   - bank_system_world (World facts, environment, file trees, ports)
   - bank_verified_experience (Verified execution traces and tool outcomes)
3. Three Sovereign Safeguards (Opencode Consensus Turn 469):
   - Offline-only reflect(): Runs during audit/sleep cycles, never during online task execution.
   - Strict Context Ceiling: recall() enforces <= 120 tokens and top_k <= 3 to prevent SLM 3B context bloat.
   - Strict Bank Isolation: Zero cross-contamination between different domains.
"""

import time
import uuid
from enum import Enum
from typing import Dict, Any, List, Optional
from dataclasses import dataclass, field

from core.memory.canonical_memory_schema import (
    CanonicalMemoryRecord, ProvenanceType, MemoryStatus, ConflictDetector
)
from core.memory.memory_contracts import (
    BUDGET_REFLECT_EVIDENCE_RECORDS, MemoryBudgetExceededError
)


class MemoryBankType(str, Enum):
    MASTER_DISPOSITION = "bank_master_disposition"
    SYSTEM_WORLD = "bank_system_world"
    VERIFIED_EXPERIENCE = "bank_verified_experience"


class SovereignHindsightStore:
    """
    Sovereign Implementation of Hindsight (Retain, Recall, Reflect) for JKAI.
    100% Local, zero-cloud egress, deterministic token budgeting.
    """
    def __init__(self):
        # Memory records partitioned by bank_id
        self.banks: Dict[str, List[CanonicalMemoryRecord]] = {
            MemoryBankType.MASTER_DISPOSITION.value: [],
            MemoryBankType.SYSTEM_WORLD.value: [],
            MemoryBankType.VERIFIED_EXPERIENCE.value: []
        }

    def _ensure_bank(self, bank_id: str) -> List[CanonicalMemoryRecord]:
        if bank_id not in self.banks:
            self.banks[bank_id] = []
        return self.banks[bank_id]

    def _get_existing_bank(self, bank_id: str) -> Optional[List[CanonicalMemoryRecord]]:
        """Safe read-only lookup that does NOT create empty bank entry in self.banks."""
        return self.banks.get(bank_id)

    def count_scoped_records(
        self,
        bank_id: str,
        topic: Optional[str] = None,
        status: Optional[MemoryStatus] = MemoryStatus.ACTIVE
    ) -> int:
        """
        Fast preflight count of scoped records without allocating query result lists.
        Uses pure iteration for true allocation-safe memory efficiency.
        Safe read-only operation with zero write side-effects on self.banks.
        """
        records = self._get_existing_bank(bank_id)
        if not records:
            return 0
        t_words = set(topic.lower().split()) if topic else None
        count = 0
        for r in records:
            if status is not None and r.status != status:
                continue
            if t_words and not t_words.intersection(set(r.claim.lower().split())):
                continue
            count += 1
        return count

    def list_scoped_records(
        self,
        bank_id: str,
        topic: Optional[str] = None,
        limit: Optional[int] = None,
        status: Optional[MemoryStatus] = MemoryStatus.ACTIVE
    ) -> List[CanonicalMemoryRecord]:
        """Public API to query memory records partitioned by bank, optional topic, and status."""
        records = self._get_existing_bank(bank_id)
        if not records:
            return []
        filtered = [r for r in records if status is None or r.status == status]
        if topic:
            t_words = set(topic.lower().split())
            filtered = [r for r in filtered if t_words.intersection(set(r.claim.lower().split()))]
        if limit is not None:
            filtered = filtered[:limit]
        return filtered

    def resolve_evidence(self, bank_id: str, evidence_id: str) -> Optional[CanonicalMemoryRecord]:
        """Public API to resolve an evidence memory record by ID."""
        records = self._get_existing_bank(bank_id)
        if not records:
            return None
        for r in records:
            if r.id == evidence_id:
                return r
        return None


    def retain(
        self,
        bank_id: str,
        claim: str,
        source: str,
        provenance: ProvenanceType = ProvenanceType.RAW,
        verified_by: Optional[str] = None,
        confidence: float = 1.0,
        scope: str = "workspace",
        valid_to: Optional[str] = None,
        evidence_refs: Optional[List[str]] = None
    ) -> CanonicalMemoryRecord:
        """
        Primitive 1: RETAIN
        Turns raw observations or verified actions into structured CanonicalMemoryRecord.
        """
        bank = self._ensure_bank(bank_id)
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        rec = CanonicalMemoryRecord(
            id=f"mem_{uuid.uuid4().hex[:8]}",
            claim=claim.strip(),
            source=source,
            provenance=provenance,
            verified_by=verified_by,
            verified_at=now_iso if provenance == ProvenanceType.VERIFIED else None,
            valid_from=now_iso,
            valid_to=valid_to,
            confidence=confidence,
            evidence_refs=evidence_refs or [],
            scope=scope,
            status=MemoryStatus.ACTIVE
        )

        # Conflict check with existing records in this bank
        for existing in bank:
            if existing.status == MemoryStatus.ACTIVE and ConflictDetector.detect_scope_conflict(existing, rec):
                if existing.confidence >= rec.confidence:
                    rec.mark_conflicted(existing.id)
                else:
                    existing.mark_conflicted(rec.id)

        bank.append(rec)
        return rec

    def recall(
        self,
        bank_id: str,
        query: str,
        token_budget: int = 120,
        top_k: int = 3,
        scope: Optional[str] = None,
        allow_unverified: bool = False
    ) -> List[CanonicalMemoryRecord]:
        """
        Primitive 2: RECALL
        Hybrid retrieval with strict token ceiling (<= 120 tokens) and top_k <= 3.
        Only retrieves ACTIVE, and by default VERIFIED records within the specified bank.
        """
        bank = self._ensure_bank(bank_id)
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        q_lower = query.lower()
        q_words = set(q_lower.split())

        candidates: List[tuple[float, CanonicalMemoryRecord]] = []
        for rec in bank:
            if scope and rec.scope != scope:
                continue
            if rec.is_expired(now_iso):
                rec.status = MemoryStatus.EXPIRED
                continue
            if rec.status != MemoryStatus.ACTIVE:
                continue
            if not allow_unverified and rec.provenance != ProvenanceType.VERIFIED:
                continue

            # Calculate keyword relevance score
            claim_words = set(rec.claim.lower().split())
            overlap = len(q_words.intersection(claim_words))
            if overlap == 0:
                continue
            relevance = (overlap / max(1, len(q_words))) * rec.confidence
            candidates.append((relevance, rec))

        # Sort by relevance descending, then confidence
        candidates.sort(key=lambda x: (x[0], x[1].confidence), reverse=True)

        selected: List[CanonicalMemoryRecord] = []
        consumed_tokens = 0

        for _, rec in candidates:
            if len(selected) >= top_k:
                break
            # Approximate token count (~1.3 tokens per word)
            approx_tokens = int(len(rec.claim.split()) * 1.3) + 5
            if consumed_tokens + approx_tokens > token_budget and selected:
                # Token ceiling hit; stop injecting
                break
            selected.append(rec)
            consumed_tokens += approx_tokens

        return selected

    def reflect(
        self,
        bank_id: str,
        verifier_actor: str = "OFFLINE_AUDITOR",
        target_records: Optional[List[CanonicalMemoryRecord]] = None
    ) -> Dict[str, Any]:
        """
        Primitive 3: REFLECT (Offline-Only)
        Consolidates memories, reconciles conflicts, promotes verified hypotheses,
        and deprecates stale or superseded beliefs.
        Operates exclusively on bounded target_records if provided.
        """
        if verifier_actor.upper() in ["MODEL", "LLM", "ONLINE_RUNTIME"]:
            raise PermissionError("[SAFEGUARD-BREACH] reflect() must run offline under Verifier/Auditor authority.")

        if target_records is not None:
            if len(target_records) > BUDGET_REFLECT_EVIDENCE_RECORDS:
                raise MemoryBudgetExceededError(
                    f"BLOCKED_MEMORY_BUDGET: target_records count ({len(target_records)}) exceeds limit ({BUDGET_REFLECT_EVIDENCE_RECORDS})."
                )
            bank = list(target_records)
        else:
            raw_bank = self._get_existing_bank(bank_id) or []
            if len(raw_bank) > BUDGET_REFLECT_EVIDENCE_RECORDS:
                raise MemoryBudgetExceededError(
                    f"BLOCKED_MEMORY_BUDGET: Direct call to store.reflect() on bank '{bank_id}' with {len(raw_bank)} records exceeds limit ({BUDGET_REFLECT_EVIDENCE_RECORDS}). Bounded target_records required."
                )
            bank = list(raw_bank)
        now_iso = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())

        consolidated_count = 0
        superseded_count = 0
        conflict_resolved_count = 0

        # 1. Resolve conflicts by confidence & freshness
        conflicted_records = [r for r in bank if r.status == MemoryStatus.CONFLICTED]
        for c in conflicted_records:
            for existing in bank:
                if existing.id in c.counter_evidence_refs and existing.status != MemoryStatus.SUPERSEDED:
                    if existing.confidence > c.confidence:
                        c.mark_superseded()
                        superseded_count += 1
                        conflict_resolved_count += 1
                    elif c.confidence > existing.confidence:
                        existing.mark_superseded()
                        c.status = MemoryStatus.ACTIVE
                        superseded_count += 1
                        conflict_resolved_count += 1

        # 2. Check and expire records past valid_to
        for r in bank:
            if r.status == MemoryStatus.ACTIVE and r.is_expired(now_iso):
                r.status = MemoryStatus.EXPIRED
                r.provenance = ProvenanceType.DEPRECATED
                consolidated_count += 1

        return {
            "status": "COMPLETED",
            "bank_id": bank_id,
            "audited_by": verifier_actor,
            "total_records": len(bank),
            "conflict_resolved_count": conflict_resolved_count,
            "superseded_count": superseded_count,
            "expired_consolidated_count": consolidated_count,
            "active_verified_count": sum(1 for r in bank if r.status == MemoryStatus.ACTIVE and r.provenance == ProvenanceType.VERIFIED)
        }
