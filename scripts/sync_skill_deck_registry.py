#!/usr/bin/env python3
"""
Sync Command Deck numbers from MAP_SKILLS.md into registry_Map_skills.json (deck_number field).

Usage (from repo root):
  python scripts/sync_skill_deck_registry.py
  python scripts/sync_skill_deck_registry.py --dry-run
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))
if str(ROOT / "core") not in sys.path:
    sys.path.insert(0, str(ROOT / "core"))

from core.utils.skill_deck_index import SkillDeckIndex  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Sync MAP deck numbers into skill registry")
    parser.add_argument("--dry-run", action="store_true", help="Report only; do not write registry")
    args = parser.parse_args()

    stats = SkillDeckIndex.get().sync_registry_deck_numbers(write=not args.dry_run)
    print("[SYNC-SKILL-DECK]", stats)
    if stats.get("error"):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
