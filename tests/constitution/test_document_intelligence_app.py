"""
JKAI ZENITH — DOCUMENT INTELLIGENCE APP TEST SUITE
File: tests/constitution/test_document_intelligence_app.py

Verifies DocumentIntelligenceApp end-to-end execution across MariaDB, Office Suite (Word/Excel), and Google Drive.
"""

import pytest
from intelligence.applications.document_intelligence_app import DocumentIntelligenceApp


def test_document_intelligence_app_contract_expiration_audit():
    res = DocumentIntelligenceApp.execute_contract_expiration_audit(
        mission_id="mis_doc_audit_2026",
        target_db="legal_contracts_db",
        drive_folder_id="folder_legal_archive"
    )

    assert res.success is True
    assert res.expiring_soon_count > 0
    assert res.report_path == "exports/mis_doc_audit_2026_expiring_contracts.xlsx"
    assert res.drive_file_id != ""
