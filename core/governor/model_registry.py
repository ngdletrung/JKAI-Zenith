"""
🏛️ ADAPTIVE MODEL GOVERNOR (AMG) v2 — MODEL REGISTRY
File: core/governor/model_registry.py

Purpose:
    Thread-safe, disk-cached singleton registry of all models available
    on connected Ollama instances.

    Lifecycle:
        startup → load JSON cache → /api/tags (detect new/changed) →
        /api/show (only new/changed) → update registry → save JSON

    Zero-code extensibility guarantee:
        When a new model is added to Ollama (ollama pull some-new-model),
        the registry auto-discovers and inspects it on the next refresh.
        No code change required anywhere in JKAI.
"""

from __future__ import annotations
import asyncio
import json
import logging
import os
import threading
import time
from typing import Dict, List, Optional, Set

from core.governor.model_capabilities import ModelCapabilityProfile, ModelClass
from core.governor.model_inspector import ModelInspector
from core.runtime.base_adapter import RuntimeAdapter, RuntimeModelInfo

logger = logging.getLogger("AMG_ModelRegistry")

# Disk cache path — relative to JKAI root, auto-created
_CACHE_FILENAME = "model_registry.json"
_REFRESH_INTERVAL_SEC = 300   # Background refresh every 5 minutes
_ENTRY_TTL_SEC = 86400        # Invalidate individual entry after 24h


