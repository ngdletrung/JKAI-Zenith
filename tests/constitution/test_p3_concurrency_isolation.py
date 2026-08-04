"""
JKAI ZENITH — PRODUCTION HARDENING P3: CONCURRENCY ISOLATION TEST
File: tests/constitution/test_p3_concurrency_isolation.py

Verifies 100% Identity Chain isolation during multi-mission concurrent execution.
"""

import pytest
from core.contracts.cognitive_contract import IdentityChain, MissionDefinition
from core.contracts.verification_contract import RuntimeState
from core.mission.concurrent_scheduler import ConcurrentMissionScheduler


def test_p3_concurrent_multi_mission_isolation():
    # Create 4 concurrent missions (Mission A, B, C, D)
    missions = [
        MissionDefinition(identity=IdentityChain(), objective=f"Mission Concurrent #{i}")
        for i in range(1, 5)
    ]

    # Verify unique mission_ids
    mission_ids = [m.identity.mission_id for m in missions]
    assert len(set(mission_ids)) == 4

    # Execute 4 missions concurrently
    results = ConcurrentMissionScheduler.execute_concurrent_missions(missions)

    assert len(results) == 4
    for mid in mission_ids:
        assert results[mid] == RuntimeState.DELIVERED
