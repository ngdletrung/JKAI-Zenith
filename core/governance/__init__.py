"""
JKAI ZENITH — GOVERNANCE / DECISION PLANE (PLANE 4 — AMG v2)
Directory: core/governance/

Responsibility:
    Model Intelligence, Capability Matching, ExecutionPolicy, PortfolioGovernor,
    ResourceGovernor, and DecisionTrace audit logging.

Constitutional Invariant:
    Governance converts TaskRequirement -> ExecutionProfile -> ResourceRequest.
    Governance is completely model-blind in its scoring math.
"""

from core.governor.model_capabilities import (
    ExecutionProfile, ModelCapabilityProfile, ModelClass, ModelPool,
    CapabilityEvidence, ModelMemoryProfile, RoleRequirement
)
from core.governor.portfolio_governor import PortfolioGovernor
from core.governor.resource_governor import ResourceGovernor
from core.governor.model_inspector import ModelInspector
from core.governor.model_registry import ModelRegistry
from core.governor.execution_policy import ExecutionPolicy
from core.governor.decision_trace import DecisionTrace, DecisionTracer, get_tracer

__all__ = [
    "ExecutionProfile",
    "ModelCapabilityProfile",
    "ModelClass",
    "ModelPool",
    "CapabilityEvidence",
    "ModelMemoryProfile",
    "RoleRequirement",
    "PortfolioGovernor",
    "ResourceGovernor",
    "ModelInspector",
    "ModelRegistry",
    "ExecutionPolicy",
    "DecisionTrace",
    "DecisionTracer",
    "get_tracer",
]
