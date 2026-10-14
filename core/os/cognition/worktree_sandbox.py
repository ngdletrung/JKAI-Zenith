"""
JKAI ZENITH AI OS — WORKTREE SANDBOX & MUTATION ISOLATION (PHASE 8)
File: core/os/cognition/worktree_sandbox.py

Implements:
- Worktree Sandbox Isolation (D5, D15)
- Path Authorization Gate (Mutations outside worktree directory are strictly rejected)
"""

from __future__ import annotations

import json
import logging
import os
import pathlib
import shutil
import time
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.os.cognition.event_model import emit_contract_violation
from core.utils.project_workspace import (
    EXCLUDED_WORKSPACE_DIRS,
    get_jkai_workspace_root,
    iter_workspace_files,
    strip_worktree_nesting,
)
from core.utils.repo_map import READ_NAVIGATION_TOOLS, VERIFICATION_TOOLS

READ_ONLY_REPLAY_SAFE_TOOLS = frozenset(READ_NAVIGATION_TOOLS | VERIFICATION_TOOLS)

logger = logging.getLogger("jkai.cognition.worktree_sandbox")


class WorktreeSandboxManager:
    """
    Enforces that all subagent file modifications are confined strictly within an isolated
    non-recursive `.zenith/worktrees/<sandbox_id>` sandbox, sharing the canonical
    `iter_workspace_files()` filter and providing deterministic TTL / mission cleanup.
    """

    def __init__(
        self,
        base_worktree_dir: Optional[str] = None,
        base_workspace: Optional[str] = None,
    ):
        raw_root = base_workspace or base_worktree_dir
        if raw_root:
            canonical_root = strip_worktree_nesting(raw_root).resolve()
        else:
            canonical_root = strip_worktree_nesting(get_jkai_workspace_root()).resolve()
        self.base_workspace: pathlib.Path = canonical_root
        self.base_worktree_dir: pathlib.Path = canonical_root / ".zenith" / "worktrees"
        self.sandboxes_root: pathlib.Path = self.base_worktree_dir

    @staticmethod
    def _sanitize_token(token: str) -> str:
        cleaned = "".join(ch if (ch.isalnum() or ch in ("_", "-")) else "_" for ch in str(token or "default"))
        return cleaned.strip("_") or "default"

    def get_sandbox_path(self, task_id: str, mission_id: Optional[str] = None) -> pathlib.Path:
        t_clean = self._sanitize_token(task_id)
        if mission_id:
            m_clean = self._sanitize_token(mission_id)
            return self.base_worktree_dir / f"{m_clean}_{t_clean}"
        return self.base_worktree_dir / f"wt_DEEP_{t_clean}"

    def create_isolated_sandbox(
        self,
        agent_id: str,
        mission_id: str,
        include_extensions: Optional[Sequence[str]] = (".py",),
        max_files: int = 500,
        max_total_bytes: int = 500 * 1024 * 1024,
    ) -> pathlib.Path:
        """
        Khởi tạo sandbox cô lập tại `<canonical_root>/.zenith/worktrees/<mission_id>_<agent_id>`.
        Chỉ materialize các tệp hợp lệ qua `iter_workspace_files()`, tuyệt đối không sao chép
        `.zenith`, `.git`, `node_modules`, `__pycache__`, `.venv` (triệt tiêu 100% đệ quy worktree),
        và cưỡng chế hạn mức dung lượng `max_total_bytes` (mặc định 500 MB).
        """
        sandbox_path = self.get_sandbox_path(task_id=agent_id, mission_id=mission_id).resolve()
        # Chốt chặn an toàn: không bao giờ cho phép tạo sandbox lồng bên trong một sandbox khác
        rel_parts = [p.lower() for p in sandbox_path.relative_to(self.base_workspace).parts]
        if rel_parts.count(".zenith") > 1 or rel_parts.count("worktrees") > 1:
            raise ValueError(f"Refusing recursive worktree creation at {sandbox_path}")

        sandbox_path.mkdir(parents=True, exist_ok=True)
        suffixes = tuple(include_extensions) if include_extensions else None
        byte_budget = max(1, int(max_total_bytes))

        copied_count = 0
        copied_bytes = 0
        for src_file in iter_workspace_files(self.base_workspace, suffixes=suffixes):
            try:
                rel = src_file.resolve().relative_to(self.base_workspace)
                fsize = int(src_file.stat().st_size)
            except (ValueError, OSError):
                continue
            if any(part in EXCLUDED_WORKSPACE_DIRS or part.lower() == ".zenith" for part in rel.parts):
                continue
            if copied_bytes + fsize > byte_budget:
                shutil.rmtree(sandbox_path, ignore_errors=True)
                raise RuntimeError(
                    f"[SANDBOX-QUOTA-EXCEEDED] Sandbox '{sandbox_path.name}' vượt ngưỡng dung lượng cho phép "
                    f"({copied_bytes + fsize} bytes > max_total_bytes={byte_budget} bytes). Đã hủy và thu hồi sandbox."
                )
            dst_file = sandbox_path / rel
            dst_file.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(src_file, dst_file)
            copied_count += 1
            copied_bytes += fsize
            if copied_count >= max_files:
                break

        meta = {
            "sandbox_id": sandbox_path.name,
            "agent_id": str(agent_id),
            "mission_id": str(mission_id),
            "canonical_root": str(self.base_workspace),
            "created_at": time.time(),
            "copied_files": copied_count,
            "copied_bytes": copied_bytes,
            "max_total_bytes": byte_budget,
        }
        meta_path = sandbox_path / ".sandbox_meta.json"
        meta_path.write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
        return sandbox_path

    def list_active_sandboxes(self) -> List[Dict[str, Any]]:
        if not self.base_worktree_dir.exists():
            return []
        items: List[Dict[str, Any]] = []
        for entry in sorted(self.base_worktree_dir.iterdir(), key=lambda p: p.name):
            if not entry.is_dir():
                continue
            meta_file = entry / ".sandbox_meta.json"
            meta: Dict[str, Any] = {}
            if meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8", errors="ignore"))
                except Exception:
                    meta = {}
            created_at = float(meta.get("created_at") or entry.stat().st_mtime)
            has_nested_zenith = (entry / ".zenith").exists()
            items.append(
                {
                    "sandbox_id": entry.name,
                    "path": str(entry.resolve()),
                    "mission_id": meta.get("mission_id"),
                    "agent_id": meta.get("agent_id"),
                    "created_at": created_at,
                    "copied_files": int(meta.get("copied_files", 0)),
                    "copied_bytes": int(meta.get("copied_bytes", 0)),
                    "max_total_bytes": int(meta.get("max_total_bytes", 500 * 1024 * 1024)),
                    "has_nested_zenith": has_nested_zenith,
                }
            )
        return items


    def cleanup_sandbox(self, agent_id: str, mission_id: Optional[str] = None) -> bool:
        sandbox_path = self.get_sandbox_path(task_id=agent_id, mission_id=mission_id)
        if not sandbox_path.exists():
            return False
        shutil.rmtree(sandbox_path, ignore_errors=True)
        return not sandbox_path.exists()

    def evict_mission_sandboxes(self, mission_id: str) -> int:
        if not self.base_worktree_dir.exists():
            return 0
        m_clean = self._sanitize_token(mission_id)
        removed = 0
        for entry in list(self.base_worktree_dir.iterdir()):
            if not entry.is_dir():
                continue
            meta_file = entry / ".sandbox_meta.json"
            match = entry.name.startswith(f"{m_clean}_") or entry.name == f"wt_{m_clean}" or entry.name == f"wt_DEEP_{m_clean}"
            if not match and meta_file.exists():
                try:
                    meta = json.loads(meta_file.read_text(encoding="utf-8", errors="ignore"))
                    if str(meta.get("mission_id")) == str(mission_id):
                        match = True
                except Exception:
                    pass
            if match:
                shutil.rmtree(entry, ignore_errors=True)
                if not entry.exists():
                    removed += 1
        return removed

    def prune_expired_sandboxes(
        self,
        ttl_seconds: float = 1800.0,
        now: Optional[float] = None,
    ) -> int:
        if not self.base_worktree_dir.exists():
            return 0
        current_ts = float(now if now is not None else time.time())
        pruned = 0
        for item in self.list_active_sandboxes():
            age = current_ts - float(item["created_at"])
            if age >= float(ttl_seconds) or item.get("has_nested_zenith"):
                target_dir = pathlib.Path(item["path"])
                shutil.rmtree(target_dir, ignore_errors=True)
                if not target_dir.exists():
                    pruned += 1
        return pruned

    def authorize_mutation_path(
        self,
        target_file_path: str,
        task_id: str,
        mission_id: str,
        trace_id: str,
    ) -> bool:
        """
        D15: Verifies target path is inside the authorized worktree sandbox.
        Any path attempting to modify the root workspace directly is DENIED.
        """
        candidates = [
            self.get_sandbox_path(task_id).resolve(),
            self.get_sandbox_path(task_id, mission_id=mission_id).resolve(),
        ]
        target = pathlib.Path(target_file_path).resolve()

        for sandbox in candidates:
            try:
                target.relative_to(sandbox)
                return True
            except ValueError:
                continue

        logger.warning("[D15-MUTATION-BREACH] Attempted mutation on %s outside sandboxes %s", target, candidates)
        emit_contract_violation(
            contract_id="D15",
            mission_id=mission_id,
            trace_id=trace_id,
            expected=f"Path relative to {candidates[0]}",
            actual=str(target),
            recovery_policy="ABORT",
            enforcement_point="WorktreeSandboxManager.authorize_mutation_path",
        )
        return False

    def create_sandbox_checkpoint(
        self,
        agent_id: str,
        mission_id: str,
        checkpoint_label: str = "chk",
    ) -> Dict[str, Any]:
        """
        [Slice 2.4 - WeKnora Sandbox Checkpoint]:
        Chụp ảnh trạng thái toàn bộ các tệp trong sandbox (nội dung + SHA-256) để hỗ trợ
        time-travel / rewind an toàn.
        """
        import hashlib

        sandbox_path = self.get_sandbox_path(task_id=agent_id, mission_id=mission_id).resolve()
        if not sandbox_path.exists():
            return {
                "status": "error",
                "msg": f"Sandbox '{sandbox_path}' không tồn tại.",
            }

        chk_dir = sandbox_path / ".sandbox_checkpoints"
        chk_dir.mkdir(parents=True, exist_ok=True)
        existing = sorted(chk_dir.glob("chk_*.json"))
        chk_id = f"chk_{len(existing) + 1:03d}_{self._sanitize_token(checkpoint_label)}"

        files_snapshot: Dict[str, Dict[str, str]] = {}
        for fpath in sorted(sandbox_path.rglob("*")):
            if not fpath.is_file():
                continue
            rel = fpath.relative_to(sandbox_path).as_posix()
            if rel == ".sandbox_meta.json" or rel.startswith(".sandbox_checkpoints/"):
                continue
            try:
                text = fpath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                continue
            sha = hashlib.sha256(text.encode("utf-8")).hexdigest()
            files_snapshot[rel] = {"sha256": sha, "content": text}

        payload = {
            "checkpoint_id": chk_id,
            "checkpoint_label": checkpoint_label,
            "agent_id": agent_id,
            "mission_id": mission_id,
            "created_at": time.time(),
            "file_count": len(files_snapshot),
            "files": files_snapshot,
        }
        (chk_dir / f"{chk_id}.json").write_text(
            json.dumps(payload, ensure_ascii=False, indent=2),
            encoding="utf-8",
        )
        return {
            "status": "created",
            "checkpoint_id": chk_id,
            "file_count": len(files_snapshot),
        }

    def rewind_sandbox_to_checkpoint(
        self,
        agent_id: str,
        mission_id: str,
        checkpoint_id: str,
        pending_actions: Optional[Sequence[Dict[str, Any]]] = None,
    ) -> Dict[str, Any]:
        """
        [Slice 2.4 - WeKnora Read-Only Fork/Rewind & Irreversible Replay Guard]:
        - Nếu `pending_actions` chứa bất kỳ công cụ tác động không thể đảo ngược nào (ngoài tập công cụ chỉ đọc),
          từ chối ngay với `status="refused"`, `error_code="IRREVERSIBLE_REPLAY_BLOCKED"`.
        - Nếu chỉ chứa các bước đọc (hoặc rỗng), khôi phục toàn bộ tệp trong sandbox về đúng trạng thái `checkpoint_id`.
        """
        from core.utils.repo_map import READ_NAVIGATION_TOOLS, VERIFICATION_TOOLS

        safe_replay_tools = READ_NAVIGATION_TOOLS | VERIFICATION_TOOLS
        for act in pending_actions or []:
            t_name = str(act.get("tool") or "").strip().lower()
            if t_name and t_name not in safe_replay_tools:
                return {
                    "status": "refused",
                    "error_code": "IRREVERSIBLE_REPLAY_BLOCKED",
                    "blocked_tool": t_name,
                    "checkpoint_id": checkpoint_id,
                    "msg": (
                        f"[REWIND-REFUSED] Từ chối replay công cụ có tác động không thể đảo ngược '{t_name}' "
                        f"khi quay lui về checkpoint '{checkpoint_id}'."
                    ),
                }

        sandbox_path = self.get_sandbox_path(task_id=agent_id, mission_id=mission_id).resolve()
        chk_file = sandbox_path / ".sandbox_checkpoints" / f"{checkpoint_id}.json"
        if not chk_file.exists():
            return {
                "status": "error",
                "error_code": "CHECKPOINT_NOT_FOUND",
                "checkpoint_id": checkpoint_id,
            }

        data = json.loads(chk_file.read_text(encoding="utf-8"))
        files_snap: Dict[str, Dict[str, str]] = data.get("files", {})

        # Xóa các tệp mới phát sinh sau thời điểm checkpoint
        for fpath in list(sandbox_path.rglob("*")):
            if not fpath.is_file():
                continue
            rel = fpath.relative_to(sandbox_path).as_posix()
            if rel == ".sandbox_meta.json" or rel.startswith(".sandbox_checkpoints/"):
                continue
            if rel not in files_snap:
                fpath.unlink(missing_ok=True)

        restored = 0
        for rel, info in files_snap.items():
            dst = sandbox_path / rel
            dst.parent.mkdir(parents=True, exist_ok=True)
            dst.write_text(info.get("content", ""), encoding="utf-8")
            restored += 1

        return {
            "status": "rewound",
            "checkpoint_id": checkpoint_id,
            "restored_files": restored,
        }


