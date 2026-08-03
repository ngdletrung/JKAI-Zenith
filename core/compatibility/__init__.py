"""
JKAI ZENITH — COMPATIBILITY SHIMS
Directory: core/compatibility/

Responsibility:
    Backward-compatibility facades for legacy callers during the 5-Plane transition.
    Preserves old import paths and method signatures with zero breaking changes.
"""

from core.utils.model_router import ModelRouter, mission_router
from core.utils.engine import JKAIIntelligenceEngine

__all__ = [
    "ModelRouter",
    "mission_router",
    "JKAIIntelligenceEngine",
]
