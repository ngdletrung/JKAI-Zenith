"""
JKAI ZENITH — PROACTIVE ECOSYSTEM EXPANSION TEST SUITE
File: tests/constitution/test_proactive_ecosystem_expansion.py

Verifies PostgresCapabilityProvider, SmtpMailCapabilityProvider, and ZeroTrustSecurityIncidentApp.
"""

import pytest
from intelligence.capabilities.postgres_provider import PostgresCapabilityProvider
from intelligence.capabilities.smtp_mail_provider import SmtpMailCapabilityProvider
from intelligence.capabilities.mikrotik_provider import AuthorizationSpec
from intelligence.applications.zero_trust_security_incident_app import ZeroTrustSecurityIncidentApp


def test_postgres_capability_provider_policy_gate():
    # Read query
    read_res = PostgresCapabilityProvider.execute_capability("postgres_execute_query", {"database": "pg_test"})
    assert read_res.success is True

    # Write denied
    write_denied = PostgresCapabilityProvider.execute_capability("postgres_execute_mutation", {"database": "pg_test"})
    assert write_denied.success is False

    # Write authorized
    auth = AuthorizationSpec(granted_scopes=["postgres:write"])
    write_auth = PostgresCapabilityProvider.execute_capability("postgres_execute_mutation", {"database": "pg_test"}, auth_spec=auth)
    assert write_auth.success is True


def test_smtp_mail_capability_provider_policy_gate():
    # Denied without scope
    denied = SmtpMailCapabilityProvider.execute_capability("smtp_send_security_alert", {"recipient": "master@jkai"})
    assert denied.success is False

    # Authorized with mail:send scope
    auth = AuthorizationSpec(granted_scopes=["mail:send"])
    auth_res = SmtpMailCapabilityProvider.execute_capability("smtp_send_security_alert", {"recipient": "master@jkai"}, auth_spec=auth)
    assert auth_res.success is True


def test_zero_trust_security_incident_app_end_to_end():
    auth = AuthorizationSpec(granted_scopes=["network:write", "mail:send", "postgres:write"])
    res = ZeroTrustSecurityIncidentApp.execute_incident_response_pipeline(
        mission_id="mis_zt_001",
        target_url="https://sec.internal",
        target_db="sec_pg_db",
        target_router="192.168.88.1",
        alert_recipient="master@jkai.internal",
        drive_folder="zt_backups",
        auth_spec=auth
    )

    assert res.success is True
    assert res.threat_mitigated is True
    assert res.alert_sent is True
    assert res.report_file == "exports/mis_zt_001_zero_trust_incident.xlsx"
    assert res.drive_backup_id != ""
