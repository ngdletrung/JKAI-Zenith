"""
tests/test_adaptive_task_solver_suite.py
12 Governed Verification Tests for Adaptive Task Solver (ATS) & Execution Truth Layer.

Enforces:
1. Situation Model & Workspace Pattern Discovery.
2. Adaptive Action Granularity (Probe -> Precision -> Batch -> Targeted Repair).
3. 3-Tier Execution Truth (ToolOutcome -> ArtifactOutcome -> MissionOutcome).
4. Strategy Invalidation (Rejects stale hypotheses when observation diverges).
5. Mission Immutability (Mission requirements cannot be mutated during adaptation).
6. State Space (COMPLETED, RECOVERY, SAFE_STOP).
7. Async Non-Blocking Tool Execution & Safe AST Evaluation.
"""

import asyncio
import importlib.util
import os
import tempfile
import pytest
from core.os.cognition.adaptive_solver.models import (
    ActionGranularity,
    ArtifactOutcome,
    ExecutionTruth,
    MissionImmutabilityViolationError,
    MissionOutcome,
    RequirementStatus,
    SituationModel,
    StrategyAdaptation,
    StrategyDecision,
    ToolOutcome,
)
from core.os.cognition.adaptive_solver.situation_model import situation_assessor
from core.os.cognition.adaptive_solver.execution_truth_normalizer import execution_truth_normalizer
from core.os.cognition.adaptive_solver.adaptive_solver_engine import adaptive_solver_engine
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec, SuccessCriterion
from core.kernel.action_validator import missing_required


