# -*- coding: utf-8 -*-
"""
tests/test_slice_2_4_weknora_hardening_contracts.py
===================================================
Kiểm thử nghiệm thu độc lập cho Slice 2.4 (4 Hạng mục Gia cố theo mẫu thiết kế WeKnora sau Phase 2):
1. Mục 1 (WeKnora Parent-Child Chunking + Retrieval Recall Harness — Gia cố Slice 1.4):
   - `search_parent_child_chunks` trong `core/utils/stream_buffer_store.py` định vị đoạn con (`child_span`),
     mở rộng ra đoạn cha (`parent_span`), cập nhật `coverage_ratio` và đo `pre_rerank_retrieval_recall`
     trước khi cắt top-K rerank.
2. Mục 2 (WeKnora Whitelist-Only Egress & SSRF-Safe Guard — Gia cố Slice 1.5):
   - `validate_egress_url_ssrf_safe` trong `tools/web_search.py` và `read_url_content` trong
     `intelligence/skills/DEVOPS/SYSTEM_CORE_EXECUTOR/logic.py` chặn tuyệt đối IP nội bộ/loopback/metadata
     (`127.0.0.1`, `169.254.169.254`, `192.168.1.1`, `localhost`, `file://`) với `SSRF_BLOCKED_PRIVATE_OR_LOOPBACK`
     và chặn tên miền ngoài `allowed_domains` với `EGRESS_DOMAIN_NOT_IN_ALLOWLIST` (`stage_attribution="CONTROLLER_GATE"`).
3. Mục 3 (WeKnora Read-Only Fork/Rewind & Sandbox Checkpoint — Gia cố Slice 2.2):
   - `WorktreeSandboxManager.create_sandbox_checkpoint` và `rewind_sandbox_to_checkpoint` khôi phục
     trạng thái tệp trong sandbox về đúng mã băm SHA-256 của checkpoint, đồng thời từ chối
     (`IRREVERSIBLE_REPLAY_BLOCKED`) nếu danh sách lệnh chờ replay chứa thao tác không thể đảo ngược.
4. Mục 4 (WeKnora Chunk Versioning `edit / diff / rollback` cho `EpisodicMutationLedger` — Gia cố Slice 2.1):
   - `RepoMapIndex` lưu phiên bản nội dung khi file biến đổi, cho phép `diff_episodic_versions`
     trích xuất unified diff giữa 2 phiên bản và `rollback_episodic_version` khôi phục tệp về phiên bản cũ
     kèm đồng bộ tức thì `RepoMap`.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from core.os.cognition.worktree_sandbox import WorktreeSandboxManager
from core.utils.repo_map import RepoMapIndex, query_repo_map
from core.utils.stream_buffer_store import store_stream
from intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR import logic as sce_logic


def test_weknora_1_parent_child_chunking_and_pre_rerank_recall():
    """
    Mục 1: Parent-child chunking tách biệt đoạn khớp hẹp (`child_span`) và ngữ cảnh mở rộng (`parent_span`),
    đồng thời tính `pre_rerank_retrieval_recall` trên tập ứng viên trước khi cắt `top_k`.
    """
    from core.utils.stream_buffer_store import search_parent_child_chunks
    lines = [f"Line {i:03d}: normal log entry" for i in range(1, 121)]
    lines[19] = "Line 020: CRITICAL_ALPHA database connection timeout in pool_a"
    lines[79] = "Line 080: CRITICAL_ALPHA replica failover triggered in pool_b"
    content = "\n".join(lines)

    env = store_stream(content, source_tool="test_weknora_pc", task_id="t_pc_01", preview_chars=120)
    sid = env["stream_id"]

    res = search_parent_child_chunks(
        stream_id=sid,
        query="CRITICAL_ALPHA",
        child_window_lines=3,
        parent_window_lines=15,
        max_results=1,
        required_spans=[(18, 22), (78, 82)],
    )
    assert res["status"] == "success"
    assert res["total_candidates_before_rerank"] == 2
    # Mặc dù max_results=1 chỉ giữ 1 kết quả sau rerank, pre_rerank_retrieval_recall vẫn đo được 1.0 (2/2 spans)
    assert res["pre_rerank_retrieval_recall"] == 1.0
    assert res["post_rerank_retrieval_recall"] == 0.5
    assert len(res["chunks"]) == 1
    chunk = res["chunks"][0]
    c_start, c_end = chunk["child_span"]
    p_start, p_end = chunk["parent_span"]
    assert p_start < c_start and p_end > c_end
    assert "CRITICAL_ALPHA" in chunk["parent_content"]


def test_weknora_2_ssrf_safe_and_whitelist_only_egress_guard(monkeypatch):
    """
    Mục 2: Chặn SSRF (loopback, RFC1918, cloud metadata 169.254.169.254, non-http scheme)
    và chặn domain ngoài allowlist cho cả `validate_egress_url_ssrf_safe` lẫn `read_url_content`.
    """
    from tools.web_search import validate_egress_url_ssrf_safe
    monkeypatch.setenv("JKAI_LOCAL_ONLY_MODE", "0")


    # 1. Chặn AWS/Cloud metadata IP 169.254.169.254
    meta_verdict = validate_egress_url_ssrf_safe("http://169.254.169.254/latest/meta-data/")
    assert meta_verdict["allowed"] is False
    assert meta_verdict["error_code"] == "SSRF_BLOCKED_PRIVATE_OR_LOOPBACK"
    assert meta_verdict["stage_attribution"] == "CONTROLLER_GATE"

    # 2. Chặn loopback / RFC1918
    loop_verdict = validate_egress_url_ssrf_safe("http://127.0.0.1:8001/admin")
    assert loop_verdict["allowed"] is False
    assert loop_verdict["error_code"] == "SSRF_BLOCKED_PRIVATE_OR_LOOPBACK"

    # 3. Chặn domain ngoài whitelist khi cung cấp allowed_domains
    wl_refused = validate_egress_url_ssrf_safe(
        "https://untrusted-site.example.org/data",
        allowed_domains=["docs.python.org", "arxiv.org"],
    )
    assert wl_refused["allowed"] is False
    assert wl_refused["error_code"] == "EGRESS_DOMAIN_NOT_IN_ALLOWLIST"
    assert wl_refused["stage_attribution"] == "CONTROLLER_GATE"

    wl_allowed = validate_egress_url_ssrf_safe(
        "https://docs.python.org/3/library/ast.html",
        allowed_domains=["docs.python.org", "arxiv.org"],
    )
    assert wl_allowed["allowed"] is True

    # 4. Kiểm chứng `read_url_content` tự động chặn SSRF trước khi mở kết nối mạng
    read_res = asyncio.run(
        sce_logic.read_url_content("http://169.254.169.254/latest/meta-data/", task_id="ssrf_test")
    )
    assert read_res["status"] == "refused"
    assert read_res["error_code"] == "SSRF_BLOCKED_PRIVATE_OR_LOOPBACK"


def test_weknora_3_sandbox_checkpoint_and_readonly_rewind_guard(tmp_path: Path):
    """
    Mục 3: Tạo checkpoint trong `WorktreeSandboxManager`, sửa tệp trong sandbox,
    kiểm chứng từ chối replay nếu có thao tác irreversible (`IRREVERSIBLE_REPLAY_BLOCKED`),
    và khôi phục (`rewind_sandbox_to_checkpoint`) tệp về đúng trạng thái checkpoint khi an toàn.
    """
    ws_root = tmp_path / "chk_repo"
    (ws_root / "app").mkdir(parents=True, exist_ok=True)
    (ws_root / "app" / "service.py").write_text("def version():\n    return 'v1'\n", encoding="utf-8")

    mgr = WorktreeSandboxManager(base_workspace=str(ws_root))
    sb = mgr.create_isolated_sandbox(agent_id="agent_c", mission_id="mis_chk", include_extensions=(".py",))
    target_py = sb / "app" / "service.py"

    chk = mgr.create_sandbox_checkpoint(agent_id="agent_c", mission_id="mis_chk", checkpoint_label="before_edit")
    assert chk["status"] == "created"
    chk_id = chk["checkpoint_id"]

    # Biến đổi tệp trong sandbox sang v2
    target_py.write_text("def version():\n    return 'v2_broken'\n", encoding="utf-8")
    assert "v2_broken" in target_py.read_text(encoding="utf-8")

    # Thử rewind kèm lệnh replay không thể đảo ngược (run_command mutation) -> Phải bị từ chối
    refused = mgr.rewind_sandbox_to_checkpoint(
        agent_id="agent_c",
        mission_id="mis_chk",
        checkpoint_id=chk_id,
        pending_actions=[{"tool": "run_command", "command": "rm -rf /tmp/prod_data"}],
    )
    assert refused["status"] == "refused"
    assert refused["error_code"] == "IRREVERSIBLE_REPLAY_BLOCKED"
    assert "v2_broken" in target_py.read_text(encoding="utf-8")

    # Rewind chỉ gồm các bước đọc (read-only branch) -> Thành công và khôi phục đúng nội dung v1
    rewound = mgr.rewind_sandbox_to_checkpoint(
        agent_id="agent_c",
        mission_id="mis_chk",
        checkpoint_id=chk_id,
        pending_actions=[{"tool": "view_file", "path": "app/service.py"}],
    )
    assert rewound["status"] == "rewound"
    assert rewound["restored_files"] >= 1
    assert "return 'v1'" in target_py.read_text(encoding="utf-8")

    mgr.cleanup_sandbox("agent_c", mission_id="mis_chk")


def test_weknora_4_episodic_chunk_versioning_diff_and_rollback(tmp_path: Path):
    """
    Mục 4: `EpisodicMutationLedger` lưu lịch sử phiên bản (`version_id = 1, 2`),
    hỗ trợ `diff_episodic_versions` xem unified diff và `rollback_episodic_version`
    khôi phục tệp + cập nhật tức thì `RepoMap`.
    """
    pkg = tmp_path / "ver_pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    mod_file = pkg / "calc.py"
    mod_file.write_text("def add_v1(a: int, b: int) -> int:\n    return a + b\n", encoding="utf-8")

    idx = RepoMapIndex(workspace_root=tmp_path)
    idx.refresh(force=True)

    # Ghi nhận phiên bản 1
    idx.notify_file_mutation(mod_file, action="write_to_file", task_id="mis_ver")
    # Sửa sang phiên bản 2 (đổi tên hàm sang add_v2)
    mod_file.write_text("def add_v2(a: int, b: int, c: int = 0) -> int:\n    return a + b + c\n", encoding="utf-8")
    idx.notify_file_mutation(mod_file, action="replace_file_content", task_id="mis_ver")

    diff_res = idx.diff_episodic_versions("ver_pkg/calc.py", from_version=1, to_version=2)
    assert diff_res["status"] == "success"
    assert "-def add_v1" in diff_res["unified_diff"]
    assert "+def add_v2" in diff_res["unified_diff"]

    # Rollback về phiên bản 1 -> File trên đĩa và chỉ mục AST RepoMap phải quay về add_v1 tức thì
    rb_res = idx.rollback_episodic_version("ver_pkg/calc.py", target_version=1, task_id="mis_ver")
    assert rb_res["status"] == "rolled_back"
    assert "def add_v1" in mod_file.read_text(encoding="utf-8")

    q_v1 = query_repo_map("add_v1", workspace_root=tmp_path)
    q_v2 = query_repo_map("add_v2", workspace_root=tmp_path)
    assert q_v1["total_matches"] >= 1
    assert q_v2["total_matches"] == 0
