# -*- coding: utf-8 -*-
"""
core/cognitive_bus/backends/fake_backend.py
Deterministic fake Tier 2 backend for tests and shadow-harness dry runs.
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


class FakeTier2Backend:
    """
    Test double. Behavior controlled by constructor args.

    failure_mode:
      None          -> always succeeds
      "timeout"     -> sleeps > timeout_ms then raises TimeoutError
      "raise"       -> raises RuntimeError immediately
      "low_conf"    -> returns confidence below threshold (tests fallthrough)
      "bad_dist"    -> returns distribution not summing to 1.0 (tests validator)
    """

    def __init__(
        self,
        confidence: float = 0.97,
        failure_mode: Optional[str] = None,
        delay_ms: float = 0.0,
        metadata: Optional[BackendMetadata] = None,
    ):
        self._confidence = confidence
        self._failure_mode = failure_mode
        self._delay_ms = delay_ms
        self._loaded = False
        self._metadata = metadata or BackendMetadata(
            name="fake-tier2",
            version="1.0",
            is_deterministic=True,
            is_local_only=True,
            supported_languages=("*",),
            calibration_state="calibrated",
            ece=0.02,
            notes="test double",
        )

    def load(self) -> None:
        self._loaded = True

    def unload(self) -> None:
        self._loaded = False

    def is_loaded(self) -> bool:
        return self._loaded

    def metadata(self) -> BackendMetadata:
        return self._metadata

    def predict(
        self,
        state: Dict[str, Any],
        questions: List[Tuple[DecisionPrimitive, str, Optional[List[str]]]],
        timeout_ms: int = 450,
    ) -> Dict[str, TypedJudgementPacket]:
        if not self._loaded:
            raise RuntimeError("FakeTier2Backend.predict called before load()")

        if self._failure_mode == "timeout":
            time.sleep((timeout_ms + 50) / 1000.0)
            raise TimeoutError("fake timeout")

        if self._failure_mode == "raise":
            raise RuntimeError("fake backend failure")

        result: Dict[str, TypedJudgementPacket] = {}
        for prim, question, options in questions:
            t0 = time.perf_counter()
            if self._delay_ms:
                time.sleep(self._delay_ms / 1000.0)

            if prim == DecisionPrimitive.BOOLEAN:
                dist = {"true": self._confidence, "false": round(1.0 - self._confidence, 6)}
                res: Any = self._confidence
            elif prim == DecisionPrimitive.CHOICE:
                opts = options or ["none_of_the_above"]
                winner = opts[0]
                rest = (1.0 - self._confidence) / max(1, len(opts) - 1)
                dist = {
                    o: (self._confidence if o == winner else round(rest, 6))
                    for o in opts
                }
                res = winner
            else:  # SCORE
                levels = options or ["0", "1", "2", "3", "4"]
                peak = min(2, len(levels) - 1)
                rest = (1.0 - self._confidence) / max(1, len(levels) - 1)
                dist = {
                    levels[i]: (self._confidence if i == peak else round(rest, 6))
                    for i in range(len(levels))
                }
                res = float(peak)

            # Ensure sum == 1.0 exactly
            residual = 1.0 - sum(dist.values())
            if residual != 0.0:
                first_k = next(iter(dist))
                dist[first_k] = round(dist[first_k] + residual, 6)

            if self._failure_mode == "bad_dist":
                dist = {k: 0.1 for k in dist}  # deliberately wrong

            conf = self._confidence
            if self._failure_mode == "low_conf":
                conf = 0.40

            result[question] = TypedJudgementPacket(
                primitive=prim,
                question=question,
                result=res,
                confidence=conf,
                distribution=dist,
                execution_tier=ExecutionTier.TIER_2_LOCAL,
                latency_ms=(time.perf_counter() - t0) * 1000.0,
                metadata={"backend": "fake"},
            )

        return result
