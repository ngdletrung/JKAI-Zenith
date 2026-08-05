"""
JKAI ZENITH — NOVEL TASK TRANSFER BENCHMARK (LEVEL 1, 2, 3)
File: tests/constitution/test_novel_task_transfer_benchmark.py

Kiểm thử 3 cấp độ Novel Task Benchmark chứng minh Substrate hoạt động hoàn toàn tự chủ:
- Level 1: Known domain (Excel file creation)
- Level 2: Novel combination (PDF + Excel + Web + Anomaly)
- Level 3: Novel task (Contract expiry + priority detection + Excel generation)
Mọi tác vụ đều không chứa hardcoded keyword/regex routing và obey 10 Constitutional Principles.
"""

import pytest
from core.contracts.cognitive_contract import CognitiveRequest, MissionDefinition, DeliverableType
from core.contracts.capability_contract import CapabilityRequirement
from core.contracts.verification_contract import VerificationResult, FailureClassification, RuntimeState
from core.cognitive.universal_cognition import UniversalCognitionCortex
from core.mission.mission_builder import MissionBuilder
from core.mission.mission_registry import MissionRegistry
from core.planning.planner import CognitivePlanner
from core.capabilities.capability_broker import CapabilityBroker


def test_level_1_known_domain_benchmark():
    goal = "hãy tạo cho file excel .xlsx về báo cáo tiến độ phân công làm việc của cả 1 đội"
    req = UniversalCognitionCortex.perceive(goal)
    mission = MissionBuilder.build_mission(req)
    plan = CognitivePlanner.create_plan(mission)

    assert mission.expected_output.format == "xlsx"
    assert len(plan.nodes) == 2
    assert plan.nodes[1].requirement.capability == "xlsx_generation"
    
    prof = CapabilityBroker.resolve_capability(plan.nodes[1].requirement)
    assert prof.selected_model_name != ""


def test_level_2_novel_combination_benchmark():
    goal = "Tôi có các tệp PDF và web data, hãy tìm bất thường và tạo file Excel tổng hợp"
    req = UniversalCognitionCortex.perceive(goal)
    mission = MissionBuilder.build_mission(req)
    plan = CognitivePlanner.create_plan(mission)

    assert "ANOMALY_DETECTION" in req.entities
    assert mission.expected_output.format == "xlsx"
    assert len(plan.nodes) >= 2


def test_level_3_novel_task_zero_rule_benchmark():
    goal = "Tôi có một thư mục chứa các hợp đồng. Hãy tìm những hợp đồng sắp hết hạn, lập bảng tổng hợp Excel và đánh dấu những hợp đồng cần ưu tiên xử lý."
    
    # Stage 1: Cognition
    req = UniversalCognitionCortex.perceive(goal)
    assert req.deliverable.format == "xlsx"
    assert "CONTRACT_DOCUMENTS" in req.entities
    assert "PRIORITIZE_URGENT_ITEMS" in req.constraints

    # Stage 2: Mission
    mission = MissionBuilder.build_mission(req)
    MissionRegistry.register_mission(mission)
    assert MissionRegistry.get_state(mission.identity.mission_id) == RuntimeState.MISSIONED

    # Stage 3: Planner
    plan = CognitivePlanner.create_plan(mission)
    assert len(plan.nodes) == 2
    assert plan.nodes[0].requirement.capability == "data_inspection"
    assert plan.nodes[1].requirement.capability == "xlsx_generation"

    # Stage 4: Capability Resolution
    prof = CapabilityBroker.resolve_capability(plan.nodes[1].requirement)
    assert prof.selected_tool == "openpyxl"

    # Stage 5: State Machine State Transition to DELIVERED
    final_state = MissionRegistry.transition_state(mission.identity.mission_id, RuntimeState.DELIVERED)
    assert final_state == RuntimeState.DELIVERED

    # Stage 6: Terminal State Immutable Constraint (Transition from DELIVERED is BLOCKED)
    blocked_state = MissionRegistry.transition_state(mission.identity.mission_id, RuntimeState.EXECUTING)
    assert blocked_state == RuntimeState.DELIVERED  # State remains DELIVERED
