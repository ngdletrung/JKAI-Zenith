import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
import pytest

from core.kernel.project_agent_loop import ProjectAgentLoop, ToolValidationError
from core.kernel.transaction_manager import WorkspaceTransactionManager
import sys
ai_brain_dir = str(Path("services/ai-brain").resolve())
if ai_brain_dir not in sys.path:
    sys.path.insert(0, ai_brain_dir)

from receptionist.executor_gateway import ExecutorGateway, ExecutionRequest, DecisionOutcome
from services.tools.definitions.browser_interact import (
    web_read,
    browser_observe,
    browser_act,
    browser_extract,
    browser_action,
)


# ═══════════════════════════════════════════════════════════════════
# 📁 PILLAR 1: FILE (M0) ACTUATOR TESTS
# ═══════════════════════════════════════════════════════════════════

def test_file_actuator_transaction_snapshot_and_rollback():
    """Kiểm tra File Actuator (M0): Khởi tạo giao dịch, sửa đổi và hoàn tác sạch sẽ."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        test_file = tmp_path / "module_test.py"
        test_file.write_text("def original_code():\n    return 42\n", encoding="utf-8")

        mgr = WorkspaceTransactionManager()
        task_id = "test_task_file_m0"

        # Bắt đầu giao dịch bảo vệ
        ok = mgr.begin_transaction(task_id, [str(test_file)])
        assert ok is True

        # Sửa đổi tệp
        test_file.write_text("def modified_code():\n    return 999\n", encoding="utf-8")
        assert "modified_code" in test_file.read_text(encoding="utf-8")

        # Rollback giao dịch khi phát hiện lỗi
        rolled_back = mgr.rollback(task_id)
        assert len(rolled_back) == 1
        assert "original_code" in test_file.read_text(encoding="utf-8")
        assert "modified_code" not in test_file.read_text(encoding="utf-8")


def test_file_actuator_atomic_new_file_creation_rollback():
    """Kiểm tra File Actuator (M0): Tự động xóa tệp mới sinh nếu giao dịch bị hủy bỏ."""
    with tempfile.TemporaryDirectory() as tmp_dir:
        tmp_path = Path(tmp_dir)
        new_file = tmp_path / "new_temp_file.py"

        mgr = WorkspaceTransactionManager()
        task_id = "test_task_new_file"

        mgr.begin_transaction(task_id, [str(new_file)])
        new_file.write_text("# Temporary code", encoding="utf-8")
        assert new_file.exists()

        mgr.rollback(task_id)
        assert not new_file.exists()


# ═══════════════════════════════════════════════════════════════════
# 🖥️ PILLAR 2: TERMINAL (M1) ACTUATOR TESTS
# ═══════════════════════════════════════════════════════════════════

def test_terminal_actuator_safe_command_normalization():
    """Kiểm tra Terminal Actuator (M1): Chuẩn hóa tham số lệnh an toàn."""
    loop = ProjectAgentLoop(executor_gateway=MagicMock(), project_root="core/security", mode="audit")
    norm_params, safe_path, old_text = loop._normalize_tool_params("run_command", {"command": "git status"})

    assert norm_params["command"] == "git status"
    assert norm_params["CommandLine"] == "git status"
    assert norm_params["cwd"] == loop.base


def test_terminal_actuator_blocks_dangerous_command():
    """Kiểm tra Terminal Actuator (M1): Chặn đứng các lệnh phá hoại hệ thống (rm -rf /, mkfs...)."""
    loop = ProjectAgentLoop(executor_gateway=MagicMock(), project_root="core/security", mode="audit")
    with pytest.raises(ToolValidationError) as exc:
        loop._normalize_tool_params("run_command", {"command": "rm -rf / --no-preserve-root"})
    assert "chặn vì lý do an toàn" in str(exc.value)


def test_terminal_actuator_blocks_unauthorized_binary():
    """Kiểm tra Terminal Actuator (M1): Chặn binary lạ không thuộc allowlist an toàn."""
    loop = ProjectAgentLoop(executor_gateway=MagicMock(), project_root="core/security", mode="audit")
    with pytest.raises(ToolValidationError) as exc:
        loop._normalize_tool_params("run_command", {"command": "nc -lvp 4444"})
    assert "không nằm trong danh sách an toàn" in str(exc.value)


# ═══════════════════════════════════════════════════════════════════
# 🌐 PILLAR 3: BROWSER (M2) ACTUATOR TESTS
# ═══════════════════════════════════════════════════════════════════

def test_browser_actuator_tools_present_in_agent_loop():
    """Kiểm tra Browser Actuator (M2): Đã tích hợp đầy đủ trong danh sách công cụ Agent Loop."""
    loop = ProjectAgentLoop(executor_gateway=MagicMock(), project_root="core/security", mode="audit")

    assert loop._is_tool_allowed("web_read") is True
    assert loop._is_tool_allowed("browser_observe") is True
    assert loop._is_tool_allowed("browser_act") is True
    assert loop._is_tool_allowed("browser_extract") is True
    assert loop._is_tool_allowed("browser_action") is True


def test_browser_actuator_param_normalization():
    """Kiểm tra Browser Actuator (M2): Chuẩn hóa các tham số của Web Read & Semantic Actuator."""
    loop = ProjectAgentLoop(executor_gateway=MagicMock(), project_root="core/security", mode="audit")

    # web_read
    p_read, _, _ = loop._normalize_tool_params("web_read", {"url": "https://example.com/docs", "filter": "API"})
    assert p_read["url"] == "https://example.com/docs"
    assert p_read["filter"] == "API"
    assert p_read["prefer_llms_txt"] is True

    # browser_observe
    p_obs, _, _ = loop._normalize_tool_params("browser_observe", {"url": "http://127.0.0.1:9999", "goal": "Audit dashboard"})
    assert p_obs["url"] == "http://127.0.0.1:9999"
    assert p_obs["goal"] == "Audit dashboard"

    # browser_act
    p_act, _, _ = loop._normalize_tool_params("browser_act", {"element_ref": "@e5", "action": "click"})
    assert p_act["element_ref"] == "@e5"
    assert p_act["action"] == "click"

    # browser_extract
    p_ext, _, _ = loop._normalize_tool_params("browser_extract", {"goal": "Get metrics", "schema": {"type": "object"}})
    assert p_ext["goal"] == "Get metrics"
    assert p_ext["schema_definition"] == {"type": "object"}


@pytest.mark.asyncio
async def test_browser_actuator_gateway_dispatch_web_read():
    """Kiểm tra Browser Actuator (M2): Gateway tiếp nhận và điều phối web_read qua ExecutorGateway."""
    gw = ExecutorGateway(http_client=MagicMock())
    req = ExecutionRequest(
        trace_id="trace_test_web_read",
        capability_token={},
        tool_name="web_read",
        tool_args={"url": "https://example.com/doc.md", "filter": "guide"},
    )

    fake_result = {
        "url": "https://example.com/doc.md",
        "title": "Example Doc",
        "content": "<UNTRUSTED_EXTERNAL_REFERENCE>Doc body</UNTRUSTED_EXTERNAL_REFERENCE>",
        "status": "success",
    }

    with patch("services.tools.definitions.browser_interact.web_read", return_value=fake_result):
        exec_res = await gw.execute_tool(req, task_id="task_triad_browser_1")
        assert exec_res.outcome == DecisionOutcome.ALLOW
        assert exec_res.tool_executed is True
        assert "<UNTRUSTED_EXTERNAL_REFERENCE>" in str(exec_res.result)


@pytest.mark.asyncio
async def test_browser_actuator_gateway_dispatch_semantic_observe_and_act():
    """Kiểm tra Browser Actuator (M2): Gateway tiếp nhận và điều phối observe & act với @eN ref."""
    gw = ExecutorGateway(http_client=MagicMock())

    # Test observe
    obs_req = ExecutionRequest(
        trace_id="trace_test_obs",
        capability_token={},
        tool_name="browser_observe",
        tool_args={"url": "http://127.0.0.1:9999", "goal": "Inspect tabs"},
    )
    fake_obs = {
        "status": "success",
        "element_count": 5,
        "snapshot": "@e1: [tab] 'Overview'\n@e2: [tab] 'Missions'\n@e3: [button] 'Run'",
        "quality_gate": {"canvas_count": 0, "shadow_roots_count": 0},
    }
    with patch("services.tools.definitions.browser_interact.browser_observe", return_value=fake_obs):
        res_obs = await gw.execute_tool(obs_req, task_id="task_triad_browser_2")
        assert res_obs.outcome == DecisionOutcome.ALLOW
        assert "@e1: [tab]" in str(res_obs.result)

    # Test act
    act_req = ExecutionRequest(
        trace_id="trace_test_act",
        capability_token={},
        tool_name="browser_act",
        tool_args={"element_ref": "@e3", "action": "click"},
    )
    fake_act = {
        "success": True,
        "action": "click",
        "element_ref": "@e3",
        "healing_tier_used": 1,
        "message": "Clicked @e3 successfully.",
        "status": "success",
    }
    with patch("services.tools.definitions.browser_interact.browser_act", return_value=fake_act):
        res_act = await gw.execute_tool(act_req, task_id="task_triad_browser_3")
        assert res_act.outcome == DecisionOutcome.ALLOW
        assert res_act.tool_executed is True
        assert "Clicked @e3" in str(res_act.result)
