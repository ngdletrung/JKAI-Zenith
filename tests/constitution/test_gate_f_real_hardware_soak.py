"""
JKAI ZENITH v4.1 — GATE F REAL HARDWARE SOAK & EVIDENCE PACKAGE TEST
File: tests/constitution/test_gate_f_real_hardware_soak.py

Tests Gate F Evidence Package Generation:
  - Verifies that metrics are DERIVED from real telemetry (not hard-coded)
  - Verifies all required artifact files are written
  - Verifies verdict is computed from ledger (verdict_basis field present)
  - Verifies mission ledger summary is written with provenance
  - Does NOT assert verdict == PASSED (verdict is an empirical finding,
    not a test expectation — it reflects real system state)
"""

import pytest
import os
import json
from pathlib import Path
from core.governance.gate_f_evidence_auditor import GateFEvidenceAuditor, GateFElevanceMetrics


def test_gate_f_evidence_package_files_written(tmp_path):
    """Gate F package must write all 5 required artifact files."""
    output_dir = str(tmp_path / "gate_f_audit")
    GateFEvidenceAuditor.generate_evidence_package(output_dir)

    assert os.path.exists(os.path.join(output_dir, "run_manifest.json")), \
        "run_manifest.json must be written"
    assert os.path.exists(os.path.join(output_dir, "hardware_snapshot.json")), \
        "hardware_snapshot.json must be written"
    assert os.path.exists(os.path.join(output_dir, "resource_metrics.json")), \
        "resource_metrics.json must be written"
    assert os.path.exists(os.path.join(output_dir, "mission_ledger_summary.json")), \
        "mission_ledger_summary.json must be written (v4.1 provenance)"
    assert os.path.exists(os.path.join(output_dir, "FINAL_VERDICT.json")), \
        "FINAL_VERDICT.json must be written"


def test_gate_f_verdict_has_provenance(tmp_path):
    """FINAL_VERDICT must include verdict_basis — proves it was derived, not declared."""
    output_dir = str(tmp_path / "gate_f_audit")
    verdict = GateFEvidenceAuditor.generate_evidence_package(output_dir)

    # verdict_basis must be present and not empty
    assert "verdict_basis" in verdict, \
        "verdict_basis field missing — verdict provenance not tracked"
    assert verdict["verdict_basis"] in (
        "derived_from_mission_ledger",
        "LEDGER_EMPTY_DEFAULT_FAIL",
    ), f"Unexpected verdict_basis: {verdict['verdict_basis']}"


def test_gate_f_metrics_not_hardcoded(tmp_path):
    """
    Verifies that operational metrics are DERIVED from real telemetry.
    The old hard-coded defaults were total_missions=100, success_rate=100.0.
    If the ledger found real missions, these must NOT be the default 100/100.
    """
    output_dir = str(tmp_path / "gate_f_audit")
    verdict = GateFEvidenceAuditor.generate_evidence_package(
        output_dir,
        missions_dir="services/mission-control/backend/missions",
    )
    m = verdict["metrics"]

    if m["total_missions"] > 0:
        # If ledger found missions, success_rate must reflect reality
        # (not the old hard-coded 100.0)
        assert m["mission_success_rate"] != 100.0 or m["total_missions"] < 10, \
            "Suspicious: 100% success rate with many missions — possible hard-coded value"
        assert m["total_missions"] != 100 or m["mission_success_rate"] != 100.0, \
            "Exact (100, 100.0) detected — likely hard-coded defaults, not derived"


def test_gate_f_default_metrics_not_passing():
    """
    GateFElevanceMetrics defaults must NOT be automatically passing.
    An uninitialised metric must be FAILED (unknown), never PASSED.
    This is the fundamental invariant: no proof = not proven.
    """
    default = GateFElevanceMetrics()
    assert default.is_gate_f_passed is False, \
        "Default GateFElevanceMetrics must be FAILED (unknown), not PASSED"
    assert default.total_missions == 0, \
        "Default total_missions must be 0 (LEDGER_EMPTY), not 100"
    assert default.mission_success_rate == 0.0, \
        "Default success_rate must be 0.0 (unknown), not 100.0"


def test_gate_f_ledger_summary_has_provenance(tmp_path):
    """mission_ledger_summary.json must contain provenance fields."""
    output_dir = str(tmp_path / "gate_f_audit")
    GateFEvidenceAuditor.generate_evidence_package(
        output_dir,
        missions_dir="services/mission-control/backend/missions",
    )
    summary_path = os.path.join(output_dir, "mission_ledger_summary.json")
    with open(summary_path, "r", encoding="utf-8") as f:
        summary = json.load(f)

    # Must have at minimum a ledger_status field
    assert "ledger_status" in summary, \
        "mission_ledger_summary.json must contain ledger_status"


def test_gate_f_hardware_snapshot_real(tmp_path):
    """Hardware snapshot must contain real CPU/RAM data — not zeros."""
    output_dir = str(tmp_path / "gate_f_audit")
    GateFEvidenceAuditor.generate_evidence_package(output_dir)
    hw_path = os.path.join(output_dir, "hardware_snapshot.json")
    with open(hw_path, "r", encoding="utf-8") as f:
        hw = json.load(f)

    assert hw.get("cpu"), "CPU field must not be empty"
    assert hw.get("ram_installed_gb", 0) > 0, "RAM must be > 0"
    assert hw.get("os"), "OS field must not be empty"
