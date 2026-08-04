"""
JKAI ZENITH v4 — GATE F REAL HARDWARE SOAK & EVIDENCE PACKAGE TEST
File: tests/constitution/test_gate_f_real_hardware_soak.py

Verifies Gate F Evidence Package Generation and Zero-Violation Invariants.
"""

import pytest
import os
import json
from core.governance.gate_f_evidence_auditor import GateFEvidenceAuditor


def test_gate_f_evidence_package_generation(tmp_path):
    output_dir = str(tmp_path / "gate_f_audit")
    verdict = GateFEvidenceAuditor.generate_evidence_package(output_dir)

    assert verdict["gate_f_status"] == "PASSED"
    assert verdict["production_complete"] is True

    # Verify key evidence files exist
    assert os.path.exists(os.path.join(output_dir, "run_manifest.json"))
    assert os.path.exists(os.path.join(output_dir, "hardware_snapshot.json"))
    assert os.path.exists(os.path.join(output_dir, "resource_metrics.json"))
    assert os.path.exists(os.path.join(output_dir, "violation_report.json"))
    assert os.path.exists(os.path.join(output_dir, "FINAL_VERDICT.json"))

    # Verify zero-tolerance violations
    with open(os.path.join(output_dir, "violation_report.json"), "r") as f:
        v_report = json.load(f)
        assert v_report["total_violations"] == 0
        assert v_report["duplicate_irreversible_execution"] == 0
        assert v_report["stale_state_execution"] == 0
        assert v_report["mission_state_loss"] == 0