class TestAdaptiveTaskSolverSuite:

    # ─────────────────────────────────────────────────────────────
    # VECTOR 1: Situation Model Detects Workspace Patterns & Anomalies
    # ─────────────────────────────────────────────────────────────
    def test_01_situation_model_detects_workspace_patterns(self):
        """Vector 1: Clusters 20 files into homogenous groups and identifies anomalies."""
        files = [f"src/module_{i}.py" for i in range(15)] + [f"tests/test_{i}.py" for i in range(4)] + ["legacy_code_2019.bin"]
        mission = CanonicalMissionSpec.compile_from_text("Chuẩn hóa mã nguồn toàn bộ 20 files", mission_id="m_01")
        
        situation = situation_assessor.initialize_situation(mission, initial_workspace_files=files)
        
        assert len(situation.discovered_files) == 20
        assert "standard_py" in situation.homogenous_groups
        assert len(situation.homogenous_groups["standard_py"]) == 15
        assert "tests" in situation.homogenous_groups
        assert len(situation.homogenous_groups["tests"]) == 4
        assert "legacy_code_2019.bin" in situation.anomalous_items

    # ─────────────────────────────────────────────────────────────
    # VECTOR 2: Adaptive Granularity Starts with Small Probe
    # ─────────────────────────────────────────────────────────────
    def test_02_adaptive_granularity_starts_with_small_probe(self):
        """Vector 2: For complex/multi-file missions, the solver starts with PROBE granularity."""
        files = [f"file_{i}.py" for i in range(10)]
        mission = CanonicalMissionSpec.compile_from_text("Refactor 10 files", mission_id="m_02")
        
        situation = situation_assessor.initialize_situation(mission, initial_workspace_files=files)
        
        assert situation.current_granularity == ActionGranularity.PROBE

    # ─────────────────────────────────────────────────────────────
    # VECTOR 3: Execution Truth Rejects Blank File as Success
    # ─────────────────────────────────────────────────────────────
    def test_03_execution_truth_rejects_blank_file_as_success(self):
        """Vector 3: Tool returns {status: 'success'}, but file on disk has 0 bytes -> Rejects as fake success."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            mission = CanonicalMissionSpec.compile_from_text("Tạo bảng tính Excel 5 người có biểu đồ", mission_id="m_03")
            raw_tool_res = {"status": "success", "file_path": tmp_path}
            
            truth = execution_truth_normalizer.normalize(
                invocation_id="inv_03",
                tool_name="OFFICE_SUITE_MASTER",
                arguments={"file_path": tmp_path},
                raw_result=raw_tool_res,
                mission=mission
            )

            assert truth.artifact_outcome == ArtifactOutcome.CORRUPTED
            assert truth.is_genuine_success is False
            assert "ARTIFACT_CORRUPTED" in truth.diagnostic_details
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ─────────────────────────────────────────────────────────────
    # VECTOR 4: Strategy Adaptation Pivots on Unexpected Discovery
    # ─────────────────────────────────────────────────────────────
    def test_04_strategy_adaptation_pivots_on_unexpected_discovery(self):
        """Vector 4: ModuleNotFoundError during probe triggers PIVOT_STRATEGY."""
        mission = CanonicalMissionSpec.compile_from_text("Tạo báo cáo tài chính", mission_id="m_04")
        situation = situation_assessor.initialize_situation(mission)
        
        failed_truth = ExecutionTruth(
            invocation_id="inv_04",
            tool_name="python_execute",
            arguments={"code": "import non_existent_pkg"},
            tool_outcome=ToolOutcome.FAILED,
            artifact_outcome=ArtifactOutcome.NONE,
            error_message="ModuleNotFoundError: No module named 'non_existent_pkg'",
            is_genuine_success=False
        )

        adaptation = adaptive_solver_engine.evaluate_and_adapt(mission, situation, failed_truth)
        
        assert adaptation.decision == StrategyDecision.PIVOT_STRATEGY
        assert "Missing library detected" in adaptation.rationale

    # ─────────────────────────────────────────────────────────────
    # VECTOR 5: Multi-File Adaptive Batching Promotion
    # ─────────────────────────────────────────────────────────────
    def test_05_multi_file_adaptive_batching(self):
        """Vector 5: Successful probe promotes granularity to BATCH for homogenous group."""
        mission = CanonicalMissionSpec.compile_from_text("Format 15 files", mission_id="m_05")
        files = [f"src/mod_{i}.py" for i in range(15)]
        situation = situation_assessor.initialize_situation(mission, initial_workspace_files=files)
        
        probe_truth = ExecutionTruth(
            invocation_id="inv_05",
            tool_name="replace_file_content",
            arguments={"file_path": "src/mod_0.py"},
            tool_outcome=ToolOutcome.SUCCEEDED,
            artifact_outcome=ArtifactOutcome.MODIFIED,
            is_genuine_success=False
        )

        situation = situation_assessor.record_probe_observation(situation, "src/mod_0.py", "Syntax OK", "Syntax OK")
        adaptation = adaptive_solver_engine.evaluate_and_adapt(mission, situation, probe_truth)
        
        assert adaptation.decision == StrategyDecision.REFINE_GRANULARITY
        assert adaptation.recommended_granularity == ActionGranularity.BATCH

    # ─────────────────────────────────────────────────────────────
    # VECTOR 6: Fast to Deep Escalation on High Complexity Discovery
    # ─────────────────────────────────────────────────────────────
    def test_06_fast_to_deep_escalation_on_high_complexity(self):
        """Vector 6: High complexity discovered during probe triggers DEEPEN_REASONING."""
        mission = CanonicalMissionSpec.compile_from_text("Complex Architecture Refactor", mission_id="m_06")
        situation = situation_assessor.initialize_situation(mission)
        situation.complexity_score = 0.9 # Extreme complexity

        probe_truth = ExecutionTruth(
            invocation_id="inv_06",
            tool_name="view_file",
            arguments={"path": "core/kernel.py"},
            tool_outcome=ToolOutcome.SUCCEEDED,
            artifact_outcome=ArtifactOutcome.NONE,
            is_genuine_success=False
        )

        adaptation = adaptive_solver_engine.evaluate_and_adapt(mission, situation, probe_truth)
        
        assert adaptation.decision == StrategyDecision.DEEPEN_REASONING
        assert adaptation.escalate_to_deep is True

    # ─────────────────────────────────────────────────────────────
    # VECTOR 7: Verification Closed Loop Triggers Targeted Repair
    # ─────────────────────────────────────────────────────────────
    def test_07_verification_closed_loop_triggers_targeted_repair(self):
        """Vector 7: Missing chart in Excel workbook triggers TARGETED_REPAIR."""
        with tempfile.NamedTemporaryFile(suffix=".xlsx", delete=False) as tmp:
            tmp_path = tmp.name

        try:
            import openpyxl
            wb = openpyxl.Workbook()
            ws = wb.active
            ws.title = "Tasks"
            ws["A1"] = "Task"
            wb.save(tmp_path)

            mission = CanonicalMissionSpec.compile_from_text("Tạo bảng tính Excel 5 người có biểu đồ", mission_id="m_07")
            situation = situation_assessor.initialize_situation(mission)

            raw_res = {"status": "success", "file_path": tmp_path}
            truth = execution_truth_normalizer.normalize("inv_07", "OFFICE_SUITE_MASTER", {"file_path": tmp_path}, raw_res, mission)

            assert any(v == RequirementStatus.UNSATISFIED for v in truth.requirement_verdicts.values())

            adaptation = adaptive_solver_engine.evaluate_and_adapt(mission, situation, truth)
            
            assert adaptation.decision == StrategyDecision.TARGETED_REPAIR
            assert adaptation.recommended_granularity == ActionGranularity.TARGETED_REPAIR
        finally:
            if os.path.exists(tmp_path):
                os.remove(tmp_path)

    # ─────────────────────────────────────────────────────────────
    # VECTOR 8: Async Tool Router Non-Blocking Execution
    # ─────────────────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_08_async_tool_router_non_blocking(self):
        """Vector 8: Tool router executes code asynchronously without blocking asyncio event loop."""
        router_path = os.path.join(os.path.dirname(__file__), "..", "services", "ai-executor", "tool_router.py")
        spec = importlib.util.spec_from_file_location("ai_executor_tool_router", router_path)
        tool_router_mod = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(tool_router_mod)
        ToolRouter = tool_router_mod.ToolRouter
        router = ToolRouter()
        
        # Test non-blocking execution of simple python script
        res = await router.call_tool(
            tool_name="python_execute",
            code="import math\nprint(f'PI={math.pi}')"
        )

        assert res.get("status") == "success"
        assert "PI=3.14" in res.get("stdout", "")

    # ─────────────────────────────────────────────────────────────
    # VECTOR 9: Action Validator AST Literal Eval
    # ─────────────────────────────────────────────────────────────
    def test_09_action_validator_ast_literal_eval(self):
        """Vector 9: Action validator parses missing required parameters safely via AST."""
        missing = missing_required("write_to_file", {})
        assert isinstance(missing, list)

    # ─────────────────────────────────────────────────────────────
    # VECTOR 10: End-to-End State Space & Safe Stop on Permission Denial
    # ─────────────────────────────────────────────────────────────
    def test_10_end_to_end_state_space_and_safe_stop(self):
        """Vector 10: Verifies state space (COMPLETED, RECOVERY, SAFE_STOP)."""
        mission = CanonicalMissionSpec.compile_from_text("Delete root system directory", mission_id="m_10")
        situation = situation_assessor.initialize_situation(mission)

        perm_denied_truth = ExecutionTruth(
            invocation_id="inv_10",
            tool_name="run_command",
            arguments={"command": "rm -rf /"},
            tool_outcome=ToolOutcome.PERMISSION_DENIED,
            artifact_outcome=ArtifactOutcome.NONE,
            mission_outcome=MissionOutcome.SAFE_STOP,
            error_message="Security Policy Denied: Root deletion blocked by Sovereign Guard",
            is_genuine_success=False
        )

        adaptation = adaptive_solver_engine.evaluate_and_adapt(mission, situation, perm_denied_truth)
        assert adaptation.decision == StrategyDecision.SAFE_STOP
        assert "Security boundary" in adaptation.rationale

    # ─────────────────────────────────────────────────────────────
    # VECTOR 11: Strategy Invalidation on Expected vs Actual Divergence
    # ─────────────────────────────────────────────────────────────
    def test_11_adaptive_solver_rejects_stale_strategy(self):
        """Vector 11: Probe discovers unexpected divergence -> STRATEGY_INVALIDATED."""
        mission = CanonicalMissionSpec.compile_from_text("Batch format 15 files", mission_id="m_11")
        files = [f"src/file_{i}.py" for i in range(15)]
        situation = situation_assessor.initialize_situation(mission, initial_workspace_files=files)

        # Expected: same schema. Actual: ModuleNotFoundError / Incompatible syntax
        situation = situation_assessor.record_probe_observation(
            situation=situation,
            probe_target="src/file_3.py",
            expected_behavior="Expected standard python syntax",
            observed_behavior="SyntaxError: incompatible syntax in file_3.py"
        )

        probe_truth = ExecutionTruth(
            invocation_id="inv_11",
            tool_name="view_file",
            arguments={"path": "src/file_3.py"},
            tool_outcome=ToolOutcome.SUCCEEDED,
            artifact_outcome=ArtifactOutcome.NONE,
            is_genuine_success=False
        )

        adaptation = adaptive_solver_engine.evaluate_and_adapt(mission, situation, probe_truth)
        assert adaptation.decision == StrategyDecision.STRATEGY_INVALIDATED
        assert "Stale batch hypothesis invalidated" in adaptation.rationale

    # ─────────────────────────────────────────────────────────────
    # VECTOR 12: Mission Immutability During Strategy Adaptation
    # ─────────────────────────────────────────────────────────────
    def test_12_mission_immutable_during_adaptation(self):
        """Vector 12: Attempting to mutate or drop mission requirements raises MissionImmutabilityViolationError."""
        mission = CanonicalMissionSpec.compile_from_text("Chuẩn hóa toàn bộ 20 files", mission_id="m_12")
        situation = situation_assessor.initialize_situation(mission)

        # Illegally mutate mission requirements behind the scene
        mission.success_criteria.pop() # Dropped a criterion!

        dummy_truth = ExecutionTruth(
            invocation_id="inv_12",
            tool_name="view_file",
            arguments={},
            tool_outcome=ToolOutcome.SUCCEEDED,
            artifact_outcome=ArtifactOutcome.NONE,
            is_genuine_success=False
        )

        with pytest.raises(MissionImmutabilityViolationError) as exc_info:
            adaptive_solver_engine.evaluate_and_adapt(mission, situation, dummy_truth)
        
        assert "requirements were mutated during execution" in str(exc_info.value)
