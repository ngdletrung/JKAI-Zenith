"""
JKAI ZENITH — MISSION CONTROL DASHBOARD WEB TEST SUITE
File: tests/constitution/test_mission_control_dashboard_exists.py

Verifies existence and HTML structure of web/mission_control_dashboard.html.
"""

import pytest
import os


def test_mission_control_dashboard_file_exists():
    dashboard_path = os.path.join("web", "mission_control_dashboard.html")
    assert os.path.exists(dashboard_path) is True

    with open(dashboard_path, "r", encoding="utf-8") as f:
        content = f.read()

    assert "JKAI ZENITH AI OS" in content
    assert "PRODUCTION-PROVEN ADAPTIVE COGNITIVE AI OS PLATFORM" in content
    assert "Identity Chain Traceability" in content
    assert "AMD RX 6600" in content
