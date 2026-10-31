import pytest
from pathlib import Path
from core.kernel.transaction_manager import WorkspaceTransactionManager, get_transaction_manager

def test_transaction_manager_snapshot_and_rollback(tmp_path: Path):
    """Kiểm tra chụp snapshot và tự động rollback khi code bị sửa hỏng."""
    tx_mgr = WorkspaceTransactionManager(shadow_dir=tmp_path / "shadow")
    
    test_file = tmp_path / "target.py"
    original_code = "def valid_func():\n    return 42\n"
    test_file.write_text(original_code, encoding="utf-8")
    
    task_id = "test_tx_001"
    
    # 1. Begin transaction
    assert tx_mgr.begin_transaction(task_id, [str(test_file)]) is True
    
    # 2. Giả lập Agent sửa sai làm hỏng cú pháp Python
    broken_code = "def valid_func():\n    return 42 +++ ??? (syntax error)"
    test_file.write_text(broken_code, encoding="utf-8")
    
    # 3. Verify transaction -> Phải phát hiện lỗi cú pháp
    is_valid, err_msg = tx_mgr.verify_transaction([str(test_file)])
    assert is_valid is False
    assert "Lỗi cú pháp Python" in str(err_msg)
    
    # 4. Rollback -> Phải tự động khôi phục 100% nội dung gốc
    restored = tx_mgr.rollback(task_id)
    assert len(restored) == 1
    assert test_file.read_text(encoding="utf-8") == original_code

def test_transaction_manager_commit_on_success(tmp_path: Path):
    """Kiểm tra commit thành công khi sửa code hợp lệ."""
    tx_mgr = WorkspaceTransactionManager(shadow_dir=tmp_path / "shadow")
    
    test_file = tmp_path / "target2.py"
    test_file.write_text("x = 1\n", encoding="utf-8")
    
    task_id = "test_tx_002"
    tx_mgr.begin_transaction(task_id, [str(test_file)])
    
    # Sửa code hợp lệ
    test_file.write_text("x = 2\n", encoding="utf-8")
    is_valid, err = tx_mgr.verify_transaction([str(test_file)])
    assert is_valid is True
    assert err is None
    
    # Commit
    tx_mgr.commit(task_id)
    assert task_id not in tx_mgr._active_transactions
    assert test_file.read_text(encoding="utf-8") == "x = 2\n"
