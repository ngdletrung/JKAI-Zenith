"""
tests/test_cognitive_execution_substrate_suite.py
Comprehensive 10-Question Substrate Verification Suite for JKAI Zenith.

Verifies the 10 Backstage Layers and the 3 Unified Fabrics:
1. Capability Fabric (Registry, Graph, Gap Detection, Composition)
2. Knowledge Fabric (Need Planner, Source Strategy, EASG)
3. Semantic Execution Fabric (Requirement Compiler, ESCL, Adaptive Solver, Truth Normalizer, Mission Ledger)
"""

import os
import tempfile
import pytest
from core.os.cognition.capability_fabric.capability_registry import capability_registry
from core.os.cognition.capability_fabric.gap_resolver import capability_gap_resolver
from core.os.cognition.capability_fabric.models import CapabilityCategory
from core.os.cognition.knowledge_fabric.knowledge_need_planner import (
    KnowledgeDomain,
    knowledge_need_planner,
)
from core.os.cognition.knowledge_fabric.source_strategy import source_selection_strategy
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec
from core.os.cognition.adaptive_solver.execution_truth_normalizer import execution_truth_normalizer
from core.os.cognition.adaptive_solver.adaptive_solver_engine import adaptive_solver_engine
from core.os.cognition.adaptive_solver.models import (
    ArtifactOutcome,
    RequirementStatus,
    StrategyDecision,
    ToolOutcome,
)
from core.os.cognition.mission_observability.mission_ledger import mission_ledger


