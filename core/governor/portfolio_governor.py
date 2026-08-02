"""
🏛️ ADAPTIVE MODEL GOVERNOR (AMG) v2 — PORTFOLIO GOVERNOR
File: core/governor/portfolio_governor.py

Purpose:
    Central decision engine. Receives a role + quality + resource state,
    queries ModelRegistry, scores all candidates via ModelScorer, applies
    the fallback chain, and returns an ExecutionProfile with a GovernorDecision.

    Key guarantee:
        No model name, family, or size appears in decision logic.
        All decisions derive from ModelCapabilityProfile + HardwareState.
"""

from __future__ import annotations
import logging
import os
from typing import Dict, List, Optional, Set

from core.governor.model_capabilities import (
    ModelCapabilityProfile, ModelClass, ModelScore, GovernorDecision,
    ExecutionProfile, ROLE_REQUIREMENTS, ROLE_MINIMUM_CAPABILITY,
    RoleRequirement,
)
from core.governor.model_registry import ModelRegistry
from core.governor.model_scorer import ModelScorer
from core.governor.resource_governor import ResourceGovernor, BackendAllocation
from core.governor.hardware_monitor import HardwareMonitor, HardwareState

logger = logging.getLogger("AMG_PortfolioGovernor")

# Quality → minimum candidate pool size before we accept degradation
_MIN_POOL_SIZE = 1

# Quality ordering for graceful degradation
_QUALITY_LADDER = ["high", "medium", "low"]

# Capability requirements string → ModelClass mapping (for auto: syntax)
_CAPABILITY_MAP: Dict[str, ModelClass] = {
    "reasoning":  ModelClass.REASONING,
    "coding":     ModelClass.CODING,
    "vision":     ModelClass.VISION,
    "embedding":  ModelClass.EMBEDDING,
    "general":    ModelClass.GENERAL,
    "moe":        ModelClass.MOE,
    "tool_use":   ModelClass.TOOL_USE,
    "tools":      ModelClass.TOOL_USE,
}


