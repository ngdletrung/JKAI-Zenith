"""
🏛️ ADAPTIVE MODEL GOVERNOR (AMG) v2 — MODEL SCORER
File: core/governor/model_scorer.py

Purpose:
    Computes ModelScore for a (model, role, quality, hardware) combination.
    Separated from PortfolioGovernor to keep scoring logic pure and testable.

    Score components:
        capability_score  — how well model capabilities match role requirements
        resource_score    — how well model fits in current hardware
        quality_score     — inherent quality tier of the model
        latency_score     — favouring smaller/faster for LOW quality targets

    Final score = weighted composite based on quality target:
        LOW quality    → latency_score heavily weighted
        MEDIUM quality → balanced
        HIGH quality   → capability_score + quality_score heavily weighted
"""

from __future__ import annotations
import logging
from typing import Dict, List, Optional

from core.governor.model_capabilities import (
    ModelCapabilityProfile, ModelClass, ModelScore,
    ROLE_CLASS_WEIGHTS, ROLE_MINIMUM_CAPABILITY,
    RoleRequirement, ROLE_REQUIREMENTS,
)
from core.governor.hardware_monitor import HardwareState
from core.governor.resource_governor import ResourceGovernor

logger = logging.getLogger("AMG_ModelScorer")

# Quality → component weight mapping
_QUALITY_WEIGHTS: Dict[str, Dict[str, float]] = {
    "low":    {"capability": 0.25, "resource": 0.30, "quality": 0.10, "latency": 0.35},
    "medium": {"capability": 0.40, "resource": 0.30, "quality": 0.20, "latency": 0.10},
    "high":   {"capability": 0.50, "resource": 0.20, "quality": 0.25, "latency": 0.05},
}


