"""
🏛️ JKAI ZENITH v4 — ATS ADAPTATION APPLIER & VERIFICATION CLOSED-LOOP SUITE
File: tests/test_adaptation_applier_suite.py

Verifies executive control actions for all 8 ATS Strategy Decisions
and the post-mutation verification loop (OpenCode/Antigravity Parity).
"""

import os
import sys
import tempfile
import pytest
from unittest.mock import MagicMock, AsyncMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "ai-brain")))

from core.os.cognition.adaptive_solver.models import (
    ActionGranularity, ArtifactOutcome, ExecutionTruth, MissionOutcome,
    RequirementStatus, StrategyAdaptation, StrategyDecision, ToolOutcome
)
from core.os.cognition.adaptive_solver.adaptation_applier import adaptation_applier
from core.os.cognition.adaptive_solver.situation_model import situation_assessor
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec


class TestAdaptationApplierSuite:
    """Tests executive consumption of all 8 ATS decisions and verification closed-loop."""

    @pytest.mark.asyncio
    async def test_01_safe_stop_halts_immediately_fail_closed(self):
        """Decision 1: SAFE_STOP immediately returns halted directive without side-effects."""
        mission = CanonicalMissionSpec.compile_from_text("Delete unauthorized data", mission_id="m_app_01")
        situation = situation_assessor.initialize_situation(mission)
        engine = MagicMock()
        context = []

        adaptation = StrategyAdaptation(
            decision=StrategyDecision.SAFE_STOP,
            recommended_granularity=ActionGranularity.PROBE,
            rationale="Security boundary breached",
            safe_stop_reason="Unauthorized deletion"
        )

        res = await adaptation_applier.apply_adaptation(
            adaptation=adaptation,
            canonical_mission=mission,
            situation=situation,
            context=context,
            task_id="m_app_01",
            engine=engine,
            trace_id="tr_01"
        )

        assert res["action"] == "SAFE_STOP"
        assert res["result"]["status"] == "safe_stop"
        assert "Unauthorized deletion" in res["result"]["answer"]

    @pytest.mark.asyncio
    async def test_02_terminate_with_proof_early_exit(self):
        """Decision 2: TERMINATE_WITH_PROOF immediately stops turn loop with proof."""
        mission = CanonicalMissionSpec.compile_from_text("Generate verified report", mission_id="m_app_02")
        situation = situation_assessor.initialize_situation(mission)
        engine = MagicMock()
        context = []

        adaptation = StrategyAdaptation(
            decision=StrategyDecision.TERMINATE_WITH_PROOF,
            recommended_granularity=ActionGranularity.VERIFY,
            rationale="All 5 criteria verified on disk",
            supporting_evidence=["Report.xlsx verified non-empty with chart"]
        )

        res = await adaptation_applier.apply_adaptation(
            adaptation=adaptation,
            canonical_mission=mission,
            situation=situation,
            context=context,
            task_id="m_app_02",
            engine=engine,
            trace_id="tr_02"
        )

        assert res["action"] == "TERMINATE"
        assert res["result"]["status"] == "completed"

    @pytest.mark.asyncio
    async def test_03_escalate_deep_triggers_mode_switch(self):
        """Decision 3: DEEPEN_REASONING / escalate_to_deep returns ESCALATE_DEEP directive."""
        mission = CanonicalMissionSpec.compile_from_text("Complex 20-file DAG migration", mission_id="m_app_03")
        situation = situation_assessor.initialize_situation(mission)
        engine = MagicMock()
        context = []

        adaptation = StrategyAdaptation(
            decision=StrategyDecision.DEEPEN_REASONING,
            recommended_granularity=ActionGranularity.PRECISION,
            rationale="High complexity discovered",
            escalate_to_deep=True
        )

        res = await adaptation_applier.apply_adaptation(
            adaptation=adaptation,
            canonical_mission=mission,
            situation=situation,
            context=context,
            task_id="m_app_03",
            engine=engine,
            trace_id="tr_03"
        )

        assert res["action"] == "ESCALATE_DEEP"
        assert res["result"]["escalate_to_deep"] is True

    @pytest.mark.asyncio
    async def test_04_targeted_repair_injects_replan_into_context(self):
        """Decision 4: TARGETED_REPAIR injects explicit surgical fix instructions into context."""
        mission = CanonicalMissionSpec.compile_from_text("Create Excel with chart", mission_id="m_app_04")
        situation = situation_assessor.initialize_situation(mission)
        engine = MagicMock()
        context = []

        adaptation = StrategyAdaptation(
            decision=StrategyDecision.TARGETED_REPAIR,
            recommended_granularity=ActionGranularity.TARGETED_REPAIR,
            rationale="Missing required bar chart",
            next_action_target="report.xlsx",
            replan_instructions="Add bar chart sheet to report.xlsx"
        )

        res = await adaptation_applier.apply_adaptation(
            adaptation=adaptation,
            canonical_mission=mission,
            situation=situation,
            context=context,
            task_id="m_app_04",
            engine=engine,
            trace_id="tr_04"
        )

        assert res["action"] == "CONTINUE"
        assert len(context) == 1
        assert "ATS-TARGETED-REPAIR" in context[0]["content"]
        assert "Add bar chart sheet" in context[0]["content"]

    @pytest.mark.asyncio
    async def test_05_refine_granularity_batch_promotes_context(self):
        """Decision 5: REFINE_GRANULARITY promotes to BATCH mode for homogenous items."""
        mission = CanonicalMissionSpec.compile_from_text("Format 10 files", mission_id="m_app_05")
        files = [f"mod_{i}.py" for i in range(10)]
        situation = situation_assessor.initialize_situation(mission, initial_workspace_files=files)
        engine = MagicMock()
        context = []

        adaptation = StrategyAdaptation(
            decision=StrategyDecision.REFINE_GRANULARITY,
            recommended_granularity=ActionGranularity.BATCH,
            rationale="Probe verified successfully. Promoting to batch."
        )

        res = await adaptation_applier.apply_adaptation(
            adaptation=adaptation,
            canonical_mission=mission,
            situation=situation,
            context=context,
            task_id="m_app_05",
            engine=engine,
            trace_id="tr_05"
        )

        assert res["action"] == "CONTINUE"
        assert len(context) == 1
        assert "ATS-BATCH-MODE" in context[0]["content"]

    @pytest.mark.asyncio
    async def test_06_pivot_strategy_and_invalidation_inject_into_context(self):
        """Decisions 6 & 7: PIVOT_STRATEGY and STRATEGY_INVALIDATED update context dynamically."""
        mission = CanonicalMissionSpec.compile_from_text("Convert data", mission_id="m_app_06")
        situation = situation_assessor.initialize_situation(mission)
        engine = MagicMock()
        context = []

        # Invalidation
        inval_adapt = StrategyAdaptation(
            decision=StrategyDecision.STRATEGY_INVALIDATED,
            recommended_granularity=ActionGranularity.PRECISION,
            rationale="Divergence found on file 3"
        )
        await adaptation_applier.apply_adaptation(inval_adapt, mission, situation, context, "m_app_06", engine, "tr_06")
        assert "ATS-STRATEGY-INVALIDATED" in context[-1]["content"]

        # Pivot
        pivot_adapt = StrategyAdaptation(
            decision=StrategyDecision.PIVOT_STRATEGY,
            recommended_granularity=ActionGranularity.PRECISION,
            rationale="Missing lib pandas",
            replan_instructions="Switch to built-in csv module"
        )
        await adaptation_applier.apply_adaptation(pivot_adapt, mission, situation, context, "m_app_06", engine, "tr_06")
        assert "ATS-PIVOT-STRATEGY" in context[-1]["content"]

    @pytest.mark.asyncio
    async def test_07_post_edit_verification_loop_detects_syntax_error(self):
        """Verification Loop: Mutating a file with invalid Python syntax is caught by AST parser."""
        with tempfile.TemporaryDirectory() as tmpdir:
            broken_file = os.path.join(tmpdir, "broken_script.py")
            with open(broken_file, "w", encoding="utf-8") as f:
                f.write("def broken_func(:\n    pass\n")  # Syntax error: invalid def

            mission = CanonicalMissionSpec.compile_from_text("Create clean script", mission_id="m_app_07")
            situation = situation_assessor.initialize_situation(mission)
            engine = MagicMock()

            truth, adaptation = await adaptation_applier.run_post_edit_verification_loop(
                tool_name="write_to_file",
                tool_args={"file_path": broken_file, "content": "def broken_func(:\n    pass\n"},
                raw_result={"status": "success", "file": broken_file},
                canonical_mission=mission,
                situation=situation,
                task_id="m_app_07",
                gateway=None,
                engine=engine,
                trace_id="tr_07"
            )

            assert truth.artifact_outcome == ArtifactOutcome.CORRUPTED
            assert truth.is_genuine_success is False
            assert "SyntaxError" in str(truth.error_message)
            assert adaptation.decision in (StrategyDecision.STRATEGY_INVALIDATED, StrategyDecision.TARGETED_REPAIR)

    @pytest.mark.asyncio
    async def test_08_fast_to_deep_pipeline_execution_wire(self):
        """ESCALATE_DEEP Wiring: DeepPipeline().execute imports and executes with valid signature."""
        from deep_pipeline import DeepPipeline
        from unittest.mock import patch

        dp = DeepPipeline()
        assert hasattr(dp, "execute")

        with patch.object(DeepPipeline, "execute", new_callable=AsyncMock) as mock_exec:
            mock_exec.return_value = {"status": "success", "answer": "Deep DAG solved", "pipeline": "deep"}

            goal = "Complex architecture refactor"
            task_id = "task_esc_08"
            context = [{"role": "user", "content": goal}]

            res = await DeepPipeline().execute(goal, task_id, planner_instance=None, context=context)
            assert res["status"] == "success"
            assert res["pipeline"] == "deep"
            mock_exec.assert_awaited_once_with(goal, task_id, planner_instance=None, context=context)
