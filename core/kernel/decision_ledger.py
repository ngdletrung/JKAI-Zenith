# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — IMMUTABLE DECISION LEDGER v1.0                   ║
║   Chuỗi Băm Bất Biến Ghi Nhận Quyết Định Nhận Thức (Hash-Chain)   ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Tính Minh Bạch & Khả Năng Giải Trình. 📜🏛️⚡*
"""

from __future__ import annotations
import time
import json
import hashlib
import logging
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

logger = logging.getLogger("JKAI.DecisionLedger")

GENESIS_PREV_HASH = "0" * 64


@dataclass
class DecisionEntry:
    entry_id: str
    decision_type: str        # "ROUTING", "MODEL_SELECTION", "POLICY", "VERIFICATION"
    task_id: str
    input_summary: str
    output_decision: str
    reason: str
    timestamp: float = field(default_factory=time.time)
    metadata: Dict[str, Any] = field(default_factory=dict)
    prev_hash: str = GENESIS_PREV_HASH
    entry_hash: str = ""

    def compute_hash(self) -> str:
        """Tính mã băm SHA-256 bảo đảm tính toàn vẹn của chuỗi."""
        payload = f"{self.entry_id}:{self.decision_type}:{self.task_id}:{self.input_summary}:{self.output_decision}:{self.prev_hash}:{self.timestamp}"
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class ImmutableDecisionLedger:
    """
    📜 Sổ Cái Quyết Định Bất Biến (Immutable Decision Ledger)
    - Ghi nhận mọi quyết định nhận thức trong chuỗi Hash-Chain.
    - Cho phép kiểm toán pháp y (Forensic Audit) và giải trình lý do (Explainability).
    - Phát hiện bất kỳ hành vi sửa đổi lịch sử quyết định nào.
    """
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self.ledger: List[DecisionEntry] = []
        self._last_hash = GENESIS_PREV_HASH

    def record_decision(
        self,
        decision_type: str,
        task_id: str,
        input_summary: str,
        output_decision: str,
        reason: str,
        metadata: Optional[Dict[str, Any]] = None
    ) -> DecisionEntry:
        """
        Ghi nhận một quyết định mới vào chuỗi Hash-Chain.
        """
        import uuid
        entry_id = f"dec_{uuid.uuid4().hex[:12]}"
        now = time.time()
        
        entry = DecisionEntry(
            entry_id=entry_id,
            decision_type=decision_type,
            task_id=task_id,
            input_summary=input_summary,
            output_decision=output_decision,
            reason=reason,
            timestamp=now,
            metadata=metadata or {},
            prev_hash=self._last_hash
        )
        entry.entry_hash = entry.compute_hash()
        
        self.ledger.append(entry)
        self._last_hash = entry.entry_hash
        
        logger.debug(f"[DECISION-LEDGER]: Đã ghi nhận quyết định '{decision_type}' (Hash: {entry.entry_hash[:12]}).")
        return entry

    def verify_integrity(self) -> Tuple[bool, Optional[int]]:
        """
        Kiểm tra tính toàn vẹn của toàn bộ chuỗi quyết định.
        Trả về (True, None) nếu hợp lệ, (False, lỗi_tại_index) nếu phát hiện can thiệp.
        """
        expected_prev = GENESIS_PREV_HASH
        for i, entry in enumerate(self.ledger):
            if entry.prev_hash != expected_prev:
                logger.error(f"[LEDGER-INTEGRITY-FAIL]: Prev hash mismatch at index {i}.")
                return False, i
            if entry.compute_hash() != entry.entry_hash:
                logger.error(f"[LEDGER-INTEGRITY-FAIL]: Hash mutation detected at index {i}.")
                return False, i
            expected_prev = entry.entry_hash
        return True, None

    def query_decisions(
        self,
        task_id: Optional[str] = None,
        decision_type: Optional[str] = None,
        limit: int = 10
    ) -> List[DecisionEntry]:
        """Truy vấn các quyết định theo task_id hoặc loại quyết định."""
        results = self.ledger
        if task_id:
            results = [e for e in results if e.task_id == task_id]
        if decision_type:
            results = [e for e in results if e.decision_type == decision_type]
        return results[-limit:]


decision_ledger = ImmutableDecisionLedger()
