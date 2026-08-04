"""
JKAI ZENITH — CYBER RECON & THREAT INTEL APP TEST SUITE
File: tests/constitution/test_cyber_recon_threat_intel_app.py

Verifies CyberReconThreatIntelApp end-to-end execution across WebRecon, MariaDB, Office Suite, and Google Drive.
"""

import pytest
from intelligence.applications.cyber_recon_threat_intel_app import CyberReconThreatIntelApp


def test_cyber_recon_threat_intel_app_end_to_end():
    res = CyberReconThreatIntelApp.execute_security_threat_audit(
        mission_id="mis_sec_audit_001",
        target_url="https://sec.internal/portal",
        target_db="sec_audit_db",
        drive_folder="sec_backups"
    )

    assert res.success is True
    assert res.vulnerabilities_detected > 0
    assert res.report_file_path == "exports/mis_sec_audit_001_cyber_security_audit.xlsx"
    assert res.drive_backup_id != ""
