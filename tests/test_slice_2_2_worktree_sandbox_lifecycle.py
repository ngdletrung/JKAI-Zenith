# -*- coding: utf-8 -*-
"""
tests/test_slice_2_2_worktree_sandbox_lifecycle.py
==================================================
Kiểm thử nghiệm thu độc lập cho Slice 2.2 (Pha 2):
1. `WorktreeSandboxManager` (`core/os/cognition/worktree_sandbox.py`):
   - Triệt tiêu đệ quy `.zenith/worktrees` bằng `strip_worktree_nesting()`.
   - Khởi tạo sandbox cô lập dùng chung bộ lọc `iter_workspace_files()` (không bao giờ sao chép `.zenith`, `.git`, `node_modules`, `__pycache__`, `.venv`).
   - Quản lý vòng đời đầy đủ: `create_isolated_sandbox`, `list_active_sandboxes`, `cleanup_sandbox`, `evict_mission_sandboxes`, `prune_expired_sandboxes(ttl_seconds=..., now=...)`.
2. `services/ai-brain/state_pipeline.py`:
   - Đồng bộ bộ lọc loại trừ chuẩn `EXCLUDED_WORKSPACE_DIRS` và `strip_worktree_nesting` từ `core.utils.project_workspace`.
3. Đóng Điều kiện Mở rộng 1 của OpenCode (Lượt 272 — `ledger-TTL`):
   - `EpisodicMutationLedger` trong `core/utils/repo_map.py` có giới hạn LRU (`max_episodes`), TTL (`episode_ttl_seconds`), `purge_expired_episodes(now=...)` và `evict_mission_episodes(mission_id)`.
4. Đóng Điều kiện Mở rộng 2 của OpenCode (Lượt 272 — `ghi-ro-gioi-han-signature`):
   - `Blast Radius Guard` phát hiện thay đổi chữ ký/số lượng tham số bắt buộc (`signature_changes`) của hàm được import liên file, đồng thời công bố minh bạch `blast_guard_blindspots`.
"""

from __future__ import annotations

import asyncio
import importlib.util
import time
from pathlib import Path

from core.os.cognition.worktree_sandbox import WorktreeSandboxManager
from core.utils.repo_map import RepoMapIndex
from intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR import logic as sce_logic


def test_worktree_sandbox_lifecycle_non_recursive_and_ttl_prune(tmp_path: Path):
    """
    1. Khởi tạo WorktreeSandboxManager từ đường dẫn đã lồng trong `.zenith/worktrees/...`
       phải tự động bóc về canonical root (`0` nested `.zenith/worktrees`).
    2. `create_isolated_sandbox` chỉ materialize tệp hợp lệ qua `iter_workspace_files()`,
       tuyệt đối không sao chép `.zenith` hay `node_modules` vào trong sandbox.
    3. `prune_expired_sandboxes` và `evict_mission_sandboxes` dọn sạch 100% thư mục sandbox.
    """
    ws_root = tmp_path / "repo_root"
    (ws_root / "src").mkdir(parents=True, exist_ok=True)
    (ws_root / "src" / "main.py").write_text("def run():\n    return 42\n", encoding="utf-8")

    # Tạo bẫy đệ quy .zenith/worktrees và node_modules trong workspace gốc
    nested_trap = ws_root / ".zenith" / "worktrees" / "wt_stale" / "sub"
    nested_trap.mkdir(parents=True, exist_ok=True)
    (nested_trap / "trap.py").write_text("TRAP = True\n", encoding="utf-8")
    (ws_root / "node_modules" / "pkg").mkdir(parents=True, exist_ok=True)
    (ws_root / "node_modules" / "pkg" / "bad.py").write_text("BAD = 1\n", encoding="utf-8")

    # Khởi tạo manager từ đường dẫn đang nằm sâu trong .zenith/worktrees
    mgr = WorktreeSandboxManager(base_workspace=str(nested_trap))
    assert mgr.base_workspace == ws_root.resolve()

    sb_path = mgr.create_isolated_sandbox(
        agent_id="coder_1",
        mission_id="mis_100",
        include_extensions=(".py",),
    )
    assert sb_path.exists()
    assert (sb_path / "src" / "main.py").exists()
    # Không được phép có .zenith hoặc node_modules bên trong sandbox
    assert not (sb_path / ".zenith").exists()
    assert not (sb_path / "node_modules").exists()

    active = mgr.list_active_sandboxes()
    assert any(item["sandbox_id"] == "mis_100_coder_1" and not item["has_nested_zenith"] for item in active)

    # Tạo thêm 1 sandbox thứ 2 và kiểm thử TTL prune
    sb_path_2 = mgr.create_isolated_sandbox(
        agent_id="tester_2",
        mission_id="mis_200",
        include_extensions=(".py",),
    )
    assert sb_path_2.exists()

    # Dọn dẹp theo mission_id cho mis_100
    evicted = mgr.evict_mission_sandboxes("mis_100")
    assert evicted == 1
    assert not sb_path.exists()

    # Dọn dẹp theo TTL (kể cả wt_stale không có .sandbox_meta.json và mis_200_tester_2)
    future_now = time.time() + 3600.0
    pruned = mgr.prune_expired_sandboxes(ttl_seconds=60.0, now=future_now)
    assert pruned >= 2
    assert not sb_path_2.exists()
    remaining = list(mgr.sandboxes_root.iterdir()) if mgr.sandboxes_root.exists() else []
    assert len(remaining) == 0


