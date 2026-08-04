"""
JKAI ZENITH v3 — GATE C ADAPTATION BENCHMARK TEST SUITE
File: tests/constitution/test_gate_c_v3_adaptive_cognition.py

Verifies 3 core v3 pillars: World Model, Meta-Planner, and Causal Experience Learning.
"""

import pytest
from core.cognitive.universal_cognition import UniversalCognitionCortex
from core.cognitive.world_model import WorldModel
from core.planning.meta_planner import MetaPlanner, PlanningStrategy
from core.memory.causal_engine import CausalExperienceEngine
from core.contracts.verification_contract import VerificationResult


def test_v3_world_model_state_persistence_across_missions():
    WorldModel.clear_state()

    # Mission A updates contract entity
    WorldModel.update_entity(
        entity_id="contract_001",
        entity_type="Contract",
        attributes={"status": "EXPIRED", "priority": "HIGH"},
        provenance="MISSION_A"
    )

    # Mission B queries contract_001 from World Model
    entity = WorldModel.get_entity("contract_001")
    assert entity is not None
    assert entity.attributes["status"] == "EXPIRED"
    assert entity.attributes["priority"] == "HIGH"
    assert entity.provenance == "MISSION_A"


def test_v3_meta_planner_strategy_selection():
    # Test high-risk goal -> HUMAN_APPROVAL_REQUIRED
    req_high_risk = UniversalCognitionCortex.perceive("Hãy xóa toàn bộ file hệ thống")
    decision_risk = MetaPlanner.select_strategy(req_high_risk)
    assert decision_risk.strategy == PlanningStrategy.HUMAN_APPROVAL_REQUIRED

    # Test artifact deliverable goal -> DECOMPOSE_DAG
    req_artifact = UniversalCognitionCortex.perceive("Tạo file Excel báo cáo tiến độ chi tiết")
    decision_artifact = MetaPlanner.select_strategy(req_artifact)
    assert decision_artifact.strategy == PlanningStrategy.DECOMPOSE_DAG


def test_v3_causal_experience_learning_evidence_only():
    task_sig = "BUILD_ARTIFACT_xlsx"
    ver_pass = VerificationResult(passed=True)

    hyp = CausalExperienceEngine.distill_causal_hypothesis(
        task_signature=task_sig,
        verification=ver_pass,
        strategy_used="openpyxl_writer"
    )

    assert hyp.recommended_strategy == "openpyxl_writer"
    assert hyp.is_evidence_only is True  # EVIDENCE, NOT TRUTH!
    assert "openpyxl_writer" in hyp.causal_explanation
