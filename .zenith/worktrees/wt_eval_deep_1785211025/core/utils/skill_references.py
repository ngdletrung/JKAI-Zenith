"""
Progressive disclosure: load references/*.md for resolved skills (cap tokens).
"""

from __future__ import annotations

import logging
import os
import re
from pathlib import Path
from typing import List, Optional, Tuple

from core.utils import path_manager

logger = logging.getLogger("jkai.skill_references")

_MAX_FILES = 3
_MAX_CHARS_PER_FILE = 4000
_MAX_TOTAL = 10000


def _intelligence_roots() -> List[Path]:
    roots: List[Path] = []
    for cand in (
        os.getenv("INTELLIGENCE_DIR", ""),
        "/intelligence",
        "/workspace/intelligence",
        str(path_manager.get_root() / "intelligence"),
        "intelligence",
    ):
        if cand:
            p = Path(cand)
            if p.is_dir() and p not in roots:
                roots.append(p)
    return roots


def _find_skill_dir(registry_id: str) -> Optional[Path]:
    rid = (registry_id or "").strip()
    if not rid:
        return None
    for root in _intelligence_roots():
        for skill_md in root.rglob("SKILL.md"):
            try:
                text = skill_md.read_text(encoding="utf-8", errors="replace")
            except Exception:
                continue
            if re.search(rf"\b{id_re_escape(rid)}\b", text, re.IGNORECASE):
                return skill_md.parent
            folder = skill_md.parent.name
            if folder.upper() == rid.upper() or rid.upper() in folder.upper():
                return skill_md.parent
    return None


def id_re_escape(s: str) -> str:
    return re.escape(s)


def _pick_reference_files(skill_dir: Path, goal: str) -> List[Path]:
    ref_dir = skill_dir / "references"
    if not ref_dir.is_dir():
        return []
    files = sorted(ref_dir.glob("*.md"))
    if not files:
        return []
    g_low = (goal or "").lower()
    scored: List[Tuple[int, Path]] = []
    for f in files:
        score = 0
        stem = f.stem.lower()
        if stem in g_low or stem.replace("_", " ") in g_low:
            score += 10
        if stem in ("checklist", "examples", "readme"):
            score += 1
        scored.append((score, f))
    scored.sort(key=lambda x: (-x[0], x[1].name))
    return [p for _, p in scored[:_MAX_FILES]]


def load_references_for_skill(registry_id: str, goal: str = "") -> str:
    skill_dir = _find_skill_dir(registry_id)
    if not skill_dir:
        return ""
    picked = _pick_reference_files(skill_dir, goal)
    if not picked:
        return ""
    parts: List[str] = []
    total = 0
    for f in picked:
        try:
            body = f.read_text(encoding="utf-8", errors="replace")[:_MAX_CHARS_PER_FILE]
        except Exception:
            continue
        chunk = f"\n### reference:{f.name}\n{body}\n"
        if total + len(chunk) > _MAX_TOTAL:
            break
        parts.append(chunk)
        total += len(chunk)
    if not parts:
        return ""
    return (
        f"<SKILL_REFERENCES skill_id=\"{registry_id}\">\n"
        + "".join(parts)
        + "</SKILL_REFERENCES>"
    )


def enrich_goal_with_skill_references(
    goal: str,
    registry_ids: Optional[List[str]] = None,
) -> Tuple[str, List[str]]:
    ids = list(registry_ids or [])
    if not ids:
        try:
            from core.utils.skill_deck_index import SkillDeckIndex

            entries = SkillDeckIndex.get().resolve_all_in_text(goal)
            ids = [e.registry_id for e in entries if e.registry_id]
        except Exception:
            ids = []
    loaded: List[str] = []
    blocks: List[str] = []
    for rid in ids[:5]:
        block = load_references_for_skill(rid, goal)
        if block:
            blocks.append(block)
            loaded.append(rid)
    if not blocks:
        return goal, []
    return f"{goal.strip()}\n\n" + "\n".join(blocks), loaded
