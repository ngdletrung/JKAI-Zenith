"""
Unit tests cho ModelOutputParser & các cải tiến Action Primitives (C1, C3, C4, C5).
Bao phủ 5 định dạng đầu ra của Local Ollama và các cơ chế an toàn.
"""

import os
import pytest
import asyncio
import importlib.util
from pathlib import Path
from core.kernel.model_output_parser import ModelOutputParser

def _load_executor_logic():
    logic_path = Path(__file__).resolve().parent.parent / "intelligence" / "skills" / "DEVOPS" / "SYSTEM_CORE_EXECUTOR" / "logic.py"
    spec = importlib.util.spec_from_file_location("system_core_executor_logic", str(logic_path))
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

executor_logic = _load_executor_logic()
replace_file_content = executor_logic.replace_file_content
delete_file = executor_logic.delete_file
write_to_file = executor_logic.write_to_file
view_file = executor_logic.view_file


# =============================================================================
# NHÓM 1: KIỂM THỬ 5 ĐỊNH DẠNG ĐẦU RA CỦA LOCAL OLLAMA (C1)
# =============================================================================

def test_format_1_raw_json():
    """Format 1: Raw JSON chuẩn."""
    raw = '{"thought": "Đọc file README", "tool": "view_file", "params": {"path": "README.md"}}'
    res = ModelOutputParser.parse(raw)
    assert res["tool"] == "view_file"
    assert res["params"]["path"] == "README.md"
    assert res["thought"] == "Đọc file README"
    assert res["final_answer"] is None


def test_format_2_markdown_fence():
    """Format 2: Bọc trong Markdown code block ```json ... ```."""
    raw = """
    Tôi sẽ phân tích thư mục này.
    ```json
    {
        "thought": "Quét danh mục",
        "action": "list_dir",
        "parameters": {"path": "."}
    }
    ```
    Hãy chờ tôi hoàn tất.
    """
    res = ModelOutputParser.parse(raw)
    assert res["tool"] == "list_dir"
    assert res["params"]["path"] == "."
    assert "Quét danh mục" in res["thought"]


def test_format_3_tool_call_tag():
    """Format 3: Semantic tag <tool_call> ... </tool_call> (Qwen / DeepSeek)."""
    raw = """
    Suy nghĩ: Cần tìm kiếm file cấu hình.
    <tool_call>
    {"name": "grep_search", "arguments": {"query": "SECRET_KEY", "path": "."}}
    </tool_call>
    """
    res = ModelOutputParser.parse(raw)
    assert res["tool"] == "grep_search"
    assert res["params"]["query"] == "SECRET_KEY"


def test_format_4_react_format():
    """Format 4: ReAct style Action: ... Action Input: ..."""
    raw = """
    Thought: Cần thực thi lệnh kiểm thử pytest
    Action: run_command
    Action Input: {"command": "pytest tests/ -v"}
    """
    res = ModelOutputParser.parse(raw)
    assert res["tool"] == "run_command"
    assert res["params"]["command"] == "pytest tests/ -v"


def test_format_5_embedded_json():
    """Format 5: JSON nằm nhúng trong văn bản giải thích không có markdown fence."""
    raw = """
    Sau khi xem xét các file mã nguồn, tôi quyết định sửa file test.
    {"thought": "Sửa mã", "tool": "replace_file_content", "params": {"path": "test.py", "target": "old", "replacement": "new"}}
    Hy vọng thao tác này giải quyết được vấn đề.
    """
    res = ModelOutputParser.parse(raw)
    assert res["tool"] == "replace_file_content"
    assert res["params"]["target"] == "old"


# =============================================================================
# NHÓM 2: KIỂM THỬ AUTO-REPAIR & EDGE CASES CỦA LOCAL LLM
# =============================================================================

def test_repair_trailing_commas():
    """Sửa lỗi dấu phẩy thừa (trailing commas) thường gặp ở local model."""
    raw = """
    ```json
    {
        "thought": "Ghi đè file",
        "tool": "write_to_file",
        "params": {
            "path": "test.txt",
            "content": "hello",
        },
    }
    ```
    """
    res = ModelOutputParser.parse(raw)
    assert res["tool"] == "write_to_file"
    assert res["params"]["content"] == "hello"


