"""
JKAI ZENITH — MIKROTIK NETWORK CAPABILITY PROVIDER TEST SUITE
File: tests/constitution/test_mikrotik_provider_extension.py

Verifies READ (automatic) vs WRITE (Policy Gate Authorized) capabilities on MikrotikNetworkCapabilityProvider.
"""

import pytest
from intelligence.capabilities.mikrotik_provider import (
    MikrotikNetworkCapabilityProvider,
    AuthorizationSpec
)


def test_mikrotik_read_capability_auto_execution():
    res = MikrotikNetworkCapabilityProvider.execute_capability(
        capability_name="mikrotik_get_interface_stats",
        parameters={"router_ip": "10.0.0.1"}
    )

    assert res.success is True
    assert res.access_level == "READ"
    assert res.data["status"] == "COMPLETED"
    assert res.data["provider"] == "mikrotik_network_provider"


def test_mikrotik_write_capability_policy_denial_without_scope():
    res = MikrotikNetworkCapabilityProvider.execute_capability(
        capability_name="mikrotik_update_firewall_rule",
        parameters={"router_ip": "10.0.0.1", "action": "drop", "src": "192.168.1.100"}
    )

    assert res.success is False
    assert "POLICY DENIED" in res.error_message


def test_mikrotik_write_capability_authorized_execution():
    auth = AuthorizationSpec(granted_scopes=["network:read", "network:write"])
    res = MikrotikNetworkCapabilityProvider.execute_capability(
        capability_name="mikrotik_update_firewall_rule",
        parameters={"router_ip": "10.0.0.1", "action": "drop", "src": "192.168.1.100"},
        auth_spec=auth
    )

    assert res.success is True
    assert res.access_level == "WRITE"
    assert res.audit_trail["authorized"] is True
    assert res.data["status"] == "COMPLETED"
