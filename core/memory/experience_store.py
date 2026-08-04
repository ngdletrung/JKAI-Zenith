"""
JKAI ZENITH — MEMORY PACKAGE: ENGRAM V2 EXPERIENCE STORE (v2.1)
File: core/memory/experience_store.py

Lưu trữ và Truy vấn Hồ sơ Trải nghiệm Engram v2 (bao gồm Trải nghiệm Thành công & Negative Memory).
"""

from __future__ import annotations
import logging
import threading
from typing import Dict, List, Optional

from core.contracts.verification_contract import ExperienceRecord

logger = logging.getLogger("jkai.memory.store")


class ExperienceStore:
    """Kho lưu trữ hồ sơ trải nghiệm Engram v2."""

    _lock = threading.RLock()
    _records: List[ExperienceRecord] = []

    @classmethod
    def add_record(cls, record: ExperienceRecord) -> None:
        with cls._lock:
            cls._records.append(record)
        logger.info(f"🧠 [ENGRAM-STORE]: Stored record signature='{record.task_signature}', outcome={record.outcome}")

    @classmethod
    def get_negative_lessons(cls, task_signature: str) -> List[str]:
        with cls._lock:
            lessons = []
            for r in cls._records:
                if r.task_signature == task_signature and r.outcome == "FAILED":
                    lessons.extend(r.negative_lessons)
            return lessons

    @classmethod
    def get_successful_strategy(cls, task_signature: str) -> Optional[str]:
        with cls._lock:
            for r in reversed(cls._records):
                if r.task_signature == task_signature and r.outcome == "SUCCESS":
                    return r.strategy_used
            return None
