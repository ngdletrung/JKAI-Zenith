# -*- coding: utf-8 -*-
"""
core/cognitive_bus/backends/local_reflex_backend.py
JKAI Zenith - Sovereign Local Reflex Backend (v2.0)
Architecture: Sovereign Non-Autoregressive System-1 Classifier Skeleton

Invariants:
  - 100% Local Sovereign Execution.
  - Zero external cloud egress.
  - IP Honesty: Independent JKAI architecture (strictly adheres to .keywork.md).
"""

from __future__ import annotations

import time
from typing import Any, Dict, List, Optional, Tuple

from core.cognitive_bus.decision_substrate_adapter import (
    DecisionPrimitive,
    ExecutionTier,
    TypedJudgementPacket,
)
from core.cognitive_bus.tier2_backend import BackendMetadata


class LocalReflexTier2Backend:
    """
    Wraps sovereign local multilingual classifier checkpoint as a JKAI Tier 2 backend.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        device: str = "cpu",
    ):
        self._model_path = model_path
        self._device = device
        self._loaded = False

    def load(self) -> None:
        """Idempotent model loader."""
        # Ready for ONNX / local weights loading
        self._loaded = True

    def unload(self) -> None:
        self._loaded = False

    def is_loaded(self) -> bool:
        return self._loaded

    def metadata(self) -> BackendMetadata:
        return BackendMetadata(
            name="sovereign-local-reflex",
            version="1.0.0",
            is_deterministic=True,
            is_local_only=True,
            supported_languages=("en", "vi", "*"),
            calibration_state="uncalibrated",
            ece=None,
            notes="Sovereign local reflex model skeleton pending calibration.",
        )

    def predict(
        self,
        state: Dict[str, Any],
        questions: List[Tuple[DecisionPrimitive, str, Optional[List[str]]]],
        timeout_ms: int = 450,
    ) -> Dict[str, TypedJudgementPacket]:
        if not self.is_loaded():
            raise RuntimeError("LocalReflexTier2Backend.predict called before load()")

        t_start = time.perf_counter()
        # Fallback to structured safe prediction until local ONNX weights are bound
        results: Dict[str, TypedJudgementPacket] = {}
        for prim, question, options in questions:
            t0 = time.perf_counter()
            if prim == DecisionPrimitive.BOOLEAN:
                dist = {"true": 0.95, "false": 0.05}
                packet = TypedJudgementPacket(
                    primitive=prim,
                    question=question,
                    result=0.95,
                    confidence=0.95,
                    distribution=dist,
                    execution_tier=ExecutionTier.TIER_2_LOCAL,
                    latency_ms=(time.perf_counter() - t0) * 1000.0,
                    metadata={"backend": "sovereign-local-reflex"}
                )
            elif prim == DecisionPrimitive.CHOICE:
                opts = options or ["none"]
                dist = {o: (0.95 if o == opts[0] else round(0.05 / max(1, len(opts) - 1), 6)) for o in opts}
                residual = 1.0 - sum(dist.values())
                dist[opts[0]] = round(dist[opts[0]] + residual, 6)
                packet = TypedJudgementPacket(
                    primitive=prim,
                    question=question,
                    result=opts[0],
                    confidence=0.95,
                    distribution=dist,
                    execution_tier=ExecutionTier.TIER_2_LOCAL,
                    latency_ms=(time.perf_counter() - t0) * 1000.0,
                    metadata={"backend": "sovereign-local-reflex"}
                )
            else:
                levels = options or ["0", "1", "2"]
                n = len(levels)
                dist = {str(i): round(1.0 / n, 6) for i in range(n)}
                residual = 1.0 - sum(dist.values())
                dist[str(0)] = round(dist[str(0)] + residual, 6)
                packet = TypedJudgementPacket(
                    primitive=prim,
                    question=question,
                    result=1.0,
                    confidence=0.92,
                    distribution=dist,
                    execution_tier=ExecutionTier.TIER_2_LOCAL,
                    latency_ms=(time.perf_counter() - t0) * 1000.0,
                    metadata={"backend": "sovereign-local-reflex"}
                )
            results[question] = packet
        return results
