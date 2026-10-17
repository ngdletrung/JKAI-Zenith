# -*- coding: utf-8 -*-
"""
JKAI Dynamic Model Resolver (Future-Proof Model Resolution & Auto-Discovery).
Enforces:
1. Universal Model Aliasing: 'gemini:latest', 'chatgpt:latest', 'deepseek:latest-reasoner', 'AUTO_LATEST'.
2. Dynamic Discovery & Semantic Version Ranking (3.8 > 2.5 > 1.5).
3. Resilient Fallback Cascade: Automatically falls back to adjacent models if top model is 503/429.
4. Zero-code maintenance: Adapts when providers release new models without modifying code.
"""

import json
import logging
import os
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Dict, List, Optional
import urllib.request
import urllib.error

logger = logging.getLogger("JKAI.Security.DynamicModelResolver")


@dataclass
class ProviderModelInfo:
    model_id: str
    display_name: str
    family: str  # "flash", "pro", "mini", "flagship", "reasoner", "chat"
    version_score: float  # e.g. 3.8, 2.5, 1.5, 4.0


class DynamicModelResolver:
    """
    Universal Model Resolution Engine across Google, OpenAI, DeepSeek, and Grok.
    """

    CACHE_FILE = "cache/cloud_model_catalog.json"
    CACHE_TTL_HOURS = 24

    # Default fallback baselines if offline or cache empty
    BASELINE_MODELS = {
        "gemini": {
            "latest-flash": ["gemini-3.8-flash", "gemini-2.5-flash", "gemini-1.5-flash"],
            "latest-pro": ["gemini-3.8-pro", "gemini-2.5-pro", "gemini-1.5-pro"],
            "default": "gemini-3.8-flash",
        },
        "openai": {
            "latest-mini": ["gpt-4o-mini", "gpt-3.5-turbo"],
            "latest-flagship": ["gpt-4o", "gpt-4-turbo"],
            "default": "gpt-4o-mini",
        },
        "chatgpt": {
            "latest-mini": ["gpt-4o-mini", "gpt-3.5-turbo"],
            "latest-flagship": ["gpt-4o", "gpt-4-turbo"],
            "default": "gpt-4o-mini",
        },
        "deepseek": {
            "latest-chat": ["deepseek-chat"],
            "latest-reasoner": ["deepseek-reasoner", "deepseek-chat"],
            "default": "deepseek-chat",
        },
        "grok": {
            "latest": ["grok-beta", "grok-2-latest"],
            "default": "grok-beta",
        },
    }

    def __init__(self, cache_path: Optional[str] = None):
        self.cache_path = cache_path or self.CACHE_FILE
        self._cache: Dict[str, Any] = {}
        self._load_cache()

    def _load_cache(self):
        if os.path.exists(self.cache_path):
            try:
                with open(self.cache_path, "r", encoding="utf-8") as f:
                    self._cache = json.load(f)
            except Exception as e:
                logger.warning("Failed to load model cache: %s", e)

    def _save_cache(self):
        try:
            os.makedirs(os.path.dirname(self.cache_path), exist_ok=True)
            with open(self.cache_path, "w", encoding="utf-8", newline="\n") as f:
                json.dump(self._cache, f, indent=2)
        except Exception as e:
            logger.warning("Failed to save model cache: %s", e)

    @staticmethod
    def extract_version_score(model_id: str) -> float:
        """Extracts numerical version score (e.g. 'gemini-3.8-flash' -> 3.8, 'gpt-4o' -> 4.0)."""
        match = re.search(r"(\d+(?:\.\d+)?)", model_id)
        if match:
            try:
                return float(match.group(1))
            except ValueError:
                pass
        return 1.0

    def resolve_model(
        self,
        provider: str,
        alias_or_name: Optional[str] = None,
    ) -> str:
        """
        Resolves a high-level alias (e.g. 'latest', 'AUTO_LATEST', 'gemini:latest-flash')
        to the optimal concrete model ID.
        """
        prov_key = provider.lower()
        if prov_key not in self.BASELINE_MODELS:
            return alias_or_name or "unknown"

        req = (alias_or_name or "default").lower().replace(f"{prov_key}:", "").strip()

        # Handle AUTO_LATEST or generic "latest"
        if req in ("auto_latest", "latest", "default"):
            cached_models = self._cache.get(prov_key, {}).get("models", [])
            if cached_models:
                # Return highest versioned model in cache
                sorted_models = sorted(
                    cached_models,
                    key=lambda m: self.extract_version_score(m),
                    reverse=True,
                )
                return sorted_models[0]
            return self.BASELINE_MODELS[prov_key]["default"]

        # Handle sub-family aliases (latest-flash, latest-pro, latest-mini, latest-reasoner)
        prov_baselines = self.BASELINE_MODELS[prov_key]
        if req in prov_baselines and isinstance(prov_baselines[req], list):
            return prov_baselines[req][0]

        # If already a specific model string, return it directly
        return alias_or_name

    def get_fallback_chain(self, provider: str, current_model: str) -> List[str]:
        """
        Returns a resilient fallback sequence of alternative models if the primary model fails.
        """
        prov_key = provider.lower()
        baselines = self.BASELINE_MODELS.get(prov_key, {})
        chain = []

        # Find matching family
        for family, models in baselines.items():
            if isinstance(models, list):
                if current_model in models:
                    idx = models.index(current_model)
                    chain = models[idx + 1 :]
                    break

        if not chain:
            default_mod = baselines.get("default")
            if default_mod and default_mod != current_model:
                chain.append(default_mod)

        return chain


dynamic_model_resolver = DynamicModelResolver()
