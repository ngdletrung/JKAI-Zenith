"""
🏛️ ADAPTIVE MODEL GOVERNOR (AMG) v2 — MODEL INSPECTOR
File: core/governor/model_inspector.py

Purpose:
    Inspects a model's intrinsic capabilities from Ollama /api/show metadata.
    Produces ModelCapabilityProfile with confidence-scored CapabilityEvidence.

AMG Constitutional Principle:
    NO model name, family name, or size string may be used as
    primary evidence for capability classification.

    Names MAY be used as low-confidence heuristic fallbacks ONLY when
    /api/show metadata is insufficient, and must be tagged:
        detection_method="heuristic", confidence < 0.60

Evidence Confidence Thresholds:
    >= 0.75  → ASSERT the ModelClass (add to model_classes)
    0.50–0.74 → RECORD as evidence only (informational)
    < 0.50   → DISCARD (noise)
"""

from __future__ import annotations
import logging
import math
import re
import time
from typing import Dict, Any, List, Optional, Set, Tuple

from core.governor.model_capabilities import (
    ModelCapabilityProfile, ModelClass, ModelMemoryProfile,
    CapabilityEvidence,
)
from core.runtime.base_adapter import RuntimeModelInfo

logger = logging.getLogger("AMG_ModelInspector")

# Confidence threshold to assert a ModelClass
ASSERT_THRESHOLD = 0.75
# Confidence floor — evidence below this is discarded entirely
EVIDENCE_FLOOR = 0.50

# Known quantization → bytes per parameter mapping
QUANT_BYTES_PER_PARAM: Dict[str, float] = {
    "fp16":       2.00,
    "bf16":       2.00,
    "fp32":       4.00,
    "q8_0":       1.00,
    "q6_k":       0.75,
    "q5_k_m":     0.625,
    "q5_k_s":     0.625,
    "q4_k_m":     0.50,
    "q4_k_s":     0.50,
    "q4_k_xl":    0.50,   # UD-Q4_K_XL
    "ud-q4_k_xl": 0.50,
    "q4_0":       0.50,
    "q3_k_m":     0.375,
    "q2_k":       0.25,
    "qat":        0.50,   # Quantization-Aware Training (conservative estimate)
}


def _bytes_per_param(quantization: str) -> float:
    """Map a quantization string to bytes-per-parameter."""
    q = quantization.lower().strip()
    # Direct match
    if q in QUANT_BYTES_PER_PARAM:
        return QUANT_BYTES_PER_PARAM[q]
    # Partial match — scan for longest key
    best = 0.50  # Q4 default
    for key, val in QUANT_BYTES_PER_PARAM.items():
        if key in q:
            best = val
            break
    return best


