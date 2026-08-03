"""
JKAI ZENITH — GOVERNANCE DOMAIN: CAPABILITY EVIDENCE & PERFORMANCE PROFILE
File: core/governance/model/evidence.py

Multi-source capability evidence gathering, confidence scoring,
CapabilityVector representation, and ModelPerformanceProfile.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time


@dataclass
class CapabilityVector:
    """Continuous multi-dimensional capability scores (0.0 - 1.0) replacing rigid enum classifications."""
    reasoning: float = 0.5
    coding: float = 0.5
    general: float = 0.5
    vision: float = 0.0
    tool_calling: float = 0.5
    multilingual: float = 0.5


@dataclass
class ModelPerformanceProfile:
    """Observed runtime performance profile dynamically updated from Observation telemetry."""
    role: str = "PLANNER"
    quality_score: float = 0.90
    latency_p50: float = 2.0
    latency_p95: float = 5.0
    tool_success_rate: float = 0.95
    structured_output_rate: float = 0.98
    failure_rate: float = 0.01
    sample_count: int = 0


@dataclass
class CapabilityEvidence:
    """Represents multi-source evidence for a model capability."""
    feature: str                        # "reasoning" | "coding" | "tool_use" | "vision" | "planning"
    source: str                         # "model_metadata" | "benchmark" | "rule_hardware" | "telemetry"
    confidence: float = 1.0             # 0.0 - 1.0 confidence score
    reliability: str = "HIGH"           # "LOW" | "MEDIUM" | "HIGH"
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class CapabilityInference:
    """Infers composite capability scores from multiple CapabilityEvidence entries."""

    def infer_score(self, evidence_list: List[CapabilityEvidence], feature: str) -> float:
        feature_evidence = [e for e in evidence_list if e.feature.lower() == feature.lower()]
        if not feature_evidence:
            return 0.5  # default neutral score

        weighted_sum = sum(e.confidence * (1.0 if e.reliability == "HIGH" else 0.7) for e in feature_evidence)
        weight_total = sum(1.0 if e.reliability == "HIGH" else 0.7 for e in feature_evidence)

        return min(1.0, max(0.0, weighted_sum / weight_total)) if weight_total > 0 else 0.5
