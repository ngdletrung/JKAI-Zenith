"""
JKAI ZENITH — MIKROTIK NETWORK CAPABILITY PROVIDER TEST SUITE
File: tests/constitution/test_mikrotik_provider_extension.py

Verifies horizontal extension of MikrotikNetworkCapabilityProvider.
"""

import pytest
from intelligence.capabilities.mikrotik_provider import MikrotikNetworkCapabilityProvider


def test_mikrotik_network_capability_provider():
    res = MikrotikNetworkCapabilityProvider.execute_capability(
        capability_name="mikrotik_get_interface_stats",
        parameters={"router_ip": "10.0.0.1"}
    )

    assert res.success is True
    assert res.data["status"] == "COMPLETED"
    assert res.data["provider"] == "mikrotik_network_provider"
    assert res.data["router_ip"] == "10.0.0.1"
