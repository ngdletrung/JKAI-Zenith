"""
JKAI ZENITH — CAPABILITIES DOMAIN (ACTION DOMAIN)
Package: core/capabilities/

Responsibility:
    Native Tools, Function Calling, Dynamic Skills, Capability Broker, and Adapters.

Constitutional Invariant:
    Capabilities represent Action abilities available to JKAI.
    They execute tools and skills, but NEVER hardcode LLM models or hardware flags.
"""

from core.kernel.skill_tool_registry import SkillToolRegistry
from core.capabilities.capability_broker import CapabilityBroker, CapabilitySet

__all__ = [
    "SkillToolRegistry",
    "CapabilityBroker",
    "CapabilitySet",
]
