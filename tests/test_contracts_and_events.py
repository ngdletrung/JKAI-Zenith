"""
JKAI ZENITH — CONTRACT KERNEL & EVENT BUS TEST SUITE
tests/test_contracts_and_events.py

Invariants tested:
    C1. All contracts in core.contracts import cleanly with zero external domain dependencies
    C2. IngressGoal, MissionContext, TaskRequirement, ExecutionProfile, ResourceAllocation, Observation instantiate cleanly
    C3. ResourceAllocation contains is_gpu_bound and is_cpu_bound properties
    C4. EventBus publishes events to subscribers asynchronously
    C5. EventBus handles wildcards '*' correctly
"""

import pytest
import asyncio
from unittest.mock import AsyncMock

from core.contracts import (
    IngressGoal, IngressEvent, MissionContext, MissionState,
    TaskRequirement, CapabilityRequirement, ExecutionProfile, ExecutionResult,
    ResourceIntent, ResourceAllocation, ResourceRequest, Observation, Telemetry,
    DomainEvent, ExecutionCompletedEvent, FallbackActivatedEvent
)
from core.events import EventBus, get_event_bus


class TestContractsKernel:

    def test_ingress_contracts(self):
        goal = IngressGoal(prompt="Build a website")
        assert goal.prompt == "Build a website"
        assert goal.goal_id is not None

    def test_mission_contracts(self):
        ctx = MissionContext(goal="Test goal", state=MissionState.RUNNING)
        assert ctx.state == MissionState.RUNNING
        assert ctx.mission_id is not None

    def test_task_contracts(self):
        req = TaskRequirement(
            role="PLANNER",
            capabilities=[CapabilityRequirement(name="reasoning", min_score=0.8)],
            quality_target="high",
        )
        assert req.role == "PLANNER"
        assert req.capabilities[0].name == "reasoning"

    def test_execution_contracts(self):
        profile = ExecutionProfile(
            model_name="qwen3.5:4b",
            role_name="PLANNER",
            num_gpu_layers=32,
        )
        payload = profile.to_ollama_payload(stream=True)
        assert payload["model"] == "qwen3.5:4b"
        assert payload["options"]["num_gpu"] == 32

    def test_resource_contracts(self):
        alloc = ResourceAllocation(backend="GPU", gpu_memory_mb=4000.0, gpu_layers=32)
        assert alloc.is_gpu_bound is True
        assert alloc.is_cpu_bound is False

    def test_observation_contracts(self):
        obs = Observation(task_id="t1", status_code=200, content="Output")
        assert obs.task_id == "t1"
        assert obs.status_code == 200


class TestEventBus:

    def test_event_bus_publish(self):
        bus = EventBus()
        received = []

        async def handler(evt: DomainEvent):
            received.append(evt)

        bus.subscribe("execution.completed", handler)

        evt = ExecutionCompletedEvent(task_id="task_100", result_content="Done")
        asyncio.run(bus.publish(evt))

        assert len(received) == 1
        assert received[0].task_id == "task_100"

    def test_event_bus_wildcard(self):
        bus = EventBus()
        received = []

        async def handler(evt: DomainEvent):
            received.append(evt)

        bus.subscribe("*", handler)

        evt = DomainEvent(event_type="any_type", task_id="task_200")
        asyncio.run(bus.publish(evt))

        assert len(received) == 1
        assert received[0].task_id == "task_200"