class PortfolioGovernor:
    """
    Singleton-friendly central governor. Can be used as instance or via class methods.
    """

    def __init__(
        self,
        registry: Optional[ModelRegistry] = None,
        policy_path: Optional[str] = None,
    ):
        self._registry = registry or ModelRegistry.instance()
        self._policy = self._load_policy(policy_path)

    # ------------------------------------------------------------------
    # Primary resolve API
    # ------------------------------------------------------------------

    def resolve(
        self,
        role: str,
        requested_model: str,
        capability_requirements: Optional[List[str]] = None,
        quality: str = "medium",
        context_len: int = 4096,
        requested_hardware: str = "auto",
        hw: Optional[HardwareState] = None,
    ) -> ExecutionProfile:
        """
        Resolve the best ExecutionProfile for the given role + constraints.

        Args:
            role:           JKAI role (e.g. "PLANNER", "RECEPTIONIST")
            requested_model: Model name OR "auto"
            capability_requirements: Capability strings from rule_hardware.md auto syntax
                                     e.g. ["reasoning", "tool_use"]
                                     These are MODEL capabilities, not task descriptions.
            quality:        "low" | "medium" | "high"
            context_len:    Context window size
            requested_hardware: "auto" | "gpu" | "cpu" | "hybrid"
            hw:             HardwareState (auto-read if None)

        Returns:
            ExecutionProfile with attached GovernorDecision for observability.
        """
        role_upper = role.upper().strip()
        quality_lower = quality.lower().strip()
        hw = hw or HardwareMonitor.get_state()

        if requested_model.strip().lower() != "auto":
            return self._resolve_explicit(
                role_upper, requested_model, quality_lower, context_len,
                requested_hardware, hw
            )
        else:
            return self._resolve_auto(
                role_upper, capability_requirements or [], quality_lower,
                context_len, requested_hardware, hw
            )

    # ------------------------------------------------------------------
    # Explicit model routing
    # ------------------------------------------------------------------

    def _resolve_explicit(
        self, role: str, model_name: str, quality: str,
        context_len: int, requested_hardware: str, hw: HardwareState,
    ) -> ExecutionProfile:
        """User specified a concrete model name → validate + compute profile."""
        profile = self._registry.get(model_name)

        if profile is None:
            logger.warning(
                f"[AMG-GOVERNOR] Explicit model '{model_name}' not in registry. "
                "Attempting fallback to best-fit for role."
            )
            return self._resolve_auto(role, [], quality, context_len, requested_hardware, hw,
                                      original_requested=model_name)

        alloc = ResourceGovernor.allocate(profile, hw, context_len, requested_hardware)
        score = ModelScorer.score(profile, role, quality, hw, context_len, requested_hardware)

        decision = GovernorDecision(
            role=role,
            quality=quality,
            requested_model=model_name,
            capability_requirements=[],
            selected_model=profile.model_name,
            backend=alloc.backend,
            gpu_layers=alloc.num_gpu_layers,
            final_score=score.final_score,
            candidates_evaluated=[score],
            rejected_candidates=[],
            rejection_reasons={},
            resolved_via="explicit",
            fallback_applied=False,
            quality_degraded=False,
            reasons=[alloc.reason],
        )
        logger.info(decision.log_summary())
        return self._build_profile(profile, role, quality, context_len, alloc, score, decision,
                                   resolved_via="explicit")

    # ------------------------------------------------------------------
    # Auto routing
    # ------------------------------------------------------------------

    def _resolve_auto(
        self,
        role: str,
        capability_requirements: List[str],
        quality: str,
        context_len: int,
        requested_hardware: str,
        hw: HardwareState,
        original_requested: str = "auto",
    ) -> ExecutionProfile:
        """
        Auto-select best model from registry for given role + requirements.
        Applies quality-aware fallback chain if preferred quality unavailable.
        """
        required_classes: Set[ModelClass] = set()
        for cap_str in capability_requirements:
            mc = _CAPABILITY_MAP.get(cap_str.strip().lower())
            if mc:
                required_classes.add(mc)

        # For specialized roles, enforce mandatory class if no explicit capabilities requested
        if not required_classes:
            if role == "VISION":
                required_classes.add(ModelClass.VISION)
            elif role == "EMBEDDER":
                required_classes.add(ModelClass.EMBEDDING)

        # Score all candidates in registry
        all_candidates = self._registry.list_all()
        if not all_candidates:
            logger.error("[AMG-GOVERNOR] Registry is empty — cannot auto-resolve. Was discover() called?")
            return self._emergency_fallback(role, quality)

        scored: List[ModelScore] = []
        rejected: Dict[str, str] = {}

        for candidate in all_candidates:
            # Filter: must have required classes (if specified)
            if required_classes:
                missing = required_classes - candidate.model_classes
                if missing:
                    rejected[candidate.model_name] = (
                        f"Missing required classes: {', '.join(c.name for c in missing)}"
                    )
                    continue

            score = ModelScorer.score(
                candidate, role, quality, hw, context_len, requested_hardware
            )
            scored.append(score)

        # Sort by final_score descending
        scored.sort(key=lambda s: s.final_score, reverse=True)

        # Apply quality-aware selection with fallback chain
        min_cap = ROLE_MINIMUM_CAPABILITY.get(role, 0.30)
        selected_score: Optional[ModelScore] = None
        fallback_applied = False
        quality_degraded = False
        current_quality = quality

        for attempt_quality in _QUALITY_LADDER[_QUALITY_LADDER.index(quality):]:
            viable = [s for s in scored if s.meets_minimum and s.final_score > 0.0]
            if viable:
                selected_score = viable[0]
                if attempt_quality != quality:
                    quality_degraded = True
                    fallback_applied = True
                    current_quality = attempt_quality
                    logger.warning(
                        f"[AMG-GOVERNOR] Quality degraded: {quality.upper()} → "
                        f"{attempt_quality.upper()} for role {role}"
                    )
                break
            # Try re-scoring with lower quality target
            if attempt_quality != quality:
                for i, score in enumerate(scored):
                    new_score = ModelScorer.score(
                        self._registry.get(score.model_name),
                        role, attempt_quality, hw, context_len, requested_hardware
                    )
                    scored[i] = new_score
                scored.sort(key=lambda s: s.final_score, reverse=True)

        graceful_failure = selected_score is None
        if graceful_failure:
            # Best we can do: take highest scored even below minimum
            if scored:
                selected_score = scored[0]
                rejected[selected_score.model_name] = "Below minimum capability — forced selection"
                logger.error(
                    f"[AMG-GOVERNOR] No model meets minimum capability for {role}. "
                    f"Forcing '{selected_score.model_name}' as last resort."
                )
            else:
                logger.error(f"[AMG-GOVERNOR] Completely empty candidate list for role {role}.")
                return self._emergency_fallback(role, current_quality)

        selected_profile = self._registry.get(selected_score.model_name)
        alloc = ResourceGovernor.allocate(
            selected_profile, hw, context_len, requested_hardware
        )

        decision = GovernorDecision(
            role=role,
            quality=current_quality,
            requested_model=original_requested,
            capability_requirements=capability_requirements,
            selected_model=selected_profile.model_name,
            backend=alloc.backend,
            gpu_layers=alloc.num_gpu_layers,
            final_score=selected_score.final_score,
            candidates_evaluated=scored[:10],  # Top 10 for trace
            rejected_candidates=list(rejected.keys()),
            rejection_reasons=rejected,
            resolved_via="auto" if not fallback_applied else "fallback",
            fallback_applied=fallback_applied,
            quality_degraded=quality_degraded,
            graceful_failure=graceful_failure,
            reasons=selected_score.reasons,
        )
        logger.info(decision.log_summary())
        _via = "auto" if not fallback_applied else "fallback"
        return self._build_profile(
            selected_profile, role, current_quality, context_len, alloc,
            selected_score, decision, resolved_via=_via
        )

    # ------------------------------------------------------------------
    # Profile builder
    # ------------------------------------------------------------------

    def _build_profile(
        self,
        profile: ModelCapabilityProfile,
        role: str,
        quality: str,
        context_len: int,
        alloc: BackendAllocation,
        score: ModelScore,
        decision: GovernorDecision,
        resolved_via: str = "explicit",
    ) -> ExecutionProfile:
        """Build the final ExecutionProfile from all computed data."""
        role_req = ROLE_REQUIREMENTS.get(role, RoleRequirement(role))

        # num_predict: honour role budget
        num_predict = role_req.max_output_tokens

        # Temperature: from role + quality adjustment
        temp = role_req.default_temp
        if quality == "high":
            temp = max(0.0, temp - 0.05)  # Slightly more deterministic for high quality
        elif quality == "low":
            temp = min(1.0, temp + 0.10)  # Slightly more creative for fast path

        # keep_alive: GPU/HYBRID stay hot, CPU can unload
        keep_alive = "-1" if alloc.backend in ("GPU", "HYBRID") else "10m"

        return ExecutionProfile(
            model_name=profile.model_name,
            role_name=role,
            backend=alloc.backend,
            memory_layout=alloc.memory_layout,
            num_gpu_layers=alloc.num_gpu_layers,
            num_predict=num_predict,
            num_ctx=context_len,
            num_thread=20,
            temperature=temp,
            top_p=0.9,
            repeat_penalty=1.1,
            use_mmap=True,
            keep_alive=keep_alive,
            resolved_via=resolved_via,
            decision=decision,
            capability_profile=profile,
        )

    # ------------------------------------------------------------------
    # Policy loading
    # ------------------------------------------------------------------

    def _load_policy(self, policy_path: Optional[str]) -> dict:
        """Load optional model_role_policy.yaml for role weight overrides."""
        paths_to_try = []
        if policy_path:
            paths_to_try.append(policy_path)

        # Standard locations
        import os
        root = os.getenv("JKAI_ROOT", "")
        if root:
            paths_to_try.append(os.path.join(root, "intelligence", "model_role_policy.yaml"))
        paths_to_try.append("/intelligence/model_role_policy.yaml")

        for path in paths_to_try:
            if os.path.exists(path):
                try:
                    import yaml  # type: ignore
                    with open(path, "r", encoding="utf-8") as f:
                        data = yaml.safe_load(f) or {}
                    logger.info(f"[AMG-GOVERNOR] Loaded role policy from {path}")
                    return data
                except ImportError:
                    logger.debug("[AMG-GOVERNOR] PyYAML not available — policy file skipped")
                except Exception as e:
                    logger.warning(f"[AMG-GOVERNOR] Policy load error: {e}")
        return {}

    # ------------------------------------------------------------------
    # Emergency fallback (last resort — registry empty or all failed)
    # ------------------------------------------------------------------

    @staticmethod
    def _emergency_fallback(role: str, quality: str) -> ExecutionProfile:
        """
        Absolute last resort. Returns a minimal viable profile.
        Should never happen in production — indicates registry was never populated.
        """
        logger.critical(
            f"[AMG-GOVERNOR] EMERGENCY FALLBACK activated for role={role}. "
            "ModelRegistry may be empty. Check Ollama connectivity."
        )
        decision = GovernorDecision(
            role=role, quality=quality, requested_model="auto",
            capability_requirements=[],
            selected_model="EMERGENCY_FALLBACK",
            backend="CPU", gpu_layers=0,
            final_score=0.0,
            candidates_evaluated=[], rejected_candidates=[],
            rejection_reasons={},
            graceful_failure=True,
            reasons=["Registry empty — emergency fallback activated"],
        )
        return ExecutionProfile(
            model_name="",
            role_name=role,
            backend="CPU",
            memory_layout="RAM_ONLY",
            num_gpu_layers=0,
            resolved_via="emergency_fallback",
            decision=decision,
        )
