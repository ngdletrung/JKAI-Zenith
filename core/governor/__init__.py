"""
🏛️ ADAPTIVE MODEL GOVERNOR (AMG) v2 — PUBLIC API
File: core/governor/__init__.py

Exports the clean public surface of the AMG subsystem.
Consumers (engine.py, model_router.py, etc.) import from here.
"""

from core.governor.model_capabilities import (
    ModelClass,
    ModelPool,
    ModelMemoryProfile,
    CapabilityEvidence,
    ModelCapabilityProfile,
    ModelScore,
    GovernorDecision,
    ExecutionProfile,
    RoleRequirement,
    ROLE_CLASS_WEIGHTS,
    ROLE_MINIMUM_CAPABILITY,
    ROLE_REQUIREMENTS,
)
from core.governor.hardware_monitor import HardwareMonitor, HardwareState
from core.governor.model_registry import ModelRegistry
from core.governor.model_inspector import ModelInspector
from core.governor.resource_governor import ResourceGovernor, BackendAllocation
from core.governor.model_scorer import ModelScorer
from core.governor.portfolio_governor import PortfolioGovernor
from core.governor.execution_policy import ExecutionPolicy

__all__ = [
    # Data model
    "ModelClass",
    "ModelPool",
    "ModelMemoryProfile",
    "CapabilityEvidence",
    "ModelCapabilityProfile",
    "ModelScore",
    "GovernorDecision",
    "ExecutionProfile",
    "RoleRequirement",
    "ROLE_CLASS_WEIGHTS",
    "ROLE_MINIMUM_CAPABILITY",
    "ROLE_REQUIREMENTS",
    # Hardware
    "HardwareMonitor",
    "HardwareState",
    # AMG Pipeline
    "ModelRegistry",
    "ModelInspector",
    "ResourceGovernor",
    "BackendAllocation",
    "ModelScorer",
    "PortfolioGovernor",
    "ExecutionPolicy",
]
