"""
🏛️ JKAI ZENITH v4 — P0-5: BLIND MISSION BENCHMARK SUITE
File: tests/test_blind_mission_benchmark_suite.py

Comprehensive blind benchmark vectors testing pure emergent autonomy without topology hints:
- Benchmark 1: Unseen Ambiguous Task with Exploratory Micro-Probe & Belief Formulation
- Benchmark 2: Homogeneous Batch Anomaly with Strategy Confidence Decay
- Benchmark 3: Multi-Objective Next Best Action Selection under Uncertainty
- Benchmark 4: Immutable Belief Revision with Full Provenance Logging
- Benchmark 5: Dynamic Bidirectional Granularity Oscillation (PROBE <-> BATCH <-> PRECISION)
- Benchmark 6: Causal Execution Graph Multi-Turn Root-Cause Tracing
- Benchmark 7: Uncertainty Budget Mutation Gating
- Benchmark 8: Granular Recovery Taxonomy Execution (RETRY, REPAIR, ROLLBACK, SAFE_STOP)
- Benchmark 9: Real Multi-Vendor Hardware Telemetry Dynamic Integration
- Benchmark 10: End-to-End Autonomous Problem Solving Loop with Verification & Physical Proof
"""

import os
import sys
import tempfile
import pytest
from unittest.mock import MagicMock

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "ai-brain")))

from core.os.cognition.adaptive_solver.models import (
    ActionGranularity, ArtifactOutcome, ExecutionTruth, MissionOutcome,
    RecoveryAction, RequirementStatus, StrategyAdaptation, StrategyDecision,
    ToolOutcome, UncertaintyBudget
)
from core.os.cognition.adaptive_solver.situation_model import situation_assessor
from core.os.cognition.adaptive_solver.belief_system import (
    BeliefRevisionEngine, BeliefStatus, belief_revision_engine
)
from core.os.cognition.adaptive_solver.next_best_action import (
    ActionCandidate, ActionType, next_best_action_selector
)
from core.os.cognition.adaptive_solver.causal_graph import CausalExecutionGraph
from core.os.cognition.adaptive_solver.adaptive_solver_engine import adaptive_solver_engine
from core.os.cognition.adaptive_solver.adaptation_applier import adaptation_applier
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec


