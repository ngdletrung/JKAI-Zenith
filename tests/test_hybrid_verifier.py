"""
Unit tests cho HybridVerifier (Triết lý "REPLACE, NOT ADD").
Kiểm chứng cả Code Path (Deterministic) và Non-Code Path (Calibrated).
"""

import pytest
from core.verification.hybrid_verifier import HybridVerifier


# =============================================================================
# NHÓM 1: CODE PATH (DETERMINISTIC GATE - ZERO LLM CALL)
# =============================================================================

def test_code_path_run_command_success():
    """Lệnh terminal exit code 0 được chấp thuận ngay lập tức."""
    result = {"status": "success", "stdout": "All tests passed", "stderr": "", "exit_code": 0}
    is_valid, reason, score = HybridVerifier.verify("run_command", {"command": "pytest"}, result)
    assert is_valid is True
    assert score == 1.0
    assert "APPROVED" in reason


def test_code_path_run_command_failure_rejected():
    """Lệnh terminal exit code != 0 bị chém thẳng tay."""
    result = {"status": "error", "stdout": "", "stderr": "SyntaxError: unexpected EOF", "exit_code": 1}
    is_valid, reason, score = HybridVerifier.verify("run_command", {"command": "python broken.py"}, result)
    assert is_valid is False
    assert score == 0.0
    assert "REJECTED" in reason


def test_code_path_write_to_file_valid_python(tmp_path):
    """Ghi file Python hợp lệ trên đĩa được thông qua."""
    valid_file = tmp_path / "valid.py"
    valid_file.write_text("def add(a, b):\n    return a + b\n", encoding="utf-8")

    result = {"status": "success", "msg": "Written"}
    is_valid, reason, score = HybridVerifier.verify(
        "write_to_file",
        {"path": str(valid_file)},
        result
    )
    assert is_valid is True
    assert score == 1.0


def test_code_path_write_to_file_syntax_error(tmp_path):
    """File Python bị lỗi cú pháp AST bị từ chối dứt khoát."""
    broken_file = tmp_path / "broken.py"
    broken_file.write_text("def add(a, b\n    return a + b\n", encoding="utf-8")

    result = {"status": "success", "msg": "Written"}
    is_valid, reason, score = HybridVerifier.verify(
        "write_to_file",
        {"path": str(broken_file)},
        result
    )
    assert is_valid is False
    assert score == 0.0
    assert "syntax error" in reason.lower()


def test_code_path_target_file_missing():
    """Công cụ báo tạo file nhưng không tìm thấy file trên đĩa -> REJECT."""
    result = {"status": "success", "msg": "Created"}
    is_valid, reason, score = HybridVerifier.verify(
        "write_to_file",
        {"path": "non_existent_ghost_file_123.py"},
        result
    )
    assert is_valid is False
    assert score == 0.0
    assert "does not exist" in reason


# =============================================================================
# NHÓM 2: NON-CODE PATH (CALIBRATED EVALUATION)
# =============================================================================

def test_non_code_path_valid_search_results():
    """Tìm kiếm web có nội dung thực tế được đánh giá độ tin cậy cao."""
    result = {
        "status": "success",
        "results": ["Python 3.14 documentation", "FastAPI architecture"]
    }
    is_valid, reason, score = HybridVerifier.verify("search_web", {"query": "python"}, result)
    assert is_valid is True
    assert score >= 0.90


def test_non_code_path_empty_payload_rejected():
    """Công cụ trả về payload rỗng bị từ chối."""
    result = []
    is_valid, reason, score = HybridVerifier.verify("search_memory", {"query": "test"}, result)
    assert is_valid is False
    assert "empty payload" in reason.lower()


def test_non_code_path_error_status_rejected():
    """Công cụ trả về dictionary lỗi bị từ chối."""
    result = {"status": "error", "msg": "API timeout"}
    is_valid, reason, score = HybridVerifier.verify("read_url_content", {"url": "https://foo"}, result)
    assert is_valid is False
    assert score == 0.0
