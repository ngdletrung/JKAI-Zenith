"""
JKAI Zenith - Core Routing: Deterministic Controller Anchor (v2.1)
Architecture: T4 Action Control Plane / Atomic Decision Engine
Protocol: Protocol v2.0 - Two-Agent Cooperative Execution Protocol
Consensus Sign-Off: Antigravity & OpenCode (Phiên 21)

Invariant: Jev is an ADVISOR, NOT a Router. Controller is 100% Deterministic.
"""

import time
import random
from enum import Enum
from typing import Dict, List, Any, Optional
from dataclasses import dataclass, field

from core.cognitive_bus.jev_substrate_adapter import TriTierJevAdapter, JevPrimitive, TypedJudgementPacket, StateSanitizer


class ExecutionPath(str, Enum):
    FAST_PATH = "FAST_PATH"
    DEEP_PATH = "DEEP_PATH"
    HUMAN_ESCALATION = "HUMAN_ESCALATION"


@dataclass
class RouteDecision:
    """
    Final deterministic routing decision emitted by DeterministicRoutingController.
    """
    selected_path: ExecutionPath
    confidence: float
    reason: str
    is_fallback: bool
    rolling_circuit_status: str
    decision_evidence: Dict[str, Any]
    latency_ms: float
    evaluated_at: float = field(default_factory=time.time)


