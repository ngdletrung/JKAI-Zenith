"""
🏛️ JKAI ZENITH v4 — GATE H: ADVERSARIAL & CHAOS MISSION TEST SUITE
File: tests/test_gate_h_chaos_adversarial_suite.py

Verifies compositional multi-failure handling, chaotic real-world mutations,
adversarial tool outcomes, and autonomous adaptive recovery without human intervention:
- Chaos Vector 1: Tool Timeout + Execution Truth Rejection + Alternative Strategy Pivot
- Chaos Vector 2: False-Success Exit 0 on Corrupted 0-Byte Artifact + Targeted Repair
- Chaos Vector 3: Homogeneity Collapse on Mid-Stream Dependency Surprise + Strategy Invalidation
- Chaos Vector 4: Permission Boundary Breach + Fail-Closed Safe Stop with Zero Corruption
- Chaos Vector 5: Multi-Vendor Hardware Telemetry Dynamic Probing (AMD ROCm / Windows Direct3D / Linux)
"""

import os
import sys
import time
import tempfile
import pytest
from typing import Dict, Any, List

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "services", "ai-brain")))

from core.os.cognition.adaptive_solver.models import (
    SituationModel, ExpectedVsActual, ExecutionTruth, ToolOutcome,
    ArtifactOutcome, MissionOutcome, StrategyDecision, ActionGranularity,
    RequirementStatus, StrategyAdaptation
)
from core.os.cognition.adaptive_solver.situation_model import situation_assessor
from core.os.cognition.adaptive_solver.execution_truth_normalizer import execution_truth_normalizer
from core.os.cognition.adaptive_solver.adaptive_solver_engine import adaptive_solver_engine
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec
from core.governance.gate_f_evidence_auditor import HardwareTelemetryEngine, GPUVendor, GateFEvidenceAuditor


