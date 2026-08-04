"""
JKAI ZENITH — OFFICE SUITE CAPABILITY PROVIDER TEST SUITE
File: tests/constitution/test_office_suite_provider_extension.py

Verifies horizontal extension of OfficeSuiteCapabilityProvider.
"""

import pytest
from intelligence.capabilities.office_suite_provider import OfficeSuiteCapabilityProvider


def test_office_suite_capability_provider():
    res = OfficeSuiteCapabilityProvider.execute_capability(
        capability_name="office_generate_xlsx",
        parameters={"target_path": "exports/quarterly_report.xlsx"}
    )

    assert res.success is True
    assert res.data["status"] == "COMPLETED"
    assert res.data["provider"] == "office_suite_provider"
    assert res.data["output_file"] == "exports/quarterly_report.xlsx"
