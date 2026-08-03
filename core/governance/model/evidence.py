"""
JKAI ZENITH — GOVERNANCE DOMAIN: CAPABILITY EVIDENCE
File: core/governance/model/evidence.py

Multi-source capability evidence gathering and confidence scoring.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time


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
