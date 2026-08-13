"""
JKAI ZENITH AI OS — MULTI-DIMENSIONAL DECISION MATRIX
File: core/os/cognition/decision_matrix.py

Tính toán quyết định chuyển đổi Topology theo hàm đa chiều:
Decision = f(Confidence, Uncertainty, Impact, Reversibility, EvidenceQuality, ToolRisk)
Xuất DecisionExplanation giải thích chi tiết điểm số và lý do (Explainable Control Flow).
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List


@dataclass
class DecisionExplanation:
    decision: str  # FAST, DEEP, ASK_USER, RECOVER, VERIFY
    score: float
    reason_codes: List[str] = field(default_factory=list)
    evidence_ids: List[str] = field(default_factory=list)


def evaluate_decision_matrix(
    confidence: float,
    uncertainty: float,
    impact: float,
    reversibility: float,
    evidence_quality: float,
    tool_risk: float,
    evidence_ids: List[str] = None
) -> DecisionExplanation:
    """
    Computes a multi-dimensional decision score and explanation.
    """
    ev_ids = evidence_ids or []
    reasons = []

    # Risk-weighted complexity score
    risk_score = (impact * (1.0 - reversibility)) + (tool_risk * 0.5)
    cognitive_demand = (uncertainty * 0.4) + ((1.0 - confidence) * 0.4) + (impact * 0.2)
    score = (cognitive_demand * 0.6) + (risk_score * 0.4)

    if tool_risk >= 0.8:
        reasons.append("HIGH_TOOL_RISK")
    if impact >= 0.7:
        reasons.append("HIGH_SYSTEM_IMPACT")
    if reversibility <= 0.3:
        reasons.append("LOW_REVERSIBILITY")
    if uncertainty >= 0.6:
        reasons.append("HIGH_UNCERTAINTY")
    if confidence < 0.6:
        reasons.append("LOW_CONFIDENCE")

    # Topology decision mapping
    if score >= 0.75:
        decision = "DEEP"
    elif score >= 0.60 and uncertainty >= 0.7:
        decision = "ASK_USER"
        reasons.append("USER_DECISION_REQUIRED")
    else:
        decision = "FAST"
        reasons.append("SUFFICIENT_CONFIDENCE_FAST")

    return DecisionExplanation(
        decision=decision,
        score=round(score, 4),
        reason_codes=reasons,
        evidence_ids=ev_ids
    )
