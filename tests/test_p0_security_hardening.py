# -*- coding: utf-8 -*-
"""
tests/test_p0_security_hardening.py
JKAI Zenith P0 Security Hardening Test Suite (TDD Exploit & Regression Prevention).

Kiểm chứng 5 chốt chặn an ninh tối thượng theo khuyến nghị của OpenCode (Lượt 337):
1. Điều kiện 1: Triệt tiêu 100% Secret Hardcode & HMAC Defaults đoán được.
2. Điều kiện 2: Bịt cổng bypass /execute tại ai-executor (buộc có ExecutionGrant).
3. Điều kiện 3: Phủ toàn diện SSRFGuard cho ai-browser (chặn loopback, private IP, metadata).
4. Điều kiện 4: Đồng bộ Blocklist cho RAG Ingest (chặn 100% sealed_C, .env, *.pem, secrets).
5. Điều kiện 5: Bảo vệ Host Bridge chống Path Traversal và cô lập quyền hạn.
"""

import asyncio
import os
import tempfile
from pathlib import Path
from unittest.mock import AsyncMock, patch

import pytest

from core.kernel.policy_snapshot import (
    create_execution_grant,
    verify_execution_grant,
    _SHARED_EXECUTION_SECRET,
)
from core.utils.project_workspace import is_allowed_workspace_rel
from tools.web_search import validate_egress_url_ssrf_safe


def test_condition_1_zero_hardcoded_secrets_and_dynamic_hmac():
    """
    [P0.1]: Tuyệt đối cấm secret hardcode và HMAC defaults tĩnh trong mã nguồn.
    - AKAI_PRIME_SUPER_SECRET_999 phải có đúng 0 lần xuất hiện trong mã nguồn logic/core.
    - _SHARED_EXECUTION_SECRET và _TOKEN_SECRET_KEY không được mang chuỗi mặc định tĩnh cũ.
    """
    root_dir = Path(".")
    hardcoded_hits = []

    for root, dirs, files in os.walk(root_dir):
        # Bỏ qua git, cache, venv, node_modules, và các tệp nhật ký/archive lịch sử
        if any(x in root for x in [".git", "__pycache__", ".venv", "node_modules", "Thao luan AI"]):
            continue
        for f in files:
            if f == "test_p0_security_hardening.py":
                continue
            if f.endswith((".py", ".sh", ".env")):
                p = Path(root) / f
                try:
                    text = p.read_text(encoding="utf-8", errors="ignore")
                    if "AKAI_PRIME_SUPER_SECRET_999" in text:
                        hardcoded_hits.append(str(p))
                    if "jkai_zenith_sovereign_governance_secret_2026" in text:
                        hardcoded_hits.append(str(p))
                    if "zenith-zero-trust-secret-key-v1" in text:
                        hardcoded_hits.append(str(p))
                    if "JKAI_OPERATIONAL_WITNESS_SHARED_SALT_2026" in text:
                        hardcoded_hits.append(str(p))
                except Exception:
                    pass

    assert len(hardcoded_hits) == 0, f"Phát hiện secret hardcode tại: {hardcoded_hits}"

    # Kiểm tra khóa runtime không phải là chuỗi tĩnh đoán trước được
    assert _SHARED_EXECUTION_SECRET != b"jkai_zenith_sovereign_governance_secret_2026"
    assert len(_SHARED_EXECUTION_SECRET) >= 16


def test_condition_2_executor_execute_endpoint_requires_grant():
    """
    [P0.2]: Endpoint /execute của ai-executor phải bắt buộc kiểm tra ExecutionGrant.
    Gửi request không có grant hoặc grant giả mạo -> Phải bị từ chối fail-closed.
    """
    from services.ai_executor_service import execute_task_with_grant_check

    # 1. Tấn công không kèm grant -> Phải bị từ chối
    unauth_payload = {
        "task_id": "attack_task_01",
        "steps": [{"tool": "terminal_exec", "args": {"cmd": "whoami"}}],
    }
    res_unauth = asyncio.run(execute_task_with_grant_check(unauth_payload))
    assert res_unauth["status"] == "error"
    assert res_unauth["denied"] is True
    assert "FAIL-CLOSED" in res_unauth["msg"]

    # 2. Tấn công với grant bị giả mạo chữ ký -> Phải bị từ chối
    forged_grant = {
        "grant_id": "grant_fake_99",
        "mission_id": "m_fake",
        "snapshot_id": "snap_fake",
        "tool_name": "batch_execute",
        "args_hash": "abc123hash",
        "expires_at": 9999999999,
        "signature": "fake_signature_abc_123",
    }
    forged_payload = {
        "task_id": "attack_task_02",
        "steps": [{"tool": "terminal_exec", "args": {"cmd": "id"}}],
        "grant": forged_grant,
    }
    res_forged = asyncio.run(execute_task_with_grant_check(forged_payload))
    assert res_forged["status"] == "error"
    assert res_forged["denied"] is True

    # 3. Yêu cầu hợp lệ được ký bởi AuthorityGateway -> Được phép thực thi
    steps_payload = [{"tool": "echo_tool", "args": {"msg": "hello"}}]
    valid_grant = create_execution_grant(
        mission_id="m_valid",
        snapshot_id="snap_valid",
        tool_name="batch_execute",
        actual_args={"steps": steps_payload},
        ttl_seconds=30,
    )
    valid_payload = {
        "task_id": "valid_task_03",
        "steps": steps_payload,
        "grant": valid_grant.to_dict(),
    }
    # Mock executor.run_steps để kiểm tra luồng bypass đã bị chặn
    with patch("services.ai_executor_service.run_steps_internal", new_callable=AsyncMock) as mock_run:
        mock_run.return_value = {"status": "success", "executed_steps": 1}
        res_valid = asyncio.run(execute_task_with_grant_check(valid_payload))
        assert res_valid["status"] == "success"
        assert res_valid.get("denied") is not True


