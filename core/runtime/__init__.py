"""
🏛️ JKAI ZENITH — RUNTIME MODULE
File: core/runtime/__init__.py
"""
from core.runtime.base_adapter import RuntimeAdapter, RuntimeModelInfo, RuntimeHealth
from core.runtime.ollama_adapter import OllamaRuntimeAdapter
from core.runtime.runtime_discovery import (
    RuntimeDiscovery, EndpointInfo, EndpointType, AvailableModel, ResidentModel, RuntimeSnapshot,
)
from core.runtime.model_lifecycle import ModelLifecycleManager, LifecycleResult, LifecycleDecision
from core.runtime.boot_cache import BootCache
from core.runtime.amg_boot import AMGBootstrap, BootRequest, BootReport

__all__ = [
    "RuntimeAdapter", "RuntimeModelInfo", "RuntimeHealth", "OllamaRuntimeAdapter",
    "RuntimeDiscovery", "EndpointInfo", "EndpointType", "AvailableModel", "ResidentModel", "RuntimeSnapshot",
    "ModelLifecycleManager", "LifecycleResult", "LifecycleDecision",
    "BootCache",
    "AMGBootstrap", "BootRequest", "BootReport",
]
