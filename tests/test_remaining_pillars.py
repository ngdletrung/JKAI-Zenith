# -*- coding: utf-8 -*-
"""
Unit test suite cho Trụ cột 4 (MultiModal & ToolChainer), Trụ cột 5 (PolicyEngine), và Trụ cột 6 (Distributed Orchestrator).
"""

import pytest
import asyncio
from core.multimodal.gateway import multimodal_gateway
from core.planning.tool_chainer import tool_chainer, ToolChainStep
from core.security.policy_engine import policy_engine, SubjectRole, SecurityContext, PolicyDecision
from core.distributed.edge_orchestrator import edge_orchestrator, NodeType


class TestRemainingPillars:
    """Kiểm tra độ chính xác của Trụ cột 4, 5 và 6."""

    # ── TRỤ CỘT 4: MULTI-MODAL & TOOL CHAINING ──
    @pytest.mark.asyncio
    async def test_multimodal_gateway_image_classification(self):
        res = await multimodal_gateway.process_image_input(
            "dummy_data", task_id="t1", user_prompt="Hình ảnh báo lỗi traceback"
        )
        assert res.image_type == "ERROR_SCREENSHOT"
        assert res.confidence >= 0.90
        assert len(res.key_visual_elements) >= 1

    @pytest.mark.asyncio
    async def test_tool_chainer_sequential_pipeline_execution(self):
        steps = [
            ToolChainStep("step_1", "WEB_SEARCH", {"query": "giá vàng"}, output_variable_name="search_data"),
            ToolChainStep("step_2", "CREATE_EXCEL", {"data": "${search_data}"}, output_variable_name="excel_file")
        ]
        res = await tool_chainer.execute_tool_chain("task_chain_1", steps)
        assert res.status == "SUCCESS"
        assert res.completed_steps == 2
        assert "search_data" in res.pipeline_outputs
        assert "excel_file" in res.pipeline_outputs

    # ── TRỤ CỘT 5: ZERO-TRUST POLICY ENGINE ──
    def test_policy_engine_protects_kernel_mutation(self):
        ctx = SecurityContext(subject_role=SubjectRole.AGENT)
        res = policy_engine.evaluate_action("MUTATION", "core/kernel/code_actuator.py", ctx)
        assert res.decision == PolicyDecision.REQUIRE_APPROVAL
        assert res.rule_name == "RULE_KERNEL_PROTECT"

    def test_policy_engine_allows_workspace_output(self):
        ctx = SecurityContext(subject_role=SubjectRole.AGENT)
        res = policy_engine.evaluate_action("MUTATION", "workspace/outputs/report.xlsx", ctx)
        assert res.decision == PolicyDecision.ALLOW

    def test_policy_engine_denies_destructive_commands(self):
        ctx = SecurityContext(subject_role=SubjectRole.AGENT)
        res = policy_engine.evaluate_action("EXECUTION", "rm -rf /", ctx)
        assert res.decision == PolicyDecision.DENY

    def test_master_role_has_sovereignty(self):
        ctx = SecurityContext(subject_role=SubjectRole.MASTER, is_authenticated=True)
        res = policy_engine.evaluate_action("MUTATION", "core/kernel/code_actuator.py", ctx)
        assert res.decision == PolicyDecision.ALLOW
        assert res.rule_name == "MASTER_SOVEREIGNTY"

    # ── TRỤ CỘT 6: DISTRIBUTED ORCHESTRATOR ──
    def test_distributed_orchestrator_node_registration(self):
        node = edge_orchestrator.register_edge_node("edge_mobile_1", "192.168.1.50", 9000)
        assert node.node_type == NodeType.EDGE_REFLEX
        assert node.node_id in edge_orchestrator.nodes

    def test_distributed_routing_resolves_nodes(self):
        node_deep = edge_orchestrator.resolve_optimal_node_for_task("reasoning")
        assert node_deep.node_type == NodeType.CENTRAL_BRAIN

        node_math = edge_orchestrator.resolve_optimal_node_for_task("math")
        assert node_math.node_type in (NodeType.EDGE_REFLEX, NodeType.CENTRAL_BRAIN)
