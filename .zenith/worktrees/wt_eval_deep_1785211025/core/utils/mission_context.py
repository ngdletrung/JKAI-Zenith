"""
Mission context pack — paths read, blueprint summary, team_pattern for follow-up turns.
"""

from __future__ import annotations

import json
import logging
import os
import time
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.utils.project_workspace import get_jkai_workspace_root

logger = logging.getLogger("jkai.mission_context")

_MAX_PATHS = 40
_MAX_SNIPPET = 2000
_MAX_BLOCK_CHARS = 12000


def _context_dir() -> Path:
    custom = os.getenv("JKAI_MISSION_CONTEXT_DIR", "").strip()
    if custom:
        return Path(custom)
    return get_jkai_workspace_root() / "scratch" / "mission_context"


def _pack_path(mission_id: str) -> Path:
    safe = "".join(c if c.isalnum() or c in "-_" else "_" for c in (mission_id or "default"))
    return _context_dir() / f"{safe}.json"


def load_context_pack(mission_id: str) -> Optional[Dict[str, Any]]:
    if not mission_id or mission_id in ("default", "null", "undefined"):
        return None
    path = _pack_path(mission_id)
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except Exception as e:
        logger.debug("[MISSION-CTX] load %s: %s", path, e)
        return None


def save_context_pack(
    mission_id: str,
    *,
    goal: str = "",
    paths_read: Optional[List[str]] = None,
    team_pattern: str = "",
    blueprint_summary: str = "",
    clone_rels: Optional[List[str]] = None,
    parent_mission_id: Optional[str] = None,
    extra: Optional[Dict[str, Any]] = None,
) -> None:
    if not mission_id:
        return
    _context_dir().mkdir(parents=True, exist_ok=True)
    existing = load_context_pack(mission_id) or {}
    paths = list(existing.get("paths_read") or [])
    for p in paths_read or []:
        if p and p not in paths:
            paths.append(p)
    paths = paths[-_MAX_PATHS:]
    pack = {
        "mission_id": mission_id,
        "parent_mission_id": parent_mission_id or existing.get("parent_mission_id"),
        "updated_at": time.time(),
        "goal_last": (goal or "")[:2000],
        "team_pattern": team_pattern or existing.get("team_pattern", ""),
        "blueprint_summary": (blueprint_summary or existing.get("blueprint_summary", ""))[:_MAX_SNIPPET],
        "paths_read": paths,
        "clone_rels": list({*(existing.get("clone_rels") or []), *(clone_rels or [])}),
        **(extra or {}),
    }
    try:
        _pack_path(mission_id).write_text(json.dumps(pack, indent=2), encoding="utf-8")
    except Exception as e:
        logger.warning("[MISSION-CTX] save failed: %s", e)


def format_context_block(pack: Optional[Dict[str, Any]]) -> str:
    if not pack:
        return ""
    lines = ["<MISSION_CONTEXT_PACK>"]
    if pack.get("parent_mission_id"):
        lines.append(f"parent_mission: {pack['parent_mission_id']}")
    if pack.get("team_pattern"):
        lines.append(f"team_pattern: {pack['team_pattern']}")
    if pack.get("clone_rels"):
        lines.append(f"clone_rels: {', '.join(pack['clone_rels'])}")
    if pack.get("paths_read"):
        lines.append("paths_read:")
        for p in pack["paths_read"][-20:]:
            lines.append(f"  - {p}")
    if pack.get("blueprint_summary"):
        lines.append(f"plan_summary: {pack['blueprint_summary'][:1500]}")
    if pack.get("goal_last"):
        lines.append(f"prior_goal: {pack['goal_last'][:800]}")
    if pack.get("last_deck_ids"):
        lines.append(f"last_deck_ids: {', '.join('#' + str(x) for x in pack['last_deck_ids'])}")
    lines.append("</MISSION_CONTEXT_PACK>")
    block = "\n".join(lines)
    return block[:_MAX_BLOCK_CHARS]


def apply_parent_context(goal: str, parent_mission_id: Optional[str]) -> str:
    if not parent_mission_id:
        return goal
    parent = load_context_pack(parent_mission_id)
    block = format_context_block(parent)
    if not block:
        return goal
    return f"{goal.strip()}\n\n{block}\n"
