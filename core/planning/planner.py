"""
JKAI ZENITH — PLANNING LAYER: PLANNER ENGINE (v2.1)
File: core/planning/planner.py

Lập Kế Hoạch Đồ Thị Task Graph (DAG) từ MissionDefinition.
Hiến pháp #5: Planner phát ra CapabilityRequirement, tuyệt đối KHÔNG tự chọn model hay hardcode model name.
"""

from __future__ import annotations
import logging
from typing import Dict, Any, List

from core.contracts.cognitive_contract import MissionDefinition, IdentityChain, DeliverableType
from core.contracts.capability_contract import CapabilityRequirement
from core.planning.task_graph import TaskGraph, TaskNode

logger = logging.getLogger("jkai.planning.planner")


class CognitivePlanner:
    """Bộ Lập Kế Hoạch Tác Chiến (Cognitive Planner)."""

    @classmethod
    def create_plan(cls, mission: MissionDefinition) -> TaskGraph:
        """
        Lập TaskGraph từ MissionDefinition.
        """
        nodes: List[TaskNode] = []
        ident = mission.identity

        output_fmt = mission.expected_output.format

        if mission.expected_output.type in (DeliverableType.FILE_BINARY, DeliverableType.FILE_CODE):
            # Step 1: Research/Inspect capability requirement
            node1_ident = IdentityChain(
                request_id=ident.request_id,
                mission_id=ident.mission_id,
                plan_id=ident.plan_id,
                task_id=f"tsk_inspect_{output_fmt}"
            )
            node1 = TaskNode(
                identity=node1_ident,
                description=f"Inspect data and design structure for {output_fmt.upper()} output",
                requirement=CapabilityRequirement(
                    capability="data_inspection",
                    complexity="medium",
                    latency="normal",
                    reasoning_depth="moderate"
                ),
                dependencies=[]
            )
            nodes.append(node1)

            # Step 2: Generation capability requirement
            node2_ident = IdentityChain(
                request_id=ident.request_id,
                mission_id=ident.mission_id,
                plan_id=ident.plan_id,
                task_id=f"tsk_build_{output_fmt}"
            )
            node2 = TaskNode(
                identity=node2_ident,
                description=f"Execute file generation for {output_fmt.upper()} deliverable",
                requirement=CapabilityRequirement(
                    capability=f"{output_fmt}_generation" if output_fmt != "markdown" else "document_generation",
                    complexity="medium",
                    latency="normal",
                    reasoning_depth="moderate",
                    verification_required=True
                ),
                dependencies=[node1_ident.task_id]
            )
            nodes.append(node2)
        else:
            # Direct response requirement
            node_ident = IdentityChain(
                request_id=ident.request_id,
                mission_id=ident.mission_id,
                plan_id=ident.plan_id,
                task_id="tsk_direct_response"
            )
            node = TaskNode(
                identity=node_ident,
                description="Synthesize direct conversational response for Master",
                requirement=CapabilityRequirement(
                    capability="conversational_synthesis",
                    complexity="low",
                    latency="ultra_low"
                ),
                dependencies=[]
            )
            nodes.append(node)

        graph = TaskGraph(identity=ident, nodes=nodes, estimated_cost=float(len(nodes)))
        logger.info(f"🗺️ [COGNITIVE-PLANNER]: Created TaskGraph for Mission ID={ident.mission_id} ({len(nodes)} nodes)")
        return graph
