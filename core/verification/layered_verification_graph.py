"""
JKAI Zenith - Core Verification: Layered Verification Graph (v2.1)
Architecture: T6 Verification & Reality Layer / Atomic Decision Engine
Protocol: Protocol v2.0 - Two-Agent Cooperative Execution Protocol
Consensus Sign-Off: Antigravity & OpenCode (Phiên 21)

Invariant: Layer-by-layer dependency execution.
Short-circuit immediately if Layer 0 (Prerequisite) fails.
Total Latency Target: ~240ms <= 400ms.
"""

import time
from enum import Enum
from typing import Dict, List, Any, Optional, Tuple
from dataclasses import dataclass, field

from core.cognitive_bus.jev_substrate_adapter import TriTierJevAdapter, JevPrimitive, TypedJudgementPacket, StateSanitizer


class VerificationLayer(str, Enum):
    LAYER_0_PREREQUISITE = "LAYER_0_PREREQUISITE"
    LAYER_1_INTEGRITY = "LAYER_1_INTEGRITY"
    LAYER_2_REALITY = "LAYER_2_REALITY"


@dataclass
class LayeredVerificationResult:
    overall_passed: bool
    failed_layer: Optional[VerificationLayer]
    failure_reason: Optional[str]
    layer_results: Dict[str, Dict[str, TypedJudgementPacket]]
    skipped_layers: List[VerificationLayer]
    total_latency_ms: float
    decision_evidence: List[Dict[str, Any]]
    evaluated_at: float = field(default_factory=time.time)


