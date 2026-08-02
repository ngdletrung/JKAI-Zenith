"""
Tests for Command Deck index (MAP_SKILLS.md ↔ registry_Map_skills.json).

Run from repo root:
  python core/utils/test_skill_deck_index.py
"""

from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

os.environ.setdefault("INTELLIGENCE_DIR", str(ROOT / "intelligence"))

from core.utils.skill_deck_index import SkillDeckIndex  # noqa: E402


def _deck() -> SkillDeckIndex:
    inst = SkillDeckIndex()
    SkillDeckIndex._instance = inst
    inst.ensure_loaded(force=True)
    return inst


def test_map_index_non_empty():
    deck = _deck()
    assert len(deck._by_deck) >= 50, f"expected MAP entries, got {len(deck._by_deck)}"


def test_resolve_1002():
    deck = _deck()
    entry = deck.resolve("1002")
    assert entry is not None, "#1002 should resolve"
    assert entry.registry_id == "SKILL_AGENTIC_DEBATE", entry.registry_id


def test_resolve_7001():
    deck = _deck()
    entry = deck.resolve("7001")
    assert entry is not None
    assert entry.registry_id == "SKILL_HUEIC_TAO_SKILL_DE_XUAT_THEO_FORM"


def test_parse_refs_and_inspect():
    deck = _deck()
    goal = "skill #1002 có gì hay không?"
    refs = deck.parse_refs(goal)
    assert "1002" in refs
    assert deck.is_inspect_intent(goal)


def test_lookup_or_explain_unknown_deck():
    deck = _deck()
    _, err = deck.lookup_or_explain("skill #99999 có gì")
    assert "99999" in err or "Không tìm thấy" in err


def test_registry_deck_number_fallback():
    deck = _deck()
    rid = deck.resolve_registry_by_deck("1002")
    assert rid == "SKILL_AGENTIC_DEBATE"


def test_sync_dry_run():
    deck = _deck()
    stats = deck.sync_registry_deck_numbers(write=False)
    assert stats.get("deck_entries", 0) > 0
    assert "error" not in stats


def test_enrich_goal_block():
    deck = _deck()
    enriched, entries = deck.enrich_goal("dùng skill #7001")
    assert entries and entries[0].registry_id
    assert "ZENITH_SKILL_DECK_RESOLVE" in enriched


def run_all() -> None:
    tests = [
        test_map_index_non_empty,
        test_resolve_1002,
        test_resolve_7001,
        test_parse_refs_and_inspect,
        test_lookup_or_explain_unknown_deck,
        test_registry_deck_number_fallback,
        test_sync_dry_run,
        test_enrich_goal_block,
    ]
    failed = 0
    for fn in tests:
        try:
            fn()
            print(f"OK  {fn.__name__}")
        except AssertionError as e:
            failed += 1
            print(f"FAIL {fn.__name__}: {e}")
        except Exception as e:
            failed += 1
            print(f"ERR  {fn.__name__}: {e}")
    if failed:
        raise SystemExit(f"{failed} test(s) failed")
    print(f"\nAll {len(tests)} tests passed.")


if __name__ == "__main__":
    run_all()
