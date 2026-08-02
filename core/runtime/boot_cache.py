"""
🏛️ ADAPTIVE MODEL GOVERNOR (AMG) v2 — REGISTRY BOOT CACHE
File: core/runtime/boot_cache.py

Purpose:
    Disk cache for ModelCapabilityProfile records (`amg_registry.json`).
    Provides incremental discovery: inspects via /api/show ONLY when model
    digest is new or updated, reducing boot time from 10-30s to <1s.

Constitutional Invariants:
    1. Disk cache is an OPTIMIZATION LAYER, never authority.
       Ollama /api/tags is the source of truth for available models and digests.
    2. Digest mismatch → automatic cache invalidation for that model.
"""

from __future__ import annotations

import json
import logging
import os
import time
from typing import Dict, Optional, Any

from core.governor.model_capabilities import ModelCapabilityProfile, ModelClass, CapabilityEvidence

logger = logging.getLogger("AMG_BootCache")

DEFAULT_CACHE_FILE = "d:\\Docker\\JKAI\\cache\\amg_registry.json"


class BootCache:
    """
    Incremental registry cache using Ollama model digests.
    """

    def __init__(self, cache_file: str = DEFAULT_CACHE_FILE):
        self.cache_file = cache_file
        self._ensure_cache_dir()

    def _ensure_cache_dir(self):
        d = os.path.dirname(self.cache_file)
        if d and not os.path.exists(d):
            try:
                os.makedirs(d, exist_ok=True)
            except Exception as e:
                logger.warning(f"[CACHE] Failed to create cache dir {d}: {e}")

    def load_cache(self) -> Dict[str, Dict[str, Any]]:
        """Load raw json entries from disk cache."""
        if not os.path.exists(self.cache_file):
            return {}
        try:
            with open(self.cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
                return data.get("profiles", {})
        except Exception as e:
            logger.warning(f"[CACHE] Error loading {self.cache_file}: {e}")
            return {}

    def save_cache(self, profiles: Dict[str, ModelCapabilityProfile]):
        """Save capability profiles to disk cache."""
        self._ensure_cache_dir()
        serialized = {}
        for name, p in profiles.items():
            serialized[name] = {
                "model_name": p.model_name,
                "architecture": p.architecture,
                "family": p.family,
                "context_length_max": p.context_length_max,
                "model_classes": [c.name for c in p.model_classes],
                "has_vision": p.has_vision,
                "has_tool_calling": p.has_tool_calling,
                "is_embedding_only": p.is_embedding_only,
                "assessment_confidence": p.assessment_confidence,
                "last_inspected_at": p.last_inspected_at,
                "ollama_digest": p.ollama_digest,
                "memory": {
                    "weight_file_size_gb": p.memory.weight_file_size_gb if p.memory else 0.0,
                    "quantization": p.memory.quantization if p.memory else "Q4_K_M",
                    "bytes_per_param": p.memory.bytes_per_param if p.memory else 0.5,
                    "total_parameters_b": p.memory.total_parameters_b if p.memory else 7.0,
                    "active_parameters_b": p.memory.active_parameters_b if p.memory else 7.0,
                    "num_layers": p.memory.num_layers if p.memory else 32,
                    "is_moe": p.memory.is_moe if p.memory else False,
                } if p.memory else None
            }
        try:
            with open(self.cache_file, "w", encoding="utf-8") as f:
                json.dump({"updated_at": time.time(), "profiles": serialized}, f, indent=2)
            logger.info(f"[CACHE] Saved {len(serialized)} profile(s) to {self.cache_file}")
        except Exception as e:
            logger.warning(f"[CACHE] Error saving {self.cache_file}: {e}")