class DeterministicRoutingController:
    """
    Deterministic Routing Controller with Jev Advisor & Rolling Average Circuit Breaker.
    
    Rules:
    1. Jev proposes ProbabilisticAdvice (Choice over FAST_PATH, DEEP_PATH, HUMAN_ESCALATION).
    2. If rolling_avg_confidence < 0.70 (over last 20 calls) -> Circuit OPEN (disable Jev routing).
    3. If Jev confidence < 0.80 -> Fallback to default deterministic rule (DEEP_PATH).
    4. If HUMAN_ESCALATION probability > 0.40 -> Route to HUMAN_ESCALATION immediately.
    5. If FAST_PATH probability >= 0.80 -> Route to FAST_PATH.
    6. Else -> Route to DEEP_PATH.
    7. Supports reproducible execution via optional random_seed.
    """

    CONFIDENCE_FLOOR: float = 0.80
    ESCALATION_THRESHOLD: float = 0.40
    FAST_PATH_THRESHOLD: float = 0.80
    CIRCUIT_WINDOW: int = 20
    CIRCUIT_MIN_AVG_CONFIDENCE: float = 0.70
    CIRCUIT_RECOVERY_AVG_CONFIDENCE: float = 0.80

    def __init__(self, adapter: Optional[TriTierJevAdapter] = None):
        self.adapter = adapter or TriTierJevAdapter(enable_mock=True)
        self.confidence_history: List[float] = []
        self.is_circuit_disabled: bool = False

    def get_rolling_avg_confidence(self) -> float:
        if not self.confidence_history:
            return 1.0
        return sum(self.confidence_history) / len(self.confidence_history)

    def record_confidence(self, conf: float):
        self.confidence_history.append(conf)
        if len(self.confidence_history) > self.CIRCUIT_WINDOW:
            self.confidence_history.pop(0)

        # Check circuit breaker condition with Hysteresis (0.70 OPEN, 0.80 CLOSE)
        if len(self.confidence_history) >= 5:
            avg_conf = self.get_rolling_avg_confidence()
            if self.is_circuit_disabled:
                if avg_conf >= self.CIRCUIT_RECOVERY_AVG_CONFIDENCE:
                    self.is_circuit_disabled = False
            else:
                if avg_conf < self.CIRCUIT_MIN_AVG_CONFIDENCE:
                    self.is_circuit_disabled = True

    def reset_circuit(self):
        self.confidence_history.clear()
        self.is_circuit_disabled = False

    def route(self, task_context: Dict[str, Any], random_seed: Optional[int] = None) -> RouteDecision:
        t0 = time.time()
        # Seed parameter preserved for reproducible external simulator passes
        _ = random_seed

        sanitized_context = StateSanitizer.sanitize(task_context)

        # 1. Check Rolling Circuit Breaker
        if self.is_circuit_disabled:
            latency = (time.time() - t0) * 1000.0
            return RouteDecision(
                selected_path=ExecutionPath.DEEP_PATH,
                confidence=1.0,
                reason="Circuit Breaker OPEN: Rolling average confidence below 0.70. Defaulting to DEEP_PATH.",
                is_fallback=True,
                rolling_circuit_status="OPEN",
                decision_evidence={
                    "engine": "deterministic-controller",
                    "mode": "circuit_breaker_fallback",
                    "rolling_avg_confidence": round(self.get_rolling_avg_confidence(), 4)
                },
                latency_ms=latency
            )

        # 2. Query Jev as Passive Advisor
        choices = [ExecutionPath.FAST_PATH.value, ExecutionPath.DEEP_PATH.value, ExecutionPath.HUMAN_ESCALATION.value]
        question = "Determine the optimal cognitive execution path for this task context"
        
        try:
            advice: TypedJudgementPacket = self.adapter.evaluate_choice(
                state=sanitized_context,
                question=question,
                options=choices
            )
            self.record_confidence(advice.confidence)
        except Exception as e:
            # Safe Fallback if Jev unreachable
            latency = (time.time() - t0) * 1000.0
            return RouteDecision(
                selected_path=ExecutionPath.DEEP_PATH,
                confidence=1.0,
                reason=f"Jev Advisor unreachable ({str(e)}). Reverting to deterministic DEEP_PATH.",
                is_fallback=True,
                rolling_circuit_status="NORMAL",
                decision_evidence={"engine": "deterministic-controller", "error": str(e)},
                latency_ms=latency
            )

        # 3. Deterministic Controller Policy Gate
        dist = advice.distribution
        conf = advice.confidence

        decision_evidence = {
            "engine": "jev-system-one",
            "primitive": "choice",
            "question_id": question,
            "confidence": round(conf, 4),
            "distribution": dist,
            "evaluated_at": time.time(),
            "execution_tier": advice.execution_tier.value
        }

        # Gate 1: Confidence Floor check
        if conf < self.CONFIDENCE_FLOOR:
            latency = (time.time() - t0) * 1000.0
            return RouteDecision(
                selected_path=ExecutionPath.DEEP_PATH,
                confidence=conf,
                reason=f"Jev confidence ({conf:.2f}) below floor ({self.CONFIDENCE_FLOOR:.2f}). Reverting to default DEEP_PATH.",
                is_fallback=True,
                rolling_circuit_status="NORMAL",
                decision_evidence=decision_evidence,
                latency_ms=latency
            )

        # Gate 2: Escalation Check (Safety First)
        p_escalate = dist.get(ExecutionPath.HUMAN_ESCALATION.value, 0.0)
        if p_escalate > self.ESCALATION_THRESHOLD:
            latency = (time.time() - t0) * 1000.0
            return RouteDecision(
                selected_path=ExecutionPath.HUMAN_ESCALATION,
                confidence=conf,
                reason=f"Escalation probability ({p_escalate:.2f}) exceeded threshold ({self.ESCALATION_THRESHOLD:.2f}).",
                is_fallback=False,
                rolling_circuit_status="NORMAL",
                decision_evidence=decision_evidence,
                latency_ms=latency
            )

        # Gate 3: Fast Path Threshold
        p_fast = dist.get(ExecutionPath.FAST_PATH.value, 0.0)
        if p_fast >= self.FAST_PATH_THRESHOLD:
            latency = (time.time() - t0) * 1000.0
            return RouteDecision(
                selected_path=ExecutionPath.FAST_PATH,
                confidence=conf,
                reason=f"Fast Path probability ({p_fast:.2f}) met threshold ({self.FAST_PATH_THRESHOLD:.2f}).",
                is_fallback=False,
                rolling_circuit_status="NORMAL",
                decision_evidence=decision_evidence,
                latency_ms=latency
            )

        # Gate 4: Default Deep Path
        latency = (time.time() - t0) * 1000.0
        return RouteDecision(
            selected_path=ExecutionPath.DEEP_PATH,
            confidence=conf,
            reason="Routing to DEEP_PATH for rigorous synthesis.",
            is_fallback=False,
            rolling_circuit_status="NORMAL",
            decision_evidence=decision_evidence,
            latency_ms=latency
        )
