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
    from core.cognitive_bus.backends.reflex_engine_backend import ReflexEngineBackend
    register("sovereign-reflex", lambda: LocalReflexTier2Backend())
    register("reflex-engine", lambda: ReflexEngineBackend())
except Exception:
    pass

# Active selection - default to fake for offline determinism; can switch to "ollama" or "sovereign-reflex"
# ONLY via explicit Master authorization (set_active_backend).
ACTIVE_BACKEND: str = "fake"


def set_active_backend(
    name: str,
    *,
    master_approved: bool = False,
    master_signature: str = "",
) -> str:
    """
    Flips ACTIVE_BACKEND ONLY when Master explicitly authorizes the change.
    Machine code is strictly prohibited from auto-flipping the active backend.
    """
    global ACTIVE_BACKEND
    if master_approved is not True or not str(master_signature).strip():
        raise PermissionError(
            "Master Governance Lock Violation: Machine is forbidden from auto-flipping "
            "ACTIVE_BACKEND. Explicit Master approval (master_approved=True and "
            "non-empty master_signature) is required."
        )
    if name not in _BACKENDS:
        raise KeyError(
            f"Unknown Tier 2 backend '{name}'. "
            f"Registered: {sorted(_BACKENDS.keys())}"
        )
    ACTIVE_BACKEND = name
    return ACTIVE_BACKEND


def build_active() -> Tier2Backend:
    return build(ACTIVE_BACKEND)