class ModelScorer:
    """
    Stateless scoring engine.
    All methods are class methods — no instance state.
    """

    @classmethod
    def score(
        cls,
        profile: ModelCapabilityProfile,
        role: str,
        quality: str,
        hw: HardwareState,
        context_len: int = 4096,
        requested_hardware: str = "auto",
    ) -> ModelScore:
        """
        Compute the complete ModelScore for a model-role-quality-hardware combination.

        Args:
            profile:  ModelCapabilityProfile from registry
            role:     JKAI role name (e.g. "PLANNER", "RECEPTIONIST")
            quality:  Target quality ("low" | "medium" | "high")
            hw:       Current HardwareState
            context_len: Requested context window
            requested_hardware: Hardware preference from rule_hardware.md

        Returns:
            ModelScore with all components and reasons.
        """
        role_upper = role.upper()
        quality_lower = quality.lower()
        reasons: List[str] = []

        # 1. Capability score
        cap_score, cap_reasons = cls._score_capability(profile, role_upper)
        reasons.extend(cap_reasons)

        # 2. Resource score
        alloc = ResourceGovernor.allocate(profile, hw, context_len, requested_hardware)
        res_score, res_reasons = cls._score_resource(alloc, hw, profile)
        reasons.extend(res_reasons)

        # 3. Quality / model tier score
        qual_score, qual_reasons = cls._score_quality(profile)
        reasons.extend(qual_reasons)

        # 4. Latency score (prefer smaller/faster)
        lat_score, lat_reasons = cls._score_latency(profile)
        reasons.extend(lat_reasons)

        # 5. Weighted composite
        weights = _QUALITY_WEIGHTS.get(quality_lower, _QUALITY_WEIGHTS["medium"])
        final = (
            cap_score  * weights["capability"] +
            res_score  * weights["resource"]   +
            qual_score * weights["quality"]    +
            lat_score  * weights["latency"]
        )

        # Check minimum capability threshold
        min_cap = ROLE_MINIMUM_CAPABILITY.get(role_upper, 0.30)
        meets_min = cap_score >= min_cap

        if not meets_min:
            reasons.append(
                f"BELOW minimum capability ({cap_score:.2f} < {min_cap:.2f} required for {role_upper})"
            )

        # Log assessment confidence warning
        if profile.is_unknown:
            reasons.append(
                f"LOW assessment confidence ({profile.assessment_confidence:.2f}) — "
                "capabilities uncertain, conservative routing applied"
            )

        return ModelScore(
            model_name=profile.model_name,
            role=role_upper,
            quality=quality_lower,
            capability_score=round(cap_score, 3),
            resource_score=round(res_score, 3),
            quality_score=round(qual_score, 3),
            latency_score=round(lat_score, 3),
            final_score=round(final, 3),
            meets_minimum=meets_min,
            reasons=reasons,
        )

    # ------------------------------------------------------------------
    # Component Scorers
    # ------------------------------------------------------------------

    @classmethod
    def _score_capability(
        cls, profile: ModelCapabilityProfile, role: str
    ) -> tuple[float, List[str]]:
        """
        Scores how well model capabilities match role class weights.
        Returns (0.0–1.0, reasons).

        UNKNOWN models (low assessment confidence) receive a penalty.
        """
        reasons: List[str] = []
        weights = ROLE_CLASS_WEIGHTS.get(role, {})

        if not weights:
            reasons.append(f"No class weights defined for role {role} — using GENERAL default")
            weights = {ModelClass.GENERAL: 1.0}

        total_possible = sum(weights.values())
        earned = sum(w for cls_, w in weights.items() if cls_ in profile.model_classes)

        raw_score = earned / total_possible if total_possible > 0 else 0.0

        # Apply assessment confidence as a dampener for UNKNOWN models
        dampened = raw_score * max(0.5, profile.assessment_confidence)

        matched = [cls_.name for cls_, w in weights.items() if cls_ in profile.model_classes]
        missing = [cls_.name for cls_, w in weights.items() if cls_ not in profile.model_classes]

        if matched:
            reasons.append(f"Matched capabilities: {', '.join(matched)}")
        if missing:
            reasons.append(f"Missing capabilities: {', '.join(missing)}")
        if dampened < raw_score:
            reasons.append(
                f"Capability score dampened by assessment confidence "
                f"({raw_score:.2f} → {dampened:.2f})"
            )

        return round(dampened, 3), reasons

    @classmethod
    def _score_resource(
        cls,
        alloc,  # BackendAllocation
        hw: HardwareState,
        profile: ModelCapabilityProfile,
    ) -> tuple[float, List[str]]:
        """
        Scores resource fit. GPU > HYBRID > CPU (for latency), but all viable.
        Non-viable allocation → score heavily penalised.
        """
        reasons: List[str] = []

        if not alloc.is_viable:
            reasons.append(f"RESOURCE: Not viable — {alloc.reason}")
            return 0.05, reasons  # Minimal score — last resort

        base = {"GPU": 1.0, "HYBRID": 0.75, "CPU": 0.50}.get(alloc.backend, 0.50)
        reasons.append(f"RESOURCE: {alloc.backend} allocation ({alloc.reason})")
        return base, reasons

    @classmethod
    def _score_quality(cls, profile: ModelCapabilityProfile) -> tuple[float, List[str]]:
        """
        Quality tier score based on model size and capability richness.
        Larger, more capable models score higher (for HIGH quality tasks).
        """
        reasons: List[str] = []
        mem = profile.memory
        if mem is None:
            return 0.5, ["No memory profile — neutral quality score"]

        # Use active parameters as quality proxy (reasoning depth)
        active = mem.active_parameters_b
        if active >= 30:
            score, tier = 1.00, "tier-5 (30B+)"
        elif active >= 14:
            score, tier = 0.85, "tier-4 (14–30B)"
        elif active >= 7:
            score, tier = 0.70, "tier-3 (7–14B)"
        elif active >= 3:
            score, tier = 0.55, "tier-2 (3–7B)"
        else:
            score, tier = 0.35, "tier-1 (<3B)"

        # Reasoning capability bonus
        if ModelClass.REASONING in profile.model_classes:
            score = min(1.0, score + 0.10)
            reasons.append(f"QUALITY: {tier} + reasoning bonus → {score:.2f}")
        else:
            reasons.append(f"QUALITY: {tier} → {score:.2f}")

        return score, reasons

    @classmethod
    def _score_latency(cls, profile: ModelCapabilityProfile) -> tuple[float, List[str]]:
        """
        Latency score — smaller/faster = higher score.
        Favoured for LOW quality targets (RECEPTIONIST, CHAT fast path).
        """
        reasons: List[str] = []
        mem = profile.memory
        if mem is None:
            return 0.5, ["No memory profile — neutral latency score"]

        active = mem.active_parameters_b
        if active <= 1:
            score, tier = 1.00, "ultra-fast (<1B)"
        elif active <= 3:
            score, tier = 0.85, "fast (1–3B)"
        elif active <= 7:
            score, tier = 0.65, "medium (3–7B)"
        elif active <= 14:
            score, tier = 0.40, "slow (7–14B)"
        else:
            score, tier = 0.20, "very slow (>14B)"

        reasons.append(f"LATENCY: {tier} → {score:.2f}")
        return score, reasons
