#!/usr/bin/env python3
"""
Build intelligence/deck_registry_overrides.json for MAP rows without SKILL_* in Skill Con.

Run: python scripts/repair_map_deck_links.py
"""

from __future__ import annotations

import json
import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
os.environ.setdefault("INTELLIGENCE_DIR", str(ROOT / "intelligence"))

import re

from core.utils.skill_deck_index import SkillDeckIndex, _MANUAL_DECK_OVERRIDES, _fold_text  # noqa: E402

OUT = ROOT / "intelligence" / "deck_registry_overrides.json"


def _token_match_registry(deck: SkillDeckIndex, title: str, keywords: str) -> tuple[str | None, float]:
    blob_in = _fold_text(f"{title} {keywords}")
    tokens = [t for t in re.findall(r"[a-z0-9_]{5,}", blob_in) if t not in ("skill", "zenith", "tinh", "nang")]
    if not tokens:
        return None, 0.0
    best_id = None
    best_score = 0.0
    for sid, data in deck._registry.items():
        blob = _fold_text(f"{sid} {data.get('name_vn', '')} {' '.join(data.get('aliases_vn') or [])}")
        hit = sum(1 for t in tokens if t in blob)
        score = hit / max(len(tokens), 1)
        if "reflex" in blob_in and "reflex" in blob:
            score += 0.35
        if "hueic" in blob_in and "hueic" in blob:
            score += 0.35
        if score > best_score:
            best_score = score
            best_id = sid
    if best_score >= 0.35:
        return best_id, min(0.9, best_score)
    return None, 0.0


def main() -> int:
    deck = SkillDeckIndex()
    SkillDeckIndex._instance = deck
    deck.ensure_loaded(force=True)

    overrides: dict = dict(_MANUAL_DECK_OVERRIDES)
    added = 0

    for entry in deck._by_deck.values():
        if entry.registry_id:
            if entry.deck_id not in overrides:
                overrides[entry.deck_id] = entry.registry_id
            continue
        rid, conf = deck._fuzzy_registry_match(entry.title, entry.keywords)
        if not rid or conf < 0.2:
            rid, conf = _token_match_registry(deck, entry.title, entry.keywords)
        if rid and conf >= 0.2:
            overrides[entry.deck_id] = rid
            added += 1
            print(f"  #{entry.deck_id} -> {rid} (conf={conf:.2f})")

    OUT.write_text(json.dumps(overrides, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    still = sum(1 for e in deck._by_deck.values() if e.deck_id not in overrides)
    print(f"[REPAIR] wrote {len(overrides)} overrides ({added} new fuzzy), unmapped left: {still}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
