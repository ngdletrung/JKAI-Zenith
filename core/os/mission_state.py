"""
JKAI AI OS — Mission State

Được tạo sau Intent Classification, dùng xuyên suốt pipeline execution.

Thay vì context bị phân tán qua OSRequestPlan + kwargs + engine.request_cache,
MissionState là single source of truth cho mọi tầng (Planner, Executor, Critic, Synthesizer).
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger("jkai.os.mission")
from core.os.world_state import WorldState
from core.os.execution_plan import ExecutionPlan
from core.os.memory_state import MemoryState


@dataclass
class MissionState:
    goal: str = ""
    original_goal: str = ""
    task_id: str = ""

    os_intent: str = "general"
    pipeline: str = "auto"
    execution_mode: str = "auto"
    routing_manifest: Optional[Any] = None

    constraints: List[str] = field(default_factory=list)
    is_deep: bool = False
    is_fast: bool = False
    use_deep_full: bool = False
    use_cursor_agent: bool = False

    workspace_target: Optional[str] = None
    workspace_mode: Optional[str] = None
    cloned_repos: List[str] = field(default_factory=list)
    fast_fix_file: Optional[str] = None
    web_only_analysis: bool = False

    known_facts: Dict[str, Any] = field(default_factory=dict)
    unknown_facts: List[str] = field(default_factory=list)

    progress: Dict[str, Any] = field(default_factory=lambda: {
        "steps": [],
        "completed": [],
        "pending": [],
        "current_step": None,
    })

    artifacts: Dict[str, Any] = field(default_factory=dict)

    team_pattern: str = "pipeline"
    capability_tags: List[str] = field(default_factory=list)

    trace_id: Optional[str] = None
    log_messages: List[Tuple[str, str]] = field(default_factory=list)
    world_state: Optional[WorldState] = None
    execution_plan: Optional[ExecutionPlan] = None
    memory_state: Optional[MemoryState] = None

    @classmethod
    def from_os_plan(
        cls,
        plan: Any,
        goal: str,
        original_goal: str,
        task_id: str,
        kwargs: dict,
        trace_id: Optional[str] = None,
    ) -> MissionState:
        ms = cls(
            goal=goal,
            original_goal=original_goal,
            task_id=task_id,
            os_intent=plan.os_intent,
            pipeline=plan.pipeline,
            execution_mode=plan.execution_mode,
            is_deep=plan.is_deep,
            is_fast=plan.is_fast,
            use_deep_full=plan.use_deep_full,
            use_cursor_agent=plan.use_cursor_agent,
            team_pattern=plan.team_pattern,
            capability_tags=list(plan.capability_tags),
            workspace_target=kwargs.get("jkai_workspace_target"),
            workspace_mode=kwargs.get("jkai_project_mode"),
            cloned_repos=kwargs.get("jkai_cloned_repos", []),
            fast_fix_file=kwargs.get("jkai_fast_fix_file"),
            web_only_analysis=kwargs.get("jkai_web_only_analysis", False),
            trace_id=trace_id or task_id,
        )
        ms._build_constraints()
        ms._build_known_facts(plan, kwargs)
        return ms

    def _build_constraints(self) -> None:
        c: List[str] = []
        if self.is_deep:
            c.append("deep_analysis")
        if self.is_fast:
            c.append("low_latency")
        if self.web_only_analysis:
            c.append("web_only")
        if self.fast_fix_file:
            c.append("single_file_fix")
        if self.workspace_target:
            c.append("workspace_aware")
        self.constraints = c

    def _build_known_facts(self, plan: Any, kwargs: dict) -> None:
        facts: Dict[str, Any] = {}
        if self.workspace_target:
            facts["workspace"] = {
                "path": self.workspace_target,
                "mode": self.workspace_mode,
            }
        if self.cloned_repos:
            facts["cloned_repos"] = self.cloned_repos
        if self.fast_fix_file:
            facts["fast_fix_target"] = self.fast_fix_file
        if self.os_intent:
            facts["os_intent"] = self.os_intent
        if self.routing_manifest:
            facts["primary_intent"] = str(
                getattr(self.routing_manifest, "primary_intent", "")
            )
            facts["complexity"] = getattr(
                self.routing_manifest, "complexity_score", 0.0
            )
        resolved = kwargs.get("resolved_skill_ids")
        if resolved:
            facts["resolved_skill_ids"] = resolved
        mission_id = kwargs.get("mission_id")
        if mission_id:
            facts["mission_id"] = mission_id
        self.known_facts = facts

    def set_unknown(self, items: List[str]) -> None:
        self.unknown_facts = items

    def mark_step_completed(self, step: str, result: Any = None) -> None:
        if step not in self.progress["completed"]:
            self.progress["completed"].append(step)
        if step in self.progress["pending"]:
            self.progress["pending"].remove(step)
        if result is not None:
            self.artifacts[step] = result
        self.progress["current_step"] = None

    def mark_step_pending(self, step: str) -> None:
        if step not in self.progress["pending"] and step not in self.progress["completed"]:
            self.progress["pending"].append(step)
        self.progress["current_step"] = step

    def add_log(self, tag: str, msg: str) -> None:
        self.log_messages.append((tag, msg))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "goal": self.goal,
            "original_goal": self.original_goal,
            "task_id": self.task_id,
            "os_intent": self.os_intent,
            "pipeline": self.pipeline,
            "execution_mode": self.execution_mode,
            "constraints": self.constraints,
            "is_deep": self.is_deep,
            "is_fast": self.is_fast,
            "workspace_target": self.workspace_target,
            "workspace_mode": self.workspace_mode,
            "known_facts": self.known_facts,
            "unknown_facts": self.unknown_facts,
            "progress": self.progress,
            "team_pattern": self.team_pattern,
            "capability_tags": self.capability_tags,
            "trace_id": self.trace_id,
            "world_state": self.world_state.model_dump() if self.world_state else None,
            "execution_plan": self.execution_plan.model_dump() if self.execution_plan else None,
            "memory_state": self.memory_state.model_dump() if self.memory_state else None,
        }
