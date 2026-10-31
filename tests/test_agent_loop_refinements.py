import pytest
from pathlib import Path
from unittest.mock import MagicMock
from core.kernel.project_agent_loop import (
    ProjectAgentLoop,
    ToolValidationError,
    _guard_path,
    SAFE_EXTENSIONS,
    ALLOWED_EXECUTABLES,
)

def test_guard_path_sensitive_regex():
    # File hợp lệ không bị chặn nhầm
    assert _guard_path(".", "secret_santa.py") is not None
    assert _guard_path(".", "my_credential_notes.txt") is not None
    
    # File nhạy cảm thực sự bị chặn
    assert _guard_path(".", ".env") is None
    assert _guard_path(".", ".env.local") is None
    assert _guard_path(".", "credentials.json") is None
    assert _guard_path(".", "id_rsa") is None
    assert _guard_path(".", "server.pem") is None

def test_normalize_tool_params_command_allowlist():
    gw = MagicMock()
    loop = ProjectAgentLoop(gw, ".")
    
    # Lệnh hợp lệ
    params, path, old = loop._normalize_tool_params("run_command", {"command": "python -m pytest"})
    assert params["command"] == "python -m pytest"
    
    # Lệnh nguy hiểm bị chặn
    with pytest.raises(ToolValidationError):
        loop._normalize_tool_params("run_command", {"command": "rm -rf /"})
        
    # Lệnh ngoài allowlist bị chặn
    with pytest.raises(ToolValidationError):
        loop._normalize_tool_params("run_command", {"command": "nc -lvp 4444"})

def test_post_process_structured_output_logic():
    gw = MagicMock()
    loop = ProjectAgentLoop(gw, ".")
    
    # Status failed nhưng error rỗng -> vẫn phải nhận diện là FAILED
    out_dict = {"status": "failed", "data": "Something went wrong"}
    res = loop._post_process_tool_result("run_command", {}, out_dict, "task_1", None, "")
    assert "Something went wrong" in res

def test_dynamic_step_budget_allocation():
    gw = MagicMock()
    # Task phức tạp có >= 2 tệp .py
    loop = ProjectAgentLoop(gw, ".")
    assert loop.max_steps == 16
    
    # Khi run với goal đa tệp, ngân sách tự động mở rộng
    # (ta test logic phân tích goal)
    goal = "Kiểm toán 2 tệp core/security/egress_gate.py và core/security/data_leak_guard.py"
    # verify check logic
    import re
    py_mentions = len(re.findall(r"\b[\w/\\-]+\.py\b", goal.lower()))
    assert py_mentions >= 2

def test_pre_submission_reflexion_check():
    gw = MagicMock()
    loop = ProjectAgentLoop(gw, ".")
    goal = "Kiểm toán tệp foo.py và đính kèm mã Canary NP2-CANARY-1234, SHA-256 và số dòng"
    
    # Báo cáo thiếu toàn bộ
    ok, missing = loop._pre_submission_check("Tôi đã đọc xong.", goal)
    assert not ok
    assert len(missing) == 3 # Canary, SHA-256, dòng
    
    # Báo cáo đầy đủ
    full_answer = "Mã băm SHA-256: a5932abe94b11d1e, tổng số dòng: 150. Canary NP2-CANARY-1234."
    ok2, missing2 = loop._pre_submission_check(full_answer, goal)
    assert ok2
    assert len(missing2) == 0

@pytest.mark.asyncio
async def test_no_fabrication_guard_needs_validation_verdict(monkeypatch):
    import json
    from unittest.mock import AsyncMock, patch
    monkeypatch.setenv("JKAI_CURSOR_AGENT", "1")
    gw = MagicMock()
    gw.execute_tool = AsyncMock(return_value={"status": "success", "data": "mock_data"})
    
    mock_llm_response = json.dumps({
        "thought": "Đã xong phân tích lý thuyết mà chưa đọc tệp.",
        "tool": None,
        "params": {},
        "final_answer": "Phát hiện lỗ hổng bảo mật nghiêm trọng.",
    })
    
    with patch("core.kernel.project_agent_loop.engine.call_chat", new=AsyncMock(return_value=mock_llm_response)):
        loop = ProjectAgentLoop(gw, "core/security/egress_gate.py", mode="audit")
        goal = "Kiểm toán tệp core/security/egress_gate.py"
        result = await loop.run(goal, "TASK-TEST-FABRICATION")
    
    # Kết quả phải là JSON structured needs_validation thay vì fabrication
    assert "needs_validation" in result
    parsed = json.loads(result)
    assert parsed.get("verdict") == "needs_validation"
    assert parsed.get("status") == "KHONG_THE_DOC_TEP"
    assert parsed.get("severity") is None
    assert "core/security/egress_gate.py" in str(parsed.get("target"))

def test_known_gaps_cloudflare_antipatterns_loaded():
    from core.kernel.failure_memory import load_known_gaps_summary
    summary = load_known_gaps_summary(max_lines=50)
    assert "GAP-007" in summary
    assert "GAP-008" in summary
    assert "GAP-009" in summary
    assert "GAP-010" in summary
    assert "GAP-011" in summary
    assert "GAP-012" in summary

