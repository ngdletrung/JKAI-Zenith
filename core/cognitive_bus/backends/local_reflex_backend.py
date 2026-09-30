# -*- coding: utf-8 -*-
"""
[ZENITH FILE DIRECTIVE]
- File: core/cognitive_bus/backends/local_reflex_backend.py
- Role: Sovereign Local Reflex Tier 2 Backend (Unified with ReflexEngineBackend).
- Ownership: Master LeeTrung
- Status: Active | Version: SDS v28.0

Invariants:
  - 100% Local Sovereign Execution (Zero external cloud egress).
  - Anti-Redundancy (.keywork.md Part IX.3): Directly subclasses ReflexEngineBackend
    so "sovereign-reflex" and "reflex-engine" share one canonical implementation.
"""

from __future__ import annotations

from typing import Optional

from core.cognitive_bus.backends.reflex_engine_backend import (
    ReflexEngineBackend,
    detect_language_bcp47,
)
from core.cognitive_bus.reflex_evolution import ReflexEvolutionManager
from core.cognitive_bus.tier2_backend import BackendMetadata


class LocalReflexTier2Backend(ReflexEngineBackend):
    """
    Canonical Sovereign Local Reflex Tier 2 Backend.
    Subclasses ReflexEngineBackend to provide full bilingual (EN/VI) single-pass
    evaluation, batching (predict_batch), and tournament shortlisting (predict_tournament).
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu",
        version: Optional[str] = None,
        evolution_manager: Optional[ReflexEvolutionManager] = None,
    ):
        super().__init__(
            model_path=model_path,
            version=version,
            device=device,
            evolution_manager=evolution_manager,
        )

    def metadata(self) -> BackendMetadata:
        base_md = super().metadata()
        return BackendMetadata(
            name="sovereign-local-reflex",
            version=base_md.version,
            is_deterministic=base_md.is_deterministic,
            is_local_only=base_md.is_local_only,
            supported_languages=base_md.supported_languages,
            calibration_state=base_md.calibration_state,
            ece=base_md.ece,
            notes=base_md.notes,
        )


__all__ = ["LocalReflexTier2Backend", "ReflexEngineBackend", "detect_language_bcp47"]
