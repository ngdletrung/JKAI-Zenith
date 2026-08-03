"""
JKAI ZENITH — COGNITIVE PLANE (PLANE 2)
Directory: core/cognitive/

Responsibility:
    High-level Mission & Intent orchestration, Cognitive Cycle execution,
    Planner, Agent Loops, and Skill/ReAct orchestration.

Constitutional Invariant:
    Modules in core/cognitive must NEVER import model names, VRAM sizes,
    GPU lane indices, or inference server endpoints.
    They express work as TaskRequirement, receiving ExecutionProfile from Governance.
"""

from core.utils.engine import JKAIIntelligenceEngine as CognitiveEngine

__all__ = ["CognitiveEngine"]
