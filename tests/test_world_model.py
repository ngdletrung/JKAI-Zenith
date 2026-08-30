# -*- coding: utf-8 -*-
"""
Unit test suite cho WorldModel v2.0 (Bản Đồ Thực Tại Động, Ràng Buộc YAML & Mô Phỏng Nhân Quả)
"""

import pytest
from core.kernel.world_model import (
    TypedWorldGraph, NodeType, ConstraintDSLEngine,
    TemporalSimulator, ScenarioSimulator, FormalInvariantEngine,
    create_default_world_graph
)
from core.kernel.state_machine import TaskState


class TestWorldModelV2:
    """Kiểm tra toàn diện các năng lực động và mô phỏng của WorldModel v2.0."""

    def test_graph_update_and_remove_node(self):
        graph = create_default_world_graph()
        # 1. Update node
        res_up = graph.update_node("redis-ai", properties={"port": 6380}, status="DEGRADED")
        assert res_up is True
        node = graph.get_node("redis-ai")
        assert node.properties["port"] == 6380
        assert node.status == "DEGRADED"

        # 2. Remove node
        res_rm = graph.remove_node("postgres-db")
        assert res_rm is True
        assert graph.get_node("postgres-db") is None
        # Các cạnh liên quan cũng phải tự động bị xóa
        assert not any(e.source_id == "postgres-db" or e.target_id == "postgres-db" for e in graph.edges)

    def test_graph_remove_edge(self):
        graph = create_default_world_graph()
        removed = graph.remove_edge("redis-ai", "port-6379", "RUNS_ON")
        assert removed is True
        assert not any(e.source_id == "redis-ai" and e.target_id == "port-6379" for e in graph.edges)

    def test_constraint_port_collision(self):
        graph = create_default_world_graph()
        # Thêm 1 port trùng lặp 6379
        graph.add_node("port-duplicate", NodeType.PORT, {"value": 6379})
        dsl = ConstraintDSLEngine()
        is_safe, violations = dsl.validate_graph(graph)
        assert is_safe is False
        assert any("RULE_PORT_UNIQUENESS" in v for v in violations)

    def test_constraint_core_integrity(self):
        graph = create_default_world_graph()
        graph.update_node("state_machine.py", status="CORRUPTED")
        dsl = ConstraintDSLEngine()
        is_safe, violations = dsl.validate_graph(graph)
        assert is_safe is False
        assert any("RULE_CORE_INTEGRITY" in v for v in violations)

    def test_simulate_action_sequence(self):
        graph = create_default_world_graph()
        actions = [
            ("UPDATE", "redis-ai", {"port": 6379}, "HEALTHY"),
            ("UPDATE", "qdrant", {"port": 6333}, "HEALTHY")
        ]
        is_safe, _, violations = TemporalSimulator.simulate_sequence(graph, actions)
        assert is_safe is True
        assert len(violations) == 0

    def test_formal_invariant_precondition(self):
        graph = create_default_world_graph()
        graph.update_node("redis-ai", status="DOWN")
        
        with pytest.raises(AssertionError, match="Redis-AI đang sập"):
            FormalInvariantEngine.assert_precondition(TaskState.EXECUTING, graph)

    def test_formal_invariant_postcondition(self):
        graph = create_default_world_graph()
        graph.update_node("qdrant", status="DOWN")
        
        with pytest.raises(AssertionError, match="dịch vụ sinh tồn"):
            FormalInvariantEngine.assert_postcondition(TaskState.COMPLETED, graph)

    def test_scenario_simulation_with_graph(self):
        graph = create_default_world_graph()
        outcome = ScenarioSimulator.simulate_what_if("Xóa redis-ai để tiết kiệm RAM", graph=graph)
        assert outcome.predicted_state == "DEGRADED"
        assert "Tuyệt đối không tắt Redis" in outcome.recommendations[0]
