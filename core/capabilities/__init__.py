"""
JKAI ZENITH — CAPABILITIES DOMAIN (ACTION DOMAIN)
Package: core/capabilities/

Responsibility:
    Native Tools, Function Calling, Dynamic Skills, and Capability Adapters.

Constitutional Invariant:
    Capabilities represent Action abilities available to JKAI.
    They execute tools and skills, but NEVER hardcode LLM models or hardware flags.
"""

from core.kernel.skill_tool_registry import SkillToolRegistry

__all__ = ["SkillToolRegistry"]
