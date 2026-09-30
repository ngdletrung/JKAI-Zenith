# -*- coding: utf-8 -*-
"""
core/cognitive_bus/backends/__init__.py
JKAI Zenith - Tier 2 Backend Registry
Swap model = changing ACTIVE_BACKEND or register custom factory.
"""

from __future__ import annotations

from typing import Callable, Dict, List

from core.cognitive_bus.tier2_backend import Tier2Backend
from core.cognitive_bus.backends.fake_backend import FakeTier2Backend

_BACKENDS: Dict[str, Callable[[], Tier2Backend]] = {}


def register(name: str, factory: Callable[[], Tier2Backend]) -> None:
    _BACKENDS[name] = factory


def build(name: str) -> Tier2Backend:
    if name not in _BACKENDS:
        raise KeyError(
            f"Unknown Tier 2 backend '{name}'. "
            f"Registered: {sorted(_BACKENDS.keys())}"
        )
    return _BACKENDS[name]()


def list_registered() -> List[str]:
    return sorted(_BACKENDS.keys())


# Default registrations
register("fake", lambda: FakeTier2Backend())

try:
    from core.cognitive_bus.backends.ollama_backend import LocalOllamaTier2Backend
    register("ollama", lambda: LocalOllamaTier2Backend())
except Exception:
    pass

try:
    from core.cognitive_bus.backends.local_reflex_backend import LocalReflexTier2Backend
    register("sovereign-reflex", lambda: LocalReflexTier2Backend())
except Exception:
    pass

# Active selection - default to fake for offline determinism; can switch to "ollama" or "sovereign-reflex"
ACTIVE_BACKEND: str = "fake"


def build_active() -> Tier2Backend:
    return build(ACTIVE_BACKEND)