def test_repair_token_truncation_unclosed_braces():
    """Phục hồi JSON bị cắt cụt do model hết token ở giữa chừng."""
    raw = '{"thought": "Đang suy nghĩ", "tool": "view_file", "params": {"path": "main.py"'
    res = ModelOutputParser.parse(raw)
    assert res["tool"] == "view_file"
    assert res["params"]["path"] == "main.py"


def test_repair_python_boolean_and_none():
    """Chuyển đổi True, False, None của Python thành JSON hợp lệ."""
    raw = '{"thought": "Check", "tool": "delete_file", "params": {"path": "temp.txt", "confirm": True, "extra": None}}'
    res = ModelOutputParser.parse(raw)
    assert res["tool"] == "delete_file"
    assert res["params"]["confirm"] is True
    assert res["params"]["extra"] is None


def test_final_answer_detection():
    """Tự động phát hiện khi model kết luận mà không gọi tool."""
    raw = "FINAL_ANSWER: Đã hoàn tất sửa lỗi cú pháp trong module router."
    res = ModelOutputParser.parse(raw)
    assert res["tool"] is None
    assert res["final_answer"] is not None
    assert "Đã hoàn tất" in res["final_answer"]


# =============================================================================
# NHÓM 3: KIỂM THỬ PRIMITIVES: AST PRE-VALIDATION & BACKUP & DELETE_FILE
# =============================================================================

@pytest.mark.asyncio
async def test_ast_pre_validation_rejects_syntax_error(tmp_path):
    """C5: replace_file_content từ chối ghi đè nếu mã Python bị lỗi cú pháp."""
    py_file = tmp_path / "sample.py"
    py_file.write_text("def hello():\n    return 'world'\n", encoding="utf-8")

    # Cố tình thay thế bằng cú pháp vỡ: thiếu dấu hai chấm
    res = await replace_file_content(
        path=str(py_file),
        target="return 'world'",
        replacement="return 'world' def broken("
    )
    assert res["status"] == "error"
    assert "AST Syntax Error" in res["msg"]
    # File gốc phải giữ nguyên
    assert py_file.read_text(encoding="utf-8") == "def hello():\n    return 'world'\n"


@pytest.mark.asyncio
async def test_replace_creates_backup_file(tmp_path):
    """C3: replace_file_content tự động tạo file .bak trước khi ghi đè."""
    txt_file = tmp_path / "data.txt"
    txt_file.write_text("Line 1\nTarget Line\nLine 3\n", encoding="utf-8")

    res = await replace_file_content(
        path=str(txt_file),
        target="Target Line",
        replacement="Replaced Line"
    )
    assert res["status"] == "success"
    assert txt_file.read_text(encoding="utf-8") == "Line 1\nReplaced Line\nLine 3\n"

    # Kiểm tra file .bak có tồn tại
    bak_files = list(tmp_path.glob("data.txt.bak.*"))
    assert len(bak_files) >= 1
    assert "Target Line" in bak_files[0].read_text(encoding="utf-8")


@pytest.mark.asyncio
async def test_delete_file_guard_and_execution(tmp_path):
    """C4: delete_file từ chối file nhạy cảm và xóa thành công khi confirm=True."""
    # 1. Từ chối khi không confirm
    temp_file = tmp_path / "temp.log"
    temp_file.write_text("temp data", encoding="utf-8")
    res_no_conf = await delete_file(path=str(temp_file), confirm=False)
    assert res_no_conf["status"] == "error"
    assert "confirm=True" in res_no_conf["msg"]
    assert temp_file.exists()

    # 2. Từ chối khi cố xóa file nhạy cảm (.env)
    env_file = tmp_path / ".env"
    env_file.write_text("API_KEY=123", encoding="utf-8")
    res_env = await delete_file(path=str(env_file), confirm=True)
    assert res_env["status"] == "error"
    assert "bảo vệ an ninh" in res_env["msg"]
    assert env_file.exists()

    # 3. Xóa thành công file thông thường
    res_ok = await delete_file(path=str(temp_file), confirm=True)
    assert res_ok["status"] == "success"
    assert not temp_file.exists()
