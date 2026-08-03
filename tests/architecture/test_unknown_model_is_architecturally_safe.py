"""
JKAI ZENITH — ARCHITECTURE TEST SUITE: UNKNOWN MODEL SAFETY
tests/architecture/test_unknown_model_is_architecturally_safe.py

Architectural Invariant Enforced:
    When an unseen / unknown model (e.g. 'totally-new-model:17b') is encountered,
    AMG v2 must execute discovery, inspection, capability inference, and safe fallback
    WITHOUT crashing or raising unhandled exceptions.
"""

import pytest
from unittest.mock import patch, MagicMock

from core.governance import ExecutionPolicy, PortfolioGovernor, ExecutionProfile
from core.contracts import TaskRequirement, CapabilityRequirement


class TestUnknownModelSafety:

    def test_unknown_model_auto_discovery_and_safe_fallback(self):
        policy = ExecutionPolicy()
        governor = policy._get_governor()

        # Request an unseen, unregistered model name
        profile = governor.resolve(
            requested_model="totally-new-model:17b",
            role="PLANNER",
            capability_requirements=["reasoning"],
            quality="high"
        )


        # Must return a valid ExecutionProfile without crashing
        assert isinstance(profile, ExecutionProfile)
        assert isinstance(profile.model_name, str)
        assert profile.resolved_via in ("explicit", "auto", "scoring", "emergency_fallback")
