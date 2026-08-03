"""
JKAI ZENITH — CONTRACT KERNEL: TASK
File: core/contracts/task.py

Contracts for TaskRequirement and CapabilityRequirement.
Expresses WHAT capability is needed without model or runtime details.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class CapabilityRequirement:
    """Individual capability requirement (e.g. reasoning, coding, vision)."""
    name: str                            # "reasoning" | "coding" | "tool_use" | "planning" | "vision" | "embedding"
    min_score: float = 0.5               # 0.0 - 1.0 required score
    weight: float = 1.0


@dataclass
class TaskRequirement:
    """
    Cognitive -> Governance contract.
    Expresses semantic task intent derived from Cognitive Kernel.
    """
    role: str                            # "PLANNER", "RECEPTIONIST", "EXECUTOR", etc.
    capabilities: List[CapabilityRequirement] = field(default_factory=list)
    quality_target: str = "medium"       # "low" | "medium" | "high" | "highest"
    latency_target: str = "medium"       # "low" | "medium" | "high"
    min_ctx: int = 4096
    requires_tools: bool = False
    requires_vision: bool = False
    metadata: Dict[str, Any] = field(default_factory=dict)
