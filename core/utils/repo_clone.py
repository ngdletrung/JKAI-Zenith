"""
Đọc GitHub repo qua API (không clone) — nhanh, nhẹ, không cần git.
Fallback git clone khi cần phân tích sâu.
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
import time
from pathlib import Path
from typing import List, Optional, Tuple
from urllib.parse import urlparse

import httpx

from core.utils.project_workspace import (
    _GIT_HOST_RE,
    get_jkai_workspace_root,
    goal_forces_web_analysis_pipeline,
    normalize_workspace_rel,
    workspace_scope_exists,
)

logger = logging.getLogger("jkai.repo_clone")

_CLONE_OPT_OUT_RE = re.compile(
    r"\b(chỉ\s+readme|chi\s+readme|web-only|web only|không\s+clone|khong\s+clone|"
    r"no\s+clone|skip\s+clone|chỉ\s+scrape|chi\s+scrape)\b",
    re.IGNORECASE,
)

_GITHUB_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:github|gitlab|bitbucket)\.com/[\w\.\-]+/[\w\.\-]+",
    re.IGNORECASE,
)

_META_NAME = ".jkai-clone-meta.json"
_DEFAULT_TTL_DAYS = 7
_MAX_API_FILES = 50


def _env_clone_enabled() -> bool:
    raw = os.getenv("JKAI_AUTO_CLONE_GITHUB", "true").strip().lower()
    return raw in ("1", "true", "yes", "on")


def extract_git_remote_urls(text: str) -> List[str]:
    if not text:
        return []
    seen = set()
    out: List[str] = []
    for m in _GITHUB_URL_RE.finditer(text):
        u = m.group(0).rstrip("/.,;)")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def alias_from_url(url: str) -> str:
    p = urlparse(url)
    parts = [x for x in p.path.strip("/").split("/") if x]
    if len(parts) >= 2:
        owner, repo = parts[0], parts[1].replace(".git", "")
        return f"{owner}-{repo}-ref"
    return "external-ref"


def clone_rel_path(url: str) -> str:
    return normalize_workspace_rel(f"scratch/projects/{alias_from_url(url)}")


def goal_should_clone_external_repo(goal: str) -> bool:
    if not _env_clone_enabled():
        return False
    if not goal or not _GIT_HOST_RE.search(goal):
        return False
    if _CLONE_OPT_OUT_RE.search(goal):
        return False
    if goal_forces_web_analysis_pipeline(goal):
        return False
    return bool(extract_git_remote_urls(goal))


def _meta_path(root: Path) -> Path:
    return root / _META_NAME


def _clone_is_fresh(root: Path, ttl_days: int) -> bool:
    if not root.is_dir():
        return False
    meta = _meta_path(root)
    if meta.is_file():
        try:
            data = json.loads(meta.read_text(encoding="utf-8"))
            ts = float(data.get("fetched_at", 0))
            return (time.time() - ts) < ttl_days * 86400
        except Exception:
            pass
    return any(root.iterdir()) if root.is_dir() else False


# ─── GitHub API reader (primary path) ─────────────────────────────────


def _parse_github_url(url: str) -> Optional[Tuple[str, str, str]]:
    """Parse GitHub URL → (owner, repo, branch)."""
    p = urlparse(url)
    parts = [x for x in p.path.strip("/").split("/") if x]
    if len(parts) < 2:
        return None
    owner, repo = parts[0], parts[1].replace(".git", "")
    branch = "main"
    if len(parts) >= 4 and parts[2] in ("tree", "blob"):
        branch = parts[3]
    return owner, repo, branch


async def _fetch_github_tree(
    owner: str, repo: str, branch: str, client: httpx.AsyncClient
) -> Optional[list]:
    """Get recursive file tree via GitHub API."""
    url = f"https://api.github.com/repos/{owner}/{repo}/git/trees/{branch}?recursive=1"
    try:
        resp = await client.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.json().get("tree", [])
        logger.warning(f"GitHub API tree error {resp.status_code} for {owner}/{repo}")
    except Exception as e:
        logger.warning(f"GitHub API tree failed: {e}")
    return None


async def _fetch_github_file(
    owner: str, repo: str, path: str, branch: str, client: httpx.AsyncClient
) -> Optional[str]:
    """Get raw file content from GitHub."""
    url = f"https://raw.githubusercontent.com/{owner}/{repo}/{branch}/{path}"
    try:
        resp = await client.get(url, timeout=15)
        if resp.status_code == 200:
            return resp.text
    except Exception:
        pass
    return None


async def _fetch_and_cache_repo(
    url: str, dest: Path, ttl_days: int
) -> Tuple[bool, str]:
    """Fetch repo via GitHub API, cache text files locally."""
    parsed = _parse_github_url(url)
    if not parsed:
        return False, "cannot parse GitHub URL"
    owner, repo, branch = parsed

    dest.mkdir(parents=True, exist_ok=True)

    async with httpx.AsyncClient() as client:
        tree = await _fetch_github_tree(owner, repo, branch, client)
        if tree is None:
            return False, "cannot fetch repo tree from GitHub API"

        text_exts = {
            ".py", ".js", ".ts", ".jsx", ".tsx", ".go", ".rs", ".java", ".c", ".cpp",
            ".h", ".hpp", ".md", ".txt", ".json", ".yaml", ".yml", ".toml", ".cfg",
            ".ini", ".xml", ".html", ".css", ".scss", ".sql", ".sh", ".bash", ".ps1",
            ".bat", ".env", ".dockerfile", ".gitignore", ".conf", ".gradle", ".lock",
        }
        fetched = 0
        for entry in tree:
            if entry.get("type") != "blob":
                continue
            filepath: str = entry.get("path", "")
            ext = Path(filepath).suffix.lower()
            if ext not in text_exts:
                continue
            if fetched >= _MAX_API_FILES:
                break

            content = await _fetch_github_file(owner, repo, filepath, branch, client)
            if content is None:
                continue

            fp = dest / filepath
            fp.parent.mkdir(parents=True, exist_ok=True)
            fp.write_text(content, encoding="utf-8")
            fetched += 1

    if fetched == 0:
        return False, "no text files to cache"

    _meta_path(dest).write_text(
        json.dumps(
            {"url": url, "fetched_at": time.time(), "files": fetched, "method": "api"},
            indent=2,
        ),
        encoding="utf-8",
    )
    return True, f"cached {fetched} files from GitHub API"


# ─── Git clone fallback ────────────────────────────────────────────────


async def _run_git_clone(url: str, dest: Path) -> Tuple[bool, str]:
    dest.parent.mkdir(parents=True, exist_ok=True)
    if dest.exists():
        import shutil
        try:
            shutil.rmtree(dest)
        except Exception as e:
            return False, f"cannot clear old clone: {e}"

    cmd = ["git", "clone", "--depth", "1", "--single-branch", url, str(dest)]
    try:
        proc = await asyncio.create_subprocess_exec(
            *cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        stdout, stderr = await asyncio.wait_for(proc.communicate(), timeout=300)
        if proc.returncode != 0:
            err = (stderr or stdout or b"").decode("utf-8", errors="replace")[:500]
            return False, err or f"git exit {proc.returncode}"
        return True, ""
    except asyncio.TimeoutError:
        return False, "git clone timeout (300s)"
    except FileNotFoundError:
        return False, "git not found in PATH"
    except Exception as e:
        return False, str(e)


# ─── Main entry ────────────────────────────────────────────────────────


async def ensure_repo_cloned(
    url: str,
    ttl_days: Optional[int] = None,
) -> Tuple[Optional[str], str]:
    """Return (workspace_rel, message). workspace_rel None on failure.

    Primary: fetch via GitHub API (fast, no git).
    Fallback: shallow git clone.
    """
    rel = clone_rel_path(url)
    if not rel:
        return None, "invalid clone path"
    ws = get_jkai_workspace_root()
    dest = ws / rel.replace("/", os.sep)
    ttl = ttl_days if ttl_days is not None else int(
        os.getenv("JKAI_CLONE_TTL_DAYS", str(_DEFAULT_TTL_DAYS))
    )

    if _clone_is_fresh(dest, ttl):
        meta = _meta_path(dest)
        method = "cached"
        if meta.is_file():
            try:
                method = json.loads(meta.read_text()).get("method", "cached")
            except Exception:
                pass
        return rel, f"reuse {method} `{rel}`"

    # Path 1: GitHub API
    if "github.com" in url:
        ok, msg = await _fetch_and_cache_repo(url, dest, ttl)
        if ok:
            return rel, msg
        logger.warning(f"GitHub API failed, fallback git clone: {msg}")
    else:
        ok = False
        msg = "not a GitHub URL"

    # Path 2: git clone fallback
    ok2, err2 = await _run_git_clone(url, dest)
    if ok2:
        _meta_path(dest).write_text(
            json.dumps(
                {"url": url, "cloned_at": time.time(), "rel": rel, "method": "git"},
                indent=2,
            ),
            encoding="utf-8",
        )
        return rel, f"cloned `{rel}`"

    return None, f"{msg}; git fallback: {err2}"


async def enrich_goal_with_repo_clone(goal: str) -> Tuple[str, List[str], Optional[str]]:
    """
    Fetch first Git URL via API (fast path) or fallback clone.
    Returns (goal, clone_rels, error).
    """
    if not goal_should_clone_external_repo(goal):
        return goal, [], None

    urls = extract_git_remote_urls(goal)
    if not urls:
        return goal, [], None

    url = urls[0]
    rel, msg = await ensure_repo_cloned(url)
    if not rel or not workspace_scope_exists(rel):
        return goal, [], msg or "fetch failed"

    block = (
        f"\n\n[JKAI REPO-CLONE]\n"
        f"- Nguồn: {url}\n"
        f"- Workspace: `/workspace/{rel}` (TTL {os.getenv('JKAI_CLONE_TTL_DAYS', '7')} ngày)\n"
        f"- {msg}\n"
        f"- Đọc/list_dir CHỈ trong thư mục đã fetch; không quét toàn bộ JKAI.\n"
        f"- Không sửa file trừ khi Master yêu cầu sửa.\n"
    )
    return (goal or "").strip() + block, [rel], None