def test_condition_3_ai_browser_ssrf_guard_blocks_private_and_metadata():
    """
    [P0.3]: Phủ toàn diện SSRFGuard cho ai-browser (/browse, /crawl, /screenshot).
    Chặn đứng mọi địa chỉ IP private, loopback, metadata và internal Docker host.
    """
    attack_urls = [
        "http://127.0.0.1:6333/collections",
        "http://localhost:11434/api/tags",
        "http://0.0.0.0:8000/metrics",
        "http://169.254.169.254/latest/meta-data",
        "http://10.0.0.5:9999/admin",
        "http://192.168.1.1/router",
        "http://172.18.0.2:8000/terminal",
        "http://ai-control-plane.internal/pulse",
        "http://host.docker.internal:9998/terminal",
    ]

    for target in attack_urls:
        check = validate_egress_url_ssrf_safe(target)
        assert check["allowed"] is False, f"SSRF Guard đã để lọt địa chỉ nguy hiểm: {target}"
        assert check["status"] == "refused"

    # URL ngoài hợp lệ phải đi qua được (khi không có whitelist gắt)
    valid_url = "https://raw.githubusercontent.com/robots.txt"
    check_valid = validate_egress_url_ssrf_safe(valid_url, allowed_domains=["githubusercontent.com"])
    assert check_valid["allowed"] is True


def test_condition_4_rag_ingest_strictly_respects_workspace_blocklist():
    """
    [P0.4]: RAG Ingest bắt buộc tuân thủ blocklist không gian làm việc.
    Chặn 100% sealed_C, .env, *.pem, và các tệp bí mật không được nuốt vào Vector DB.
    """
    from rag.ingest.ingest import should_allow_ingest_file

    forbidden_files = [
        "sealed_C/sovereign_exam_tasks.json",
        "sealed_C/group_E_master_communication_rubric.md",
        ".env",
        ".env.production",
        "certs/server_private_key.pem",
        "credentials/service_account.json",
        "config/master_secret_token.txt",
    ]

    for fpath in forbidden_files:
        assert should_allow_ingest_file(fpath) is False, f"RAG Ingest để lọt file nhạy cảm: {fpath}"

    valid_files = [
        "docs/architecture/SYSTEM_ARCHITECTURE.md",
        "README.md",
        "CHANGELOG.md",
        "knowledge/python_best_practices.txt",
    ]

    for fpath in valid_files:
        assert should_allow_ingest_file(fpath) is True, f"RAG Ingest chặn nhầm tài liệu hợp lệ: {fpath}"


def test_condition_5_host_bridge_path_traversal_containment():
    """
    [P0.5]: Host Bridge & Path Traversal Containment.
    Bảo đảm mọi đường dẫn file do user chỉ định không được thoát ra ngoài thư mục workspace.
    """
    from scripts.host_bridge import is_safe_contained_path

    workspace_root = Path(".").resolve()

    # Đường dẫn hợp lệ trong workspace
    assert is_safe_contained_path("core/kernel/policy_snapshot.py", workspace_root) is True
    assert is_safe_contained_path("README.md", workspace_root) is True

    # Đường dẫn cố tình thoát ra ngoài (Path Traversal)
    assert is_safe_contained_path("../../../Windows/System32/cmd.exe", workspace_root) is False
    assert is_safe_contained_path("..\\..\\..\\Windows\\win.ini", workspace_root) is False
    assert is_safe_contained_path("C:/Windows/notepad.exe", workspace_root) is False
    assert is_safe_contained_path("/etc/passwd", workspace_root) is False


def test_condition_6_no_docker_socket_mounted_in_production_compose():
    """
    [P0.6 - Red Team Audit Pinning]: Triệt để gỡ bỏ docker.sock khỏi docker-compose.yml.
    Bảo đảm không có service nào (ai-control-plane, ai-worker, mission-control...) mount docker.sock,
    tuân thủ tuyệt đối Điều 3 .keyword.md ("Cấm mount docker.sock vào container Lab của AI").
    """
    compose_path = Path("docker-compose.yml")
    assert compose_path.exists(), "Tệp docker-compose.yml không tồn tại"
    content = compose_path.read_text(encoding="utf-8")
    assert "docker.sock" not in content, (
        "docker-compose.yml vẫn còn chứa mount docker.sock! "
        "Yêu cầu triệt để gỡ bỏ hoặc kiểm soát nghiêm ngặt theo khuyến nghị Red Team Lượt 340."
    )

