"""
JKAI ZENITH AI OS — TASK PROFILER
File: core/os/cognition/task_profiler.py

Computes multi-dimensional TaskProfile signals from input goal, history, and context.
Separates Task Complexity from Execution Topology.
"""

from __future__ import annotations
import re
from dataclasses import dataclass, field
from typing import Dict, Any, List, Set, Optional


@dataclass
class TaskProfile:
    """Multi-dimensional profile of a user request."""
    complexity: float = 0.0        # Estimated cognitive demand (0.0 to 1.0)
    risk: float = 0.0              # Safety and system risk (0.0 to 1.0)
    uncertainty: float = 0.0       # Ambiguity and knowledge gap (0.0 to 1.0)
    side_effects: bool = False     # Causes system/environment side-effects
    statefulness: bool = False     # Requires state tracking across steps
    mutation_scope: str = "NONE"   # NONE, SINGLE_FILE, MULTI_FILE, SYSTEM_STATE
    tool_breadth: int = 0          # Estimated number of tool types needed
    verification_need: str = "LOW" # LOW, MEDIUM, HIGH, CRITICAL
    reason_codes: List[str] = field(default_factory=list)


def profile_task(goal: str, history: Optional[List] = None, kwargs: Optional[Dict[str, Any]] = None) -> TaskProfile:
    """
    Computes a multi-dimensional TaskProfile from goal text and context signals.
    """
    g = (goal or "").strip().lower()
    kw = kwargs or {}
    profile = TaskProfile()

    # 1. Check Capability Acknowledgement / Greeting / Math (REFLEX signals)
    from core.utils.jkai_capabilities import goal_is_capabilities_inquiry
    if goal_is_capabilities_inquiry(goal):
        profile.reason_codes.append("CAPABILITY_QUERY")
        profile.verification_need = "LOW"
        return profile

    if re.search(r"^(xin chào|chào|hello|hi|cảm ơn|thanks|tạm biệt|bye)\b", g):
        profile.reason_codes.append("GREETING_SOCIAL")
        profile.verification_need = "LOW"
        return profile

    # 2. Risk & Mutation Scope Analysis
    if re.search(r"\b(xóa|drop|rm\s+-rf|truncate|systemctl\s+stop|flush\s+iptables|delete\s+database|format\s+disk)\b", g):
        profile.risk = 1.0
        profile.side_effects = True
        profile.mutation_scope = "SYSTEM_STATE"
        profile.verification_need = "CRITICAL"
        profile.reason_codes.append("HIGH_RISK_DESTRUCTIVE_COMMAND")
        return profile

    # 3. Multi-file & Architectural Scope Analysis
    if re.search(r"\b(tái\ thiết\ kế|microservice|toàn\ bộ\ pipeline|viết\ lại\ core|architecture|refactor\ project)\b", g):
        profile.complexity = 0.85
        profile.uncertainty = 0.6
        profile.mutation_scope = "MULTI_FILE"
        profile.verification_need = "HIGH"
        profile.reason_codes.append("ARCHITECTURAL_MULTI_FILE")
    elif re.search(r"\b(sửa|fix|update|tạo|create|viết|write)\b", g):
        profile.complexity = 0.4
        profile.mutation_scope = "SINGLE_FILE"
        profile.verification_need = "MEDIUM"
        profile.reason_codes.append("SINGLE_FILE_ACTION")
    elif re.search(r"\b(xem|đọc|read|check|kiểm\ tra|quét|scan)\b", g):
        profile.complexity = 0.2
        profile.mutation_scope = "NONE"
        profile.verification_need = "LOW"
        profile.reason_codes.append("READ_ONLY_INSPECTION")

    return profile
