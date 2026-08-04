"""
JKAI ZENITH — NETWORK INFRASTRUCTURE AI APP TEST SUITE
File: tests/constitution/test_network_infrastructure_ai.py

Verifies NetworkInfrastructureAIApp end-to-end execution with READ (automatic) vs WRITE (Policy Gate) capabilities.
"""

import pytest
from intelligence.applications.network_infrastructure_ai import NetworkInfrastructureAIApp
from intelligence.capabilities.mikrotik_provider import AuthorizationSpec


def test_network_infrastructure_ai_app_read_only_remediation():
    res = NetworkInfrastructureAIApp.execute_network_incident_remediation(
        mission_id="mis_net_read_01",
        target_router="192.168.88.1",
        target_db="net_db",
        drive_folder="net_logs"
    )

    assert res.success is True
    assert res.remediation_applied is False
    assert res.incident_type == "HIGH_TRAFFIC_SPIKE"
    assert res.drive_backup_id != ""


def test_network_infrastructure_ai_app_authorized_write_remediation():
    auth = AuthorizationSpec(granted_scopes=["network:read", "network:write"])
    res = NetworkInfrastructureAIApp.execute_network_incident_remediation(
        mission_id="mis_net_write_02",
        target_router="192.168.88.1",
        target_db="net_db",
        drive_folder="net_logs",
        auth_spec=auth
    )

    assert res.success is True
    assert res.remediation_applied is True
    assert res.incident_type == "HIGH_TRAFFIC_SPIKE"
    assert res.report_path == "exports/mis_net_write_02_network_remediation.xlsx"
