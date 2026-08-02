#!/usr/bin/env python3
"""
Unit tests for JKAI Zenith Core Modules:
- AgentRouter
- ContextManager
- ToolSchemaValidator
"""

import pytest
from intelligence.agents.agent_router import agent_router
from core.kernel.context_manager import context_manager
from core.guardrails.tool_schema_validator import tool_schema_validator


def test_agent_router_loads_agents():
    """Verify that agent router successfully scans and registers agent markdown files."""
    agents = agent_router.list_agents()
    assert isinstance(agents, list)
    assert len(agents) > 0
    names = [a["name"] for a in agents]
    assert "planner" in names or "executor" in names or "critic" in names


def test_agent_router_task_routing():
    """Verify keyword task routing to specialized agents."""
    routed_plan = agent_router.route_task("Hãy lập kế hoạch và chiến lược phát triển hệ thống")
    assert routed_plan["name"].lower() in ["planner", "strategist", "coordinator"]

    routed_code = agent_router.route_task("Viết script Python và chạy build code")
    assert routed_code["name"].lower() in ["executor", "sparc_engineer", "default_executor"]


def test_context_manager_pruning():
    """Verify token estimation and message pruning."""
    system_msg = {"role": "system", "content": "System prompt rule."}
    messages = [
        system_msg,
        {"role": "user", "content": "Hello " * 500},
        {"role": "assistant", "content": "World " * 500},
        {"role": "user", "content": "Latest turn"}
    ]

    pruned = context_manager.prune_messages(messages)
    assert len(pruned) >= 2
    assert pruned[0] == system_msg  # System prompt remains pinned at top
    assert pruned[-1]["content"] == "Latest turn"  # Most recent user turn is preserved


def test_tool_schema_validator_parser():
    """Verify parsing JSON tool calls from markdown blocks."""
    json_text = '```json\n{"tool": "run_command", "args": {"command": "ls -la"}}\n```'
    tool_name, args, err = tool_schema_validator.parse_tool_call(json_text)

    assert err is None
    assert tool_name == "run_command"
    assert args == {"command": "ls -la"}


def test_tool_schema_validator_coercion():
    """Verify parameter validation and type coercion."""
    schema = {
        "required": ["task_id", "timeout"],
        "properties": {
            "task_id": {"type": "string"},
            "timeout": {"type": "integer"},
            "is_async": {"type": "boolean"}
        }
    }

    raw_args = {"task_id": "123", "timeout": "60", "is_async": "true"}
    coerced, err = tool_schema_validator.validate_and_coerce("test_tool", raw_args, schema)

    assert err is None
    assert coerced["timeout"] == 60
    assert coerced["is_async"] is True
