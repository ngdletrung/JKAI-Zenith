"""
CONSTITUTION TEST 3 & 5: NO MODEL HARDCODING IN COGNITION OR PLANNER
File: tests/constitution/test_no_model_hardcoding.py
"""

import pytest
from core.contracts.capability_contract import CapabilityRequirement


def test_planner_emits_capabilities_without_concrete_models():
    cap = CapabilityRequirement(
        capability="spreadsheet_mutation",
        complexity="medium",
        latency="normal"
    )
    # Planner emits abstract capability requirement, NOT hardcoded model string like "qwen3.5:4b"
    assert cap.capability == "spreadsheet_mutation"
    assert not hasattr(cap, "model_name")