class TestCognitiveExecutionSubstrateSuite:

    # ─────────────────────────────────────────────────────────────
    # VECTOR 1: Q1 & Q2 - Requirement Compiler Generates Verifiable Criteria
    # ─────────────────────────────────────────────────────────────
    def test_01_q1_q2_requirement_compiler_generates_verifiable_criteria(self):
        """Vector 1: Compiles natural language goal into machine-verifiable requirements."""
        goal = "Tạo cho tôi 1 file excel để quản lý công việc và theo dõi tiến độ của 5 người trong 1 phòng, phong cách văn phòng có biểu đồ theo dõi rõ ràng"
        mission = CanonicalMissionSpec.compile_from_text(goal, mission_id="m_sub_01")

        assert mission.mission_id == "m_sub_01"
        assert len(mission.success_criteria) >= 3
        crit_descs = " ".join([sc.description.lower() for sc in mission.success_criteria])
        assert "5" in crit_descs or "người" in crit_descs
        assert "biểu đồ" in crit_descs or "chart" in crit_descs

    # ─────────────────────────────────────────────────────────────
    # VECTOR 2: Q3 - Knowledge Need Planner Formulates Explicit Needs
    # ─────────────────────────────────────────────────────────────
    def test_02_q3_knowledge_need_planner_isolates_noise(self):
        """Vector 2: HR query produces INTERNAL_REGULATION and blocks generic internet noise."""
        mission = CanonicalMissionSpec.compile_from_text("Lập quy trình phê duyệt nghỉ phép cho phòng Kỹ thuật", mission_id="m_sub_02")
        need = knowledge_need_planner.plan_needs(mission)

        assert need.target_domain == KnowledgeDomain.INTERNAL_REGULATION
        assert need.requires_internal_authority is True
        assert any("Generic Internet" in p for p in need.prohibited_noise)

    # ─────────────────────────────────────────────────────────────
    # VECTOR 3: Q4 & Q5 - Source Strategy & EASG Gateway Binding
    # ─────────────────────────────────────────────────────────────
    def test_03_q4_q5_source_strategy_and_easg_filtering(self):
        """Vector 3: Maps KnowledgeNeed to authoritative source channels."""
        mission = CanonicalMissionSpec.compile_from_text("Tra cứu API Microsoft Graph mới nhất", mission_id="m_sub_03")
        need = knowledge_need_planner.plan_needs(mission)
        channels = source_selection_strategy.select_channels(need)

        assert need.target_domain == KnowledgeDomain.OFFICIAL_DOCS
        assert len(channels) >= 2
        assert channels[0].channel_name == "official_vendor_docs"

    # ─────────────────────────────────────────────────────────────
    # VECTOR 4: Q6 - Capability Fabric Registry & Prerequisites
    # ─────────────────────────────────────────────────────────────
    def test_04_q6_capability_fabric_registry_prerequisites(self):
        """Vector 4: Verifies capability boundaries and prerequisite checking."""
        cap = capability_registry.get("xlsx.create_and_chart")
        assert cap is not None
        assert "create_xlsx" in cap.can_do
        assert "charts" in cap.can_do
        assert "read_sharepoint" in cap.cannot_do
        assert "openpyxl" in cap.requires_prerequisites

        missing = capability_registry.check_prerequisites("xlsx.create_and_chart")
        assert isinstance(missing, list)

    # ─────────────────────────────────────────────────────────────
    # VECTOR 5: Q7 - Capability Gap Resolver Detects & Composes
    # ─────────────────────────────────────────────────────────────
    def test_05_q7_capability_gap_resolver_detects_and_composes(self):
        """Vector 5: Detects missing actions and produces composition recipes."""
        required = ["create_xlsx", "charts", "custom_exotic_action_xyz"]
        matched, gaps = capability_gap_resolver.analyze_requirements(required)

        assert len(matched) >= 1
        assert any(g.missing_capability == "custom_exotic_action_xyz" for g in gaps)
        
        chart_gap = next((g for g in gaps if "chart" in g.missing_capability), None)
        if chart_gap and chart_gap.resolvable_by_composition:
            comp = capability_gap_resolver.compose_solution(chart_gap)
            assert comp is not None
            assert "PYTHON_OPENPYXL" in comp.composition_strategy

    # ─────────────────────────────────────────────────────────────
    # VECTOR 6: Q8 - ESCL Typed Invocation Contract
    # ─────────────────────────────────────────────────────────────
    def test_06_q8_escl_typed_contract_invocation(self):
        """Vector 6: Validates typed tool execution contract."""
        from core.kernel.tool_contracts import canonicalize, get_contract
        contract = get_contract("grep_search")
        assert contract is not None
        
        # Test alias canonicalization: pattern -> query
        name, canonical_kws, issues = canonicalize("grep_search", {"pattern": "def foo", "path": "/tmp"})
        assert canonical_kws.get("query") == "def foo"
        assert len(issues) == 0

    # ─────────────────────────────────────────────────────────────
    # VECTOR 7: Q9 - Execution Truth Distinguishes Multi-Level Outcomes
    # ─────────────────────────────────────────────────────────────
    def test_07_q9_execution_truth_normalizer_distinguishes_outcomes(self):
        """Vector 7: Proves ToolOutcome != ArtifactOutcome != RequirementOutcome."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name
            # 0 bytes blank file

        try:
            mission = CanonicalMissionSpec.compile_from_text("Tạo bảng tính Excel 5 người có biểu đồ", mission_id="m_sub_07")
            raw_res = {"status": "success", "file_path": tmp_path}
            
            truth = execution_truth_normalizer.normalize(
                invocation_id="inv_sub_07",
                tool_name="OFFICE_SUITE_MASTER",
                arguments={"file_path": tmp_path},
                raw_result=raw_res,
                mission=mission
            )

            # Tool technically succeeded, BUT artifact is corrupted (0 bytes) and genuine success is False!
            assert truth.tool_outcome == ToolOutcome.SUCCEEDED
            assert truth.artifact_outcome == ArtifactOutcome.CORRUPTED
            assert truth.is_genuine_success is False
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ─────────────────────────────────────────────────────────────
    # VECTOR 8: Q10 - Mission Observability Ledger Audits All 10 Questions
    # ─────────────────────────────────────────────────────────────
    def test_08_q10_mission_ledger_answers_all_10_questions(self):
        """Vector 8: Verifies full causal trace in Mission Ledger answering all 10 questions."""
        mission = CanonicalMissionSpec.compile_from_text("Tạo file Excel 5 người có biểu đồ", mission_id="m_sub_08")
        rec = mission_ledger.create_record(mission)

        need = knowledge_need_planner.plan_needs(mission)
        mission_ledger.record_knowledge_planning(mission.mission_id, need, ["official_vendor_docs"])
        mission_ledger.record_capabilities(mission.mission_id, [capability_registry.get("xlsx.create_and_chart")], {"req_0": "xlsx.create_and_chart"})

        truth = execution_truth_normalizer.normalize(
            invocation_id="inv_sub_08",
            tool_name="OFFICE_SUITE_MASTER",
            arguments={"file_path": "test.xlsx"},
            raw_result={"status": "error", "error": "Disk full"},
            mission=mission
        )
        mission_ledger.record_execution_truth(mission.mission_id, truth)
        mission_ledger.finalize_record(mission.mission_id, is_proven=False, proof_details="Failed on tool error")

        audit_json = mission_ledger.export_audit_json(mission.mission_id)
        assert "q1_master_intent" in audit_json
        assert "q3_knowledge_need" in audit_json
        assert "q6_available_capabilities" in audit_json
        assert "q9_execution_truths" in audit_json
        assert "q10_is_proven_completed" in audit_json

    # ─────────────────────────────────────────────────────────────
    # VECTOR 9: Closed-Loop Feedback Triggers Targeted Repair
    # ─────────────────────────────────────────────────────────────
    def test_09_closed_loop_feedback_replan_on_incomplete_requirements(self):
        """Vector 9: When chart is missing from workbook, solver triggers TARGETED_REPAIR."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Tasks"
            ws["A1"] = "Task"
            wb.save(tmp_path) # Valid file without chart

            mission = CanonicalMissionSpec.compile_from_text("Tạo bảng tính Excel 5 người có biểu đồ", mission_id="m_sub_09")
            truth = execution_truth_normalizer.normalize("inv_09", "OFFICE_SUITE_MASTER", {"file_path": tmp_path}, {"status": "success"}, mission)
            
            from core.os.cognition.adaptive_solver.situation_model import situation_assessor
            situation = situation_assessor.initialize_situation(mission)

            adaptation = adaptive_solver_engine.evaluate_and_adapt(mission, situation, truth)
            assert adaptation.decision == StrategyDecision.TARGETED_REPAIR
            assert "Targeted repair needed" in adaptation.replan_instructions
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ─────────────────────────────────────────────────────────────
    # VECTOR 10: End-to-End Autonomous Excel Mission with Proof
    # ─────────────────────────────────────────────────────────────
    def test_10_end_to_end_autonomous_excel_mission(self):
        """Vector 10: Complete simulated autonomous mission ending in genuine proof."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            import openpyxl
            from openpyxl.chart import BarChart, Reference
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "ProgressTracker"
            ws.append(["Staff", "Progress%"])
            for i in range(5):
                ws.append([f"Staff_{i+1}", 20 * (i+1)])
            
            chart = BarChart()
            data = Reference(ws, min_col=2, min_row=1, max_row=6)
            chart.add_data(data, titles_from_data=True)
            ws.add_chart(chart, "E2")
            wb.save(tmp_path)

            mission = CanonicalMissionSpec.compile_from_text("Tạo bảng tính Excel 5 người có biểu đồ", mission_id="m_sub_10")
            truth = execution_truth_normalizer.normalize("inv_10", "OFFICE_SUITE_MASTER", {"file_path": tmp_path}, {"status": "success"}, mission)

            assert truth.is_genuine_success is True

            from core.os.cognition.adaptive_solver.situation_model import situation_assessor
            situation = situation_assessor.initialize_situation(mission)
            adaptation = adaptive_solver_engine.evaluate_and_adapt(mission, situation, truth)

            assert adaptation.decision == StrategyDecision.TERMINATE_WITH_PROOF
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)
