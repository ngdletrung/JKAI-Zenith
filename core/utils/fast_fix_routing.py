"""
Fast path for single-file / small-scope fixes — bypass full Planner ceremony.
"""

from __future__ import annotations

import os
import re
from typing import Optional, Tuple

from core.utils.project_workspace import (
    _FIX_RE,
    _NO_FIX_RE,
    _PY_FILE_RE,
    detect_workspace_target,
    goal_forces_web_analysis_pipeline,
    workspace_scope_exists,
)

_SINGLE_FILE_RE = re.compile(
    r"\b(sửa|sua|fix|typo|đổi|doi)\b.*\b([\w\-]+(?:/[\w\-]+)*\.(?:py|md|json|yaml|yml|ts|tsx|js))\b",
    re.IGNORECASE,
)

_SMALL_SCOPE_RE = re.compile(
    r"\b(một file|mot file|single file|chỉ file|chi file|this file)\b",
    re.IGNORECASE,
)


def _env_fast_fix() -> bool:
    raw = os.getenv("JKAI_FAST_FIX_PATH", "true").strip().lower()
    return raw in ("1", "true", "yes", "on")


def detect_fast_fix_target(goal: str) -> Optional[str]:
    """Relative path to single file under workspace, if intent matches."""
    if not _env_fast_fix() or not goal or goal.strip().startswith("/"):
        return None
    if _NO_FIX_RE.search(goal) or goal_forces_web_analysis_pipeline(goal):
        return None
    if not _FIX_RE.search(goal) and not _SMALL_SCOPE_RE.search(goal):
        return None

    m = _SINGLE_FILE_RE.search(goal)
    if m:
        rel = m.group(2).replace("\\", "/")
        return rel

    pm = _PY_FILE_RE.search(goal)
    if pm and (_FIX_RE.search(goal) or _SMALL_SCOPE_RE.search(goal)):
        return pm.group(1).replace("\\", "/")

    scope = detect_workspace_target(goal)
    if scope and _FIX_RE.search(goal) and _SMALL_SCOPE_RE.search(goal):
        return None
    return None


def goal_should_use_fast_fix_path(goal: str) -> bool:
    target = detect_fast_fix_target(goal)
    if not target:
        return False
    try:
        from core.utils.project_workspace import get_jkai_workspace_root

        p = get_jkai_workspace_root() / target.replace("/", os.sep)
        return p.is_file()
    except Exception:
        return False


def fast_fix_directive(goal: str, file_rel: str) -> str:
    return (
        f"{goal.strip()}\n\n"
        f"[JKAI FAST-FIX]\n"
        f"- Phạm vi DUY NHẤT: `/workspace/{file_rel}`\n"
        f"- Sửa tối thiểu, chạy test/linter nếu có, không lập blueprint dài.\n"
        f"- Dùng view_file → replace_file_content → run_command.\n"
    )
