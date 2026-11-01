# -*- coding: utf-8 -*-
"""
C15 — Throttle the two dashboard proxies (fail-first).

Master deliberately opened the "red zone" (`verify_nuclear_key()` returns True),
so this item does NOT add auth. What is still missing is protection against
double-fire: a double-clicked Warmup button fans out into concurrent embedding
storms, and repeated Import clicks start duplicate pipelines.

Contract:
1. Mission Control exposes a cross-worker cooldown helper backed by Redis SET NX.
2. Both `warmup` and `import_intel` actions consult it before calling ai-brain.
3. ai-brain serialises /warmup with an asyncio lock instead of running in parallel.
"""

import importlib
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MC_BACKEND = ROOT / "services" / "mission-control" / "backend"
MC_MAIN = MC_BACKEND / "main.py"
AI_BRAIN_MAIN = ROOT / "services" / "ai-brain" / "main.py"


def load_mc_warmup():
    path = str(MC_BACKEND)
    sys.path.insert(0, path)
    try:
        for name in ("mc_core.warmup", "mc_core", "mc_core.redis_client"):
            sys.modules.pop(name, None)
        return importlib.import_module("mc_core.warmup")
    finally:
        sys.path.remove(path)


def test_action_slot_blocks_repeat_within_window():
    module = load_mc_warmup()
    taken = set()

    class FakeRedis:
        def set(self, key, value, nx=False, ex=None):
            if key in taken:
                return None
            taken.add(key)
            return True

    module.redis_safe = lambda func, default=None: func(FakeRedis())
    assert module.acquire_action_slot("warmup", seconds=10) is True
    assert module.acquire_action_slot("warmup", seconds=10) is False
    assert module.acquire_action_slot("import_intel", seconds=10) is True


def test_action_slot_fails_open_when_redis_is_down():
    module = load_mc_warmup()
    module.redis_safe = lambda func, default=None: default
    assert module.acquire_action_slot("warmup", seconds=10) is True


def test_mission_control_actions_are_throttled():
    source = MC_MAIN.read_text(encoding="utf-8")
    assert "acquire_action_slot" in source
    assert "acquire_action_slot('warmup'" in source
    assert "acquire_action_slot('import_intel'" in source


def test_ai_brain_serialises_warmup():
    source = AI_BRAIN_MAIN.read_text(encoding="utf-8")
    assert "_warmup_lock = asyncio.Lock()" in source
    assert "async with _warmup_lock" in source
