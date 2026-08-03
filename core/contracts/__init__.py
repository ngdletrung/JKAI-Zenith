"""
JKAI ZENITH — CONTRACT KERNEL
Package: core/contracts/

Responsibility:
    Pure, zero-dependency data contracts for communication across the 5 Domains.
    Contains ONLY dataclasses, Enums, and type definitions.

Constitutional Invariant:
    Modules in core/contracts MUST NEVER import from core.cognitive, core.governance,
    core.knowledge, core.capabilities, core.runtime, or core.infrastructure.
"""

from core.contracts.ingress import IngressGoal, IngressEvent
from core.contracts.mission import MissionContext, MissionState, SuccessCriteria, MissionContract
from core.contracts.task import TaskRequirement, CapabilityRequirement

from core.contracts.execution import ExecutionProfile, ExecutionIntent, ExecutionResult, GovernorDecision, ExecutionLease, ResourceGrant
from core.contracts.resource import ResourceIntent, ResourceAllocation, ResourceRequest, BackendType
from core.contracts.observation import Observation, Telemetry, EvaluationResult
from core.contracts.events import DomainEvent, ExecutionCompletedEvent, FallbackActivatedEvent

__all__ = [
    "IngressGoal",
    "IngressEvent",
    "MissionContext",
    "MissionState",
    "SuccessCriteria",
    "MissionContract",
    "TaskRequirement",
    "CapabilityRequirement",
    "ExecutionProfile",
    "ExecutionIntent",
    "ExecutionResult",
    "ExecutionLease",
    "GovernorDecision",
    "ResourceIntent",
    "ResourceAllocation",
    "ResourceRequest",
    "BackendType",
    "Observation",
    "Telemetry",
    "EvaluationResult",
    "DomainEvent",
    "ExecutionCompletedEvent",
    "FallbackActivatedEvent",
]
