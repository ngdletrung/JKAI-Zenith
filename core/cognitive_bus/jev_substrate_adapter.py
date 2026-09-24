# -*- coding: utf-8 -*-
"""
Backward compatibility bridge: re-exports from sovereign decision_substrate_adapter and state_sanitizer.
Will be deprecated in favor of core.cognitive_bus.decision_substrate_adapter and core.sanitizer.state_sanitizer.
"""

from core.sanitizer.state_sanitizer import StateSanitizer
from core.cognitive_bus.decision_substrate_adapter import (
    DecisionPrimitive,
    JevPrimitive,
    ExecutionTier,
    TypedJudgementPacket,
    ParallelBatchVerdict,
    CircuitBreaker,
    AdaptiveLatencyGuard,
    TriTierDecisionAdapter,
    TriTierJevAdapter,
)

__all__ = [
    "StateSanitizer",
    "DecisionPrimitive",
    "JevPrimitive",
    "ExecutionTier",
    "TypedJudgementPacket",
    "ParallelBatchVerdict",
    "CircuitBreaker",
    "AdaptiveLatencyGuard",
    "TriTierDecisionAdapter",
    "TriTierJevAdapter",
]
