"""
JKAI ZENITH — PRODUCTION HARDENING P4: RESOURCE PRESSURE TEST
File: tests/constitution/test_p4_resource_pressure.py

Verifies hardware safety boundaries (VRAM < 7.5GB, RAM < 110GB) under RX 6600 & Xeon E5-2699 v4.
"""

import pytest
from core.capabilities.resource_pressure_governor import ResourcePressureGovernor


def test_p4_hardware_resource_pressure_limits():
    metrics = ResourcePressureGovernor.evaluate_hardware_pressure(active_models_count=2)
    assert metrics.is_safe is True
    assert metrics.vram_peak_gb <= 7.5
    assert metrics.ram_peak_gb <= 110.0
