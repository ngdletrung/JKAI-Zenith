"""
core/os/cognition/adaptive_solver/causal_graph.py
P0-3: Causal Execution Graph (Causal Provenance & Multi-Turn Diagnostics).

Maintains a directed causal graph of every agent action:
Cause -> Action -> Effect -> Evidence -> Verification.

Allows JKAI to trace back across 5-30 minute long-running tasks, identify root causes
of failures, and understand why specific replans and targeted repairs were initiated.
"""

from __future__ import annotations
import time
from dataclasses import asdict, dataclass, field
from typing import Any, Dict, List, Optional


@dataclass
class CausalNode:
    """An atomic action step within the causal execution graph."""
    action_id: str
    parent_action_id: Optional[str]
    cause: str                      # Why this action was initiated
    tool_name: str                  # Which capability was invoked
    arguments: Dict[str, Any]       # Concrete inputs
    expected_effect: str            # What was supposed to happen
    actual_effect: str              # What actually happened on disk/system
    evidence: Optional[str] = None  # Physical storage proof / test output
    verification_status: str = "PENDING"  # PASSED | FAILED | PENDING | BYPASSED
    created_at: float = field(default_factory=time.time)


class CausalExecutionGraph:
    """Directed Acyclic Graph tracking causal execution chains for a Mission."""

    def __init__(self, mission_id: str):
        self.mission_id = mission_id
        self._nodes: Dict[str, CausalNode] = {}
        self._children: Dict[str, List[str]] = {}

    def record_action(
        self,
        action_id: str,
        cause: str,
        tool_name: str,
        arguments: Dict[str, Any],
        expected_effect: str,
        actual_effect: str,
        parent_action_id: Optional[str] = None,
        evidence: Optional[str] = None,
        verification_status: str = "PENDING"
    ) -> CausalNode:
        """Records a new causal node in the execution graph."""
        node = CausalNode(
            action_id=action_id,
            parent_action_id=parent_action_id,
            cause=cause,
            tool_name=tool_name,
            arguments=arguments,
            expected_effect=expected_effect,
            actual_effect=actual_effect,
            evidence=evidence,
            verification_status=verification_status
        )
        self._nodes[action_id] = node

        if parent_action_id:
            if parent_action_id not in self._children:
                self._children[parent_action_id] = []
            self._children[parent_action_id].append(action_id)

        return node

    def update_verification(self, action_id: str, status: str, evidence: Optional[str] = None):
        """Updates verification status and physical evidence for an action node."""
        if action_id in self._nodes:
            self._nodes[action_id].verification_status = status
            if evidence:
                self._nodes[action_id].evidence = evidence

    def get_causal_chain(self, action_id: str) -> List[CausalNode]:
        """Traces back the causal ancestry from a specific action to the root trigger."""
        chain = []
        curr_id = action_id
        while curr_id and curr_id in self._nodes:
            node = self._nodes[curr_id]
            chain.append(node)
            curr_id = node.parent_action_id
        chain.reverse()
        return chain

    def get_failed_branches(self) -> List[CausalNode]:
        """Returns all action nodes that resulted in verification failures."""
        return [node for node in self._nodes.values() if node.verification_status == "FAILED"]

    def to_dict(self) -> Dict[str, Any]:
        """Exports full causal graph for mission ledger and audit artifacts."""
        return {
            "mission_id": self.mission_id,
            "total_actions": len(self._nodes),
            "nodes": {k: asdict(v) for k, v in self._nodes.items()},
            "failed_count": len(self.get_failed_branches())
        }
