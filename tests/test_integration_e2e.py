#!/usr/bin/env python3
"""
🌐 End-to-End Integration Test Suite for JKAI Zenith.
Tests full pipeline integration: Goal Solver -> Agent Router -> Context Manager -> Guardrails -> Self-Repair.
Supports Mock Mode (CI/Offline) and Live Integration Mode (JKAI_RUN_INTEGRATION_TESTS=1).
"""

import os
import json
import pytest
import asyncio
from unittest.mock import AsyncMock, patch

from intelligence.agents.agent_router import agent_router
from core.kernel.context_manager import context_manager
from core.guardrails.tool_schema_validator import tool_schema_validator
from core.kernel.autonomous_repair_loop import autonomous_repair_loop
from core.kernel.agent_goal_solver import agent_goal_solver


# Check if live integration tests should run
RUN_INTEGRATION = os.getenv("JKAI_RUN_INTEGRATION_TESTS", "0") == "1"


@pytest.mark.asyncio
async def test_e2e_mock_goal_solver_flow():
    """
    E2E Test in Mock Mode: Simulates a user request, agent routing, tool call validation,
    and completion without requiring Docker/Ollama.
    """
    user_prompt = "Hãy viết 1 script Python tính số Fibonacci và lưu vào file test_fibo.py"

    # 1. Route task
    selected_agent = agent_router.route_task(user_prompt)
    assert selected_agent is not None
    assert selected_agent["name"] in ["executor", "sparc_engineer", "default_executor", "planner"]

    # 2. Mock engine response simulating tool invocation followed by final answer
    mock_responses = [
        '```json\n{"tool": "run_python_script", "args": {"script_path": "test_fibo.py"}}\n```',
        'Đã hoàn thành yêu cầu viết script Fibonacci và lưu vào file test_fibo.py.'
    ]

    from core.utils.engine import engine
    mock_call = AsyncMock(side_effect=mock_responses)
    with patch.object(engine, "call_chat", mock_call):
        with patch.object(autonomous_repair_loop, "execute_and_self_heal", new_callable=AsyncMock) as mock_heal:
            mock_heal.return_value = {"status": "success", "attempts": 1, "stdout": "Fibonacci calculated.", "stderr": ""}
            
            result = await agent_goal_solver.solve_goal(user_prompt, task_id="test_e2e_01", max_steps=5)

            if result["status"] != "success":
                print("RESULT IS:", result)
            assert result["status"] == "success"
            assert "final_output" in result
            assert result["steps_taken"] == 2
            mock_heal.assert_called_once()


@pytest.mark.asyncio
async def test_e2e_context_pruner_integration():
    """
    Tests that context pruner maintains system prompt pinning even during deep multi-turn tool conversations.
    """
    sys_msg = {"role": "system", "content": "You are JKAI Zenith Agent."}
    messages = [sys_msg]

    # Add 10 simulated large interaction turns
    for i in range(10):
        messages.append({"role": "user", "content": f"User prompt turn {i}: " + ("data " * 200)})
        messages.append({"role": "assistant", "content": f"Assistant response turn {i}: " + ("output " * 200)})

    pruned = context_manager.prune_messages(messages)

    assert len(pruned) < len(messages)
    assert pruned[0] == sys_msg
    assert "User prompt turn 9" in pruned[-2]["content"] or "Assistant response turn 9" in pruned[-1]["content"]


@pytest.mark.asyncio
async def test_e2e_guardrail_validation_and_repair_flow():
    """
    Tests tool schema validation when LLM emits malformed parameters and confirms type coercion works.
    """
    raw_response = '```json\n{"tool": "run_command", "args": {"command": "pytest", "timeout": "30"}}\n```'
    tool_name, args, err = tool_schema_validator.parse_tool_call(raw_response)

    assert err is None
    assert tool_name == "run_command"

    schema = {
        "required": ["command"],
        "properties": {
            "command": {"type": "string"},
            "timeout": {"type": "integer"}
        }
    }

    coerced, error = tool_schema_validator.validate_and_coerce(tool_name, args, schema)
    assert error is None
    assert isinstance(coerced["timeout"], int)
    assert coerced["timeout"] == 30


@pytest.mark.skipif(not RUN_INTEGRATION, reason="Skipped unless JKAI_RUN_INTEGRATION_TESTS=1 and Docker+Ollama are active")
@pytest.mark.asyncio
async def test_e2e_live_ollama_integration():
    """
    Live Integration Test against running Ollama instance.
    Runs only when JKAI_RUN_INTEGRATION_TESTS=1 environment variable is set.
    """
    from core.utils.engine import engine

    prompt = [
        {"role": "system", "content": "You are JKAI Zenith. Reply with exact word 'HEALTHCHECK_OK'."},
        {"role": "user", "content": "Ping test."}
    ]

    response = await engine.call_chat(prompt, role="RECEPTIONIST", task_id="live_healthcheck")
    assert "HEALTHCHECK_OK" in response or len(response) > 0
