"""
JKAI ZENITH — HORIZONTAL CAPABILITY EXPANSION TEST SUITE
File: tests/constitution/test_horizontal_capability_expansion.py

Verifies that new capabilities (Google Drive) extend horizontally via Capability Providers
without modifying the Cognitive Kernel.
"""

import pytest
from intelligence.capabilities.google_drive_provider import GoogleDriveCapabilityProvider


def test_google_drive_horizontal_extension():
    res = GoogleDriveCapabilityProvider.execute_capability(
        capability_name="gdrive_upload_file",
        parameters={"filename": "quarterly_report.xlsx", "folder_id": "root"}
    )

    assert res.success is True
    assert res.data["status"] == "COMPLETED"
    assert res.data["provider"] == "google_drive_provider"