def test_state_pipeline_shares_canonical_workspace_filter_and_worktree_cleanup():
    """
    `services/ai-brain/state_pipeline.py` phải dùng chung `strip_worktree_nesting`
    và `EXCLUDED_WORKSPACE_DIRS` từ `core.utils.project_workspace`.
    """
    sp_path = Path(__file__).resolve().parents[1] / "services" / "ai-brain" / "state_pipeline.py"
    source = sp_path.read_text(encoding="utf-8")
    assert "strip_worktree_nesting" in source
    assert "EXCLUDED_WORKSPACE_DIRS" in source


def test_episodic_mutation_ledger_ttl_lru_and_mission_eviction(tmp_path: Path):
    """
    Đóng Điều kiện 1 Lượt 272 của OpenCode (`ledger-TTL`):
    - Giới hạn số lượng episode tối đa (`max_episodes`).
    - Hỗ trợ thu hồi theo nhiệm vụ (`evict_mission_episodes(mission_id)`).
    - Hỗ trợ thu hồi theo thời gian sống (`purge_expired_episodes(now=...)`).
    """
    pkg = tmp_path / "core_pkg"
    pkg.mkdir(parents=True, exist_ok=True)
    mod_a = pkg / "mod_a.py"
    mod_a.write_text("def f1():\n    return 1\n", encoding="utf-8")

    idx = RepoMapIndex(workspace_root=tmp_path, max_episodes=3, episode_ttl_seconds=120.0)
    idx.refresh(force=True)

    # Ghi 4 biến đổi liên tiếp (3 của mis_A, 1 của mis_B) -> LRU cap = 3 phải giữ đúng 3 bản ghi mới nhất
    for i in range(3):
        mod_a.write_text(f"def f1():\n    return {i}\n", encoding="utf-8")
        idx.notify_file_mutation(mod_a, action="write_to_file", task_id="mis_A", sha256=f"sha_a_{i}")

    mod_a.write_text("def f1():\n    return 99\n", encoding="utf-8")
    idx.notify_file_mutation(mod_a, action="write_to_file", task_id="mis_B", sha256="sha_b_0")

    ledger_all = idx.get_episodic_mutation_ledger()
    assert ledger_all["episode_count"] == 3
    assert ledger_all["max_episodes"] == 3
    assert ledger_all["episode_ttl_seconds"] == 120.0

    # Evict mission mis_A -> chỉ còn 1 episode của mis_B
    evicted_count = idx.evict_mission_episodes("mis_A")
    assert evicted_count == 2
    after_evict = idx.get_episodic_mutation_ledger()
    assert after_evict["episode_count"] == 1
    assert after_evict["episodes"][0]["task_id"] == "mis_B"

    # Purge theo TTL ở thời điểm tương lai (+300s > 120s) -> 0 episode
    purged_count = idx.purge_expired_episodes(now=time.time() + 300.0)
    assert purged_count == 1
    after_purge = idx.get_episodic_mutation_ledger()
    assert after_purge["episode_count"] == 0


def test_blast_radius_signature_change_detection_and_explicit_blindspots(tmp_path: Path):
    """
    Đóng Điều kiện 2 Lượt 272 của OpenCode (`ghi-ro-gioi-han-signature`):
    - Khi sửa hàm đang được module khác import theo kiểu đổi chữ ký / tăng số tham số bắt buộc
      (mà không xóa tên hàm), `blast_radius_impact` phải phát hiện `signature_changes`
      và đính kèm danh sách `blast_guard_blindspots` minh bạch.
    """
    pkg = tmp_path / "billing"
    pkg.mkdir(parents=True, exist_ok=True)
    (pkg / "__init__.py").write_text("", encoding="utf-8")

    provider = pkg / "pricing.py"
    consumer = pkg / "checkout.py"

    provider.write_text(
        "def calculate_total(amount: float, tax: float = 0.1) -> float:\n"
        "    return amount * (1.0 + tax)\n",
        encoding="utf-8",
    )
    consumer.write_text(
        "from billing.pricing import calculate_total\n\n"
        "def process_order(x: float) -> float:\n"
        "    return calculate_total(x)\n",
        encoding="utf-8",
    )

    idx = RepoMapIndex(workspace_root=tmp_path)
    idx.refresh(force=True)
    from core.utils.repo_map import _GLOBAL_INDEXES
    _GLOBAL_INDEXES[str(tmp_path.resolve()).lower()] = idx

    # Thay đổi chữ ký hàm `calculate_total`: tăng số tham số bắt buộc từ 1 lên 3
    res = asyncio.run(
        sce_logic.replace_file_content(
            path=str(provider),
            target="def calculate_total(amount: float, tax: float = 0.1) -> float:",
            replacement="def calculate_total(amount: float, currency: str, region: str, tax: float = 0.1) -> float:",
            task_id="slice_2_2_sig_test",
        )
    )
    assert res["status"] == "success"
    impact = res.get("blast_radius_impact")
    assert impact is not None

    sig_changes = impact.get("signature_changes", [])
    assert len(sig_changes) >= 1
    first_change = sig_changes[0]
    assert first_change["symbol"] == "calculate_total"
    assert first_change["old_required_args"] == 1
    assert first_change["new_required_args"] == 3
    assert "billing/checkout.py" in first_change["affected_importers"]

    blindspots = impact.get("blast_guard_blindspots", [])
    assert isinstance(blindspots, list) and len(blindspots) >= 3
    assert "[BLAST-RADIUS-WARNING]" in res["msg"]
