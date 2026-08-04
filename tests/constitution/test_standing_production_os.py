"""
JKAI ZENITH — STANDING PRODUCTION OPERATION TEST SUITE
File: tests/constitution/test_standing_production_os.py

Verifies boot sequence and operational readiness of StandingProductionOS.
"""

import pytest
import sys, os
sys.path.insert(0, ".")
from scripts.run_standing_production_os import StandingProductionOS, OperatingStatus


def test_standing_production_os_boot_sequence():
    status = StandingProductionOS.boot_standing_os()

    assert isinstance(status, OperatingStatus)
    assert status.mode == "STANDING_PRODUCTION_OPERATION"
    assert status.kernel_status == "FROZEN_BY_DEFAULT"
    assert status.architecture_stop is True
    assert status.active_providers_count == 7
    assert status.active_applications_count == 5
    assert status.is_ready_for_operator is True
