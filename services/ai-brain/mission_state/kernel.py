# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/mission_state/kernel.py
# - Role: State Event Bus, Reducer, and MissionRuntime Engine
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v1.0

import asyncio
import logging
from typing import Callable, List, Dict, Any, Union
from datetime import datetime

from .schema import (
    MissionState,
    MissionMetadata,
    MissionFacts,
    MissionPlanner,
    MissionBudget,
    ScopedMemory,
    MissionReferences,
    MissionEvent,
)

logger = logging.getLogger("JKAI.MissionKernel")

class MissionEventBus:
    """Async Event Bus supporting wildcard subscriptions."""
    def __init__(self):
        self._subscribers: Dict[str, List[Callable]] = {}

    def subscribe(self, event_type: str, callback: Callable):
        if event_type not in self._subscribers:
            self._subscribers[event_type] = []
        self._subscribers[event_type].append(callback)

    async def publish(self, event: MissionEvent):
        # Notify specific subscribers
        tasks = []
        if event.event_type in self._subscribers:
            for cb in self._subscribers[event.event_type]:
                tasks.append(asyncio.create_task(cb(event)))
        # Notify wildcard subscribers
        if "*" in self._subscribers:
            for cb in self._subscribers["*"]:
                tasks.append(asyncio.create_task(cb(event)))
        
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

class MissionReducer:
    """Pure functions to compute new state from event and current state."""
    @staticmethod
    def apply(state: MissionState, event: MissionEvent) -> MissionState:
        # Immutable state update by copying
        new_state = state.model_copy(deep=True)
        t = event.event_type
        p = event.payload

        if t == "MissionStarted":
            new_state.lifecycle = "RUNNING"
        elif t == "MissionCompleted":
            new_state.lifecycle = "SUCCESS"
        elif t == "MissionFailed":
            new_state.lifecycle = "FAILED"
            new_state.planner.blocked_by = p.get("reason")
        elif t == "TaskBlocked":
            new_state.lifecycle = "BLOCKED"
            new_state.planner.blocked_by = p.get("reason")
        elif t == "TaskResumed":
            new_state.lifecycle = "RUNNING"
            new_state.planner.blocked_by = None
        elif t == "CostIncurred":
            new_state.budget.current_cost_usd += p.get("cost", 0.0)
            new_state.budget.total_prompt_tokens += p.get("prompt_tokens", 0)
            new_state.budget.total_completion_tokens += p.get("completion_tokens", 0)
            new_state.budget.api_calls_count += p.get("api_calls", 0)
            new_state.budget.search_calls_count += p.get("search_calls", 0)
            new_state.budget.tool_calls_count += p.get("tool_calls", 0)
        elif t == "PlanUpdated":
            new_state.planner.current_plan = p.get("plan", [])
        elif t == "StepCompleted":
            step = p.get("step")
            if step:
                if step in new_state.planner.current_plan:
                    new_state.planner.current_plan.remove(step)
                if step not in new_state.planner.completed_steps:
                    new_state.planner.completed_steps.append(step)
        elif t == "StepConfidenceRecorded":
            step = p.get("step")
            conf = p.get("confidence", 1.0)
            if step:
                new_state.planner.step_confidence[step] = conf
        elif t == "EntityResolved":
            entity = p.get("entity")
            if entity:
                # Add to stack, keep last 10
                new_state.active_entity_stack.append({
                    "entity": entity,
                    "confidence": p.get("confidence", 1.0),
                    "resolved_at": datetime.utcnow().isoformat()
                })
                new_state.active_entity_stack = new_state.active_entity_stack[-10:]
        elif t == "MemoryUpdated":
            scope = p.get("scope", "mission")
            key = p.get("key")
            val = p.get("value")
            if key:
                if scope == "global":
                    new_state.memory.global_memory[key] = val
                elif scope == "mission":
                    new_state.memory.mission_memory[key] = val
                elif scope == "tool":
                    new_state.memory.tool_memory[key] = val
                else: # agent scope
                    agent_name = scope
                    if agent_name not in new_state.memory.agent_memory:
                        new_state.memory.agent_memory[agent_name] = {}
                    new_state.memory.agent_memory[agent_name][key] = val
        elif t == "ToolMemoryCleared":
            new_state.memory.tool_memory.clear()
        
        return new_state

class MissionRuntime:
    """The Mission Kernel controlling state, event flow, and capabilities."""
    def __init__(self, user_goal: str, constraints: List[str] = None, model_profile: str = "default"):
        metadata = MissionMetadata(
            user_goal=user_goal,
            initial_constraints=constraints or [],
            model_profile=model_profile
        )
        self.state = MissionState(
            metadata=metadata,
            facts=MissionFacts(),
            planner=MissionPlanner(),
            budget=MissionBudget(),
            memory=ScopedMemory(),
            references=MissionReferences()
        )
        self.event_bus = MissionEventBus()
        self.reducer = MissionReducer()
        self.event_log: List[MissionEvent] = []
        self.snapshots: Dict[int, MissionState] = {} # Step ID -> state copy
        
        # Subscribe local handlers
        self.event_bus.subscribe("*", self._process_state_update)
        
        # Registry for capabilities (decoupling planner from tool execution)
        self._capabilities: Dict[str, Callable] = {}

    async def _process_state_update(self, event: MissionEvent):
        # Prevent infinite loops in handler
        self.event_log.append(event)
        self.state = self.reducer.apply(self.state, event)
        step_id = len(self.event_log)
        self.snapshots[step_id] = self.state.model_copy(deep=True)
        
        # Budget check
        if self.state.budget.current_cost_usd >= self.state.budget.max_cost_usd:
            logger.warning("[BUDGET-EXCEEDED] %s >= %s. Terminating.", self.state.budget.current_cost_usd, self.state.budget.max_cost_usd)
            await self.emit("MissionFailed", {"reason": "Budget limit exceeded"})

    async def emit(self, event_type: str, payload: Dict[str, Any]):
        event = MissionEvent(
            mission_id=self.state.metadata.mission_id,
            event_type=event_type,
            payload=payload
        )
        await self.event_bus.publish(event)

    async def rollback(self, step_id: int):
        """Roll back state to a specific historical step (Time Travel)."""
        if step_id in self.snapshots:
            self.state = self.snapshots[step_id].model_copy(deep=True)
            self.event_log = self.event_log[:step_id]
            logger.info("[ROLLBACK] State rolled back to step %s.", step_id)
            await self.emit("StateRollbacked", {"target_step": step_id})
        else:
            logger.error("[ROLLBACK-ERR] Step %s not found in snapshots.", step_id)

    # Capability Registry Actions
    def register_capability(self, name: str, handler: Callable):
        self._capabilities[name] = handler
        logger.info("[CAPABILITY-REGISTERED] %s", name)

    async def execute_capability(self, name: str, *args, **kwargs) -> Any:
        if name not in self._capabilities:
            raise ValueError(f"Capability '{name}' is not registered.")
        
        logger.info("[EXEC-CAPABILITY] %s with args=%s, kwargs=%s", name, args, kwargs)
        await self.emit("CostIncurred", {"tool_calls": 1})
        try:
            res = await self._capabilities[name](*args, **kwargs)
            return res
        except Exception as e:
            logger.error("[CAPABILITY-ERR] %s failed: %s", name, e)
            raise e
