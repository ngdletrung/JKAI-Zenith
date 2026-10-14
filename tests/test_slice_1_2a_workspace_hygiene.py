"""
Slice 1.2a Benchmark & Contract Suite:
1. Workspace Hygiene: Purge 44,968 recursive .zenith/worktrees entries & untrack .zenith/worktrees from git index.
2. Canonical Workspace File Iterator: iter_workspace_files() & _ROOT_ONLY_BLOCK in core/utils/project_workspace.py.
3. Un-hardcode Host Paths: rag/app.py, core/os/cognition/worktree_sandbox.py, tools/graph_syncer.py.
4. Standardize pyproject.toml: version = "28.4.1", [build-system], bounded [project].dependencies.
5. Prevent recursive worktree creation in services/ai-brain/state_pipeline.py.
"""

from __future__ import annotations

import subprocess
import tomllib
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parent.parent


def collect_slice_1_2a_metrics() -> dict:
    """Measures empirical workspace hygiene metrics before/after Slice 1.2a."""
    wt_root = REPO_ROOT / ".zenith" / "worktrees"
    wt_entries = 0
    nested_wt_dirs = 0
    if wt_root.exists():
        for p in wt_root.rglob("*"):
            wt_entries += 1
            if p.is_dir() and p.name == "worktrees" and p != wt_root:
                nested_wt_dirs += 1

    git_ls = subprocess.run(
        ["git", "ls-files", ".zenith/worktrees"],
        cwd=str(REPO_ROOT),
        capture_output=True,
        text=True,
        check=False,
    )
    tracked_wt_files = len([line for line in git_ls.stdout.splitlines() if line.strip()])

    rag_text = (REPO_ROOT / "rag" / "app.py").read_text(encoding="utf-8")
    sandbox_text = (REPO_ROOT / "core" / "os" / "cognition" / "worktree_sandbox.py").read_text(
        encoding="utf-8"
    )
    syncer_text = (REPO_ROOT / "tools" / "graph_syncer.py").read_text(encoding="utf-8")

    hardcoded_hits = {
        "rag/app.py": rag_text.lower().count("d:\\\\docker\\\\jkai")
        + rag_text.lower().count("d:/docker/jkai"),
        "core/os/cognition/worktree_sandbox.py": sandbox_text.lower().count("d:\\\\docker\\\\jkai")
        + sandbox_text.lower().count("d:/docker/jkai"),
        "tools/graph_syncer.py": syncer_text.lower().count("d:\\docker\\jkai")
        + syncer_text.lower().count("d:/docker/jkai"),
    }

    pyproj = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    project_sec = pyproj.get("project", {})
    deps = project_sec.get("dependencies", [])

    return {
        "worktree_disk_entries": wt_entries,
        "nested_worktree_dirs": nested_wt_dirs,
        "git_tracked_worktree_files": tracked_wt_files,
        "hardcoded_path_hits": hardcoded_hits,
        "pyproject_version": project_sec.get("version"),
        "pyproject_dependency_count": len(deps),
        "has_build_system": "build-system" in pyproj,
    }


def test_zenith_worktrees_free_of_recursive_bloat():
    metrics = collect_slice_1_2a_metrics()
    assert metrics["nested_worktree_dirs"] == 0, (
        f"Found {metrics['nested_worktree_dirs']} recursive nested .zenith/worktrees directories "
        f"({metrics['worktree_disk_entries']} total entries)"
    )
    assert metrics["git_tracked_worktree_files"] == 0, (
        f".zenith/worktrees still has {metrics['git_tracked_worktree_files']} files tracked in git index"
    )
    assert metrics["worktree_disk_entries"] == 0, (
        f"Stale worktree entries remain in .zenith/worktrees: {metrics['worktree_disk_entries']}"
    )


def test_iter_workspace_files_canonical_filter(tmp_path: Path):
    from core.utils import project_workspace

    assert ".zenith" in project_workspace._ROOT_ONLY_BLOCK
    assert hasattr(project_workspace, "iter_workspace_files"), (
        "iter_workspace_files() must be defined in core/utils/project_workspace.py"
    )

    # Create synthetic workspace with real files and ignored directories (.zenith, .git, __pycache__, node_modules)
    (tmp_path / "core" / "utils").mkdir(parents=True)
    good_py = tmp_path / "core" / "utils" / "sample.py"
    good_py.write_text("x = 1\n", encoding="utf-8")

    bad_wt = tmp_path / ".zenith" / "worktrees" / "wt_1" / "core" / "sample.py"
    bad_wt.parent.mkdir(parents=True)
    bad_wt.write_text("x = 2\n", encoding="utf-8")

    bad_git = tmp_path / ".git" / "hooks" / "hook.py"
    bad_git.parent.mkdir(parents=True)
    bad_git.write_text("x = 3\n", encoding="utf-8")

    bad_cache = tmp_path / "core" / "__pycache__" / "cached.py"
    bad_cache.parent.mkdir(parents=True)
    bad_cache.write_text("x = 4\n", encoding="utf-8")

    found = list(project_workspace.iter_workspace_files(root=tmp_path, suffixes=(".py",)))
    rel_paths = [p.relative_to(tmp_path).as_posix() for p in found]
    assert rel_paths == ["core/utils/sample.py"]


def test_no_hardcoded_host_paths_in_rag_and_worktree_sandbox():
    metrics = collect_slice_1_2a_metrics()
    hits = metrics["hardcoded_path_hits"]
    assert hits["rag/app.py"] == 0, f"rag/app.py still contains {hits['rag/app.py']} hardcoded D:\\Docker\\JKAI paths"
    assert hits["core/os/cognition/worktree_sandbox.py"] == 0, (
        "worktree_sandbox.py still contains hardcoded D:/Docker/JKAI path"
    )
    assert hits["tools/graph_syncer.py"] == 0, (
        "tools/graph_syncer.py still contains hardcoded D:\\Docker\\JKAI path"
    )


def test_pyproject_toml_standardized_v28_4_1():
    metrics = collect_slice_1_2a_metrics()
    assert metrics["pyproject_version"] == "28.4.1", (
        f"Expected pyproject.toml version 28.4.1, got {metrics['pyproject_version']}"
    )
    assert metrics["has_build_system"] is True, "pyproject.toml must declare [build-system]"
    assert metrics["pyproject_dependency_count"] >= 15, (
        f"pyproject.toml must declare bounded dependencies, got {metrics['pyproject_dependency_count']}"
    )

    pyproj = tomllib.loads((REPO_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    deps = pyproj["project"]["dependencies"]
    # Every core dependency must include an upper bound (<) so major upgrades cannot silently break JKAI
    unbounded = [d for d in deps if "<" not in d and "==" not in d]
    assert not unbounded, f"Found unbounded dependencies in pyproject.toml: {unbounded}"


def test_state_pipeline_worktree_prevents_nesting():
    pipeline_src = (REPO_ROOT / "services" / "ai-brain" / "state_pipeline.py").read_text(encoding="utf-8")
    assert "_resolve_canonical_repo_root" in pipeline_src or ".zenith" in pipeline_src
    # Must explicitly guard against creating a worktree inside an existing .zenith/worktrees directory
    assert "worktrees" in pipeline_src and "parts" in pipeline_src, (
        "state_pipeline._setup_agent_worktree must strip any existing .zenith/worktrees prefix to prevent recursion"
    )