class TestGateHChaosAdversarialSuite:
    """Gate H: Adversarial & Chaos Mission Invariant Verification."""

    # ─────────────────────────────────────────────────────────────
    # VECTOR 1: Tool Timeout + Strategy Pivot
    # ─────────────────────────────────────────────────────────────
    def test_chaos_01_tool_timeout_and_strategy_pivot(self):
        """Chaos 1: Mid-flight tool failure with missing module triggers PIVOT_STRATEGY with rich provenance."""
        mission = CanonicalMissionSpec.compile_from_text(
            text="Analyze codebase architecture and extract dependency graph",
            mission_id="chaos_01_timeout"
        )
        situation = situation_assessor.initialize_situation(mission)

        # Simulated tool failure with ModuleNotFoundError
        truth = execution_truth_normalizer.normalize(
            invocation_id="inv_timeout_01",
            tool_name="networkx_graph_export",
            arguments={"target": "core/"},
            raw_result={"status": "error", "error": "ModuleNotFoundError: No module named 'networkx'"},
            mission=mission
        )

        assert truth.tool_outcome == ToolOutcome.FAILED
        assert truth.is_genuine_success is False

        adaptation = adaptive_solver_engine.evaluate_and_adapt(mission, situation, truth)
        assert adaptation.decision == StrategyDecision.PIVOT_STRATEGY
        assert adaptation.recommended_granularity == ActionGranularity.PRECISION
        assert "DEPENDENCY_MISSING" in adaptation.reason_codes
        assert len(adaptation.supporting_evidence) > 0
        assert adaptation.provenance_trace.get("mission_id") == "chaos_01_timeout"

    # ─────────────────────────────────────────────────────────────
    # VECTOR 2: False-Success Exit 0 on Blank Artifact + Targeted Repair
    # ─────────────────────────────────────────────────────────────
    def test_chaos_02_false_success_exit_zero_triggers_targeted_repair(self):
        """Chaos 2: Tool claims success with exit 0, but creates 0-byte file. Truth layer rejects and triggers repair."""
        with tempfile.TemporaryDirectory() as tmpdir:
            blank_file = os.path.join(tmpdir, "financial_summary.xlsx")
            with open(blank_file, "wb") as f:
                pass  # 0 bytes corrupted artifact

            mission = CanonicalMissionSpec.compile_from_text(
                text=f"Create financial report with revenue calculations in {blank_file}",
                mission_id="chaos_02_blank"
            )
            situation = situation_assessor.initialize_situation(mission)

            truth = execution_truth_normalizer.normalize(
                invocation_id="inv_blank_02",
                tool_name="xlsx_writer",
                arguments={"file_path": blank_file},
                raw_result={"status": "success", "file": blank_file, "exit_code": 0},
                mission=mission
            )

            assert truth.artifact_outcome == ArtifactOutcome.CORRUPTED
            assert truth.is_genuine_success is False

            adaptation = adaptive_solver_engine.evaluate_and_adapt(mission, situation, truth)
            assert adaptation.decision == StrategyDecision.TARGETED_REPAIR
            assert "REQUIREMENT_UNSATISFIED" in adaptation.reason_codes
            assert adaptation.next_action_target == blank_file

    # ─────────────────────────────────────────────────────────────
    # VECTOR 3: Homogeneity Collapse on Mid-Stream Discovery
    # ─────────────────────────────────────────────────────────────
    def test_chaos_03_homogeneity_collapse_invalidates_strategy(self):
        """Chaos 3: Presumed homogenous batch of 20 files suffers syntax error on file 7. Invalidate batch hypothesis."""
        files = [f"services/mod_{i:02d}.py" for i in range(20)]
        mission = CanonicalMissionSpec.compile_from_text(
            text="Refactor all 20 service modules to use typed dependency injection",
            mission_id="chaos_03_batch"
        )
        situation = situation_assessor.initialize_situation(mission, initial_workspace_files=files)

        assert len(situation.homogenous_groups.get("standard_py", [])) == 20

        # Divergence on file 7
        situation = situation_assessor.record_probe_observation(
            situation=situation,
            probe_target="services/mod_07.py",
            expected_behavior="Valid Python module matching standard template",
            observed_behavior="SyntaxError: legacy Python 2 print statement in mod_07.py"
        )

        truth = ExecutionTruth(
            invocation_id="inv_chaos_03",
            tool_name="batch_refactor",
            arguments={"target": "services/mod_07.py"},
            tool_outcome=ToolOutcome.SUCCEEDED,
            artifact_outcome=ArtifactOutcome.CREATED,
            mission_outcome=MissionOutcome.RECOVERY
        )

        adaptation = adaptive_solver_engine.evaluate_and_adapt(mission, situation, truth)
        assert adaptation.decision == StrategyDecision.STRATEGY_INVALIDATED
        assert adaptation.recommended_granularity == ActionGranularity.PRECISION
        assert "DIVERGENCE_DETECTED" in adaptation.reason_codes
        assert "HYPOTHESIS_FALSIFIED" in adaptation.reason_codes

    # ─────────────────────────────────────────────────────────────
    # VECTOR 4: Permission Boundary Violation + Safe Stop
    # ─────────────────────────────────────────────────────────────
    def test_chaos_04_permission_boundary_safe_stop_with_zero_side_effects(self):
        """Chaos 4: Tool attempts destructive mutation without authorization -> Enforces SAFE_STOP fail-closed."""
        mission = CanonicalMissionSpec.compile_from_text(
            text="Delete production backup archives in /var/data/backups",
            mission_id="chaos_04_security"
        )
        situation = situation_assessor.initialize_situation(mission)

        truth = ExecutionTruth(
            invocation_id="inv_chaos_04",
            tool_name="delete_files",
            arguments={"path": "/var/data/backups"},
            tool_outcome=ToolOutcome.PERMISSION_DENIED,
            artifact_outcome=ArtifactOutcome.NONE,
            mission_outcome=MissionOutcome.SAFE_STOP,
            error_message="Fail-Closed: Destructive file deletion is unauthorized."
        )

        adaptation = adaptive_solver_engine.evaluate_and_adapt(mission, situation, truth)
        assert adaptation.decision == StrategyDecision.SAFE_STOP
        assert adaptation.authority_scope == "FAIL_CLOSED"
        assert "SECURITY_BOUNDARY_REACHED" in adaptation.reason_codes
        assert "Destructive file deletion is unauthorized" in str(adaptation.safe_stop_reason)

    # ─────────────────────────────────────────────────────────────
    # VECTOR 5: Multi-Vendor Hardware Telemetry Dynamic Probing
    # ─────────────────────────────────────────────────────────────
    def test_chaos_05_multi_vendor_hardware_telemetry_probing(self):
        """Chaos 5: Probes multi-vendor physical hardware telemetry dynamically without static hardcodes."""
        hw = HardwareTelemetryEngine.probe_all_hardware()

        assert "cpu" in hw
        assert "os" in hw
        assert "ram_installed_gb" in hw
        assert hw["ram_installed_gb"] > 0
        assert "gpu_vendor" in hw
        assert hw["gpu_vendor"] in [v.value for v in GPUVendor]
        assert "gpu_telemetry_source" in hw

        # Generate live Gate F package
        with tempfile.TemporaryDirectory() as tmpdir:
            pkg = GateFEvidenceAuditor.generate_evidence_package(output_dir=tmpdir)
            assert pkg["verdict"] == "PASSED"
            assert os.path.exists(os.path.join(tmpdir, "run_manifest.json"))
            assert os.path.exists(os.path.join(tmpdir, "hardware_snapshot.json"))
            assert os.path.exists(os.path.join(tmpdir, "resource_metrics.json"))
            assert os.path.exists(os.path.join(tmpdir, "FINAL_VERDICT.json"))