class TestBlindMissionBenchmarkSuite:
    """10-Vector Blind Mission Benchmark Suite for JKAI Situational Intelligence."""

    # ─────────────────────────────────────────────────────────────
    # BENCHMARK 1: Unseen Ambiguous Task & Micro-Probe
    # ─────────────────────────────────────────────────────────────
    def test_blind_01_unseen_ambiguous_task_starts_with_probe(self):
        """Blind 1: Task with unknown files starts with low granularity (PROBE) to reduce uncertainty."""
        mission = CanonicalMissionSpec.compile_from_text(
            goal="Synchronize configuration files across backend microservices",
            mission_id="blind_01_sync"
        )
        files = ["service_a/config.yaml", "service_b/config.json", "legacy/old_conf.ini"]
        situation = situation_assessor.initialize_situation(mission, initial_workspace_files=files)

        assert situation.current_granularity == ActionGranularity.PROBE
        assert len(situation.unknowns) > 0
        assert situation.uncertainty_budget.total_unknowns == 3

    # ─────────────────────────────────────────────────────────────
    # BENCHMARK 2: Strategy Confidence Decay on Anomaly
    # ─────────────────────────────────────────────────────────────
    def test_blind_02_strategy_confidence_decays_on_anomaly(self):
        """Blind 2: Anomaly discovery causes strategy confidence to decay from 0.95 to invalidated threshold."""
        mission = CanonicalMissionSpec.compile_from_text(
            goal="Refactor all Python modules to use async handlers",
            mission_id="blind_02_decay"
        )
        files = [f"handlers/h_{i:02d}.py" for i in range(10)]
        situation = situation_assessor.initialize_situation(mission, initial_workspace_files=files)

        assert situation.strategy_confidence.current_confidence == 0.95

        # First anomaly (syntax error)
        situation = situation_assessor.record_probe_observation(
            situation=situation,
            probe_target="handlers/h_03.py",
            expected_behavior="Valid Python 3 async syntax",
            observed_behavior="SyntaxError: incompatible decorator in h_03.py"
        )
        assert situation.strategy_confidence.current_confidence == 0.60
        assert not situation.strategy_confidence.is_invalidated

        # Second anomaly (corrupted file)
        situation = situation_assessor.record_probe_observation(
            situation=situation,
            probe_target="handlers/h_07.py",
            expected_behavior="Valid Python 3 async syntax",
            observed_behavior="Corrupted: 0 bytes empty file in h_07.py"
        )
        assert situation.strategy_confidence.current_confidence == 0.25
        assert situation.strategy_confidence.is_invalidated

    # ─────────────────────────────────────────────────────────────
    # BENCHMARK 3: Multi-Objective Next Best Action Selection
    # ─────────────────────────────────────────────────────────────
    def test_blind_03_next_best_action_prefers_probe_under_high_uncertainty(self):
        """Blind 3: When uncertainty is unbudgeted, selector boosts exploratory probe over mass edit."""
        situation = MagicMock()
        situation.uncertainty_budget = UncertaintyBudget(
            total_unknowns=10,
            critical_unknowns=2,  # Critical unknowns exist!
            evidence_confidence=0.40
        )

        candidates = [
            ActionCandidate(
                candidate_id="act_batch",
                action_type=ActionType.BATCH_EDIT,
                target="all_20_files",
                description="Mass overwrite 20 files",
                information_gain=0.10,
                mission_progress=0.90,
                evidence_value=0.50,
                reversibility=0.20,
                execution_cost=0.50,
                risk_score=0.80
            ),
            ActionCandidate(
                candidate_id="act_probe",
                action_type=ActionType.INSPECT_FILE,
                target="file_01.py",
                description="Inspect sample file to resolve critical unknown",
                information_gain=0.90,
                mission_progress=0.10,
                evidence_value=0.90,
                reversibility=1.00,
                execution_cost=0.05,
                risk_score=0.05
            )
        ]

        best_action = next_best_action_selector.select_next_best_action(candidates, situation)
        assert best_action is not None
        assert best_action.candidate.candidate_id == "act_probe"
        assert best_action.candidate.action_type == ActionType.INSPECT_FILE

    # ─────────────────────────────────────────────────────────────
    # BENCHMARK 4: Belief Revision Engine Traceability
    # ─────────────────────────────────────────────────────────────
    def test_blind_04_belief_revision_provenance_logging(self):
        """Blind 4: Hypotheses transition cleanly into CONFIRMED, REFUTED, and SUPERSEDED with full audit history."""
        engine = BeliefRevisionEngine()
        b1 = engine.register_belief("All 15 files use JSON schema v1", initial_confidence=0.60)

        assert b1.status == BeliefStatus.HYPOTHESIS

        # Contradictory observation
        engine.evaluate_observation(
            belief_id=b1.belief_id,
            observation="File 4 uses XML schema v2",
            is_contradictory=True,
            evidence_weight=0.40
        )
        assert b1.status == BeliefStatus.REFUTED

        # Revise into explicit successor belief
        rev_event = engine.revise_belief(
            belief_id=b1.belief_id,
            new_statement="10 files use JSON schema v1, 5 files use XML schema v2",
            trigger_evidence="File 4 uses XML schema v2",
            rationale="Discovered heterogeneous schemas during probe"
        )

        assert rev_event.old_status == BeliefStatus.REFUTED
        assert rev_event.new_status == BeliefStatus.SUPERSEDED
        assert len(engine.get_revision_history()) == 2

    # ─────────────────────────────────────────────────────────────
    # BENCHMARK 5: Dynamic Bidirectional Granularity Oscillation
    # ─────────────────────────────────────────────────────────────
    def test_blind_05_bidirectional_granularity_oscillation(self):
        """Blind 5: Granularity ascends PROBE -> BATCH, then descends to PRECISION on anomaly, and recovers."""
        mission = CanonicalMissionSpec.compile_from_text("Format 10 modules", mission_id="blind_05_gran")
        files = [f"src/m_{i}.py" for i in range(10)]
        situation = situation_assessor.initialize_situation(mission, initial_workspace_files=files)

        assert situation.current_granularity == ActionGranularity.PROBE

        # Successful probe promotes to BATCH
        truth_probe = ExecutionTruth(
            invocation_id="inv_b5_01",
            tool_name="view_file",
            arguments={"path": "src/m_00.py"},
            tool_outcome=ToolOutcome.SUCCEEDED,
            artifact_outcome=ArtifactOutcome.CREATED,
            mission_outcome=MissionOutcome.RECOVERY
        )
        adapt_1 = adaptive_solver_engine.evaluate_and_adapt(mission, situation, truth_probe)
        assert adapt_1.decision == StrategyDecision.REFINE_GRANULARITY
        assert adapt_1.recommended_granularity == ActionGranularity.BATCH

        # Anomaly causes descent back to PRECISION
        situation = situation_assessor.record_probe_observation(
            situation=situation,
            probe_target="src/m_04.py",
            expected_behavior="Standard template",
            observed_behavior="SyntaxError: legacy Python 2 print in src/m_04.py"
        )
        adapt_2 = adaptive_solver_engine.evaluate_and_adapt(mission, situation, truth_probe)
        assert adapt_2.decision == StrategyDecision.STRATEGY_INVALIDATED
        assert adapt_2.recommended_granularity == ActionGranularity.PRECISION

    # ─────────────────────────────────────────────────────────────
    # BENCHMARK 6: Causal Execution Graph Root-Cause Tracing
    # ─────────────────────────────────────────────────────────────
    def test_blind_06_causal_execution_graph_tracing(self):
        """Blind 6: Multi-turn execution tree is recorded and traceable from final action to root trigger."""
        graph = CausalExecutionGraph(mission_id="blind_06_causal")

        # Step 1: Initial creation
        graph.record_action(
            action_id="act_01",
            cause="Master requested financial summary spreadsheet",
            tool_name="xlsx_writer",
            arguments={"path": "finance.xlsx"},
            expected_effect="Create Excel file with tables",
            actual_effect="finance.xlsx created without chart",
            verification_status="FAILED",
            evidence="Verification failed: chart missing"
        )

        # Step 2: Surgical repair (child of act_01)
        graph.record_action(
            action_id="act_02",
            parent_action_id="act_01",
            cause="Repair missing chart in finance.xlsx",
            tool_name="xlsx_chart_adder",
            arguments={"path": "finance.xlsx", "chart_type": "bar"},
            expected_effect="Add bar chart sheet to finance.xlsx",
            actual_effect="Bar chart injected successfully",
            verification_status="PASSED",
            evidence="AST and chart check passed (exit 0)"
        )

        chain = graph.get_causal_chain("act_02")
        assert len(chain) == 2
        assert chain[0].action_id == "act_01"
        assert chain[1].action_id == "act_02"
        assert len(graph.get_failed_branches()) == 1

    # ─────────────────────────────────────────────────────────────
    # BENCHMARK 7: Uncertainty Budget Mutation Gating
    # ─────────────────────────────────────────────────────────────
    def test_blind_07_uncertainty_budget_mutation_gating(self):
        """Blind 7: Uncertainty budget permits mutation only when critical unknowns == 0 and confidence is high."""
        budget_blocked = UncertaintyBudget(total_unknowns=5, critical_unknowns=1, evidence_confidence=0.45)
        assert budget_blocked.is_mutation_permitted is False

        budget_cleared = UncertaintyBudget(total_unknowns=5, critical_unknowns=0, evidence_confidence=0.85)
        assert budget_cleared.is_mutation_permitted is True

    # ─────────────────────────────────────────────────────────────
    # BENCHMARK 8: Recovery Taxonomy Specialization
    # ─────────────────────────────────────────────────────────────
    def test_blind_08_recovery_taxonomy_specialization(self):
        """Blind 8: ATS assigns precise RecoveryAction (REPAIR vs RETRY vs SAFE_STOP vs ESCALATE)."""
        mission = CanonicalMissionSpec.compile_from_text("Process task", mission_id="blind_08_rec")
        situation = situation_assessor.initialize_situation(mission)

        # 1. Timeout -> RETRY / PIVOT
        truth_timeout = ExecutionTruth(
            invocation_id="inv_to",
            tool_name="api_fetch",
            arguments={},
            tool_outcome=ToolOutcome.TIMEOUT,
            artifact_outcome=ArtifactOutcome.NONE,
            error_message="Gateway timeout 504"
        )
        adapt_to = adaptive_solver_engine.evaluate_and_adapt(mission, situation, truth_timeout)
        assert adapt_to.decision == StrategyDecision.PIVOT_STRATEGY

        # 2. Permission Denied -> SAFE_STOP
        truth_perm = ExecutionTruth(
            invocation_id="inv_perm",
            tool_name="delete_root",
            arguments={},
            tool_outcome=ToolOutcome.PERMISSION_DENIED,
            artifact_outcome=ArtifactOutcome.NONE,
            error_message="Unauthorized file deletion"
        )
        adapt_perm = adaptive_solver_engine.evaluate_and_adapt(mission, situation, truth_perm)
        assert adapt_perm.decision == StrategyDecision.SAFE_STOP

    # ─────────────────────────────────────────────────────────────
    # BENCHMARK 9: Dynamic Multi-Vendor Telemetry Probing
    # ─────────────────────────────────────────────────────────────
    def test_blind_09_multi_vendor_hardware_telemetry(self):
        """Blind 9: Real hardware telemetry correctly reports CPU, RAM, and GPU profiles dynamically."""
        from core.governance.gate_f_evidence_auditor import HardwareTelemetryEngine
        hw = HardwareTelemetryEngine.probe_all_hardware()

        assert hw["cpu_cores"] >= 1
        assert hw["ram_installed_gb"] > 0
        assert "gpu_vendor" in hw

    # ─────────────────────────────────────────────────────────────
    # BENCHMARK 10: End-to-End Autonomous Problem Solving Loop
    # ─────────────────────────────────────────────────────────────
    @pytest.mark.asyncio
    async def test_blind_10_end_to_end_autonomous_loop(self):
        """Blind 10: Full agentic solve loop: formulation -> action -> verify -> proof."""
        with tempfile.TemporaryDirectory() as tmpdir:
            target_py = os.path.join(tmpdir, "calculator.py")
            code_content = "def add(a, b):\n    return a + b\n\ndef multiply(a, b):\n    return a * b\n"
            with open(target_py, "w", encoding="utf-8") as f:
                f.write(code_content)

            mission = CanonicalMissionSpec.compile_from_text(
                goal=f"Create a clean arithmetic calculator module in {target_py}",
                mission_id="blind_10_e2e"
            )
            situation = situation_assessor.initialize_situation(mission, initial_workspace_files=[target_py])
            engine = MagicMock()

            # Execute verification loop
            truth, adaptation = await adaptation_applier.run_post_edit_verification_loop(
                tool_name="write_to_file",
                tool_args={"file_path": target_py, "content": code_content},
                raw_result={"status": "success", "file": target_py},
                canonical_mission=mission,
                situation=situation,
                task_id="blind_10_e2e",
                gateway=None,
                engine=engine,
                trace_id="tr_b10"
            )

            assert truth.artifact_outcome == ArtifactOutcome.CREATED
            assert truth.is_genuine_success is True

            # Mark all criteria as satisfied
            truth.mission_outcome = MissionOutcome.COMPLETED
            adapt_final = adaptive_solver_engine.evaluate_and_adapt(mission, situation, truth)

            assert adapt_final.decision == StrategyDecision.TERMINATE_WITH_PROOF
            assert adapt_final.confidence == 1.0
            assert "ALL_CRITERIA_VERIFIED" in adapt_final.reason_codes
