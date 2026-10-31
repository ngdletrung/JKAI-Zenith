from unittest.mock import MagicMock
import pytest
from core.kernel.project_agent_loop import ProjectAgentLoop
from core.kernel.context_manager import inspect_system_prefix_cache_alignment, context_manager

def test_static_system_prefix_is_immutable_across_goals():
    """Vũ khí 2 (Anthropic & xAI): Static System Prefix phải bất biến tuyệt đối giữa các goals khác nhau."""
    loop = ProjectAgentLoop(executor_gateway=MagicMock(), project_root="core/security", mode="audit")
    
    prefix1 = loop._static_system_prefix()
    prefix2 = loop._static_system_prefix()
    
    assert prefix1 == prefix2
    assert "NP3-CANARY" not in prefix1
    assert "Mục tiêu Master" not in prefix1
    assert "JSON" in prefix1
    assert "view_file" in prefix1

def test_static_system_prefix_cache_alignment():
    """Vũ khí 2: Tiền tố tĩnh phải vượt qua kiểm định Cache Alignment (không chứa volatile tokens)."""
    loop = ProjectAgentLoop(executor_gateway=MagicMock(), project_root="core/security", mode="audit")
    prefix = loop._static_system_prefix()
    
    align_result = inspect_system_prefix_cache_alignment(prefix, prefix_window_chars=1000)
    assert align_result["cache_aligned"] is True
    assert align_result["volatile_flag"] is False
    assert len(align_result["offending_matches"]) == 0

def test_three_block_prompt_architecture():
    """Kiểm tra cấu trúc 3 khối: Khối 1 tĩnh, Khối 2 lịch sử, Khối 3 đuôi động."""
    loop = ProjectAgentLoop(executor_gateway=MagicMock(), project_root="core/security", mode="audit")
    goal = "[TASK-001 | Canary: NP3-CANARY-TEST] Kiểm toán bảo mật"
    
    messages = loop.build_initial_messages(goal=goal, task_id="task_test_123")
    
    # Khối 1: Index 0 phải là static system prefix
    assert messages[0]["role"] == "system"
    assert messages[0]["content"] == loop._static_system_prefix()
    
    # Khối 2: Index 1 phải là task-specific context (chứa goal, canary, scope)
    assert messages[1]["role"] == "user"
    assert "NP3-CANARY-TEST" in messages[1]["content"]
    assert "core/security" in messages[1]["content"]
