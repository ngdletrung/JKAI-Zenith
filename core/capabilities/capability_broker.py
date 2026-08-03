"""
JKAI ZENITH — CAPABILITIES DOMAIN: CAPABILITY BROKER
File: core/capabilities/capability_broker.py

Matches TaskRequirement intent against registered tools, skills, and adapters.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from core.contracts import TaskRequirement


@dataclass
class CapabilitySet:
    """Consolidated set of resolved tools, skills, and action capabilities for a Task."""
    tools: List[Dict[str, Any]] = field(default_factory=list)
    skills: List[str] = field(default_factory=list)
    adapters: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)


class CapabilityBroker:
    """Brokers and negotiates capability sets based on TaskRequirement."""

    def __init__(self):
        self._tool_registry: Dict[str, Dict[str, Any]] = {}
        self._skill_registry: List[str] = []

    def register_tool(self, tool_name: str, schema: Dict[str, Any]):
        self._tool_registry[tool_name] = schema

    def register_skill(self, skill_name: str):
        if skill_name not in self._skill_registry:
            self._skill_registry.append(skill_name)

    def resolve_capabilities(self, task_req: TaskRequirement) -> CapabilitySet:
        resolved_tools = []
        resolved_skills = []

        if task_req.requires_tools:
            resolved_tools = list(self._tool_registry.values())
            resolved_skills = list(self._skill_registry)

        return CapabilitySet(
            tools=resolved_tools,
            skills=resolved_skills,
            metadata={"requires_vision": task_req.requires_vision}
        )
