"""
Unit Test Suite for JKAI AI OS RequestOrchestrator Pipeline.
Kiểm tra toàn diện các handler, pipeline resolver, slash commands, và bypass logic.
"""

import pytest
import asyncio
from unittest.mock import MagicMock, AsyncMock, patch

from core.os.orchestrator import orchestrate_request, OSRequestPlan
from core.os.orchestrator.pipeline_resolver import PipelineResolver
from core.os.cognition.execution_governor import ExecutionTopology, ExecutionPolicy
from core.os.orchestrator.slash_registry import SlashCommandRegistry


@pytest.mark.asyncio
async def test_math_reflex_early_exit():
    """Kiểm tra phản xạ toán học <1ms trả về kết quả sớm."""
    plan = await orchestrate_request(goal="2+2", task_id="test_math_1")
    assert plan.early_response is not None
    assert "4" in plan.early_response["answer"]
    assert plan.pipeline == "fast"


@pytest.mark.asyncio
async def test_math_reflex_percentage():
    """Kiểm tra phản xạ toán học phần trăm."""
    plan = await orchestrate_request(goal="15% của 2000000", task_id="test_math_2")
    assert plan.early_response is not None
    assert "300,000" in plan.early_response["answer"] or "300000" in plan.early_response["answer"]


@pytest.mark.asyncio
async def test_slash_command_research():
    """Kiểm tra lệnh tắt /research."""
    plan = await orchestrate_request(goal="/research Trí tuệ nhân tạo thế hệ mới", task_id="test_slash_1")
    assert plan.os_intent == "research"
    assert "Trí tuệ nhân tạo thế hệ mới" in plan.goal


@pytest.mark.asyncio
async def test_slash_command_status():
    """Kiểm tra lệnh tắt /status trả về kết quả sớm."""
    plan = await orchestrate_request(goal="/status", task_id="test_slash_2")
    assert plan.early_response is not None
    assert "JKAI ZENITH SYSTEM HEALTH" in plan.early_response["answer"]


@pytest.mark.asyncio
async def test_slash_command_code():
    """Kiểm tra lệnh tắt /code."""
    plan = await orchestrate_request(goal="/code Viết hàm fibonacci bằng python", task_id="test_slash_3")
    assert "CODING" in plan.capability_tags
    assert "CODING EXPERT DIRECTIVE" in plan.goal


@pytest.mark.asyncio
async def test_fast_bypass_whitelist():
    """Kiểm tra câu chào đơn giản được bypass nhanh."""
    plan = await orchestrate_request(goal="xin chào", task_id="test_bypass_1")
    assert plan.pipeline == "fast"
    assert plan.is_fast is True
    assert plan.is_deep is False
    assert plan.os_intent == "social"


@pytest.mark.asyncio
async def test_fast_bypass_blocked_on_anaphora():
    """Kiểm tra câu ngắn có chứa từ chỉ định ngữ cảnh (nó, cái đó) không bị bypass sai."""
    history = [{"role": "user", "content": "File này có lỗi gì?"}, {"role": "assistant", "content": "File bị lỗi cú pháp."}]
    plan = await orchestrate_request(goal="nó ở đâu", history=history, task_id="test_bypass_2")
    assert plan.pipeline in ("fast", "deep")


@pytest.mark.asyncio
async def test_pipeline_resolver_master_fast_sovereignty():
    """Kiểm tra Master chọn fast thì 100% giữ FAST kể cả khi topology là MULTI_AGENT."""
    plan = OSRequestPlan(goal="Phân tích toàn bộ hệ thống")
    policy = ExecutionPolicy(
        topology=ExecutionTopology.MULTI_AGENT,
        user_facing_mode="DEEP",
        reason="Complex multi-file task"
    )
    pipeline, is_fast, is_deep, use_deep_full = PipelineResolver.resolve(
        plan=plan,
        exec_policy=policy,
        requested_mode="fast",
        user_explicit_deep=False,
        has_deep_skill=False
    )
    assert pipeline == "fast"
    assert is_fast is True
    assert is_deep is False
    assert use_deep_full is False


@pytest.mark.asyncio
async def test_pipeline_resolver_master_explicit_deep():
    """Kiểm tra Master chọn deep thì chuyển sang DEEP."""
    plan = OSRequestPlan(goal="Lập kế hoạch kiến trúc đa tác tử")
    policy = ExecutionPolicy(
        topology=ExecutionTopology.MULTI_AGENT,
        user_facing_mode="DEEP",
        reason="Master explicit"
    )
    pipeline, is_fast, is_deep, use_deep_full = PipelineResolver.resolve(
        plan=plan,
        exec_policy=policy,
        requested_mode="deep",
        user_explicit_deep=True,
        has_deep_skill=False
    )
    assert pipeline == "deep"
    assert is_fast is False
    assert is_deep is True
    assert use_deep_full is True


@pytest.mark.asyncio
async def test_facade_backward_compatibility():
    """Kiểm tra import từ core.os.request_orchestrator cũ vẫn hoạt động trơn tru."""
    from core.os.request_orchestrator import orchestrate_request as old_orchestrate, _BYPASS_WHITELIST, _log
    assert "xin chào" in _BYPASS_WHITELIST
    plan = await old_orchestrate(goal="2+2", task_id="test_facade")
    assert plan.early_response is not None
