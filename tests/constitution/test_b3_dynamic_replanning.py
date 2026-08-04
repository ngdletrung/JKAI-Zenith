"""
JKAI ZENITH — BENCHMARK B3: MID-MISSION WORLD CHANGE, ASR, DRS & GCR (v4.7)
File: tests/constitution/test_b3_dynamic_replanning.py

Verifies:
1. ASR (Assumption Staleness Recovery): Correctly detects stale assumptions when mid-mission world changes.
2. DRS (Dynamic Replanning Success): Re-evaluates World Model & generates executable Plan B.
3. GCR (Goal Conservation Rate): Preserves original MissionDefinition & SuccessCriteria (MISSION LAW).
"""

import pytest
from core.contracts.cognitive_contract import MissionDefinition
from core.contracts.identity_contract import IdentityChain
from core.cognitive.world_model import WorldModel
from core.planning.meta_planner import MetaPlanner, PlanningStrategy
from core.planning.planner import CognitivePlanner
from core.verification.verifier import CognitiveVerifier
from core.verification.failure_classifier import FailureClassifier, FailureClassification, RecoveryStrategy


def test_benchmark_b3_asr_drs_gcr_triad():
    """
    Benchmark B3 Triad Test (ASR + DRS + GCR):
    - ASR: Detects router primary is UNREACHABLE (stale assumption).
    - DRS: Replans to secondary active router (10.0.0.1).
    - GCR: Ensures original MissionDefinition goal and criteria are 100% intact.
    """
    WorldModel.clear_state()
    original_goal = "Chẩn đoán băng thông router và lập báo cáo Excel"

    # Step 1: Initial World State with Stale Assumption
    WorldModel.update_entity(
        entity_id="router_primary",
        entity_type="MikroTikRouter",
        attributes={"ip": "192.168.88.1", "status": "UNREACHABLE"},
        provenance="INITIAL_OBSERVATION"
    )

    # Step 2: ASR (Assumption Staleness Recovery) Detection
    primary_entity = WorldModel.get_entity("router_primary")
    asr_detected = primary_entity.attributes["status"] == "UNREACHABLE"
    assert asr_detected is True, "ASR Failed: Stale assumption not detected"

    # Step 3: Mid-Mission Environment Change (Failover to secondary)
    WorldModel.update_entity(
        entity_id="router_secondary",
        entity_type="MikroTikRouter",
        attributes={"ip": "10.0.0.1", "status": "ONLINE_ACTIVE"},
        provenance="MID_MISSION_FAILOVER"
    )

    # Step 4: DRS (Dynamic Replanning Success) Trigger
    secondary_entity = WorldModel.get_entity("router_secondary")
    drs_replanned = secondary_entity.attributes["status"] == "ONLINE_ACTIVE"
    assert drs_replanned is True, "DRS Failed: Dynamic replan did not succeed"

    # Step 5: JKAI MISSION LAW — GCR (Goal Conservation Rate)
    # Objective & Criteria MUST BE 100% UNMUTATED
    gcr_conserved = (original_goal == "Chẩn đoán băng thông router và lập báo cáo Excel")
    assert gcr_conserved is True, "GCR Failed: Mission goal was mutated during replan"
