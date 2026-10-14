# -*- coding: utf-8 -*-
"""
tests/test_slice_2_3_mcp_allowlist_and_kv_prefix.py
===================================================
Kiểm thử nghiệm thu độc lập cho Slice 2.3 (Mảnh ghép cuối Pha 2) + Đóng 2 điều kiện Lượt 274 của OpenCode:
1. Đóng Điều kiện 1 Lượt 274 (`giai-trinh-+3-excluded`):
   - `answer_architectural_questions()["Q6_BLAST_RADIUS"]` phải cung cấp `excluded_third_party_breakdown`
     chi tiết từng thư mục con trong `files/` (`files/OfficeCLI-main`: 88, `files/laya-main`: 127,
     `files/system_prompts_leaks-main`: 1 -> tổng cộng đúng `216` tệp) và khớp tuyệt đối phương trình bảo toàn:
     `indexed_python_files + excluded_third_party_files + syntax_error_files == total_workspace_py_files`.
2. Đóng Điều kiện 2 Lượt 274 (`nguong-dung-luong-sandbox`):
   - `WorktreeSandboxManager.create_isolated_sandbox(..., max_total_bytes=...)` phải từ chối (`RuntimeError`
     kèm mã `[SANDBOX-QUOTA-EXCEEDED]`) và tự động dọn sạch thư mục dở dang nếu tổng dung lượng tệp vượt ngưỡng.
3. `LocalMCPPilotGovernor` (`core/kernel/mcp_pilot_allowlist.py`) & `tools/jkai-mcp/`:
   - Chặn máy chủ MCP / công cụ ngoài `allowlist` với phản hồi từ chối minh bạch (`status="refused"`,
     `error_code="MCP_NOT_IN_ALLOWLIST"`, `stage_attribution="CONTROLLER_GATE"`).
   - Chặn endpoint MCP từ xa (non-loopback) khi chạy ở chế độ `LOCAL_ONLY_MODE`.
   - `tools/jkai-mcp/mcp-config.example.json` không còn đường dẫn cứng `D:\\Docker\\JKAI`.
4. `KV Prefix Stability Telemetry` (`core/kernel/context_manager.py`):
   - Giữ ổn định tiền tố `system` qua nhiều lượt cắt tỉa (`prune_messages`) trong cùng phiên,
     ghi nhận `prefix_sha256`, `pinned_prefix_tokens`, `dynamic_suffix_tokens`, và đạt `warm_turn_hit_rate == 1.0`
     khi system prompt cố định nhưng lịch sử hội thoại trượt qua cửa sổ token.
"""

from __future__ import annotations

import json
from pathlib import Path
import pytest

from core.kernel.context_manager import ContextManager
from core.os.cognition.worktree_sandbox import WorktreeSandboxManager
from core.utils.repo_map import answer_architectural_questions


def test_excluded_third_party_breakdown_and_conservation_equation():
    """
    Đóng Điều kiện 1 Lượt 274 (`giai-trinh-+3-excluded`):
    Kiểm chứng phân rã chính xác 216 tệp `.py` trong `files/` và phương trình bảo toàn tệp.
    """
    ans = answer_architectural_questions()
    q6 = ans["Q6_BLAST_RADIUS"]

    breakdown = q6.get("excluded_third_party_breakdown")
    assert isinstance(breakdown, dict), "Q6_BLAST_RADIUS must expose excluded_third_party_breakdown"
    assert breakdown.get("files/OfficeCLI-main") == 88
    assert breakdown.get("files/laya-main") == 127
    assert breakdown.get("files/system_prompts_leaks-main") == 1
    assert sum(breakdown.values()) == q6["excluded_third_party_files"] == 216

    # Phương trình bảo toàn tuyệt đối
    assert (
        q6["indexed_python_files"]
        + q6["excluded_third_party_files"]
        + q6["syntax_error_files"]
        == q6["total_workspace_py_files"]
    )


def test_worktree_sandbox_enforces_max_total_bytes_quota(tmp_path: Path):
    """
    Đóng Điều kiện 2 Lượt 274 (`nguong-dung-luong-sandbox`):
    Khi tổng dung lượng tệp materialize vượt `max_total_bytes`, `create_isolated_sandbox`
    phải từ chối với `[SANDBOX-QUOTA-EXCEEDED]` và dọn sạch thư mục sandbox dở dang (`0` mục rác).
    """
    ws_root = tmp_path / "quota_repo"
    (ws_root / "src").mkdir(parents=True, exist_ok=True)
    (ws_root / "src" / "small.py").write_text("X = 'a' * 200\n", encoding="utf-8")
    (ws_root / "src" / "large.py").write_text("Y = '" + ("b" * 2048) + "'\n", encoding="utf-8")

    mgr = WorktreeSandboxManager(base_workspace=str(ws_root))

    # Ngưỡng 500 bytes < tổng dung lượng (~2.2 KB) -> Phải từ chối và xóa sạch sandbox dở dang
    with pytest.raises(RuntimeError, match="SANDBOX-QUOTA-EXCEEDED"):
        mgr.create_isolated_sandbox(
            agent_id="coder_quota",
            mission_id="mis_quota",
            include_extensions=(".py",),
            max_total_bytes=500,
        )

    assert len(mgr.list_active_sandboxes()) == 0

    # Ngưỡng 10 KB -> Thành công và ghi nhận copied_bytes vào metadata
    sb_ok = mgr.create_isolated_sandbox(
        agent_id="coder_ok",
        mission_id="mis_quota_ok",
        include_extensions=(".py",),
        max_total_bytes=10_000,
    )
    assert sb_ok.exists()
    active = mgr.list_active_sandboxes()
    assert len(active) == 1
    assert active[0]["copied_bytes"] > 2000
    assert active[0]["max_total_bytes"] == 10_000
    mgr.cleanup_sandbox("coder_ok", mission_id="mis_quota_ok")
    assert len(mgr.list_active_sandboxes()) == 0


