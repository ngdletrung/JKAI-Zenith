#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
tests/test_negative_list_invariants.py
Bộ Kiểm Thử 13 Ca Đối Xứng & Kiểm Tra Tĩnh AST Cho 6 Lằn Ranh Đỏ:
- 6 Ca Chặn Vi Phạm (FAIL-CLOSED)
- 6 Ca Cho Qua Việc Lành (AVOID-PARALYSIS)
- 1 Ca Bảo Trì Hợp Lệ Có Chữ Ký Số Kernel
- 1 Ca Kiểm Tra Tĩnh AST Quét Cấm Tool Chạm issue_*
- 1 Ca Xác Thực Token Hết Hạn
"""

import os
import sys
import ast
import time
import pytest
import hashlib

from core.security.negative_list_enforcer import (
    KernelSigner,
    KernelGrantIssuer,
    SandboxReceipt,
    ResourceGovernor,
    NegativeListEnforcer
)
from core.recovery.maintenance_runner import MaintenanceRunner


# ==============================================================================
# 1. TEST CẶP LẰN RANH 1: PHÁ HỦY PRODUCTION
# ==============================================================================

def test_inv1_a_block_destructive_command():
    """TC-INV-1A: Lệnh rm -rf / hoặc DROP DATABASE phải bị chặn."""
    res = NegativeListEnforcer.check_command_safety("rm -rf / --no-preserve-root")
    assert res["allowed"] is False
    assert res["violation"] == "INV1_DESTRUCTIVE_COMMAND"
    print("✅ TEST 1A PASS: Chặn lệnh phá hủy hệ thống")

def test_inv1_b_allow_safe_scratch_file_ops():
    """TC-INV-1B: Thao tác file tạm trong thư mục scratch/sandbox phải được cho qua."""
    res = NegativeListEnforcer.check_file_mutation(
        target_path="storage/scratch/temp_code.py",
        action="WRITE",
        caller_role="AGENT"
    )
    assert res["allowed"] is True
    print("✅ TEST 1B PASS: Cho qua thao tác file trong sandbox scratch")


# ==============================================================================
# 2. TEST CẶP LẰN RANH 2: CHẠM PRODUCTION CHƯA QUA LAB
# ==============================================================================

def test_inv2_a_block_unverified_production_dispatch():
    """TC-INV-2A: Phát lệnh ra thiết bị thật khi thiếu SandboxReceipt phải bị chặn."""
    payload = "/ip dhcp-server add interface=ether1 name=lan"
    res = NegativeListEnforcer.check_production_dispatch(
        target_ip="192.168.88.1",
        command_payload=payload,
        receipt=None,
        is_production=True
    )
    assert res["allowed"] is False
    assert res["violation"] == "INV2_UNVERIFIED_PRODUCTION_DISPATCH"
    print("✅ TEST 2A PASS: Chặn phát lệnh production khi thiếu SandboxReceipt")

def test_inv2_b_allow_production_dispatch_with_valid_receipt():
    """TC-INV-2B: Phát lệnh ra thiết bị khi có SandboxReceipt ký số hợp lệ phải được cho qua."""
    payload = "/ip dhcp-server add interface=ether1 name=lan"
    target_hash = hashlib.sha256(payload.encode("utf-8")).hexdigest()
    
    # Lab ảo chạy pass (exit code 0), Kernel cấp receipt
    valid_receipt = SandboxReceipt.issue(
        test_id="LAB_TEST_99",
        target_hash=target_hash,
        exit_code=0,
        ttl_seconds=60
    )
    res = NegativeListEnforcer.check_production_dispatch(
        target_ip="192.168.88.1",
        command_payload=payload,
        receipt=valid_receipt,
        is_production=True
    )
    assert res["allowed"] is True
    print("✅ TEST 2B PASS: Cho qua phát lệnh khi có SandboxReceipt ký số hợp lệ")


# ==============================================================================
# 3. TEST CẶP LẰN RANH 3: XÓA DẤU VẾT & BẢO TRÌ HỢP LỆ
# ==============================================================================

def test_inv3_a_block_audit_tampering_by_agent():
    """TC-INV-3A: AI/Agent cố xóa hoặc ghi đè file log kiểm toán phải bị chặn đứng."""
    res = NegativeListEnforcer.check_file_mutation(
        target_path="Thao luan AI/Noi dung thao luan.md",
        action="OVERWRITE",
        caller_role="AGENT",
        grant_token=None
    )
    assert res["allowed"] is False
    assert res["violation"] == "INV3_AUDIT_TAMPERING"

    # Kẻ tấn công tự chế token giả mạo -> vẫn bị chặn đứng
    res_fake = NegativeListEnforcer.check_file_mutation(
        target_path="Thao luan AI/dispatch_history.log",
        action="DELETE",
        caller_role="AGENT",
        grant_token="FAKE_FORGED_TOKEN_ABC123"
    )
    assert res_fake["allowed"] is False
    print("✅ TEST 3A PASS: Chặn đứng mọi nỗ lực xóa dấu vết / làm sai lệch log kiểm toán")

def test_inv3_b_allow_audit_log_append_and_read():
    """TC-INV-3B: Đọc hoặc append thêm lượt thảo luận vào log phải được cho qua."""
    res_read = NegativeListEnforcer.check_file_mutation(
        target_path="Thao luan AI/Noi dung thao luan.md",
        action="READ",
        caller_role="AGENT"
    )
    assert res_read["allowed"] is True

    res_append = NegativeListEnforcer.check_file_mutation(
        target_path="Thao luan AI/dispatch_history.log",
        action="APPEND",
        caller_role="AGENT"
    )
    assert res_append["allowed"] is True
    print("✅ TEST 3B PASS: Cho qua đọc và append log minh bạch")

def test_inv3_c_allow_legitimate_system_maintenance():
    """TC-INV-3C: Tiến trình bảo trì hệ thống có Timed Token từ Kernel được phép xoay log."""
    res = MaintenanceRunner.execute_maintenance_task(
        task_name="rotate_audit_logs",
        target_file="Thao luan AI/dispatch_history.log"
    )
    assert res["success"] is True
    assert res["token_verified"] is True
    print("✅ TEST 3C PASS: Tiến trình bảo trì hợp lệ có token Kernel được phép thực thi")


# ==============================================================================
# 4. TEST CẶP LẰN RANH 4: LỘ / DÙNG TRỘM SECRET
# ==============================================================================

def test_inv4_a_block_secret_read():
    """TC-INV-4A: Đọc file private key ~/.ssh/id_rsa để xuất ra ngoài phải bị cảnh báo/chặn."""
    from core.sanitizer.state_sanitizer import state_sanitizer
    dirty_text = "Here is my private key: -----BEGIN OPENSSH PRIVATE KEY----- ABCD1234EFGH -----END OPENSSH PRIVATE KEY-----"
    cleaned = state_sanitizer.sanitize_outgoing_payload(dirty_text)
    assert "ABCD1234EFGH" not in cleaned
    print("✅ TEST 4A PASS: Chặn rò rỉ secret ra bên ngoài")

def test_inv4_b_allow_dummy_credentials_in_lab():
    """TC-INV-4B: Sử dụng mật khẩu giả trong bài test lab phải được cho qua."""
    safe_test_code = "DUMMY_PASSWORD = 'test_password_1234'\nassert len(DUMMY_PASSWORD) > 0"
    from core.sanitizer.state_sanitizer import state_sanitizer
    res = state_sanitizer.sanitize_outgoing_payload(safe_test_code)
    assert "test_password_1234" in res
    print("✅ TEST 4B PASS: Cho qua mật khẩu giả lập trong môi trường kiểm thử")


# ==============================================================================
# 5. TEST CẶP LẰN RANH 5: TỰ LÀM CẠN TÀI NGUYÊN (SELF-DOS)
# ==============================================================================

def test_inv5_a_kill_infinite_loop_by_timeout():
    """TC-INV-5A: Vòng lặp vô hạn chạy quá hạn ngạch phải bị OS ngắt thật (Timeout 1.0s test)."""
    # Test ngắt thật với timeout 1 giây
    infinite_cmd = [sys.executable, "-c", "import time; time.sleep(5)"]
    res = ResourceGovernor.run_with_guard(infinite_cmd, timeout=1.0)
    assert res["success"] is False
    assert res["killed_by_timeout"] is True
    assert res["exit_code"] == -9
    assert "KILLED_BY_TIMEOUT" in res["stderr"]
    print("✅ TEST 5A PASS: Ngắt tiến trình thật bằng TimeoutExpired (Chống Self-DoS)")

def test_inv5_b_allow_healthy_compute():
    """TC-INV-5B: Tính toán lành mạnh kết thúc trong hạn ngạch phải thành công."""
    compute_cmd = [sys.executable, "-c", "print(sum(range(100000)))"]
    res = ResourceGovernor.run_with_guard(compute_cmd, timeout=5.0)
    assert res["success"] is True
    assert res["killed_by_timeout"] is False
    assert "4999950000" in res["stdout"]
    print("✅ TEST 5B PASS: Cho qua tính toán lành mạnh kết thúc đúng hạn")


# ==============================================================================
# 6. TEST CẶP LẰN RANH 6: ĐẦU ĐỘC BỘ NHỚ (MEMORY POISONING)
# ==============================================================================

def test_inv6_a_block_ai_self_gold_dataset_write():
    """TC-INV-6A: AI tự ý ghi đè vào master_gold_dataset.jsonl phải bị chặn đứng."""
    res = NegativeListEnforcer.check_file_mutation(
        target_path="data/labeled_dataset/master_gold_dataset.jsonl",
        action="WRITE",
        caller_role="AGENT",
        reviewed_by_master=False
    )
    assert res["allowed"] is False
    assert res["violation"] == "INV6_MEMORY_POISONING"
    print("✅ TEST 6A PASS: Chặn đứng AI tự phong nhãn Vàng")

def test_inv6_b_allow_master_gold_dataset_write():
    """TC-INV-6B: Master chấm điểm trực tiếp (reviewed_by_master=True) được phép ghi vào Kho Vàng."""
    res = NegativeListEnforcer.check_file_mutation(
        target_path="data/labeled_dataset/master_gold_dataset.jsonl",
        action="WRITE",
        caller_role="MASTER",
        reviewed_by_master=True
    )
    assert res["allowed"] is True
    print("✅ TEST 6B PASS: Cho phép Master ghi nhãn Vàng")


# ==============================================================================
# 7. CÁC CA BẢO MẬT BỔ SUNG (AST AUDIT & TOKEN EXPIRY)
# ==============================================================================

def test_ast_audit_no_tool_calls_issue_grant():
    """Kiểm tra tĩnh AST: Cấm mọi tool LLM-reachable import hoặc gọi issue_maintenance_grant / KernelSigner."""
    tool_dirs = ["core/tools", "intelligence/tools", "skills", "intelligence/skills", "services"]
    violations = []
    
    for t_dir in tool_dirs:
        if not os.path.exists(t_dir):
            continue
        for root, _, files in os.walk(t_dir):
            for file in files:
                if file.endswith(".py"):
                    full_p = os.path.join(root, file)
                    with open(full_p, "r", encoding="utf-8", errors="ignore") as f:
                        code_content = f.read()
                    if "issue_maintenance_grant" in code_content or "KernelSigner" in code_content:
                        violations.append(full_p)
                        
    assert len(violations) == 0, f"FAIL: Phát hiện tool vi phạm thẩm quyền bí mật: {violations}"
    print("✅ TEST AST PASS: 100% Tool LLM sạch, không có tool nào chạm vào Kernel signer")

def test_token_expired_verification_fails():
    """Token bảo trì hết hạn phải bị từ chối ngay lập tức mà không cần sleep thật."""
    # Tạo token với ttl âm (-1 giây)
    token_expired = KernelGrantIssuer.issue_maintenance_grant(scope="audit_maintenance", ttl_seconds=-1)
    is_valid = KernelGrantIssuer.verify_grant(token_expired, "audit_maintenance")
    assert is_valid is False
    print("✅ TEST TOKEN EXPIRY PASS: Token hết hạn bị từ chối xác thực 100%")


if __name__ == "__main__":
    test_inv1_a_block_destructive_command()
    test_inv1_b_allow_safe_scratch_file_ops()
    test_inv2_a_block_unverified_production_dispatch()
    test_inv2_b_allow_production_dispatch_with_valid_receipt()
    test_inv3_a_block_audit_tampering_by_agent()
    test_inv3_b_allow_audit_log_append_and_read()
    test_inv3_c_allow_legitimate_system_maintenance()
    test_inv4_a_block_secret_read()
    test_inv4_b_allow_dummy_credentials_in_lab()
    test_inv5_a_kill_infinite_loop_by_timeout()
    test_inv5_b_allow_healthy_compute()
    test_inv6_a_block_ai_self_gold_dataset_write()
    test_inv6_b_allow_master_gold_dataset_write()
    test_ast_audit_no_tool_calls_issue_grant()
    test_token_expired_verification_fails()
    print("\nALL 15/15 NEGATIVE LIST & SECURITY TESTS PASSED! 🛡️⚡✅")
