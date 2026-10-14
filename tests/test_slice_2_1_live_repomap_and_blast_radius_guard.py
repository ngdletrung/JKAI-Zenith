# -*- coding: utf-8 -*-
"""
tests/test_slice_2_1_live_repomap_and_blast_radius_guard.py
===========================================================
Kiểm thử nghiệm thu độc lập cho Slice 2.1 (Phase 2 — Đại Trụ II Chiều Sâu):
1. Đồng bộ tự động tức thì (`< 5ms`) giữa các thao tác sửa file (`write_to_file`,
   `replace_file_content`, `multi_replace_file_content`, `delete_file`) và `RepoMapIndex`
   mà không bị trễ bởi cửa sổ cache 30 giây hay phải chạy tay `graph_syncer.py`.
2. Kiểm tra tác động chéo liên file (`Cross-File Blast Radius Impact Guard`):
   Khi sửa/xóa một hàm hoặc lớp trong file A khiến file B (đang `from A import symbol`)
   bị gãy phụ thuộc, công cụ sửa file phát hiện ngay `broken_downstream_imports` và cảnh báo
   trực tiếp cho Agent.
3. Bộ nhớ kinh nghiệm biến đổi mã nguồn (`EpisodicMutationLedger`):
   Theo dõi chuỗi thao tác sửa file theo `task_id` / `mission_id`, ghi nhận các phụ thuộc
   liên file bị gãy (`unresolved_broken_imports`) và tự động xóa cảnh báo khi Agent đã sửa xong file B.
4. Nâng cấp `tools/graph_syncer.py`: Hoạt động Local-First qua `RepoMapIndex` khi không bật FalkorDB.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

from core.utils.repo_map import (
    get_repo_map_index,
    query_repo_map,
)
from intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR import logic as core_logic
import tools.graph_syncer as graph_syncer


def test_live_repomap_auto_sync_on_write_and_replace_without_30s_stale_window(tmp_path: Path):
    """
    [Slice 2.1 - Đồng bộ tức thì RepoMap khi sửa file]:
    Khi `RepoMapIndex` vừa quét xong (đang trong cửa sổ cache 30s), mọi thao tác
    `write_to_file` / `replace_file_content` phải tự động cập nhật chỉ mục AST của file đó
    ngay lập tức để `query_repo_map` nhìn thấy symbol mới mà không cần `force=True`.
    """
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    provider_py = pkg_dir / "provider.py"
    provider_py.write_text(
        "def compute_alpha(x: int) -> int:\n    return x + 1\n",
        encoding="utf-8",
    )

    # Khởi tạo index lần đầu (bắt đầu cửa sổ cache 30s)
    idx = get_repo_map_index(workspace_root=tmp_path)
    assert idx is not None
    q1 = query_repo_map(query="compute_alpha", workspace_root=tmp_path)
    assert q1["total_matches"] >= 1

    # Ngay lập tức dùng replace_file_content thêm hàm compute_beta vào provider.py
    edit_res = asyncio.run(
        core_logic.replace_file_content(
            path=str(provider_py),
            target="def compute_alpha(x: int) -> int:\n    return x + 1",
            replacement=(
                "def compute_alpha(x: int) -> int:\n    return x + 1\n\n"
                "def compute_beta(y: int) -> int:\n    return y * 2"
            ),
            task_id="test_s21_live_sync",
        )
    )
    assert edit_res["status"] == "success"

    # Truy vấn ngay lập tức (không truyền force=True) phải thấy ngay compute_beta
    q2 = query_repo_map(query="compute_beta", workspace_root=tmp_path)
    assert q2["total_matches"] >= 1
    assert q2["symbol_matches"][0]["name"] == "compute_beta"
    assert q2["symbol_matches"][0]["path"] == "pkg/provider.py"


def test_cross_file_blast_radius_impact_detects_broken_downstream_importers_on_edit(tmp_path: Path):
    """
    [Slice 2.1 - Kiểm tra tác động chéo liên file (Cross-File Blast Radius Guard)]:
    Khi `pkg/consumer.py` đang `from pkg.provider import compute_alpha`, nếu Agent sửa
    `pkg/provider.py` đổi tên `compute_alpha` thành `compute_alpha_v2`, kết quả trả về của
    `replace_file_content` phải đính kèm `blast_radius_impact` chỉ rõ:
    - `removed_symbols`: `["compute_alpha"]`
    - `added_symbols`: `["compute_alpha_v2"]`
    - `broken_downstream_imports`: chứa `pkg/consumer.py` với `missing_symbols: ["compute_alpha"]`.
    """
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    provider_py = pkg_dir / "provider.py"
    consumer_py = pkg_dir / "consumer.py"

    provider_py.write_text(
        "def compute_alpha(x: int) -> int:\n    return x + 10\n",
        encoding="utf-8",
    )
    consumer_py.write_text(
        "from pkg.provider import compute_alpha\n\n"
        "def run_pipeline(v: int) -> int:\n    return compute_alpha(v)\n",
        encoding="utf-8",
    )

    # Nạp RepoMapIndex cho workspace
    get_repo_map_index(workspace_root=tmp_path)

    # Đổi tên compute_alpha -> compute_alpha_v2 trong provider.py
    edit_res = asyncio.run(
        core_logic.replace_file_content(
            path=str(provider_py),
            target="def compute_alpha(x: int) -> int:",
            replacement="def compute_alpha_v2(x: int) -> int:",
            task_id="mission_blast_check",
        )
    )
    assert edit_res["status"] == "success"
    impact = edit_res.get("blast_radius_impact")
    assert impact is not None
    assert "compute_alpha" in impact["removed_symbols"]
    assert "compute_alpha_v2" in impact["added_symbols"]
    assert len(impact["broken_downstream_imports"]) == 1
    broken = impact["broken_downstream_imports"][0]
    assert broken["importer_path"] == "pkg/consumer.py"
    assert "compute_alpha" in broken["missing_symbols"]
    assert "[BLAST-RADIUS-WARNING]" in edit_res["msg"]


def test_episodic_mutation_ledger_tracks_and_resolves_broken_downstream_imports(tmp_path: Path):
    """
    [Slice 2.1 - Bộ nhớ kinh nghiệm biến đổi mã nguồn (EpisodicMutationLedger)]:
    - Ghi nhận lịch sử biến đổi file theo `task_id`.
    - Khi `pkg/provider.py` xóa `compute_alpha`, `get_episodic_mutation_ledger` báo cáo
      `unresolved_broken_imports` tại `pkg/consumer.py`.
    - Khi Agent tiếp tục sửa `pkg/consumer.py` sang `from pkg.provider import compute_alpha_v2`,
      `unresolved_broken_imports` tự động được giải tỏa về `[]`!
    """
    from core.utils.repo_map import get_episodic_mutation_ledger
    pkg_dir = tmp_path / "pkg"
    pkg_dir.mkdir(parents=True, exist_ok=True)
    (pkg_dir / "__init__.py").write_text("", encoding="utf-8")
    provider_py = pkg_dir / "provider.py"
    consumer_py = pkg_dir / "consumer.py"

    provider_py.write_text(
        "def legacy_helper(a: int) -> int:\n    return a * 3\n",
        encoding="utf-8",
    )
    consumer_py.write_text(
        "from pkg.provider import legacy_helper\n\n"
        "def use_helper(a: int) -> int:\n    return legacy_helper(a)\n",
        encoding="utf-8",
    )
    get_repo_map_index(workspace_root=tmp_path)

    # Bước 1: Đổi legacy_helper -> modern_helper ở provider.py
    asyncio.run(
        core_logic.replace_file_content(
            path=str(provider_py),
            target="def legacy_helper(a: int) -> int:",
            replacement="def modern_helper(a: int) -> int:",
            task_id="mission_episodic_01",
        )
    )
    ledger_step1 = get_episodic_mutation_ledger(task_id="mission_episodic_01", workspace_root=tmp_path)
    assert ledger_step1["episode_count"] >= 1
    assert len(ledger_step1["unresolved_broken_imports"]) == 1
    assert ledger_step1["unresolved_broken_imports"][0]["importer_path"] == "pkg/consumer.py"

    # Bước 2: Cập nhật consumer.py sang modern_helper
    asyncio.run(
        core_logic.replace_file_content(
            path=str(consumer_py),
            target="from pkg.provider import legacy_helper\n\ndef use_helper(a: int) -> int:\n    return legacy_helper(a)",
            replacement="from pkg.provider import modern_helper\n\ndef use_helper(a: int) -> int:\n    return modern_helper(a)",
            task_id="mission_episodic_01",
        )
    )
    ledger_step2 = get_episodic_mutation_ledger(task_id="mission_episodic_01", workspace_root=tmp_path)
    assert ledger_step2["episode_count"] >= 2
    assert ledger_step2["unresolved_broken_imports"] == []


def test_graph_syncer_local_ast_sync_works_without_falkordb(monkeypatch):
    """
    [Slice 2.1 - Đồng bộ Local-First trong tools/graph_syncer.py]:
    Khi `JKAI_ENABLE_FALKOR_SYNC=0` (mặc định Local-First), `sync_knowledge()`
    đồng bộ trực tiếp qua `RepoMapIndex` và trả về thống kê đồ thị AST thực tế.
    """
    monkeypatch.setenv("JKAI_ENABLE_FALKOR_SYNC", "0")
    res = asyncio.run(graph_syncer.sync_knowledge())
    assert isinstance(res, dict)
    assert res.get("status") == "success"
    assert res.get("mode") == "local_ast_graph"
    assert res.get("indexed_python_files", 0) >= 2300
    assert res.get("dependency_edges", 0) >= 2000
