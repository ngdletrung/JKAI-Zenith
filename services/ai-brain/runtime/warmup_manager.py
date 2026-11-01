# -*- coding: utf-8 -*-
"""Single owner for warming the shared embedding cache (ai-brain)."""

import os

from core.config import settings

HOT_FILES = [
    "identity/ZENITH_IDENTITY.md",
    "rules_software.md",
    "rule_hardware.md",
    "SKILL_PROTOCOL.md",
    "registry_Map_skills.json",
]


def hot_file_paths():
    return [os.path.join(settings.INTELLIGENCE_DIR, name) for name in HOT_FILES]


def warm_hot_embeddings(paths=None, limit: int = 2000) -> int:
    """Embed each hot file through the shared embedder so the first real query is a cache hit."""
    from core.utils.embed import embed

    warmed = 0
    for path in (paths if paths is not None else hot_file_paths()):
        if not os.path.exists(path):
            continue
        with open(path, "r", encoding="utf-8") as f:
            content = f.read()[:limit]
        if content and embed(content):
            warmed += 1
    return warmed


def warmup_report() -> dict:
    """Warm the hot files and report what actually happened."""
    paths = hot_file_paths()
    warmed = warm_hot_embeddings(paths)
    return {
        "status": "ok",
        "warmed": warmed,
        "total": len(paths),
        "missing": [p for p in paths if not os.path.exists(p)],
    }
