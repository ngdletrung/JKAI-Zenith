"""
JKAI ZENITH — MEMORY PACKAGE: ENGRAM V2 EXPERIENCE STORE (v2.2)
File: core/memory/experience_store.py

Lưu trữ và Truy vấn Hồ sơ Trải nghiệm Engram v2 (bao gồm Trải nghiệm Thành công & Negative Memory).
[P0-INFRA N4]: Bịt rò rỉ RAM vô hạn bằng cấu trúc giới hạn dung lượng LRU (maxlen=500)
và cơ chế loại bỏ theo thời gian sống (TTL Eviction).
"""

from __future__ import annotations
import collections
import logging
import threading
import time
from typing import Deque, Dict, List, Optional

from core.contracts.verification_contract import ExperienceRecord

logger = logging.getLogger("jkai.memory.store")


class ExperienceStore:
    """Kho lưu trữ hồ sơ trải nghiệm Engram v2 có chặn trần RAM và TTL."""

    MAX_RECORDS: int = 500
    DEFAULT_TTL_SECONDS: float = 86400 * 7  # 7 days

    _lock = threading.RLock()
    _ttl_seconds: float = DEFAULT_TTL_SECONDS
    _records: Deque[ExperienceRecord] = collections.deque(maxlen=MAX_RECORDS)

    @classmethod
    def set_ttl(cls, ttl_seconds: float) -> None:
        with cls._lock:
            cls._ttl_seconds = float(ttl_seconds)

    @classmethod
    def set_max_records(cls, max_records: int) -> None:
        with cls._lock:
            cls.MAX_RECORDS = max_records
            cls._records = collections.deque(cls._records, maxlen=max_records)

    @classmethod
    def _evict_expired_locked(cls, now: Optional[float] = None) -> None:
        current_time = time.time() if now is None else now
        cutoff = current_time - cls._ttl_seconds
        # Records are appended chronologically, oldest is at left
        while cls._records:
            oldest = cls._records[0]
            rec_ts = getattr(oldest, "timestamp", current_time)
            if rec_ts < cutoff:
                cls._records.popleft()
            else:
                break

    @classmethod
    def add_record(cls, record: ExperienceRecord, now: Optional[float] = None) -> None:
        with cls._lock:
            cls._evict_expired_locked(now=now)
            cls._records.append(record)
        logger.info(f"🧠 [ENGRAM-STORE]: Stored record signature='{record.task_signature}', outcome={record.outcome} (total: {len(cls._records)})")

    @classmethod
    def get_negative_lessons(cls, task_signature: str, now: Optional[float] = None) -> List[str]:
        with cls._lock:
            cls._evict_expired_locked(now=now)
            lessons = []
            for r in cls._records:
                if r.task_signature == task_signature and r.outcome == "FAILED":
                    lessons.extend(r.negative_lessons)
            return lessons

    @classmethod
    def get_successful_strategy(cls, task_signature: str, now: Optional[float] = None) -> Optional[str]:
        with cls._lock:
            cls._evict_expired_locked(now=now)
            for r in reversed(cls._records):
                if r.task_signature == task_signature and r.outcome == "SUCCESS":
                    return r.strategy_used
            return None

    @classmethod
    def count(cls) -> int:
        with cls._lock:
            return len(cls._records)

    @classmethod
    def clear(cls) -> None:
        with cls._lock:
            cls._records.clear()
