# -*- coding: utf-8 -*-
"""
core/cognitive_bus/tier2_backend.py
JKAI Zenith - Sovereign Tier 2 Backend Protocol (v2.0)

Contract for local System-1 decision backends (Local Ollama, ONNX, Sovereign Classifiers).
Any object implementing this Protocol can be injected into TriTierDecisionAdapter
as `tier2_backend`. Swapping backend = swapping one file.

Design invariants:
  - Zero external egress: implementation MUST NOT make outbound network calls
    except to localhost (e.g. 127.0.0.1 Ollama) or in-process.
  - Determinism: same (state, questions) -> same (result, confidence) within
    backend-defined tolerance. Backends that are stochastic MUST document it
    and expose `is_deterministic = False`.
  - Calibration is first-class: every backend exposes `calibration_metadata()`
    so the kernel can refuse to authorize on uncalibrated confidence.
  - Language routing is backend responsibility, not caller responsibility.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Protocol, Tuple, runtime_checkable

from core.cognitive_bus.decision_substrate_adapter import (
    DecisionPrimitive,
    TypedJudgementPacket,
)


@dataclass(frozen=True)
class BackendMetadata:
    """
    Self-declared provenance of a Tier 2 backend.
    Used by kernel to decide whether confidence is trustworthy.
    """
    name: str                              # e.g. "sovereign-local-classifier", "ollama-qwen3"
    version: str                           # e.g. "0.3.7"
    is_deterministic: bool                 # True if same input -> same output
    is_local_only: bool                    # True if zero non-localhost egress
    supported_languages: Tuple[str, ...]   # BCP-47 codes, e.g. ("en", "vi", "*")
    calibration_state: str                 # "calibrated" | "uncalibrated" | "unknown"
    ece: Optional[float] = None            # Expected Calibration Error, if known
    notes: str = ""


@runtime_checkable
class Tier2Backend(Protocol):
    """
    Minimal contract a Tier 2 backend must satisfy.

    Implementations:
      - FakeTier2Backend            (tests, deterministic mock)
      - LocalReflexTier2Backend     (sovereign local multilingual classifier)
      - LocalOllamaTier2Backend     (local Ollama via structured JSON)
    """

    def load(self) -> None:
        """Idempotent. Load weights / open connections. Must not block > 30s."""
        ...

    def unload(self) -> None:
        """Release resources. Must be safe to call twice."""
        ...

    def is_loaded(self) -> bool:
        ...

    def metadata(self) -> BackendMetadata:
        ...

    def predict(
        self,
        state: Dict[str, Any],
        questions: List[Tuple[DecisionPrimitive, str, Optional[List[str]]]],
        timeout_ms: int = 450,
    ) -> Dict[str, TypedJudgementPacket]:
        """
        Return one TypedJudgementPacket per question, keyed by question string.

        Contract:
          - MUST return a packet for EVERY question, or raise.
          - MUST NOT block longer than timeout_ms (raise TimeoutError).
          - MUST set execution_tier=ExecutionTier.TIER_2_LOCAL.
          - MUST set latency_ms to measured wall time, not a constant.
          - confidence MUST be in [0, 1] and reflect backend's own calibration.
          - distribution MUST sum to 1.0 (+- 1e-6).
        """
        ...
