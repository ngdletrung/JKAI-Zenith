"""
JKAI ZENITH — PLANNING LAYER: TASK GRAPH & DAG NODES (v2.1)
File: core/planning/task_graph.py

Định nghĩa Đồ Thị Tác Chiến Hướng Chu Trình (DAG Task Graph).
Mỗi TaskNode phát ra CapabilityRequirement abstract (không hardcode model name).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from core.contracts.cognitive_contract import IdentityChain
from core.contracts.capability_contract import CapabilityRequirement


@dataclass(frozen=True)
class TaskNode:
    """Nút tác chiến trong DAG Task Graph."""
    identity: IdentityChain
    description: str
    requirement: CapabilityRequirement
    dependencies: List[str] = field(default_factory=list)
    completed: bool = False


@dataclass(frozen=True)
class TaskGraph:
    """Đồ thị DAG chứa danh sách các nút tác chiến."""
    identity: IdentityChain
    nodes: List[TaskNode] = field(default_factory=list)
    estimated_cost: float = 1.0
