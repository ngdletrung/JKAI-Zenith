# -*- coding: utf-8 -*-
"""
tests/test_experience_store.py
Unit tests for ExperienceStore LRU cap (500) and TTL eviction.
Spec compliance:
- Insert 600 records -> count <= 500 (oldest 100 evicted)
- Expired TTL records are evicted
- Thread safety with RLock preserved
"""

import time
import pytest
from core.contracts.verification_contract import ExperienceRecord
from core.memory.experience_store import ExperienceStore


@pytest.fixture(autouse=True)
def clean_store():
    ExperienceStore.clear()
    ExperienceStore.set_ttl(86400 * 7)
    ExperienceStore.set_max_records(500)
    yield
    ExperienceStore.clear()


def test_experience_store_lru_cap_600_inserts():
    """Test inserting 600 records results in len <= 500, oldest evicted."""
    for i in range(600):
        rec = ExperienceRecord(
            task_signature=f"task_{i}",
            strategy_used=f"strategy_{i}",
            outcome="SUCCESS",
            timestamp=time.time()
        )
        ExperienceStore.add_record(rec)

    assert ExperienceStore.count() == 500
    # The oldest (0 to 99) should be evicted
    assert ExperienceStore.get_successful_strategy("task_0") is None
    assert ExperienceStore.get_successful_strategy("task_99") is None
    # The newest (599) must be present
    assert ExperienceStore.get_successful_strategy("task_599") == "strategy_599"


def test_experience_store_ttl_eviction():
    """Test that records older than TTL are evicted."""
    ExperienceStore.set_ttl(60.0)  # 60s TTL
    now = 1000.0

    # Insert an old record (timestamp 900, which is 100s ago > 60s TTL)
    old_rec = ExperienceRecord(
        task_signature="expired_task",
        strategy_used="old_strategy",
        outcome="SUCCESS",
        timestamp=900.0
    )
    ExperienceStore.add_record(old_rec, now=900.0)

    # Insert a fresh record (timestamp 990, 10s ago < 60s TTL)
    fresh_rec = ExperienceRecord(
        task_signature="fresh_task",
        strategy_used="fresh_strategy",
        outcome="SUCCESS",
        timestamp=990.0
    )
    ExperienceStore.add_record(fresh_rec, now=990.0)

    # When querying at time 1000, old_rec should be evicted
    assert ExperienceStore.get_successful_strategy("expired_task", now=now) is None
    assert ExperienceStore.get_successful_strategy("fresh_task", now=now) == "fresh_strategy"
    assert ExperienceStore.count() == 1


def test_experience_store_negative_lessons_and_retrieval():
    """Test retrieving negative lessons with outcome FAILED."""
    rec = ExperienceRecord(
        task_signature="failing_task",
        outcome="FAILED",
        negative_lessons=["Do not divide by zero", "Check bounds"],
        timestamp=time.time()
    )
    ExperienceStore.add_record(rec)

    lessons = ExperienceStore.get_negative_lessons("failing_task")
    assert "Do not divide by zero" in lessons
    assert "Check bounds" in lessons