class ModelRegistry:
    """
    Singleton model registry. Thread-safe. Disk-cached.

    Usage:
        registry = ModelRegistry.instance()
        await registry.discover(adapters)          # call at startup
        profile = registry.get("qwen3.5:4b")
        models  = registry.list_by_class(ModelClass.REASONING)
    """

    _instance: Optional["ModelRegistry"] = None
    _lock: threading.RLock = threading.RLock()

    def __new__(cls) -> "ModelRegistry":
        with cls._lock:
            if cls._instance is None:
                cls._instance = super().__new__(cls)
                cls._instance._initialized = False
            return cls._instance

    @classmethod
    def instance(cls) -> "ModelRegistry":
        return cls()

    def __init__(self):
        if getattr(self, "_initialized", False):
            return
        self._profiles: Dict[str, ModelCapabilityProfile] = {}
        self._adapters: List[RuntimeAdapter] = []
        self._cache_path: str = self._resolve_cache_path()
        self._last_refresh: float = 0.0
        self._bg_thread: Optional[threading.Thread] = None
        self._initialized = True
        self._load_disk_cache()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def register_adapters(self, adapters: List[RuntimeAdapter]) -> None:
        """Register runtime adapters to discover models from."""
        with self._lock:
            self._adapters = list(adapters)

    async def discover(self, adapters: Optional[List[RuntimeAdapter]] = None) -> int:
        """
        Discover all models from registered adapters.
        Only calls /api/show for new or changed models (digest check).
        Returns count of profiles in registry after discovery.
        """
        if adapters:
            with self._lock:
                self._adapters = list(adapters)

        new_count = 0
        for adapter in self._adapters:
            new_count += await self._discover_from_adapter(adapter)

        self._save_disk_cache()
        self._last_refresh = time.monotonic()

        if not self._bg_thread or not self._bg_thread.is_alive():
            self._start_background_refresh()

        logger.info(
            f"[AMG-REGISTRY] Discovery complete — {len(self._profiles)} models registered, "
            f"{new_count} new/updated"
        )
        return len(self._profiles)

    def get(self, model_name: str) -> Optional[ModelCapabilityProfile]:
        """Lookup a model profile by name (case-insensitive, partial match supported)."""
        with self._lock:
            clean = model_name.strip().lower()
            # Exact match
            if clean in self._profiles:
                return self._profiles[clean]
            # Prefix match (e.g. "qwen3.5" matches "qwen3.5:4b")
            for name, profile in self._profiles.items():
                if name.startswith(clean) or clean.startswith(name.split(":")[0]):
                    return profile
            return None

    def list_all(self) -> List[ModelCapabilityProfile]:
        """Returns all profiles sorted by model name."""
        with self._lock:
            return sorted(self._profiles.values(), key=lambda p: p.model_name)

    def list_by_class(self, cls: ModelClass) -> List[ModelCapabilityProfile]:
        """Returns all profiles that have the specified ModelClass asserted."""
        with self._lock:
            return [p for p in self._profiles.values() if cls in p.model_classes]

    def list_by_classes(self, *classes: ModelClass, require_all: bool = False) -> List[ModelCapabilityProfile]:
        """
        Returns profiles matching ModelClass criteria.
        require_all=True  → model must have ALL specified classes
        require_all=False → model must have AT LEAST ONE
        """
        with self._lock:
            result = []
            for p in self._profiles.values():
                if require_all:
                    if all(c in p.model_classes for c in classes):
                        result.append(p)
                else:
                    if any(c in p.model_classes for c in classes):
                        result.append(p)
            return result

    def list_names(self) -> List[str]:
        with self._lock:
            return list(self._profiles.keys())

    def count(self) -> int:
        with self._lock:
            return len(self._profiles)

    def invalidate(self, model_name: str) -> None:
        """Force re-inspection of a specific model on next discover()."""
        with self._lock:
            self._profiles.pop(model_name.strip().lower(), None)

    def clear(self) -> None:
        """Clear entire registry (for testing)."""
        with self._lock:
            self._profiles.clear()

    def inject(self, profile: ModelCapabilityProfile) -> None:
        """
        Directly inject a profile (used in tests for mock models).
        This is the extension point for test_new_model_zero_code_change.
        """
        with self._lock:
            self._profiles[profile.model_name.strip().lower()] = profile

    def register(self, profile: ModelCapabilityProfile) -> None:
        """Alias for inject(). Directly registers a ModelCapabilityProfile."""
        self.inject(profile)

    # ------------------------------------------------------------------
    # Discovery internals
    # ------------------------------------------------------------------

    async def _discover_from_adapter(self, adapter: RuntimeAdapter) -> int:
        """
        Discover models from one adapter.
        Returns count of new/updated profiles.
        """
        try:
            health = await adapter.health_check()
            if not health.is_alive:
                logger.warning(f"[AMG-REGISTRY] Adapter {adapter.runtime_id} offline: {health.error}")
                return 0
        except Exception as e:
            logger.warning(f"[AMG-REGISTRY] Health check failed for {adapter.runtime_id}: {e}")
            return 0

        # Get current model list with digests
        try:
            from core.runtime.ollama_adapter import OllamaRuntimeAdapter
            if isinstance(adapter, OllamaRuntimeAdapter):
                models_meta = await adapter.list_models_with_digest()
            else:
                names = await adapter.list_models()
                models_meta = [{"name": n, "digest": "", "size_gb": 0.0} for n in names]
        except Exception as e:
            logger.error(f"[AMG-REGISTRY] list_models failed on {adapter.runtime_id}: {e}")
            return 0

        new_count = 0
        for entry in models_meta:
            name    = entry["name"].strip().lower()
            digest  = entry.get("digest", "")
            size_gb = entry.get("size_gb", 0.0)

            # Skip if cached entry is still valid (same digest, not expired)
            existing = self._profiles.get(name)
            if existing and self._is_cache_valid(existing, digest):
                continue

            # New or changed model — call /api/show
            info = await self._safe_inspect(adapter, name, size_gb)
            if info is None:
                continue

            profile = ModelInspector.build_profile(info)
            with self._lock:
                self._profiles[name] = profile
            new_count += 1
            logger.debug(f"[AMG-REGISTRY] Registered: {name}")

        return new_count

    async def _safe_inspect(
        self, adapter: RuntimeAdapter, model_name: str, size_gb: float
    ) -> Optional[RuntimeModelInfo]:
        """Calls adapter.inspect_model() with error handling."""
        try:
            info = await adapter.inspect_model(model_name)
            if info is None:
                # Build minimal info from tags data
                info = RuntimeModelInfo(model_name=model_name, size_gb=size_gb)
            elif info.size_gb <= 0 and size_gb > 0:
                info.size_gb = size_gb
            return info
        except Exception as e:
            logger.warning(f"[AMG-REGISTRY] inspect_model({model_name}) failed: {e}")
            return RuntimeModelInfo(model_name=model_name, size_gb=size_gb)

    @staticmethod
    def _is_cache_valid(profile: ModelCapabilityProfile, current_digest: str) -> bool:
        """Check if cached profile is still valid."""
        # Expired?
        age = time.time() - profile.last_inspected_at
        if age > _ENTRY_TTL_SEC:
            return False
        # Digest changed (model was updated)?
        if current_digest and profile.ollama_digest and profile.ollama_digest != current_digest:
            return False
        return True

    # ------------------------------------------------------------------
    # Disk cache
    # ------------------------------------------------------------------

    def _resolve_cache_path(self) -> str:
        """Resolve path to model_registry.json cache file."""
        # Try JKAI_ROOT env var first
        root = os.getenv("JKAI_ROOT", "")
        if not root:
            # Walk up from this file to find JKAI root
            here = os.path.dirname(os.path.abspath(__file__))
            for _ in range(5):
                if os.path.exists(os.path.join(here, "intelligence")):
                    root = here
                    break
                here = os.path.dirname(here)
        cache_dir = os.path.join(root, "core", "cache") if root else "/tmp/jkai_cache"
        os.makedirs(cache_dir, exist_ok=True)
        return os.path.join(cache_dir, _CACHE_FILENAME)

    def _load_disk_cache(self) -> None:
        """Load profiles from disk cache on startup."""
        if not os.path.exists(self._cache_path):
            return
        try:
            with open(self._cache_path, "r", encoding="utf-8") as f:
                data = json.load(f)
            loaded = 0
            for name, raw in data.items():
                profile = self._deserialize_profile(name, raw)
                if profile:
                    self._profiles[name] = profile
                    loaded += 1
            logger.info(f"[AMG-REGISTRY] Loaded {loaded} profiles from disk cache")
        except Exception as e:
            logger.warning(f"[AMG-REGISTRY] Cache load failed: {e}")

    def _save_disk_cache(self) -> None:
        """Persist profiles to disk cache."""
        try:
            data = {}
            with self._lock:
                for name, profile in self._profiles.items():
                    data[name] = self._serialize_profile(profile)
            with open(self._cache_path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            logger.warning(f"[AMG-REGISTRY] Cache save failed: {e}")

    @staticmethod
    def _serialize_profile(p: ModelCapabilityProfile) -> dict:
        mem = p.memory
        return {
            "model_name":           p.model_name,
            "architecture":         p.architecture,
            "family":               p.family,
            "context_length_max":   p.context_length_max,
            "model_classes":        [c.name for c in p.model_classes],
            "has_vision":           p.has_vision,
            "has_tool_calling":     p.has_tool_calling,
            "is_embedding_only":    p.is_embedding_only,
            "assessment_confidence": p.assessment_confidence,
            "last_inspected_at":    p.last_inspected_at,
            "ollama_digest":        p.ollama_digest,
            "memory": {
                "weight_file_size_gb":      mem.weight_file_size_gb,
                "quantization":             mem.quantization,
                "bytes_per_param":          mem.bytes_per_param,
                "total_parameters_b":       mem.total_parameters_b,
                "active_parameters_b":      mem.active_parameters_b,
                "num_layers":               mem.num_layers,
                "is_moe":                   mem.is_moe,
                "kv_cache_mb_per_1k_ctx":   mem.kv_cache_mb_per_1k_ctx,
                "detection_method":         mem.detection_method,
            } if mem else None,
        }

    @staticmethod
    def _deserialize_profile(name: str, raw: dict) -> Optional[ModelCapabilityProfile]:
        try:
            classes: Set[ModelClass] = set()
            for cname in raw.get("model_classes", ["GENERAL"]):
                try:
                    classes.add(ModelClass[cname])
                except KeyError:
                    pass
            if not classes:
                classes = {ModelClass.GENERAL}

            mem_raw = raw.get("memory")
            mem = None
            if mem_raw:
                from core.governor.model_capabilities import ModelMemoryProfile
                mem = ModelMemoryProfile(
                    weight_file_size_gb=mem_raw.get("weight_file_size_gb", 0.0),
                    quantization=mem_raw.get("quantization", "Q4_K_M"),
                    bytes_per_param=mem_raw.get("bytes_per_param", 0.5),
                    total_parameters_b=mem_raw.get("total_parameters_b", 3.0),
                    active_parameters_b=mem_raw.get("active_parameters_b", 3.0),
                    num_layers=mem_raw.get("num_layers", 32),
                    is_moe=mem_raw.get("is_moe", False),
                    kv_cache_mb_per_1k_ctx=mem_raw.get("kv_cache_mb_per_1k_ctx", 256.0),
                    detection_method=mem_raw.get("detection_method", "heuristic"),
                )

            return ModelCapabilityProfile(
                model_name=raw.get("model_name", name),
                architecture=raw.get("architecture", "transformer"),
                family=raw.get("family", ""),
                context_length_max=raw.get("context_length_max", 8192),
                memory=mem,
                model_classes=classes,
                has_vision=raw.get("has_vision", False),
                has_tool_calling=raw.get("has_tool_calling", True),
                is_embedding_only=raw.get("is_embedding_only", False),
                assessment_confidence=raw.get("assessment_confidence", 0.0),
                last_inspected_at=raw.get("last_inspected_at", 0.0),
                ollama_digest=raw.get("ollama_digest", ""),
            )
        except Exception as e:
            logger.warning(f"[AMG-REGISTRY] Failed to deserialize '{name}': {e}")
            return None

    # ------------------------------------------------------------------
    # Background refresh
    # ------------------------------------------------------------------

    def _start_background_refresh(self) -> None:
        def _refresh_loop():
            while True:
                time.sleep(_REFRESH_INTERVAL_SEC)
                if self._adapters:
                    try:
                        asyncio.run(self.discover())
                    except Exception as e:
                        logger.warning(f"[AMG-REGISTRY] Background refresh error: {e}")

        self._bg_thread = threading.Thread(
            target=_refresh_loop, daemon=True, name="AMG-RegistryRefresh"
        )
        self._bg_thread.start()
        logger.debug("[AMG-REGISTRY] Background refresh thread started")