class LayeredVerificationGraph:
    """
    Dependency-Aware Verification Graph for Atomic Verification.
    
    Structure:
    - Layer 0: Prerequisite ['artifact_exists'] -> Must pass (p >= 0.80, conf >= 0.85).
               If FAIL: Short-circuit reject. Layer 1 and 2 are NEVER executed.
    - Layer 1: Semantic Integrity ['schema_valid', 'content_complete'] -> Parallel within layer.
               If FAIL: Short-circuit reject. Layer 2 is NEVER executed.
    - Layer 2: Reality & Side Effects ['side_effects_checked', 'delivery_confirmed'] -> Parallel within layer.
    """

    PASS_PROB_THRESHOLD: float = 0.80
    CONFIDENCE_FLOOR: float = 0.85

    LAYER_0_QUESTIONS = ["artifact_exists"]
    LAYER_1_QUESTIONS = ["schema_valid", "content_complete"]
    LAYER_2_QUESTIONS = ["side_effects_checked", "delivery_confirmed"]

    def __init__(self, adapter: Optional[TriTierJevAdapter] = None):
        self.adapter = adapter or TriTierJevAdapter(enable_mock=True)

    def verify_observation(self, observation_state: Dict[str, Any]) -> LayeredVerificationResult:
        t0 = time.time()
        sanitized_state = StateSanitizer.sanitize(observation_state)
        layer_results: Dict[str, Dict[str, TypedJudgementPacket]] = {}
        decision_evidence: List[Dict[str, Any]] = []
        skipped_layers: List[VerificationLayer] = []

        # =========================================================================
        # LAYER 0: Prerequisite Checks (artifact_exists)
        # =========================================================================
        l0_batch = [(JevPrimitive.NOUL, q, None) for q in self.LAYER_0_QUESTIONS]
        l0_verdict = self.adapter.evaluate_parallel_batch(sanitized_state, l0_batch)
        layer_results[VerificationLayer.LAYER_0_PREREQUISITE.value] = l0_verdict.judgements

        for q, packet in l0_verdict.judgements.items():
            decision_evidence.append({
                "layer": VerificationLayer.LAYER_0_PREREQUISITE.value,
                "question": q,
                "probability": packet.result,
                "confidence": packet.confidence,
                "tier": packet.execution_tier.value
            })

            # Gate Check Layer 0
            if packet.confidence < self.CONFIDENCE_FLOOR or packet.result < self.PASS_PROB_THRESHOLD:
                total_latency = (time.time() - t0) * 1000.0
                skipped_layers = [VerificationLayer.LAYER_1_INTEGRITY, VerificationLayer.LAYER_2_REALITY]
                return LayeredVerificationResult(
                    overall_passed=False,
                    failed_layer=VerificationLayer.LAYER_0_PREREQUISITE,
                    failure_reason=f"Prerequisite failed on '{q}': result={packet.result:.2f}, confidence={packet.confidence:.2f}",
                    layer_results=layer_results,
                    skipped_layers=skipped_layers,
                    total_latency_ms=total_latency,
                    decision_evidence=decision_evidence
                )

        # =========================================================================
        # LAYER 1: Semantic Integrity Checks (schema_valid, content_complete)
        # =========================================================================
        l1_batch = [(JevPrimitive.NOUL, q, None) for q in self.LAYER_1_QUESTIONS]
        l1_verdict = self.adapter.evaluate_parallel_batch(sanitized_state, l1_batch)
        layer_results[VerificationLayer.LAYER_1_INTEGRITY.value] = l1_verdict.judgements

        for q, packet in l1_verdict.judgements.items():
            decision_evidence.append({
                "layer": VerificationLayer.LAYER_1_INTEGRITY.value,
                "question": q,
                "probability": packet.result,
                "confidence": packet.confidence,
                "tier": packet.execution_tier.value
            })

            # Gate Check Layer 1
            if packet.confidence < self.CONFIDENCE_FLOOR or packet.result < self.PASS_PROB_THRESHOLD:
                total_latency = (time.time() - t0) * 1000.0
                skipped_layers = [VerificationLayer.LAYER_2_REALITY]
                return LayeredVerificationResult(
                    overall_passed=False,
                    failed_layer=VerificationLayer.LAYER_1_INTEGRITY,
                    failure_reason=f"Integrity check failed on '{q}': result={packet.result:.2f}, confidence={packet.confidence:.2f}",
                    layer_results=layer_results,
                    skipped_layers=skipped_layers,
                    total_latency_ms=total_latency,
                    decision_evidence=decision_evidence
                )

        # =========================================================================
        # LAYER 2: Reality & Side Effects (side_effects_checked, delivery_confirmed)
        # =========================================================================
        l2_batch = [(JevPrimitive.NOUL, q, None) for q in self.LAYER_2_QUESTIONS]
        l2_verdict = self.adapter.evaluate_parallel_batch(sanitized_state, l2_batch)
        layer_results[VerificationLayer.LAYER_2_REALITY.value] = l2_verdict.judgements

        for q, packet in l2_verdict.judgements.items():
            decision_evidence.append({
                "layer": VerificationLayer.LAYER_2_REALITY.value,
                "question": q,
                "probability": packet.result,
                "confidence": packet.confidence,
                "tier": packet.execution_tier.value
            })

            # Gate Check Layer 2
            if packet.confidence < self.CONFIDENCE_FLOOR or packet.result < self.PASS_PROB_THRESHOLD:
                total_latency = (time.time() - t0) * 1000.0
                return LayeredVerificationResult(
                    overall_passed=False,
                    failed_layer=VerificationLayer.LAYER_2_REALITY,
                    failure_reason=f"Reality check failed on '{q}': result={packet.result:.2f}, confidence={packet.confidence:.2f}",
                    layer_results=layer_results,
                    skipped_layers=[],
                    total_latency_ms=total_latency,
                    decision_evidence=decision_evidence
                )

        # All layers passed!
        total_latency = (time.time() - t0) * 1000.0
        return LayeredVerificationResult(
            overall_passed=True,
            failed_layer=None,
            failure_reason=None,
            layer_results=layer_results,
            skipped_layers=[],
            total_latency_ms=total_latency,
            decision_evidence=decision_evidence
        )
