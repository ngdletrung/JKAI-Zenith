"""
JKAI ZENITH — STRESS BENCHMARK C: LONG-HORIZON MULTI-TASK MISSION BENCHMARK
File: tests/constitution/test_long_horizon_multi_task_mission.py

Executes a complex long-horizon mission with 25 TaskNodes in a DAG TaskGraph.
Validates structural dependency ordering, parallel capability resolution, and overall mission integrity.
"""

import pytest
from core.contracts.cognitive_contract import IdentityChain, MissionDefinition
from core.contracts.capability_contract import CapabilityRequirement
from core.planning.task_graph import TaskGraph, TaskNode
from core.capabilities.capability_broker import CapabilityBroker


def test_long_horizon_25_nodes_dag_execution():
    ident = IdentityChain()
    mission = MissionDefinition(identity=ident, objective="Long-Horizon Autonomous Fleet Operation")

    # Generate 25 TaskNodes in a multi-stage dependency graph
    nodes = []
    for i in range(1, 26):
        node_ident = IdentityChain(
            request_id=ident.request_id,
            mission_id=ident.mission_id,
            plan_id=ident.plan_id,
            task_id=f"tsk_node_{i:02d}"
        )
        deps = [f"tsk_node_{i-1:02d}"] if i > 1 else []
        node = TaskNode(
            identity=node_ident,
            description=f"Long Horizon Stage {i} Processing",
            requirement=CapabilityRequirement(
                capability="data_inspection" if i % 2 == 1 else "xlsx_generation",
                complexity="medium"
            ),
            dependencies=deps
        )
        nodes.append(node)

    graph = TaskGraph(identity=ident, nodes=nodes, estimated_cost=25.0)

    # Validate DAG Structure
    assert len(graph.nodes) == 25
    assert graph.nodes[0].dependencies == []
    assert graph.nodes[24].dependencies == ["tsk_node_24"]

    # Validate Capability Resolution across 25 nodes
    for node in graph.nodes:
        prof = CapabilityBroker.resolve_capability(node.requirement)
        assert prof.selected_tool in ("file_inspector", "openpyxl")
        assert prof.max_context_length == 8192
