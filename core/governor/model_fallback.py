"""
🏛️ ADAPTIVE MODEL GOVERNOR (AMG) — MODEL FALLBACK
File: core/governor/model_fallback.py
Role: Health check & graceful fallback strategy when target model is missing or failing.
"""

import logging
from typing import Set, Optional
from core.governor.model_capabilities import ModelCapabilityProfile

logger = logging.getLogger("AMG_ModelFallback")

class ModelFallback:
    """
    Best-Effort Autonomous Model Adaptation & Fallback.
    Selects a resident fallback model if requested model fails or is un-pulled in Ollama.
    """
    DEFAULT_GPU_FALLBACK = "qwen2.5-coder:3b"
    DEFAULT_CPU_FALLBACK = "qwen2.5-coder:3b"

    @classmethod
    def resolve_fallback(cls, requested_model: str, loaded_models: Set[str], preferred_backend: str = "GPU") -> str:
        if not requested_model:
            return cls.DEFAULT_GPU_FALLBACK

        clean_req = requested_model.strip().lower()
        
        # 1. Target model is loaded and ready
        if clean_req in loaded_models or clean_req.split(":")[0] in loaded_models:
            return requested_model

        # 2. If target model is not in loaded set, check if any resident model can serve as fallback
        if loaded_models:
            for resident in loaded_models:
                if "coder" in resident or "qwen" in resident or "llama" in resident:
                    logger.warning(
                        f"[AMG-FALLBACK]: Model '{requested_model}' not currently resident. "
                        f"Gracefully falling back to resident model '{resident}' for zero-latency execution."
                    )
                    return resident

        # 3. Default fallback
        logger.warning(f"[AMG-FALLBACK]: Target '{requested_model}' unavailable. Falling back to default '{cls.DEFAULT_GPU_FALLBACK}'.")
        return cls.DEFAULT_GPU_FALLBACK