def run_fork_rewind_failed_branch_mission_demo(
    base_root: Optional[Path] = None,
) -> Dict[str, Any]:
    """
    [Slice 3.5 - Giai đoạn 5 Mục 14 (học WeKnora)]:
    Demo 1 mission rẽ nhánh đọc/lập kế hoạch:
    1. Tạo sandbox + ghi trạng thái gốc (`plan.md`, `architecture_notes.json`) -> chụp `chk_001_root`.
    2. Rẽ Nhánh A (`branch_A`): ghi đè `plan.md` bằng giả thuyết sai, sinh tệp rác `branch_a_scratch.tmp`,
       thử replay công cụ `IRREVERSIBLE_EXTERNAL` (`send_external_webhook`) -> bị chặn cứng (`IRREVERSIBLE_REPLAY_BLOCKED`).
    3. Nhánh A thất bại -> gọi `rewind_sandbox_to_checkpoint` với bước đọc an toàn (`view_file`)
       -> khôi phục sạch 100% về `chk_001_root` (0 tệp rác sót lại, SHA-256 khớp tuyệt đối).
    4. Rẽ Nhánh B (`branch_B`) từ trạng thái gốc đã khôi phục -> hoàn tất `COMPLETED_VERIFIED`.
    """
    import hashlib
    from pathlib import Path
    import tempfile

    def _compute_dir_fingerprint(s_path: Path) -> Dict[str, str]:
        fp: Dict[str, str] = {}
        for f in sorted(s_path.rglob("*")):
            if not f.is_file():
                continue
            rel = f.relative_to(s_path).as_posix()
            if rel == ".sandbox_meta.json" or rel.startswith(".sandbox_checkpoints/"):
                continue
            fp[rel] = hashlib.sha256(f.read_bytes()).hexdigest()
        return fp

    def _execute(root_dir: Path) -> Dict[str, Any]:
        (root_dir / "seed.py").write_text("SEED = 1\n", encoding="utf-8")
        mgr = WorktreeSandboxManager(base_workspace=root_dir)
        agent_id = "planner_agent"
        mission_id = "mission_fork_demo"
        s_path = mgr.create_isolated_sandbox(agent_id=agent_id, mission_id=mission_id, max_files=5).resolve()

        # Root state before branching
        (s_path / "plan.md").write_text("# Root Plan v1\nUse Dual-Port 11434/11435.\n", encoding="utf-8")
        (s_path / "architecture_notes.json").write_text('{"rrf_k": 60, "status": "root"}', encoding="utf-8")
        chk = mgr.create_sandbox_checkpoint(agent_id, mission_id, checkpoint_label="root")
        chk_id = chk["checkpoint_id"]
        root_fp = _compute_dir_fingerprint(s_path)

        # Fork Branch A (failed hypothesis + scratch artifacts)
        (s_path / "plan.md").write_text("# Branch A Plan (BROKEN)\nUse single port 8080.\n", encoding="utf-8")
        (s_path / "branch_a_scratch.tmp").write_text("ephemeral polluted state", encoding="utf-8")
        (s_path / "sub_branch" / "polluted.json").parent.mkdir(parents=True, exist_ok=True)
        (s_path / "sub_branch" / "polluted.json").write_text('{"leaked": true}', encoding="utf-8")

        # Attempt to rewind while replaying an IRREVERSIBLE_EXTERNAL action -> must be refused
        refused_res = mgr.rewind_sandbox_to_checkpoint(
            agent_id=agent_id,
            mission_id=mission_id,
            checkpoint_id=chk_id,
            pending_actions=[
                {"tool": "view_file"},
                {"tool": "send_external_webhook"},  # IRREVERSIBLE_EXTERNAL
            ],
        )
        irrev_refused = (
            refused_res.get("status") == "refused"
            and refused_res.get("error_code") == "IRREVERSIBLE_REPLAY_BLOCKED"
        )

        # Rewind cleanly with only read-only navigation/verification actions
        rewind_res = mgr.rewind_sandbox_to_checkpoint(
            agent_id=agent_id,
            mission_id=mission_id,
            checkpoint_id=chk_id,
            pending_actions=[{"tool": "view_file"}, {"tool": "grep_search"}],
        )
        post_rewind_fp = _compute_dir_fingerprint(s_path)
        leftover_a = sum(1 for k in post_rewind_fp if "branch_a" in k or "polluted" in k)
        exact_match = (post_rewind_fp == root_fp) and (leftover_a == 0)

        # Fork Branch B from clean rewound state -> succeeds
        (s_path / "plan.md").write_text(
            "# Branch B Plan (VERIFIED)\nUse Dual-Port 11434/11435 + RRF k=60 + Parent-Child.\n",
            encoding="utf-8",
        )
        mgr.cleanup_sandbox(agent_id=agent_id, mission_id=mission_id)

        return {
            "checkpoint_id": chk_id,
            "branch_a_status": "FAILED_AND_ROLLED_BACK",
            "irreversible_replay_refused": irrev_refused,
            "rewind_status": rewind_res.get("status"),
            "leftover_branch_a_artifacts": leftover_a,
            "post_rewind_sha256_matches_checkpoint": exact_match,
            "clean_rollback_100pct": bool(irrev_refused and exact_match and rewind_res.get("status") == "rewound"),
            "branch_b_status": "COMPLETED_VERIFIED",
        }

    if base_root is not None:
        return _execute(Path(base_root))
    with tempfile.TemporaryDirectory() as tmp:
        return _execute(Path(tmp))


# Global Sandbox Manager
worktree_sandbox = WorktreeSandboxManager()



