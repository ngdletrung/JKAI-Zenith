"""
🏛️ ADAPTIVE MODEL GOVERNOR (AMG) v2 — DATA CONTRACTS
File: core/governor/model_capabilities.py

Role: Shared type system for the entire AMG pipeline.
      Consumed by ModelRegistry, ModelInspector, PortfolioGovernor, ExecutionPolicy.

AMG Constitutional Principle:
    No model name, model size, or model family string may appear in any AMG
    decision logic. All decisions derive from:
        CapabilityEvidence + ModelMemoryProfile + HardwareState + RoleRequirement + QualityTarget.
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, Set, List
from enum import Enum, auto
import math


# ---------------------------------------------------------------------------
# 1. Model Capability Taxonomy
# ---------------------------------------------------------------------------

class ModelClass(Enum):
    """
    Intrinsic capability classification of a model (set by ModelInspector).
    A model can hold multiple classes simultaneously.

    IMPORTANT TAXONOMY:
        ModelClass = what a model CAN DO (capability)
        RoleRequirement = what a task NEEDS (task requirement)

        'planning' is a task/role requirement (→ RoleRequirement)
        'reasoning' is a model capability     (→ ModelClass.REASONING)
        Do NOT conflate these two layers.

    Example:
        qwen3.5:4b     → {GENERAL, REASONING, TOOL_USE}
        moondream      → {VISION}
        nomic-embed    → {EMBEDDING}
        qwen3-30b-a3b  → {GENERAL, REASONING, MOE, TOOL_USE}
        coder:3b       → {CODING, TOOL_USE}
    """
    GENERAL   = auto()   # General-purpose chat / instruction following
    REASONING = auto()   # CoT / chain-of-thought / thinking-budget models
    CODING    = auto()   # Code generation / debugging specialists
    VISION    = auto()   # Multi-modal: image + text understanding
    EMBEDDING = auto()   # Embedding-only (no generative output)
    MOE       = auto()   # Mixture-of-Experts: large total params, sparse activation
    TOOL_USE  = auto()   # Function/tool calling capability (structured JSON output)


class ModelPool(Enum):
    """
    Runtime pool label — NOT a fixed property of the model.
    Computed by PortfolioGovernor based on:
        ModelClass set + quality target + current HardwareState.

    Same model may be in different pools at different times:
        qwen3.5:4b + quality=LOW   → FAST
        qwen3.5:4b + quality=HIGH  → REASONING (if better options unavailable)
    """
    FAST      = "fast"       # Low-latency, typically GPU, small active footprint
    REASONING = "reasoning"  # Mid-tier quality, reasoning-capable
    HEAVY     = "heavy"      # High quality, large models, RAM/Hybrid
    VISION    = "vision"     # Vision-capable models
    EMBEDDING = "embedding"  # Embedding-only models


# ---------------------------------------------------------------------------
# 1b. CapabilityScore — Evidence-Governed Capability Measurement (North Star v3.0)
# ---------------------------------------------------------------------------

from datetime import datetime

_UNKNOWN_SENTINEL = object()  # Sentinel to distinguish "not yet measured" from 0.0


@dataclass
class CapabilityScore:
    """
    A single dimension of a model's measured capability.

    Constitutional Principle (North Star v3.0):
        If not yet measured → value = None, confidence = 0.0, source = "UNKNOWN".
        We NEVER infer capability from parameter count or model name.
        This aligns with EEC-8: Epistemic Humility.

    Examples:
        # Benchmarked model:
        coding_strength = CapabilityScore(
            value=0.81, confidence=0.92,
            source="benchmark:P53-CODE-v1",
            measured_at=datetime.utcnow(),
            benchmark_version="P53-CODE-v1",
        )

        # Not yet benchmarked:
        reasoning_strength = CapabilityScore.unknown()
    """
    value: Optional[float]           # None = UNKNOWN (not yet measured)
    confidence: float                 # 0.0 = no evidence, 1.0 = high confidence
    source: str                       # "UNKNOWN" | "benchmark:P53-CODE-v1" | "declared"
    measured_at: Optional[datetime]   # None = never measured
    benchmark_version: str            # "" if UNKNOWN

    @classmethod
    def unknown(cls) -> "CapabilityScore":
        """Create an UNKNOWN capability score — not yet measured."""
        return cls(
            value=None,
            confidence=0.0,
            source="UNKNOWN",
            measured_at=None,
            benchmark_version="",
        )

    @classmethod
    def declared(cls, value: float, source: str = "declared") -> "CapabilityScore":
        """
        Create a capability score from declared/intrinsic metadata (e.g., context window).
        confidence = 0.70 (declared but not empirically measured).
        """
        return cls(
            value=value,
            confidence=0.70,
            source=source,
            measured_at=None,
            benchmark_version="",
        )

    @classmethod
    def benchmarked(cls, value: float, confidence: float,
                    benchmark_id: str, measured_at: Optional[datetime] = None) -> "CapabilityScore":
        """Create a capability score from an empirical benchmark run."""
        return cls(
            value=value,
            confidence=confidence,
            source=f"benchmark:{benchmark_id}",
            measured_at=measured_at or datetime.utcnow(),
            benchmark_version=benchmark_id,
        )

    @property
    def is_known(self) -> bool:
        """True if we have at least some measured evidence."""
        return self.value is not None and self.confidence > 0.0

    @property
    def effective_value(self) -> float:
        """
        Return value for scoring, applying confidence weight.
        Returns 0.5 (neutral) if UNKNOWN — does not penalise or reward.
        Caller should check is_known to decide if this is real evidence.
        """
        if self.value is None:
            return 0.5  # Neutral — no evidence either way
        return self.value * self.confidence + 0.5 * (1.0 - self.confidence)

    def __repr__(self) -> str:
        if self.value is None:
            return "CapabilityScore(UNKNOWN)"
        return f"CapabilityScore(v={self.value:.3f}, conf={self.confidence:.2f}, src={self.source!r})"


@dataclass
class QuantitativeCapabilityProfile:
    """
    5-dimensional evidence-governed capability profile for a model.
    All scores are CapabilityScore instances (value + confidence + provenance).

    Constitutional Principle (North Star v3.0):
        NO dimension is inferred from parameter count or model family name.
        All scores start as UNKNOWN and are populated by:
          1. Empirical benchmark runs (Phase 5.4)
          2. Explicit operator declarations
          3. External measurement imports

    Operational fields (vram_cost_gb, latency_ms_per_token) are measured or
    declared from hardware profiling — NOT estimated from param count.
    """
    # Measured capability dimensions (all start as UNKNOWN)
    reasoning_strength: CapabilityScore = field(
        default_factory=CapabilityScore.unknown)
    coding_strength: CapabilityScore = field(
        default_factory=CapabilityScore.unknown)
    tool_use_strength: CapabilityScore = field(
        default_factory=CapabilityScore.unknown)
    instruction_following: CapabilityScore = field(
        default_factory=CapabilityScore.unknown)
    reliability: CapabilityScore = field(
        default_factory=CapabilityScore.unknown)

    # Operational cost (declared or measured from hardware profiling)
    vram_cost_gb: float = 0.0                  # 0.0 = not yet profiled
    latency_ms_per_token: float = 0.0          # 0.0 = not yet profiled
    throughput_tokens_per_sec: float = 0.0     # 0.0 = not yet profiled
    context_window_tokens: int = 8192          # from model metadata

    @property
    def any_dimension_unknown(self) -> bool:
        dims = [self.reasoning_strength, self.coding_strength,
                self.tool_use_strength, self.instruction_following, self.reliability]
        return any(not d.is_known for d in dims)

    def task_complexity_match(
        self,
        task_complexity: float,
        task_weights: Optional[Dict[str, float]] = None,
    ) -> float:
        """
        Compute how well this capability profile matches required task complexity.
        task_complexity in [0.0, 1.0]: 0 = trivial, 1 = expert-level multi-step.

        Uses task_weights to weight dimensions per-mission type.
        When a dimension is UNKNOWN, it contributes a neutral score (0.5) so
        UNKNOWN models are neither rewarded nor penalised on that dimension.

        Args:
            task_complexity: 0.0–1.0 required difficulty.
            task_weights:    Dict of dimension → weight, e.g.
                             {"reasoning": 0.35, "coding": 0.30, "tool_use": 0.15,
                              "reliability": 0.10, "instruction_following": 0.10}
                             Defaults to equal weights if not provided.

        Returns:
            0.0–1.0 match score (higher = better fit for this task complexity).
        """
        weights = task_weights or {
            "reasoning": 0.25, "coding": 0.25, "tool_use": 0.20,
            "instruction_following": 0.15, "reliability": 0.15,
        }

        dims = {
            "reasoning":             self.reasoning_strength,
            "coding":                self.coding_strength,
            "tool_use":              self.tool_use_strength,
            "instruction_following": self.instruction_following,
            "reliability":           self.reliability,
        }

        total_weight = sum(weights.values()) or 1.0
        weighted_fit = 0.0

        for dim_name, score in dims.items():
            w = weights.get(dim_name, 0.0)
            effective = score.effective_value  # 0.5 if UNKNOWN
            # Required level scales with task_complexity
            required = task_complexity
            shortfall = max(0.0, required - effective)
            fit = (1.0 - shortfall) * w
            weighted_fit += fit

        return round(max(0.0, min(1.0, weighted_fit / total_weight)), 4)


# Backward-compat alias (deprecated — use QuantitativeCapabilityProfile directly)
QuantitativeCapabilityVector = QuantitativeCapabilityProfile


# ---------------------------------------------------------------------------
# 2. Capability Evidence (confidence-scored, multi-source)
# ---------------------------------------------------------------------------

@dataclass
class CapabilityEvidence:
    """
    A single piece of evidence for a model capability.
    Multiple evidences are accumulated; final confidence is computed by ModelInspector.
    """
    capability: ModelClass
    confidence: float            # 0.0–1.0
    sources: List[str]           # e.g. ["capabilities_api", "template", "model_tags"]
    detection_method: str        # "metadata" | "heuristic"
    raw_key: str = ""            # The actual Ollama key that produced this evidence

    # Confidence thresholds for asserting a capability class
    ASSERT_THRESHOLD: float = field(default=0.75, init=False, repr=False)

    @property
    def is_asserted(self) -> bool:
        """True if confidence is high enough to assert the capability."""
        return self.confidence >= 0.75

    def __post_init__(self):
        object.__setattr__(self, 'ASSERT_THRESHOLD', 0.75)


# ---------------------------------------------------------------------------
# 3. Model Memory Profile — separates compute from storage
# ---------------------------------------------------------------------------

@dataclass
class ModelMemoryProfile:
    """
    Precise memory model for a language model.

    CRITICAL DISTINCTION for MoE models:
        - active_parameters_b = params activated PER TOKEN (compute cost)
        - weight_file_size_gb  = ALL weights must be resident somewhere (memory cost)

    Example — Qwen3-30B-A3B UD-Q4_K_XL:
        total_parameters_b       = 30.0
        active_parameters_b      = 3.0      ← compute (per token)
        weight_file_size_gb      = 17.0     ← ALL weights need storage
        estimated_full_weight_mb = 17408    ← if entire model on GPU
        estimated_gpu_resident_mb ≈ 5500    ← after 32-layer offload to GPU
        estimated_ram_resident_mb ≈ 11900   ← remaining in 64GB RAM
    """
    # Physical footprint
    weight_file_size_gb: float              # Actual file/download size (source of truth)
    quantization: str                       # "Q4_K_M", "UD-Q4_K_XL", "QAT", "FP16", etc.
    bytes_per_param: float                  # Derived: Q4≈0.5, Q8≈1.0, FP16≈2.0

    # Structural parameters
    total_parameters_b: float
    active_parameters_b: float             # = total for dense; << total for MoE
    num_layers: int = 32                   # Transformer layer count
    is_moe: bool = False

    # Computed memory estimates (populated by ResourceGovernor)
    estimated_full_weight_mb: float = 0.0       # All weights on GPU (may exceed VRAM)
    estimated_gpu_resident_mb: float = 0.0      # Weights actually on GPU after layer split
    estimated_ram_resident_mb: float = 0.0      # Weights offloaded to RAM

    # KV Cache scaling (per 1k context)
    kv_cache_mb_per_1k_ctx: float = 256.0       # ~256MB per 1k ctx (typical Q4 models)

    # Provenance
    detection_method: str = "heuristic"         # "api_show" | "file_size" | "heuristic"

    def kv_cache_for_context(self, context_len: int) -> float:
        """Estimated KV cache VRAM for a given context length (in MB)."""
        return (context_len / 1024.0) * self.kv_cache_mb_per_1k_ctx


# ---------------------------------------------------------------------------
# 4. Model Capability Profile — atomic unit of the Model Registry
# ---------------------------------------------------------------------------

@dataclass
class ModelCapabilityProfile:
    """
    Represents the inspected DNA of a language model.
    Populated by ModelInspector from Ollama /api/show metadata.

    NOTE: Does NOT contain role_scores (those are computed at decision time
    by PortfolioGovernor as ModelScore, because scores depend on runtime context).
    """
    model_name: str

    # Structural metadata (from /api/show)
    architecture: str = "transformer"
    family: str = ""                     # e.g. "qwen", "gemma", "llama", "phi"
    context_length_max: int = 8192

    # Memory profile (populated by ResourceGovernor using ModelMemoryProfile)
    memory: Optional[ModelMemoryProfile] = field(default=None, repr=False)

    # Capability evidences (from ModelInspector, confidence-scored)
    capability_evidences: List[CapabilityEvidence] = field(default_factory=list)

    # Final asserted capability classes (confidence >= 0.75)
    model_classes: Set[ModelClass] = field(default_factory=lambda: {ModelClass.GENERAL})

    # Convenience capability flags (derived from model_classes)
    has_vision: bool = False
    has_tool_calling: bool = True        # Default True; set False if metadata says otherwise
    is_embedding_only: bool = False

    # Registry metadata
    last_inspected_at: float = 0.0      # Unix timestamp
    ollama_digest: str = ""             # Model digest from /api/tags for cache invalidation

    # Classification confidence — how well we know this model
    # LOW (< 0.50): minimal metadata, mostly heuristics → treat as UNKNOWN
    # MEDIUM (0.50–0.80): partial metadata
    # HIGH (> 0.80): full /api/show metadata with confident capability evidence
    assessment_confidence: float = 0.0

    # ── North Star v3.0: Quantitative Capability Profile (evidence-governed) ─
    # Populated by ModelInspector from empirical benchmark data.
    # NEVER auto-estimated from parameter count — starts as UNKNOWN.
    # Use quant_vector property to access (logs warning if UNKNOWN).
    _quant_vector: Optional[QuantitativeCapabilityProfile] = field(
        default=None, repr=False, compare=False
    )

    @property
    def is_unknown(self) -> bool:
        """True when we have very little confidence in the capability classification."""
        return self.assessment_confidence < 0.40

    @property
    def has_class(self, cls: ModelClass) -> bool:
        return cls in self.model_classes

    @property
    def is_reasoning_model(self) -> bool:
        return ModelClass.REASONING in self.model_classes

    @property
    def is_moe(self) -> bool:
        return ModelClass.MOE in self.model_classes

    @property
    def parameters_active_b(self) -> float:
        """Shortcut to active parameters for scheduling decisions."""
        return self.memory.active_parameters_b if self.memory else 3.0

    @property
    def estimated_size_gb(self) -> float:
        """Shortcut to file size."""
        return self.memory.weight_file_size_gb if self.memory else 2.5

    @property
    def quant_vector(self) -> QuantitativeCapabilityProfile:
        """
        Return the QuantitativeCapabilityProfile (evidence-governed capability scores).

        Constitutional Principle: NEVER fall back to param-count estimation.
        If _quant_vector is None, return a profile with all dimensions UNKNOWN.
        This ensures epistemic humility: we do not pretend to know what we haven't measured.
        """
        if self._quant_vector is not None:
            return self._quant_vector
        # Return UNKNOWN profile (not estimated from params)
        import logging
        logging.getLogger("jkai.governor.model_capabilities").warning(
            "[AMG] quant_vector requested for '%s' but no benchmark data available. "
            "All capability scores = UNKNOWN. Run Phase 5.4 benchmark to populate.",
            self.model_name,
        )
        unknown = QuantitativeCapabilityProfile(
            context_window_tokens=self.context_length_max,
        )
        return unknown

    @property
    def context_window_tokens(self) -> int:
        """Usable context window — from quant_vector (which may override context_length_max)."""
        if self._quant_vector is not None:
            return self._quant_vector.context_window_tokens
        return self.context_length_max

    def has_any_class(self, *classes: ModelClass) -> bool:
        return bool(self.model_classes.intersection(classes))

    def __repr__(self) -> str:
        classes = ", ".join(c.name for c in self.model_classes)
        size = f"{self.estimated_size_gb:.1f}GB"
        active = f"{self.parameters_active_b:.1f}B active"
        ctx = f"{self.context_window_tokens // 1024}k ctx"
        return f"ModelCapabilityProfile({self.model_name!r} | {active} | {size} | {ctx} | [{classes}])"


# ---------------------------------------------------------------------------
# 5. Role Requirements
# ---------------------------------------------------------------------------

# Role scoring weights: defines which ModelClass contributes how much to each role
# These are used by PortfolioGovernor to compute ModelScore.capability_score
ROLE_CLASS_WEIGHTS: Dict[str, Dict[ModelClass, float]] = {
    "RECEPTIONIST":   {ModelClass.GENERAL: 3.0, ModelClass.REASONING: 1.0},
    "CHAT":           {ModelClass.GENERAL: 3.0, ModelClass.REASONING: 1.0},
    "SUMMARIZER":     {ModelClass.GENERAL: 3.0},
    "CRITIC":         {ModelClass.GENERAL: 2.0, ModelClass.REASONING: 3.0},
    "PLANNER":        {ModelClass.REASONING: 4.0, ModelClass.GENERAL: 1.0, ModelClass.MOE: 2.0},
    "EXECUTOR":       {ModelClass.CODING: 4.0, ModelClass.GENERAL: 1.0},
    "EXECUTOR_ALPHA": {ModelClass.CODING: 4.0, ModelClass.GENERAL: 1.0},
    "EXECUTOR_BETA":  {ModelClass.CODING: 4.0, ModelClass.GENERAL: 1.0},
    "DEEP_REASONER":  {ModelClass.REASONING: 5.0, ModelClass.MOE: 3.0, ModelClass.GENERAL: 1.0},
    "VISION":         {ModelClass.VISION: 5.0},
    "EMBEDDER":       {ModelClass.EMBEDDING: 5.0},
}

# Minimum capability score (0.0–1.0) a fallback model must meet for each role
ROLE_MINIMUM_CAPABILITY: Dict[str, float] = {
    "RECEPTIONIST":   0.20,
    "CHAT":           0.20,
    "SUMMARIZER":     0.20,
    "CRITIC":         0.40,
    "PLANNER":        0.55,
    "EXECUTOR":       0.50,
    "EXECUTOR_ALPHA": 0.50,
    "EXECUTOR_BETA":  0.50,
    "DEEP_REASONER":  0.70,
    "VISION":         0.90,  # Must have VISION class — no degradation
    "EMBEDDER":       0.90,  # Must have EMBEDDING class — no degradation
}


@dataclass
class RoleRequirement:
    """Execution characteristics required for a JKAI role."""
    role_name: str
    reasoning_budget: str = "LOW"           # LOW | MEDIUM | HIGH
    max_output_tokens: int = 512
    default_temp: float = 0.2
    requires_tools: bool = False
    minimum_capability_score: float = 0.30  # Minimum score for fallback acceptance


# Default role requirement catalogue
ROLE_REQUIREMENTS: Dict[str, RoleRequirement] = {
    "RECEPTIONIST":   RoleRequirement("RECEPTIONIST",   "LOW",    384, 0.20, minimum_capability_score=0.20),
    "CHAT":           RoleRequirement("CHAT",           "LOW",    512, 0.40, minimum_capability_score=0.20),
    "SUMMARIZER":     RoleRequirement("SUMMARIZER",     "LOW",    512, 0.10, minimum_capability_score=0.20),
    "CRITIC":         RoleRequirement("CRITIC",         "MEDIUM", 768, 0.10, minimum_capability_score=0.40),
    "PLANNER":        RoleRequirement("PLANNER",        "MEDIUM", 1024, 0.05, requires_tools=True, minimum_capability_score=0.55),
    "EXECUTOR":       RoleRequirement("EXECUTOR",       "MEDIUM", 1024, 0.00, requires_tools=True, minimum_capability_score=0.50),
    "EXECUTOR_ALPHA": RoleRequirement("EXECUTOR_ALPHA", "MEDIUM", 1024, 0.00, requires_tools=True, minimum_capability_score=0.50),
    "EXECUTOR_BETA":  RoleRequirement("EXECUTOR_BETA",  "MEDIUM", 1024, 0.00, requires_tools=True, minimum_capability_score=0.50),
    "DEEP_REASONER":  RoleRequirement("DEEP_REASONER",  "HIGH",   4096, 0.25, minimum_capability_score=0.70),
    "VISION":         RoleRequirement("VISION",         "LOW",    512, 0.10, minimum_capability_score=0.90),
    "EMBEDDER":       RoleRequirement("EMBEDDER",       "LOW",    0,   0.00, minimum_capability_score=0.90),
}


# ---------------------------------------------------------------------------
# 6. Decision-Time Scoring and Tracing
# ---------------------------------------------------------------------------

@dataclass
class ModelScore:
    """
    Fitness score for a (model, role, quality, hardware) combination.
    Computed at decision time by PortfolioGovernor — NOT cached in ModelCapabilityProfile.
    """
    model_name: str
    role: str
    quality: str                  # "low" | "medium" | "high"

    capability_score: float       # 0.0–1.0: how well model classes match role weights
    resource_score: float         # 0.0–1.0: fit within current VRAM/RAM
    quality_score: float          # 0.0–1.0: model quality tier (larger = higher)
    latency_score: float          # 0.0–1.0: smaller/faster = higher (favoured for LOW quality)

    final_score: float            # Composite weighted score
    meets_minimum: bool = True    # False if capability_score < ROLE_MINIMUM_CAPABILITY

    reasons: List[str] = field(default_factory=list)

    def __lt__(self, other: "ModelScore") -> bool:
        return self.final_score < other.final_score


@dataclass
class GovernorDecision:
    """
    Full decision trace emitted by PortfolioGovernor.
    Attached to ExecutionProfile for observability.
    """
    role: str
    quality: str
    requested_model: str                      # "auto" or explicit name
    capability_requirements: List[str]        # From rule_hardware.md auto syntax

    selected_model: str
    backend: str                              # "GPU" | "HYBRID" | "CPU"
    gpu_layers: int

    final_score: float
    candidates_evaluated: List[ModelScore]   # All models considered
    rejected_candidates: List[str]           # Names of rejected candidates
    rejection_reasons: Dict[str, str]        # model_name → reason string

    fallback_applied: bool = False
    quality_degraded: bool = False           # e.g. HIGH request → MEDIUM outcome
    graceful_failure: bool = False           # True if no model met minimum_capability

    reasons: List[str] = field(default_factory=list)
    resolved_via: str = "explicit"           # "explicit" | "auto" | "fallback" | "emergency_fallback"

    def log_summary(self) -> str:
        lines = [
            f"[AMG] {self.role}/{self.quality.upper()} | requested='{self.requested_model}'",
        ]
        if self.candidates_evaluated:
            lines.append("  Candidates:")
            for s in sorted(self.candidates_evaluated, key=lambda x: x.final_score, reverse=True):
                flag = "→ SELECTED" if s.model_name == self.selected_model else \
                       f"→ REJECTED({self.rejection_reasons.get(s.model_name, '?')})"
                lines.append(f"    {s.model_name:<40} score={s.final_score:.2f}  {flag}")
        lines.append(f"  Decision: {self.selected_model} | {self.backend} | {self.gpu_layers} layers")
        if self.quality_degraded:
            lines.append(f"  ⚠ Quality degraded: requested={self.quality}")
        if self.graceful_failure:
            lines.append("  ✖ Graceful failure: no model met minimum capability threshold")
        return "\n".join(lines)


# ---------------------------------------------------------------------------
# 7. Execution Profile — model-agnostic contract consumed by Engine
# ---------------------------------------------------------------------------

@dataclass
class ExecutionProfile:
    """
    The fully derived, model-agnostic execution contract.
    Engine must NEVER inspect model_name to make branching decisions.
    Everything is pre-computed here by the AMG pipeline.
    """
    model_name: str
    role_name: str

    # Hardware routing
    # backend   = COMPUTE path (which processor handles inference)
    # memory_layout = MEMORY domain (where model weights reside)
    # These are SEPARATE concepts — a HYBRID backend has VRAM+RAM memory layout.
    backend: str = "GPU"                 # "GPU" | "HYBRID" | "CPU"
    memory_layout: str = "VRAM_ONLY"     # "VRAM_ONLY" | "VRAM_RAM_SPLIT" | "RAM_ONLY"
    num_gpu_layers: int = 32

    # Generation parameters
    num_predict: int = 512
    num_ctx: int = 4096
    num_thread: int = 20
    temperature: float = 0.2
    top_p: float = 0.9
    repeat_penalty: float = 1.1
    use_mmap: bool = True
    keep_alive: str = "-1"

    # Raw overrides from rule_hardware.md (applied last, highest precedence)
    raw_options: Dict[str, Any] = field(default_factory=dict)

    # Provenance (for debugging and observability)
    resolved_via: str = "explicit"           # "explicit" | "auto" | "fallback"
    decision: Optional[GovernorDecision] = field(default=None, compare=False, repr=False)
    capability_profile: Optional[ModelCapabilityProfile] = field(default=None, compare=False, repr=False)

    def to_ollama_options(self) -> Dict[str, Any]:
        """Serialize to Ollama API options dict."""
        opts: Dict[str, Any] = {
            "num_gpu":      self.num_gpu_layers,
            "num_predict":  self.num_predict,
            "num_ctx":      self.num_ctx,
            "temperature":  self.temperature,
            "top_p":        self.top_p,
            "repeat_penalty": self.repeat_penalty,
            "use_mmap":     self.use_mmap,
        }
        if self.num_thread:
            opts["num_thread"] = self.num_thread
        # Raw overrides have highest precedence
        opts.update(self.raw_options)
        return {k: v for k, v in opts.items() if v is not None}

    def to_ollama_payload(
        self,
        messages: Optional[List[Dict[str, Any]]] = None,
        stream: bool = False,
    ) -> Dict[str, Any]:
        """
        Serialize ExecutionProfile to complete Ollama /api/chat payload.
        Consumed by NeuralRuntime and Engine.
        """
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "options": self.to_ollama_options(),
            "stream": stream,
            "keep_alive": self.keep_alive,
        }
        if messages is not None:
            payload["messages"] = messages
        return payload

    def to_resource_request(self):
        """
        Convert ExecutionProfile to ResourceRequest for HardwareScheduler.
        M4 resource enforcement contract.
        """
        from core.utils.models import ResourceRequest, BackendType

        gpu_mb = 0.0
        ram_mb = 0.0

        if self.capability_profile and self.capability_profile.memory_profile:
            mem = self.capability_profile.memory_profile
            gpu_mb = float(getattr(mem, "estimated_gpu_resident_mb", 0.0))
            ram_mb = float(getattr(mem, "estimated_ram_resident_mb", 0.0))
        elif self.backend == "GPU":
            gpu_mb = 4000.0
        elif self.backend == "HYBRID":
            gpu_mb = 3500.0
            ram_mb = 8000.0
        else:
            ram_mb = 4000.0

        backend_enum = BackendType.CPU
        try:
            backend_enum = BackendType(self.backend.upper())
        except ValueError:
            pass

        return ResourceRequest(
            backend=backend_enum,
            gpu_memory_mb=gpu_mb,
            ram_memory_mb=ram_mb,
            gpu_layers=self.num_gpu_layers,
            concurrency=1,
        )