class ModelInspector:
    """
    Stateless capability classifier.
    All logic reads from RuntimeModelInfo (from Ollama /api/show).
    No singleton — use the class methods directly.
    """

    @classmethod
    def build_profile(
        cls,
        info: RuntimeModelInfo,
        existing_digest: str = "",
    ) -> ModelCapabilityProfile:
        """
        Build a complete ModelCapabilityProfile from Ollama /api/show data.

        Args:
            info: RuntimeModelInfo from OllamaAdapter.inspect_model()
            existing_digest: Previous digest to detect changes

        Returns:
            ModelCapabilityProfile with asserted model_classes and memory profile.
        """
        model_info: Dict[str, Any] = info.model_info or {}
        details: Dict[str, Any] = info.details or {}
        capabilities: List[str] = info.capabilities or []
        template: str = info.template or ""

        # 1. Extract structural metadata
        arch = cls._extract_architecture(model_info, details)
        family = cls._extract_family(model_info, details)
        ctx_len = cls._extract_context_length(model_info, arch)
        num_layers = cls._extract_num_layers(model_info, arch)
        quantization = cls._extract_quantization(details, info.model_name)
        total_params_b = cls._extract_total_params(model_info)

        # 2. Collect capability evidence (no name-based primary detection)
        evidences: List[CapabilityEvidence] = []

        evidences.extend(cls._detect_moe(model_info, info.model_name))
        active_params_b = cls._get_active_params(model_info, total_params_b,
                                                  [e for e in evidences
                                                   if e.capability == ModelClass.MOE
                                                   and e.is_asserted])

        evidences.extend(cls._detect_reasoning(model_info, details, capabilities, template))
        evidences.extend(cls._detect_vision(model_info, details, capabilities))
        evidences.extend(cls._detect_embedding(model_info, details, capabilities, template))
        evidences.extend(cls._detect_coding(model_info, details, template))
        evidences.extend(cls._detect_tool_use(model_info, details, capabilities, template))

        # 3. Assert model_classes from high-confidence evidences
        model_classes: Set[ModelClass] = set()
        for ev in evidences:
            if ev.is_asserted:
                model_classes.add(ev.capability)

        # If EMBEDDING asserted → model is embedding-only, remove GENERAL
        # Otherwise always ensure GENERAL as baseline
        is_embedding = ModelClass.EMBEDDING in model_classes
        if not is_embedding:
            model_classes.add(ModelClass.GENERAL)

        # 4. Compute overall assessment confidence
        # (how much we trust the capability classification)
        assessment_conf = cls._compute_assessment_confidence(evidences, model_info, capabilities)

        # 5. Build memory profile
        bpp = _bytes_per_param(quantization)
        memory = cls._build_memory_profile(
            total_params_b=total_params_b,
            active_params_b=active_params_b,
            file_size_gb=info.size_gb,
            quantization=quantization,
            bpp=bpp,
            num_layers=num_layers,
            is_moe=(ModelClass.MOE in model_classes),
        )

        # 6. Derive convenience flags
        has_vision = ModelClass.VISION in model_classes
        is_embedding = ModelClass.EMBEDDING in model_classes
        has_tools = "tools" in capabilities or "functions" in capabilities

        profile = ModelCapabilityProfile(
            model_name=info.model_name,
            architecture=arch,
            family=family,
            context_length_max=ctx_len,
            memory=memory,
            capability_evidences=evidences,
            model_classes=model_classes,
            has_vision=has_vision,
            has_tool_calling=has_tools,
            is_embedding_only=is_embedding,
            assessment_confidence=assessment_conf,
            last_inspected_at=time.time(),
            ollama_digest=info.digest,
        )
        logger.info(
            f"[AMG-INSPECT] {info.model_name!r} → "
            f"classes=[{', '.join(c.name for c in model_classes)}] | "
            f"confidence={assessment_conf:.2f} | "
            f"active={active_params_b:.1f}B | total={total_params_b:.1f}B | "
            f"file={info.size_gb:.1f}GB | ctx={ctx_len}"
        )
        if profile.is_unknown:
            logger.warning(
                f"[AMG-INSPECT] {info.model_name!r}: LOW confidence ({assessment_conf:.2f}) — "
                "treating capabilities as UNKNOWN. Routing will use conservative defaults."
            )
        return profile

    # ------------------------------------------------------------------
    # Structural Extractors
    # ------------------------------------------------------------------

    @classmethod
    def _extract_architecture(cls, model_info: Dict, details: Dict) -> str:
        return (
            model_info.get("general.architecture")
            or details.get("family", "")
            or "transformer"
        ).lower()

    @classmethod
    def _extract_family(cls, model_info: Dict, details: Dict) -> str:
        return (
            details.get("family", "")
            or model_info.get("general.architecture", "")
        ).lower()

    @classmethod
    def _extract_context_length(cls, model_info: Dict, arch: str) -> int:
        # Try arch-specific key first (e.g. "qwen3.context_length")
        for key in [
            f"{arch}.context_length",
            "llama.context_length",
            "general.context_length",
        ]:
            val = model_info.get(key)
            if isinstance(val, (int, float)) and val > 0:
                return int(val)
        return 8192

    @classmethod
    def _extract_num_layers(cls, model_info: Dict, arch: str) -> int:
        for key in [
            f"{arch}.block_count",
            "llama.block_count",
            "general.block_count",
        ]:
            val = model_info.get(key)
            if isinstance(val, int) and val > 0:
                return val
        return 32  # Sensible default for most 7B-class models

    @classmethod
    def _extract_quantization(cls, details: Dict, model_name: str) -> str:
        quant = details.get("quantization_level", "")
        if not quant:
            # Try to extract from model name as weak fallback
            name_lower = model_name.lower()
            for q in ["fp16", "bf16", "q8_0", "q6_k", "q5_k_m", "q5_k_s",
                       "q4_k_m", "q4_k_s", "q4_k_xl", "ud-q4_k_xl", "q4_0",
                       "q3_k_m", "q2_k", "qat"]:
                if q in name_lower:
                    return q.upper()
            return "Q4_K_M"  # Most common default
        return quant.upper()

    @classmethod
    def _extract_total_params(cls, model_info: Dict) -> float:
        # Direct parameter count
        for key in ["general.parameter_count", "llama.parameter_count"]:
            val = model_info.get(key)
            if isinstance(val, (int, float)) and val > 0:
                return round(val / 1e9, 2)
        return 7.0  # Safe default

    # ------------------------------------------------------------------
    # Capability Detectors — Metadata-Only, No Name Matching as Primary
    # ------------------------------------------------------------------

    @classmethod
    def _detect_moe(
        cls, model_info: Dict, model_name: str
    ) -> List[CapabilityEvidence]:
        """
        Detects Mixture-of-Experts architecture from /api/show metadata.
        Falls back to name heuristic at low confidence only.
        """
        evidences: List[CapabilityEvidence] = []

        # Primary: explicit expert keys from model_info
        expert_keys = {
            "num_experts":                   None,
            "num_experts_per_tok":           None,
            "expert_count":                  None,
            "experts_used":                  None,
        }
        # Check arch-prefixed variants (Ollama model_info uses arch prefix)
        found_keys = []
        for base_key in list(expert_keys.keys()):
            for prefix in ["", "qwen3.", "llama.", "mistral.", "deepseek.", "general."]:
                full_key = prefix + base_key
                if full_key in model_info:
                    found_keys.append(full_key)

        if found_keys:
            evidences.append(CapabilityEvidence(
                capability=ModelClass.MOE,
                confidence=0.95,
                sources=["model_info_expert_keys"],
                detection_method="metadata",
                raw_key=", ".join(found_keys),
            ))
            return evidences  # High confidence from metadata — no need for heuristics

        # Fallback: name heuristic (low confidence — NOT primary source)
        # Patterns like "30b-a3b", "35b-a3b" suggest MoE (active params notation)
        name_lower = model_name.lower()
        moe_pattern = re.search(r"\d+b[-_]a\d+b", name_lower)
        moe_keywords = ["moe", "-moe", "_moe"]
        has_name_hint = moe_pattern is not None or any(k in name_lower for k in moe_keywords)

        if has_name_hint:
            evidences.append(CapabilityEvidence(
                capability=ModelClass.MOE,
                confidence=0.60,   # Below ASSERT_THRESHOLD (0.75) → informational only
                sources=["name_heuristic"],
                detection_method="heuristic",
            ))
        return evidences

    @classmethod
    def _get_active_params(
        cls, model_info: Dict, total_params_b: float,
        moe_evidences: List[CapabilityEvidence]
    ) -> float:
        """
        Determine active (per-token) parameter count.
        For dense models: active == total.
        For MoE models: read from expert metadata or estimate.
        """
        if not moe_evidences:
            return total_params_b  # Dense model

        # Try to read active params from metadata
        for prefix in ["", "qwen3.", "llama.", "mistral.", "deepseek."]:
            used = model_info.get(f"{prefix}num_experts_per_tok") or \
                   model_info.get(f"{prefix}experts_used")
            count = model_info.get(f"{prefix}num_experts") or \
                    model_info.get(f"{prefix}expert_count")
            if used and count:
                # Each expert handles roughly total_params / num_experts parameters
                active = (total_params_b / count) * used
                return round(active, 2)

        # Fallback for MoE: assume ~10-15% of total params active per token
        # (This is typical for Qwen3/Mixtral-style MoE)
        return round(total_params_b * 0.12, 2)

    @classmethod
    def _detect_reasoning(
        cls, model_info: Dict, details: Dict,
        capabilities: List[str], template: str
    ) -> List[CapabilityEvidence]:
        """
        Multi-source reasoning detection with confidence accumulation.
        Single source < 0.75 → not asserted. Multiple sources → higher confidence.
        """
        evidence_components: List[Tuple[str, float]] = []

        # Source 1: Ollama capabilities list (most reliable — explicit API)
        if "thinking" in capabilities:
            evidence_components.append(("capabilities_api_thinking", 0.95))

        # Source 2: model_info tags
        tags = model_info.get("general.tags", [])
        if isinstance(tags, list):
            if "thinking" in tags or "reasoning" in tags:
                evidence_components.append(("model_info_tags", 0.85))

        # Source 3: Chat template contains thinking delimiters
        if template and ("<think>" in template or "<|thinking|>" in template
                         or "thinking_mode" in template):
            evidence_components.append(("chat_template_thinking_tag", 0.80))

        # Source 4: Model card / description metadata
        desc = str(model_info.get("general.description", "")).lower()
        if "chain-of-thought" in desc or "reasoning" in desc or "thinking" in desc:
            evidence_components.append(("model_description", 0.65))

        if not evidence_components:
            return []

        # Combine confidences: take max + small bonus per additional source
        max_conf = max(s[1] for s in evidence_components)
        bonus = 0.05 * (len(evidence_components) - 1)
        combined = min(1.0, max_conf + bonus)

        if combined < EVIDENCE_FLOOR:
            return []

        return [CapabilityEvidence(
            capability=ModelClass.REASONING,
            confidence=round(combined, 3),
            sources=[s[0] for s in evidence_components],
            detection_method="metadata" if any(
                "api" in s[0] or "model_info" in s[0] for s in evidence_components
            ) else "heuristic",
        )]

    @classmethod
    def _detect_vision(
        cls, model_info: Dict, details: Dict, capabilities: List[str]
    ) -> List[CapabilityEvidence]:
        evidence_components: List[Tuple[str, float]] = []

        # Source 1: Ollama capabilities list
        if "vision" in capabilities:
            evidence_components.append(("capabilities_api_vision", 0.95))

        # Source 2: Architecture is CLIP or includes vision encoder
        arch = model_info.get("general.architecture", "").lower()
        if arch in ("clip", "llava", "moondream") or "vision" in arch:
            evidence_components.append(("architecture_vision", 0.92))

        # Source 3: Vision-specific model_info keys
        vision_keys = [k for k in model_info if "vision" in k.lower()
                       or "clip" in k.lower() or "image" in k.lower()]
        if vision_keys:
            evidence_components.append(("model_info_vision_keys", 0.88))

        if not evidence_components:
            return []

        max_conf = max(s[1] for s in evidence_components)
        combined = min(1.0, max_conf + 0.03 * (len(evidence_components) - 1))
        if combined < EVIDENCE_FLOOR:
            return []

        return [CapabilityEvidence(
            capability=ModelClass.VISION,
            confidence=round(combined, 3),
            sources=[s[0] for s in evidence_components],
            detection_method="metadata",
        )]

    @classmethod
    def _detect_embedding(
        cls, model_info: Dict, details: Dict,
        capabilities: List[str], template: str
    ) -> List[CapabilityEvidence]:
        evidence_components: List[Tuple[str, float]] = []

        # Source 1: Ollama capabilities list
        if "embedding" in capabilities:
            evidence_components.append(("capabilities_api_embedding", 0.98))

        # Source 2: Pooling type present (embedding-specific architecture key)
        pooling_keys = [k for k in model_info if "pooling" in k.lower()]
        if pooling_keys:
            evidence_components.append(("model_info_pooling_key", 0.92))

        # Source 3: No chat template (embedding models lack generation template)
        if not template and "embedding" in capabilities:
            evidence_components.append(("no_chat_template", 0.70))

        # Source 4: Architecture is known embedding arch
        arch = model_info.get("general.architecture", "").lower()
        if arch in ("bert", "nomic-bert", "xlm-roberta", "sentence-transformers"):
            evidence_components.append(("embedding_architecture", 0.95))

        if not evidence_components:
            return []

        max_conf = max(s[1] for s in evidence_components)
        combined = min(1.0, max_conf + 0.02 * (len(evidence_components) - 1))
        if combined < EVIDENCE_FLOOR:
            return []

        return [CapabilityEvidence(
            capability=ModelClass.EMBEDDING,
            confidence=round(combined, 3),
            sources=[s[0] for s in evidence_components],
            detection_method="metadata",
        )]

    @classmethod
    def _detect_coding(
        cls, model_info: Dict, details: Dict, template: str
    ) -> List[CapabilityEvidence]:
        """
        Coding capability detection — conservative.
        Only metadata-based signals. Tokenizer vocabulary NOT used.
        """
        evidence_components: List[Tuple[str, float]] = []

        # Source 1: model_info general.tags contains "code"
        tags = model_info.get("general.tags", [])
        if isinstance(tags, list) and any("code" in str(t).lower() for t in tags):
            evidence_components.append(("model_info_code_tags", 0.88))

        # Source 2: details.families contains code-family identifier
        families = details.get("families", []) or []
        if isinstance(families, list) and any("code" in str(f).lower() for f in families):
            evidence_components.append(("details_families_code", 0.85))

        # Source 3: Chat template has code-oriented system prompt hints
        if template and ("code" in template.lower() or "programming" in template.lower()):
            evidence_components.append(("template_code_system", 0.70))

        if not evidence_components:
            return []

        max_conf = max(s[1] for s in evidence_components)
        combined = min(1.0, max_conf + 0.03 * (len(evidence_components) - 1))
        if combined < EVIDENCE_FLOOR:
            return []

        return [CapabilityEvidence(
            capability=ModelClass.CODING,
            confidence=round(combined, 3),
            sources=[s[0] for s in evidence_components],
            detection_method="metadata",
        )]

    @classmethod
    def _detect_tool_use(
        cls, model_info: Dict, details: Dict,
        capabilities: List[str], template: str
    ) -> List[CapabilityEvidence]:
        """
        Tool/function calling detection.
        TOOL_USE is a distinct ModelClass — 'planning' is a task requirement,
        but tool-use is a model structural capability (structured JSON output).
        """
        evidence_components: List[Tuple[str, float]] = []

        # Source 1: Ollama capabilities list (most reliable)
        if "tools" in capabilities:
            evidence_components.append(("capabilities_api_tools", 0.97))

        # Source 2: model_info tags
        tags = model_info.get("general.tags", [])
        if isinstance(tags, list) and any("tool" in str(t).lower() or "function" in str(t).lower()
                                          for t in tags):
            evidence_components.append(("model_info_tool_tags", 0.85))

        # Source 3: Chat template contains tool-call markers
        if template and any(marker in template for marker in
                            ["<tool_call>", "<function_call>", "tools", "tool_calls"]):
            evidence_components.append(("template_tool_markers", 0.80))

        if not evidence_components:
            return []

        max_conf = max(s[1] for s in evidence_components)
        combined = min(1.0, max_conf + 0.03 * (len(evidence_components) - 1))
        if combined < EVIDENCE_FLOOR:
            return []

        return [CapabilityEvidence(
            capability=ModelClass.TOOL_USE,
            confidence=round(combined, 3),
            sources=[s[0] for s in evidence_components],
            detection_method="metadata",
        )]

    @classmethod
    def _compute_assessment_confidence(  # noqa
        cls,
        evidences: List[CapabilityEvidence],
        model_info: Dict,
        capabilities: List[str],
    ) -> float:
        """
        Overall confidence in the capability classification.
        Reflects how much information we had from /api/show.

        HIGH (> 0.80): Full metadata — architecture, params, capabilities list all present
        MEDIUM (0.50–0.80): Partial metadata
        LOW (< 0.50): Minimal — treat profile as UNKNOWN, use conservative routing
        """
        score = 0.0

        # Did we get model_info keys? (most important signal)
        if len(model_info) > 5:
            score += 0.40
        elif len(model_info) > 0:
            score += 0.20

        # Did Ollama return a capabilities list?
        if capabilities:
            score += 0.30

        # Did we have at least one high-confidence capability evidence?
        high_conf = [e for e in evidences
                     if e.confidence >= ASSERT_THRESHOLD and e.detection_method == "metadata"]
        if high_conf:
            score += 0.20
        elif evidences:
            score += 0.10

        # Penalty: only heuristic evidences → reduce confidence
        heuristic_only = all(e.detection_method == "heuristic" for e in evidences) if evidences else True
        if heuristic_only and evidences:
            score *= 0.60

        return round(min(1.0, score), 3)

    # ------------------------------------------------------------------
    # Memory Profile Builder
    # ------------------------------------------------------------------

    @classmethod
    def _build_memory_profile(
        cls,
        total_params_b: float,
        active_params_b: float,
        file_size_gb: float,
        quantization: str,
        bpp: float,
        num_layers: int,
        is_moe: bool,
    ) -> ModelMemoryProfile:
        """
        Build ModelMemoryProfile with accurate MoE/dense memory distinction.

        KEY PRINCIPLE:
            For MoE: file_size_gb ≠ active_params × bpp
            Qwen3-30B-A3B: 17GB file, 3B active/token
            ALL 17GB weights must be resident (GPU or RAM).
            Only 3B worth of weights are COMPUTED per token.

        GPU resident formula (layer-split approach):
            per_layer_mb = (file_size_gb × 1024) / num_layers
            gpu_layers   = floor(safe_vram_mb / per_layer_mb)
            gpu_resident = gpu_layers × per_layer_mb
            ram_resident = total_weight - gpu_resident
        """
        # If file size unknown, estimate from params × bpp
        if file_size_gb <= 0:
            file_size_gb = round(total_params_b * bpp, 2)

        total_weight_mb = file_size_gb * 1024.0

        # Per-layer memory cost (used for GPU layer calculation)
        per_layer_mb = total_weight_mb / max(num_layers, 1)

        # Estimate full GPU VRAM requirement
        # KV cache adds overhead proportional to active params
        # (active params determine attention head sizes)
        kv_per_1k = round(256.0 * (active_params_b / max(total_params_b, 1.0))
                          if is_moe else 256.0, 1)

        return ModelMemoryProfile(
            weight_file_size_gb=file_size_gb,
            quantization=quantization,
            bytes_per_param=bpp,
            total_parameters_b=total_params_b,
            active_parameters_b=active_params_b,
            num_layers=num_layers,
            is_moe=is_moe,
            estimated_full_weight_mb=round(total_weight_mb, 0),
            # GPU-resident estimate: computed by ResourceGovernor with actual VRAM
            estimated_gpu_resident_mb=0.0,   # filled in by ResourceGovernor
            estimated_ram_resident_mb=0.0,   # filled in by ResourceGovernor
            kv_cache_mb_per_1k_ctx=kv_per_1k,
            detection_method="api_show" if file_size_gb > 0 else "heuristic",
        )
