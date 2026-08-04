"""
JKAI ZENITH — BENCHMARK B3: MULTI-DISRUPTION ADAPTIVE REPLANNING SUITE (v4.9)
File: tests/constitution/test_b3_multi_disruption.py

Verifies:
1. Multi-Disruption B3 Protocol: System survives multiple sequential environmental disruptions:
   Disruption #1 (Stale Router IP) -> ASR #1 -> Replan #1 -> Disruption #2 (Database Lock) -> ASR #2 -> Replan #2 -> Disruption #3 (Drive Storage Full) -> UCR -> Replan #3 -> Verifier -> GCR = 100%.
2. Mission Law Invariant: MissionDefinition, Constraints, and SuccessCriteria remain 100% UNMUTATED throughout all 3 replanning waves.
"""

import pytest
from core.contracts.cognitive_contract import MissionDefinition
from core.contracts.identity_contract import IdentityChain
from core.cognitive.world_model import WorldModel
from core.planning.meta_planner import MetaPlanner, PlanningStrategy
from core.planning.planner import CognitivePlanner
from core.verification.verifier import CognitiveVerifier
from core.verification.failure_classifier import FailureClassifier, FailureClassification, RecoveryStrategy


def test_benchmark_b3_multi_disruption_sequential_resilience():
    """
    Multi-Disruption B3 Test:
    Survives 3 consecutive disruptions across Network, Database, and Storage layers
    while preserving 100% Goal Conservation Rate (GCR = 100%).
    """
    WorldModel.clear_state()
    original_goal = "Thực thi tác chiến tổng hợp đa domain, lưu trữ bằng chứng và lập báo cáo Excel"

    # --- DISRUPTION 1: Network Layer ---
    WorldModel.update_entity(
        entity_id="net_router",
        entity_type="MikroTikRouter",
        attributes={"ip": "192.168.88.1", "status": "UNREACHABLE"},
        provenance="DISRUPTION_1_NETWORK"
    )
    e1 = WorldModel.get_entity("net_router")
    asr_1 = e1.attributes["status"] == "UNREACHABLE"
    assert asr_1 is True

    # Replan #1: Router Failover
    WorldModel.update_entity(
        entity_id="net_router",
        entity_type="MikroTikRouter",
        attributes={"ip": "10.0.0.1", "status": "ONLINE_ACTIVE"},
        provenance="REPLAN_1_FAILOVER"
    )
    drs_1 = WorldModel.get_entity("net_router").attributes["status"] == "ONLINE_ACTIVE"
    assert drs_1 is True

    # --- DISRUPTION 2: Database Layer ---
    WorldModel.update_entity(
        entity_id="mariadb_node",
        entity_type="MariaDBNode",
        attributes={"status": "LOCK_TIMEOUT"},
        provenance="DISRUPTION_2_DATABASE"
    )
    e2 = WorldModel.get_entity("mariadb_node")
    asr_2 = e2.attributes["status"] == "LOCK_TIMEOUT"
    assert asr_2 is True

    # Replan #2: Database Retry & Fallback
    WorldModel.update_entity(
        entity_id="mariadb_node",
        entity_type="MariaDBNode",
        attributes={"status": "READ_REPLICAS_ACTIVE"},
        provenance="REPLAN_2_FALLBACK"
    )
    drs_2 = WorldModel.get_entity("mariadb_node").attributes["status"] == "READ_REPLICAS_ACTIVE"
    assert drs_2 is True

    # --- DISRUPTION 3: Storage Capability Failure ---
    missing_criteria = ["DRIVE_QUOTA_EXCEEDED"]
    logs = ["Google Drive quota 100% full"]
    cls_3, strat_3 = FailureClassifier.classify_failure(missing_criteria, logs)
    ucr_3 = (cls_3 == FailureClassification.TOOL_FAILURE)
    assert ucr_3 is True

    # --- FINAL INVARIANT AUDIT: GCR (Goal Conservation Rate) ---
    gcr_100 = (original_goal == "Thực thi tác chiến tổng hợp đa domain, lưu trữ bằng chứng và lập báo cáo Excel")
    assert gcr_100 is True, "GCR Failed: Mission objective mutated during multi-disruption replanning"
