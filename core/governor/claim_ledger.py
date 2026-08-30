# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — DEMS v1.0: EVIDENCE & CLAIM LEDGER               ║
│   Hồ Sơ Nhận Thức & Phân Xử Mệnh Đề Đa Chiều (Claim Ledger)     │
╚══════════════════════════════════════════════════════════════════╝
Tuân thủ 7 Bất biến DEMS:
  I-DEMS-02: Evidence Provenance (Truy nguyên chính xác về trace_id)
  I-DEMS-03: Claim ≠ Belief (Claim không tự động thành Belief)
  I-DEMS-04: No Silent Resolution (Tranh chấp CONTESTED không tự chọn)
  I-DEMS-05: Unknown Is Valid (Trạng thái UNKNOWN là hợp lệ)
  I-DEMS-06: LLM Has No Authority (Model inference không tự nâng cấp)
"""

from __future__ import annotations
import time
import uuid
import json
import sqlite3
import os
import logging
from enum import Enum
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple

logger = logging.getLogger("JKAI.DEMS.ClaimLedger")

DEFAULT_CLAIM_DB_PATH = "intelligence/claim_ledger.db"


class ClaimStatus(str, Enum):
    ACTIVE = "ACTIVE"          # Bằng chứng rõ ràng, hợp lệ để nạp vào Context
    CONTESTED = "CONTESTED"    # Có mâu thuẫn ngang quyền, bắt buộc phải kiểm chứng
    SUPERSEDED = "SUPERSEDED"  # Đã bị thay thế bởi quan sát mới có căn cứ xác thực
    UNKNOWN = "UNKNOWN"        # Chưa có quan sát thực tế (không cho phép LLM bịa)


class ClaimScope(str, Enum):
    RUNTIME = "RUNTIME"
    STATIC_CONFIG = "STATIC_CONFIG"
    USER_PREFERENCE = "USER_PREFERENCE"
    SYSTEM_POLICY = "SYSTEM_POLICY"
    GENERAL = "GENERAL"


@dataclass
class EvidenceItem:
    evidence_id: str
    trace_id: str              # I-DEMS-02: Provenance liên kết ngược về RawTrace gốc
    source_type: str           # "tool_stdout", "file_content", "user_prompt", "model_infer"
    provenance: str            # File path, command signature
    scope: ClaimScope
    timestamp: float
    verification_hash: str
    payload: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClaimItem:
    claim_id: str
    subject: str
    predicate: str
    object_val: str
    scope: ClaimScope
    evidence_refs: List[str]   # Danh sách evidence_id bảo chứng
    authority_level: int       # 1 (Model Inference) -> 4 (Runtime Tool)
    freshness: float           # Timestamp lúc claim được tạo
    directness: float          # 1.0 (Direct) vs 0.5 (Indirect/Graph)
    verification_score: float  # 1.0 nếu có exit code 0 / schema match
    applicability: float = 1.0 # 0.0 -> 1.0 (Mission/Task Relevance)
    status: ClaimStatus = ClaimStatus.UNKNOWN
    superseded_by: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def calculate_score(
        self,
        current_time: Optional[float] = None,
        scope_target: Optional[ClaimScope] = None,
        mission_applicability: Optional[float] = None
    ) -> float:
        """
        6-Factor Evidence & Claim Arbitration Signal (DEMS Standard):
        - Authority (Nguồn uy quyền)
        - Freshness (Độ tươi mới theo thời gian)
        - Scope Match (Khớp phạm vi nhận thức)
        - Directness (Độ trực tiếp quan sát)
        - Verification (Đã qua kiểm chứng kỹ thuật)
        - Applicability (Độ phù hợp mục tiêu nhiệm vụ - Mission Relevance)
        """
        now = current_time or time.time()
        # 1. Authority (Chuẩn hóa về 0.0 - 1.0)
        auth_norm = min(1.0, max(0.2, self.authority_level / 4.0))

        # 2. Freshness decay
        age_hours = max(0.0, (now - self.freshness) / 3600.0)
        fresh_score = max(0.1, 1.0 / (1.0 + 0.05 * age_hours))

        # 3. Scope match
        scope_match = 1.0 if (scope_target is None or self.scope == scope_target) else 0.4

        # 4. Directness
        direct_score = self.directness

        # 5. Verification
        verif_score = self.verification_score

        # 6. Applicability / Relevance to Mission (P0 DEMS Improvement)
        app_score = self.applicability if mission_applicability is None else mission_applicability

        # Trọng số 6 chiều DEMS Chuẩn hóa (Applicability là bộ lọc phân loại quyết định)
        total_score = (
            0.20 * auth_norm +
            0.20 * fresh_score +
            0.25 * app_score +
            0.15 * scope_match +
            0.10 * direct_score +
            0.10 * verif_score
        )
        return round(total_score, 4)


class ClaimLedger:
    """
    📜 Quản Trị Mệnh Đề & Phân Xử Xung Đột (Claim Ledger)
    - Quản lý các mệnh đề (Subject, Predicate, Object, Scope).
    - Cùng tồn tại đa chiều, ghi nhận cả các khẳng định đối lập.
    - Phân xử tranh chấp xác định:
        * Khác cấp Authority: Cấp cao hơn $\rightarrow$ ACTIVE, cấp thấp hơn $\rightarrow$ SUPERSEDED.
        * Cùng cấp Authority: Mâu thuẫn $\rightarrow$ Cả hai chuyển thành CONTESTED (I-DEMS-04).
    """
    def __init__(self, db_path: str = DEFAULT_CLAIM_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        self._init_db()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, timeout=30.0)
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA synchronous=NORMAL")
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS evidence_records (
                    evidence_id TEXT PRIMARY KEY,
                    trace_id TEXT NOT NULL,
                    source_type TEXT NOT NULL,
                    provenance TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    verification_hash TEXT NOT NULL,
                    payload_json TEXT NOT NULL
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS claims (
                    claim_id TEXT PRIMARY KEY,
                    subject TEXT NOT NULL,
                    predicate TEXT NOT NULL,
                    object_val TEXT NOT NULL,
                    scope TEXT NOT NULL,
                    evidence_refs_json TEXT NOT NULL,
                    authority_level INTEGER NOT NULL,
                    freshness REAL NOT NULL,
                    directness REAL NOT NULL,
                    verification_score REAL NOT NULL,
                    status TEXT NOT NULL,
                    superseded_by TEXT,
                    created_at REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_claims_subj_pred ON claims(subject, predicate)")
            conn.execute("CREATE INDEX IF NOT EXISTS idx_claims_status ON claims(status)")

    def add_evidence(self, evidence: EvidenceItem) -> None:
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO evidence_records (
                    evidence_id, trace_id, source_type, provenance,
                    scope, timestamp, verification_hash, payload_json
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                evidence.evidence_id, evidence.trace_id, evidence.source_type, evidence.provenance,
                evidence.scope.value if isinstance(evidence.scope, ClaimScope) else str(evidence.scope),
                evidence.timestamp, evidence.verification_hash, json.dumps(evidence.payload, ensure_ascii=False)
            ))

    def register_claim(
        self,
        subject: str,
        predicate: str,
        object_val: str,
        scope: ClaimScope,
        evidence_id: str,
        authority_level: int,
        directness: float = 1.0,
        verification_score: float = 1.0
    ) -> ClaimItem:
        """
        Đăng ký một Claim mới và kích hoạt thuật toán phân xử xác định (Deterministic Arbitration).
        """
        now = time.time()
        c_id = f"clm_{uuid.uuid4().hex[:12]}"
        subj_clean = subject.strip().lower()
        pred_clean = predicate.strip().lower()
        obj_clean = object_val.strip()

        new_claim = ClaimItem(
            claim_id=c_id,
            subject=subj_clean,
            predicate=pred_clean,
            object_val=obj_clean,
            scope=scope,
            evidence_refs=[evidence_id],
            authority_level=authority_level,
            freshness=now,
            directness=directness,
            verification_score=verification_score,
            status=ClaimStatus.ACTIVE,
            created_at=now
        )

        # Kiểm tra xung đột với các Claim hiện có cùng (subject, predicate, scope)
        existing_claims = self.get_claims_by_predicate(subj_clean, pred_clean, scope)

        with self._get_connection() as conn:
            for old_claim in existing_claims:
                if old_claim.status in (ClaimStatus.SUPERSEDED, ClaimStatus.UNKNOWN):
                    continue

                if old_claim.object_val == new_claim.object_val:
                    # Cùng giá trị -> Bổ sung evidence ref và tăng độ tin cậy
                    if evidence_id not in old_claim.evidence_refs:
                        old_claim.evidence_refs.append(evidence_id)
                        old_claim.freshness = now
                        old_claim.authority_level = max(old_claim.authority_level, new_claim.authority_level)
                        self._update_claim(conn, old_claim)
                    return old_claim
                else:
                    # MÂU THUẪN (Khác object_val)
                    if new_claim.authority_level > old_claim.authority_level:
                        # Claim mới có uy quyền cao hơn -> Cũ bị SUPERSEDED
                        old_claim.status = ClaimStatus.SUPERSEDED
                        old_claim.superseded_by = new_claim.claim_id
                        self._update_claim(conn, old_claim)
                        new_claim.status = ClaimStatus.ACTIVE
                    elif new_claim.authority_level < old_claim.authority_level:
                        # Claim mới có uy quyền thấp hơn -> Mới bị SUPERSEDED bởi cũ
                        new_claim.status = ClaimStatus.SUPERSEDED
                        new_claim.superseded_by = old_claim.claim_id
                    else:
                        # CÙNG CẤP UY QUYỀN (I-DEMS-04: No Silent Resolution) -> Cả hai chuyển thành CONTESTED
                        old_claim.status = ClaimStatus.CONTESTED
                        new_claim.status = ClaimStatus.CONTESTED
                        self._update_claim(conn, old_claim)

            # Lưu Claim mới vào DB
            conn.execute("""
                INSERT INTO claims (
                    claim_id, subject, predicate, object_val, scope,
                    evidence_refs_json, authority_level, freshness,
                    directness, verification_score, status, superseded_by, created_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                new_claim.claim_id, new_claim.subject, new_claim.predicate, new_claim.object_val,
                new_claim.scope.value if isinstance(new_claim.scope, ClaimScope) else str(new_claim.scope),
                json.dumps(new_claim.evidence_refs), new_claim.authority_level, new_claim.freshness,
                new_claim.directness, new_claim.verification_score, new_claim.status.value,
                new_claim.superseded_by, new_claim.created_at
            ))

        return new_claim

    def get_claims_by_predicate(self, subject: str, predicate: str, scope: Optional[ClaimScope] = None) -> List[ClaimItem]:
        subj_clean = subject.strip().lower()
        pred_clean = predicate.strip().lower()
        with self._get_connection() as conn:
            if scope:
                scope_val = scope.value if isinstance(scope, ClaimScope) else str(scope)
                rows = conn.execute("""
                    SELECT claim_id, subject, predicate, object_val, scope,
                           evidence_refs_json, authority_level, freshness,
                           directness, verification_score, status, superseded_by, created_at
                    FROM claims WHERE subject = ? AND predicate = ? AND scope = ?
                """, (subj_clean, pred_clean, scope_val)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT claim_id, subject, predicate, object_val, scope,
                           evidence_refs_json, authority_level, freshness,
                           directness, verification_score, status, superseded_by, created_at
                    FROM claims WHERE subject = ? AND predicate = ?
                """, (subj_clean, pred_clean)).fetchall()
            return [self._row_to_claim(r) for r in rows]

    def get_active_claims(self, subject: Optional[str] = None) -> List[ClaimItem]:
        with self._get_connection() as conn:
            if subject:
                rows = conn.execute("""
                    SELECT claim_id, subject, predicate, object_val, scope,
                           evidence_refs_json, authority_level, freshness,
                           directness, verification_score, status, superseded_by, created_at
                    FROM claims WHERE subject = ? AND status = 'ACTIVE'
                """, (subject.strip().lower(),)).fetchall()
            else:
                rows = conn.execute("""
                    SELECT claim_id, subject, predicate, object_val, scope,
                           evidence_refs_json, authority_level, freshness,
                           directness, verification_score, status, superseded_by, created_at
                    FROM claims WHERE status = 'ACTIVE'
                """).fetchall()
            return [self._row_to_claim(r) for r in rows]

    def _update_claim(self, conn: sqlite3.Connection, claim: ClaimItem):
        conn.execute("""
            UPDATE claims SET
                evidence_refs_json = ?,
                authority_level = ?,
                freshness = ?,
                status = ?,
                superseded_by = ?
            WHERE claim_id = ?
        """, (
            json.dumps(claim.evidence_refs), claim.authority_level, claim.freshness,
            claim.status.value if isinstance(claim.status, ClaimStatus) else str(claim.status),
            claim.superseded_by, claim.claim_id
        ))

    def _row_to_claim(self, row: tuple) -> ClaimItem:
        return ClaimItem(
            claim_id=row[0],
            subject=row[1],
            predicate=row[2],
            object_val=row[3],
            scope=ClaimScope(row[4]) if row[4] in ClaimScope._value2member_map_ else ClaimScope.GENERAL,
            evidence_refs=json.loads(row[5]),
            authority_level=row[6],
            freshness=row[7],
            directness=row[8],
            verification_score=row[9],
            status=ClaimStatus(row[10]),
            superseded_by=row[11],
            created_at=row[12]
        )


claim_ledger = ClaimLedger()