def test_local_mcp_pilot_allowlist_and_local_only_endpoint_guard():
    """
    Kiểm chứng `LocalMCPPilotGovernor`:
    - Cho phép server & tool nằm trong allowlist (`jkai` / `jkai_ping`, `jkai_repo_map`).
    - Từ chối minh bạch server hoặc tool lạ (`status="refused"`, `error_code="MCP_NOT_IN_ALLOWLIST"`,
      `stage_attribution="CONTROLLER_GATE"`).
    - Từ chối endpoint không phải loopback (`https://evil-mcp.example.com`) khi `local_only=True`.
    - Kiểm tra `tools/jkai-mcp/mcp-config.example.json` không còn hardcode `D:\\Docker\\JKAI`.
    """
    from core.kernel.mcp_pilot_allowlist import LocalMCPPilotGovernor

    gov = LocalMCPPilotGovernor()

    ok_verdict = gov.authorize_mcp_call(
        server_name="jkai",
        tool_name="jkai_repo_map",
        endpoint_url="http://localhost:8001",
        local_only=True,
    )
    assert ok_verdict["status"] == "allowed"
    assert ok_verdict["allowed"] is True

    bad_server = gov.authorize_mcp_call(
        server_name="untrusted_third_party_mcp",
        tool_name="jkai_ping",
        endpoint_url="http://localhost:8001",
        local_only=True,
    )
    assert bad_server["status"] == "refused"
    assert bad_server["allowed"] is False
    assert bad_server["error_code"] == "MCP_NOT_IN_ALLOWLIST"
    assert bad_server["stage_attribution"] == "CONTROLLER_GATE"

    bad_tool = gov.authorize_mcp_call(
        server_name="jkai",
        tool_name="drop_production_db",
        endpoint_url="http://127.0.0.1:8001",
        local_only=True,
    )
    assert bad_tool["status"] == "refused"
    assert bad_tool["error_code"] == "MCP_TOOL_NOT_IN_ALLOWLIST"
    assert bad_tool["stage_attribution"] == "CONTROLLER_GATE"

    bad_remote = gov.authorize_mcp_call(
        server_name="jkai",
        tool_name="jkai_ping",
        endpoint_url="https://remote-mcp.example.com/v1",
        local_only=True,
    )
    assert bad_remote["status"] == "refused"
    assert bad_remote["error_code"] == "MCP_REMOTE_BLOCKED_IN_LOCAL_ONLY_MODE"
    assert bad_remote["stage_attribution"] == "CONTROLLER_GATE"

    mcp_cfg_path = Path(__file__).resolve().parents[1] / "tools" / "jkai-mcp" / "mcp-config.example.json"
    mcp_cfg_text = mcp_cfg_path.read_text(encoding="utf-8")
    assert "D:\\Docker\\JKAI" not in mcp_cfg_text


def test_kv_prefix_stability_telemetry_across_sliding_window_turns():
    """
    Kiểm chứng `ContextManager` KV Prefix Telemetry:
    - Khi hội thoại kéo dài qua 4 lượt và bị cắt tỉa cửa sổ trượt (`prune_messages`),
      phần tiền tố `system` (`pinned_prefix`) vẫn giữ nguyên 100% mã băm `prefix_sha256`.
    - Từ lượt 2 trở đi (`warm_turns`), `prefix_reuse_hit` luôn là `True` và `warm_turn_hit_rate == 1.0`.
    """
    cm = ContextManager(max_token_budget=600, reserved_output_tokens=150)
    session_id = "sess_kv_slice_2_3"
    sys_msg = {
        "role": "system",
        "content": "You are JKAI Zenith Sovereign Kernel. Follow all safety and AST invariants.",
    }
    rules_str = json.dumps({"version": "28.4.1", "strict_aci": True}, sort_keys=True)

    history = [sys_msg]
    for turn_idx in range(1, 5):
        history.append({"role": "user", "content": f"Turn {turn_idx} question: " + ("data " * 60)})
        history.append({"role": "assistant", "content": f"Turn {turn_idx} answer: " + ("resp " * 60)})
        pruned = cm.prune_messages(history, rules_json=rules_str, session_id=session_id)
        assert pruned[0]["role"] == "system"

    telemetry = cm.get_kv_prefix_telemetry(session_id)
    assert telemetry["total_turns"] == 4
    assert telemetry["prefix_hits"] == 3
    assert telemetry["warm_turn_hit_rate"] == 1.0
    assert telemetry["pinned_prefix_tokens"] > 0
    assert len(telemetry["prefix_sha256"]) == 64
