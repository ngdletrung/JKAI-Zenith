"""
🏛️ JKAI ZENITH — RUNTIME MODULE
File: core/runtime/__init__.py

NOTE: amg_boot is NOT imported here to prevent circular import.
  amg_boot → model_inspector → base_adapter → runtime/__init__ → amg_boot (cycle)
  Import AMGBootstrap, BootRequest, BootReport directly from core.runtime.amg_boot.
"""
from core.runtime.base_adapter import RuntimeAdapter, RuntimeModelInfo, RuntimeHealth
from core.runtime.ollama_adapter import OllamaRuntimeAdapter
from core.runtime.runtime_discovery import (
    RuntimeDiscovery, EndpointInfo, EndpointType, AvailableModel, ResidentModel, RuntimeSnapshot,
)
from core.runtime.model_lifecycle import ModelLifecycleManager, LifecycleResult, LifecycleDecision
from core.runtime.boot_cache import BootCache

__all__ = [
    "RuntimeAdapter", "RuntimeModelInfo", "RuntimeHealth", "OllamaRuntimeAdapter",
    "RuntimeDiscovery", "EndpointInfo", "EndpointType", "AvailableModel", "ResidentModel", "RuntimeSnapshot",
    "ModelLifecycleManager", "LifecycleResult", "LifecycleDecision",
    "BootCache",
    # AMGBootstrap, BootRequest, BootReport: import directly from core.runtime.amg_boot
]


def __getattr__(name):
    """Lazy import for amg_boot classes to preserve backward compatibility."""
    if name in ("AMGBootstrap", "BootRequest", "BootReport"):
        from core.runtime import amg_boot as _amg
        return getattr(_amg, name)
    raise AttributeError(f"module 'core.runtime' has no attribute {name!r}")
