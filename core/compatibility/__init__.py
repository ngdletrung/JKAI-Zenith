"""
JKAI ZENITH — COMPATIBILITY SHIMS
Directory: core/compatibility/

Responsibility:
    Backward-compatibility facades for legacy callers during the 5-Domain transition.
    Preserves old import paths and method signatures with zero breaking changes.

Expiration Policy:
    deprecated_since: "v20.5"
    removal_target:   "v22.0"
    replacement:      "core.cognitive, core.governance, core.runtime, core.infrastructure"
"""

import warnings
from core.utils.model_router import ModelRouter, mission_router
from core.utils.engine import JKAIIntelligenceEngine

DEPRECATED_SINCE = "v20.5"
REMOVAL_TARGET = "v22.0"
REPLACEMENT = "core.cognitive, core.governance, core.runtime"

def warn_compatibility_usage(shim_name: str):
    warnings.warn(
        f"[DEPRECATED]: {shim_name} is deprecated since {DEPRECATED_SINCE} "
        f"and scheduled for removal in {REMOVAL_TARGET}. Use {REPLACEMENT} instead.",
        DeprecationWarning,
        stacklevel=2,
    )

__all__ = [
    "ModelRouter",
    "mission_router",
    "JKAIIntelligenceEngine",
    "DEPRECATED_SINCE",
    "REMOVAL_TARGET",
]
