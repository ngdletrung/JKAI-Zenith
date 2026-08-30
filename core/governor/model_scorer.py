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


from dataclasses import dataclass, field

@dataclass
class RuntimeState:
    """Runtime execution state for Dynamic Model Escalation (Phase 6.0)."""
    uncertainty: float = 0.0          # 0.0 (certain) to 1.0 (highly uncertain)
    failure_count: int = 0            # Number of previous attempt failures
    failure_class: Optional[str] = None
    evidence_deficit: float = 0.0     # 0.0 to 1.0 (unmet proof obligations)
    progress: float = 0.0             # 0.0 to 1.0
    remaining_budget_tokens: int = 50000
    context_pressure: float = 0.0     # 0.0 to 1.0
    latency_ms: float = 0.0
    cost: float = 0.0


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
        task_complexity: float = 0.5,
        runtime_state: Optional[RuntimeState] = None,
    ) -> ModelScore:
        """
        Compute the complete ModelScore for a model-role-quality-hardware combination.

        Args:
            profile:         ModelCapabilityProfile from registry
            role:            JKAI role name (e.g. "PLANNER", "RECEPTIONIST")
            quality:         Target quality ("low" | "medium" | "high")
            hw:              Current HardwareState
            context_len:     Requested context window
            requested_hardware: Hardware preference from rule_hardware.md
            task_complexity: Task complexity score 0.0–1.0 from TaskProfiler.
                             0.0 = trivial; 1.0 = expert-level multi-step reasoning.
                             Used for 5D vector match scoring (North Star v3.0).

        Returns:
            ModelScore with all components and reasons.
        """
        role_upper = role.upper()
        quality_lower = quality.lower()
        task_complexity = max(0.0, min(1.0, task_complexity))
        reasons: List[str] = []

        # 1. CapabilityFit (evidence-governed matching)
        cap_fit, cap_reasons = cls._score_capability_fit(profile, role_upper, task_complexity)
        reasons.extend(cap_reasons)

        # 2. Resource & Cost Penalty (hardware fit, VRAM, latency)
        alloc = ResourceGovernor.allocate(profile, hw, context_len, requested_hardware)
        res_score, res_reasons = cls._score_resource(alloc, hw, profile)
        reasons.extend(res_reasons)

        cost_penalty = max(0.0, 1.0 - res_score) * 0.20
        reasons.append(f"UTILITY-COST-PENALTY: res_score={res_score:.2f} → penalty={cost_penalty:.3f}")

        # 3. Context Penalty (context capacity vs requested context)
        model_ctx = profile.context_window_tokens
        if context_len > model_ctx:
            ctx_penalty = min(0.30, (context_len - model_ctx) / context_len * 0.50)
            reasons.append(f"UTILITY-CONTEXT-PENALTY: req={context_len} > cap={model_ctx} → penalty={ctx_penalty:.3f}")
        else:
            ctx_penalty = 0.0

        # 4. Risk Penalty & Reliability Bonus
        rel_score = profile.quant_vector.reliability
        if rel_score.is_known:
            rel_val = rel_score.value or 0.5
            rel_bonus = (rel_val - 0.50) * 0.20 if rel_val > 0.50 else 0.0
            risk_penalty = (0.50 - rel_val) * 0.30 if rel_val < 0.50 else 0.0
            reasons.append(f"UTILITY-RELIABILITY: val={rel_val:.2f} (src={rel_score.source}) → bonus={rel_bonus:.3f}, risk_penalty={risk_penalty:.3f}")
        else:
            rel_bonus = 0.0
            risk_penalty = 0.0
            reasons.append("UTILITY-RELIABILITY: UNKNOWN → bonus=0.000, risk_penalty=0.000 (Epistemic Humility)")

        # 5. Model Quality Tier score
        qual_score, qual_reasons = cls._score_quality(profile)
        reasons.extend(qual_reasons)

        # 6. Latency score (for fast path)
        lat_score, lat_reasons = cls._score_latency(profile)
        reasons.extend(lat_reasons)

        # 7. Runtime State Escalation (Phase 6.0: Dynamic Model Escalation)
        escalation_bonus = 0.0
        uncertainty_penalty = 0.0
        if runtime_state is not None:
            reasoning_val = profile.quant_vector.reasoning_strength.effective_value
            # High reasoning capability model (>= 0.65) receives escalation bonus under uncertainty or failure
            if reasoning_val >= 0.65 and (runtime_state.uncertainty > 0.3 or runtime_state.failure_count > 0 or runtime_state.evidence_deficit > 0.3):
                state_severity = max(runtime_state.uncertainty, min(1.0, runtime_state.failure_count * 0.4), runtime_state.evidence_deficit)
                escalation_bonus = reasoning_val * state_severity * 0.30
                reasons.append(f"RUNTIME-ESCALATION-BONUS: reasoning={reasoning_val:.2f} severity={state_severity:.2f} → bonus=+{escalation_bonus:.3f}")

            # Low reasoning model (< 0.60) is penalized when failure count increases
            if runtime_state.failure_count > 0 and reasoning_val < 0.60:
                uncertainty_penalty = (0.60 - reasoning_val) * runtime_state.failure_count * 0.25
                reasons.append(f"RUNTIME-UNCERTAINTY-PENALTY: reasoning={reasoning_val:.2f} fails={runtime_state.failure_count} → penalty=-{uncertainty_penalty:.3f}")

        # 8. Utility Function (North Star v3.0 & Phase 6.0)
        # Utility(model, task, state) = CapabilityFit - CostPenalty - RiskPenalty - ContextPenalty + ReliabilityBonus + EscalationBonus - UncertaintyPenalty
        quality_weight = {"low": 0.10, "medium": 0.20, "high": 0.30}.get(quality_lower, 0.20)
        latency_weight = {"low": 0.30, "medium": 0.10, "high": 0.05}.get(quality_lower, 0.10)

        utility = (
            cap_fit * 0.45
            + qual_score * quality_weight
            + lat_score * latency_weight
            - cost_penalty
            - risk_penalty
            - ctx_penalty
            + rel_bonus
            + escalation_bonus
            - uncertainty_penalty
        )
        final = round(max(0.0, min(1.0, utility)), 3)
        reasons.append(f"UTILITY-FINAL: fit={cap_fit:.2f} qual={qual_score:.2f} lat={lat_score:.2f} esc=+{escalation_bonus:.2f} → utility={final:.3f}")

        # Check minimum capability threshold
        min_cap = ROLE_MINIMUM_CAPABILITY.get(role_upper, 0.30)
        meets_min = cap_fit >= min_cap

        if not meets_min:
            reasons.append(
                f"BELOW minimum capability ({cap_fit:.2f} < {min_cap:.2f} required for {role_upper})"
            )

        if profile.is_unknown:
            reasons.append(
                f"LOW assessment confidence ({profile.assessment_confidence:.2f}) — "
                "capabilities uncertain, conservative routing applied"
            )

        return ModelScore(
            model_name=profile.model_name,
            role=role_upper,
            quality=quality_lower,
            capability_score=round(cap_fit, 3),
            resource_score=round(res_score, 3),
            quality_score=round(qual_score, 3),
            latency_score=round(lat_score, 3),
            final_score=final,
            meets_minimum=meets_min,
            reasons=reasons,
        )

    # ------------------------------------------------------------------
    # Component Scorers
    # ------------------------------------------------------------------

    @classmethod
    def _score_capability_fit(
        cls, profile: ModelCapabilityProfile, role: str, task_complexity: float
    ) -> tuple[float, List[str]]:
        """
        Scores capability fit using evidence-governed profile and task complexity.
        """
        reasons: List[str] = []
        weights = ROLE_CLASS_WEIGHTS.get(role, {})

        if not weights:
            reasons.append(f"No class weights defined for role {role} — using GENERAL default")
            weights = {ModelClass.GENERAL: 1.0}

        total_possible = sum(weights.values())
        earned = sum(w for cls_, w in weights.items() if cls_ in profile.model_classes)

        raw_score = earned / total_possible if total_possible > 0 else 0.0
        dampened = raw_score * max(0.5, profile.assessment_confidence)

        # Blend with quantitative profile match if available
        quant_match = profile.quant_vector.task_complexity_match(task_complexity)
        fit = dampened * 0.70 + quant_match * 0.30

        matched = [cls_.name for cls_, w in weights.items() if cls_ in profile.model_classes]
        missing = [cls_.name for cls_, w in weights.items() if cls_ not in profile.model_classes]

        if matched:
            reasons.append(f"Matched capabilities: {', '.join(matched)}")
        if missing:
            reasons.append(f"Missing capabilities: {', '.join(missing)}")
        reasons.append(f"CAPABILITY-FIT: raw={raw_score:.2f} quant_match={quant_match:.2f} → fit={fit:.3f}")

        return round(fit, 3), reasons

    # Backward-compat alias
    _score_capability = _score_capability_fit


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
