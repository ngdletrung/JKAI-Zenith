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
from core.contracts.mission import MissionContext, MissionState
from core.contracts.task import TaskRequirement, CapabilityRequirement
from core.contracts.execution import ExecutionProfile, ExecutionIntent, ExecutionResult
from core.contracts.resource import ResourceIntent, ResourceAllocation, ResourceRequest
from core.contracts.observation import Observation, Telemetry
from core.contracts.events import DomainEvent, ExecutionCompletedEvent, FallbackActivatedEvent

__all__ = [
    "IngressGoal",
    "IngressEvent",
    "MissionContext",
    "MissionState",
    "TaskRequirement",
    "CapabilityRequirement",
    "ExecutionProfile",
    "ExecutionIntent",
    "ExecutionResult",
    "ResourceIntent",
    "ResourceAllocation",
    "ResourceRequest",
    "Observation",
    "Telemetry",
    "DomainEvent",
    "ExecutionCompletedEvent",
    "FallbackActivatedEvent",
]

