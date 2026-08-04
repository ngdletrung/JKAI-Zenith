"""
JKAI ZENITH — ENTERPRISE CAPABILITY ECOSYSTEM & APPLICATION TEST SUITE
File: tests/constitution/test_enterprise_capability_ecosystem.py

Verifies the 5-Capability Ecosystem (Drive, Office, MikroTik, MariaDB, WebRecon)
and Enterprise Automation Application Layer working in unison on JKAI Zenith AI OS Platform.
"""

import pytest
from intelligence.capabilities.mariadb_provider import MariaDBCapabilityProvider
from intelligence.capabilities.web_recon_provider import WebReconCapabilityProvider
from intelligence.applications.enterprise_automation_app import EnterpriseAutomationApp


def test_mariadb_capability_provider_read_and_write():
    read_res = MariaDBCapabilityProvider.execute_capability(
        capability_name="mariadb_inspect_schema",
        parameters={"database": "sales_db"}
    )
    assert read_res.success is True
    assert read_res.access_level == "READ"

    write_denied = MariaDBCapabilityProvider.execute_capability(
        capability_name="mariadb_execute_mutation",
        parameters={"database": "sales_db"}
    )
    assert write_denied.success is False
    assert "POLICY DENIED" in write_denied.error_message

    write_auth = MariaDBCapabilityProvider.execute_capability(
        capability_name="mariadb_execute_mutation",
        parameters={"database": "sales_db"},
        auth_scope=["db:read", "db:write"]
    )
    assert write_auth.success is True
    assert write_auth.access_level == "WRITE"


def test_web_recon_capability_provider():
    res = WebReconCapabilityProvider.execute_capability(
        capability_name="web_search_global",
        parameters={"target_url": "https://api.internal/health"}
    )
    assert res.success is True
    assert res.data["provider"] == "web_recon_provider"


def test_enterprise_automation_app_end_to_end():
    res = EnterpriseAutomationApp.execute_cross_domain_audit(
        mission_id="mis_enterprise_99",
        target_router="192.168.1.1",
        target_db="finance_prod"
    )

    assert res.success is True
    assert len(res.steps_completed) == 5
    assert "MARIADB_SCHEMA_INSPECTED" in res.steps_completed
    assert "DRIVE_BACKUP_COMPLETED" in res.steps_completed
    assert "excel_report" in res.output_artifacts
