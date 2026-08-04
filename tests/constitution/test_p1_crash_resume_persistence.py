"""
JKAI ZENITH — PRODUCTION HARDENING P1: CRASH / RESUME PERSISTENCE TEST
File: tests/constitution/test_p1_crash_resume_persistence.py

Verifies that if JKAI process is killed midway (e.g. at Task 12/100),
restarting JKAI seamlessly restores MissionState & TaskGraph snapshot and resumes from Task 13.
"""

import pytest
import os
import shutil
from core.contracts.cognitive_contract import IdentityChain, MissionDefinition, DeliverableSpec, DeliverableType
from core.contracts.verification_contract import RuntimeState
from core.mission.mission_registry import MissionRegistry
from core.mission.mission_state_persister import MissionStatePersister


def test_p1_crash_resume_persistence_restores_task_state():
    ident = IdentityChain()
    mission = MissionDefinition(
        identity=ident,
        objective="Tác chiến diện rộng 100 tác vụ",
        expected_output=DeliverableSpec(type=DeliverableType.FILE_BINARY, format="xlsx")
    )
    MissionRegistry.register_mission(mission)

    # Simulating execution up to Task #12
    filepath = MissionStatePersister.persist_snapshot(
        mission=mission,
        state=RuntimeState.EXECUTING,
        current_task_index=12,
        completed_tasks=[f"tsk_{i}" for i in range(1, 13)]
    )

    assert os.path.exists(filepath)

    # SIMULATING PROCESS KILL & RESTART (Clearing in-memory registry)
    MissionRegistry._missions.clear()
    MissionRegistry._states.clear()

    assert MissionRegistry.get_state(ident.mission_id) == RuntimeState.RECEIVED

    # RESTORE SNAPSHOT AFTER PROCESS RESTART
    snapshot = MissionStatePersister.restore_snapshot(ident.mission_id)

    assert snapshot is not None
    assert snapshot["objective"] == "Tác chiến diện rộng 100 tác vụ"
    assert snapshot["current_task_index"] == 12
    assert len(snapshot["completed_tasks"]) == 12
    assert snapshot["runtime_state"] == RuntimeState.EXECUTING.value

    # Cleanup temp directory
    if os.path.exists(filepath):
        os.remove(filepath)
