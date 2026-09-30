import os
import shutil
import tempfile
import hashlib
import pytest
from pathlib import Path
from intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR.logic import (
    write_to_file,
    replace_file_content,
    delete_file,
    verify_file,
    read_file,
    _calculate_sha256,
    _guard_path_internal
)

@pytest.fixture
def temp_workspace():
    """Tạo thư mục sandbox cô lập cho kiểm thử M0 File Primitive."""
    test_dir = tempfile.mkdtemp(prefix="jkai_m0_test_")
    yield test_dir
    if os.path.exists(test_dir):
        shutil.rmtree(test_dir, ignore_errors=True)

@pytest.mark.asyncio
async def test_write_atomic_creates_file_and_checksum(temp_workspace):
    target_file = os.path.join(temp_workspace, "test_atomic.txt")
    test_content = "Hello JKAI M0 Sovereign Actuator!\nLine 2\n"
    
    res = await write_to_file(target_path=target_file, content=test_content)
    
    assert res["status"] == "success"
    assert os.path.exists(target_file)
    assert res["atomic"] is True
    assert res["size_bytes"] == len(test_content.encode("utf-8"))
    
    # Kiểm tra sha256 trả về khớp với sha256 vật lý trên đĩa
    expected_sha = hashlib.sha256(test_content.encode("utf-8")).hexdigest()
    assert res["sha256"] == expected_sha
    assert _calculate_sha256(target_file) == expected_sha
    
    # Kiểm tra đọc lại
    read_res = await read_file(path=target_file)
    assert read_res["status"] == "success"
    assert read_res["content"] == test_content

@pytest.mark.asyncio
async def test_write_atomic_refuses_overwrite_without_flag(temp_workspace):
    target_file = os.path.join(temp_workspace, "no_overwrite.txt")
    await write_to_file(target_path=target_file, content="Original")
    
    res = await write_to_file(target_path=target_file, content="New Content", overwrite=False)
    assert res["status"] == "error"
    assert "đã tồn tại" in res["msg"]
    
    # Nội dung cũ không bị thay đổi
    with open(target_file, "r", encoding="utf-8") as f:
        assert f.read() == "Original"

@pytest.mark.asyncio
async def test_write_atomic_backup_on_overwrite(temp_workspace):
    target_file = os.path.join(temp_workspace, "with_backup.txt")
    orig_content = "V1 - Initial Content"
    new_content = "V2 - Overwritten Content"
    
    await write_to_file(target_path=target_file, content=orig_content)
    
    res = await write_to_file(target_path=target_file, content=new_content, overwrite=True)
    assert res["status"] == "success"
    assert res["backup_path"] is not None
    assert os.path.exists(res["backup_path"])
    
    # Kiểm tra nội dung file backup là bản cũ
    with open(res["backup_path"], "r", encoding="utf-8") as f:
        assert f.read() == orig_content
        
    # File hiện tại là bản mới
    with open(target_file, "r", encoding="utf-8") as f:
        assert f.read() == new_content

@pytest.mark.asyncio
async def test_write_atomic_ast_syntax_check(temp_workspace):
    py_file = os.path.join(temp_workspace, "broken.py")
    broken_code = "def syntax_error(:\n    pass\n"
    
    res = await write_to_file(target_path=py_file, content=broken_code)
    assert res["status"] == "error"
    assert "AST Syntax Error" in res["msg"]
    assert not os.path.exists(py_file)  # Không được tạo file lỗi ra đĩa

@pytest.mark.asyncio
async def test_path_guards_security(temp_workspace):
    # Cấm ghi vào file nhạy cảm
    env_file = os.path.join(temp_workspace, ".env")
    res_env = await write_to_file(target_path=env_file, content="SECRET=123")
    assert res_env["status"] == "error"
    assert "chính sách bảo vệ an ninh" in res_env["msg"]

    # Cấm thao tác trực tiếp trên root
    res_root = await write_to_file(target_path="C:\\", content="danger")
    assert res_root["status"] == "error"
    assert "nghiêm cấm để bảo vệ an toàn" in res_root["msg"]

@pytest.mark.asyncio
async def test_replace_file_content_with_backup_and_checksum(temp_workspace):
    file_path = os.path.join(temp_workspace, "surgery.txt")
    initial = "Line 1: Alpha\nLine 2: TARGET_TO_REPLACE\nLine 3: Gamma\n"
    
    await write_to_file(target_path=file_path, content=initial)
    
    rep_res = await replace_file_content(
        path=file_path,
        target="TARGET_TO_REPLACE",
        replacement="REPLACED_SUCCESSFULLY"
    )
    
    assert rep_res["status"] == "success"
    assert rep_res["atomic"] is True
    assert rep_res["backup_path"] is not None
    assert os.path.exists(rep_res["backup_path"])
    
    # Kiểm tra checksum sau thay thế
    expected_sha = _calculate_sha256(file_path)
    assert rep_res["sha256"] == expected_sha
    
    with open(file_path, "r", encoding="utf-8") as f:
        new_text = f.read()
    assert "REPLACED_SUCCESSFULLY" in new_text
    assert "TARGET_TO_REPLACE" not in new_text

@pytest.mark.asyncio
async def test_delete_file_safety_and_backup(temp_workspace):
    del_file = os.path.join(temp_workspace, "to_delete.txt")
    content = "Sensitive or temporary data"
    await write_to_file(target_path=del_file, content=content)
    
    # Không confirm -> từ chối
    res_no_conf = await delete_file(path=del_file, confirm=False)
    assert res_no_conf["status"] == "error"
    assert "xác nhận bắt buộc" in res_no_conf["msg"]
    assert os.path.exists(del_file)
    
    # Có confirm -> xóa và tự động backup
    res_del = await delete_file(path=del_file, confirm=True)
    assert res_del["status"] == "success"
    assert not os.path.exists(del_file)
    assert res_del["backup_path"] is not None
    assert os.path.exists(res_del["backup_path"])
    
    # Kiểm tra nội dung file backup còn nguyên
    with open(res_del["backup_path"], "r", encoding="utf-8") as f:
        assert f.read() == content

@pytest.mark.asyncio
async def test_verify_file_sensor(temp_workspace):
    v_file = os.path.join(temp_workspace, "sensor_check.txt")
    content = "Line A\nLine B\nLine C\n"
    await write_to_file(target_path=v_file, content=content)
    
    v_res = await verify_file(path=v_file)
    assert v_res["status"] == "success"
    assert v_res["exists"] is True
    assert v_res["is_file"] is True
    assert v_res["line_count"] == 3
    assert v_res["size_bytes"] == len(content.encode("utf-8"))
    assert v_res["sha256"] == hashlib.sha256(content.encode("utf-8")).hexdigest()
    
    # Kiểm tra file không tồn tại
    non_existent = os.path.join(temp_workspace, "ghost.txt")
    ghost_res = await verify_file(path=non_existent)
    assert ghost_res["status"] == "error"
    assert "không tồn tại" in ghost_res["msg"]
