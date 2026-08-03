"""
JKAI ZENITH — GOVERNANCE DOMAIN: SUITABILITY ENGINE & MODEL PERFORMANCE MATRIX
File: core/governance/model/evidence.py

Hard Constraint Filter + SuitabilityEngine (Capability vs Context vs Resource vs Risk),
Tri-tiered CapabilityEvidence, ModelIdentity, and Multi-Dimensional ModelPerformanceProfile.
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple
import time
import uuid
from core.contracts import TaskRequirement


@dataclass
class ModelIdentity:
    """Canonical model identity separate from human-facing model names."""
    provider: str                      # "ollama" | "vllm" | "llamacpp" | "remote"
    name: str                          # Human-facing model reference
    digest: str = ""                   # Content digest or SHA256
    model_id: str = field(default_factory=lambda: uuid.uuid4().hex[:12])


@dataclass
class CapabilityVector:
    """Continuous multi-dimensional capability scores (0.0 - 1.0) replacing rigid enum classifications."""
    reasoning: float = 0.5
    coding: float = 0.5
    general: float = 0.5
    vision: float = 0.0
    tool_calling: float = 0.5
    multilingual: float = 0.5
    vietnamese: float = 0.5
    context_handling: float = 0.5
    latency: float = 0.5


@dataclass
class ModelPerformanceProfile:
    """Observed runtime performance profile indexed by (model, role, context_class)."""
    model_name: str = ""
    role: str = "PLANNER"
    context_class: str = "MEDIUM"      # "SMALL" | "MEDIUM" | "LARGE"
    quality_score: float = 0.90
    latency_p50: float = 2.0
    latency_p95: float = 5.0
    tool_success_rate: float = 0.95
    structured_output_rate: float = 0.98
    failure_rate: float = 0.01
    sample_count: int = 0


@dataclass
class CapabilityEvidence:
    """
    Tri-tiered evidence for a model capability.
    Evidence layers:
        - "static": metadata, /api/show, parameter count, architecture
        - "runtime": latency, tokens/sec, VRAM/RAM pressure, failure rate
        - "empirical": task success rate, tool-call success, Vietnamese response quality, RAG grounding
    """
    feature: str                        # "reasoning" | "coding" | "tool_use" | "vision" | "planning"
    source: str                         # "model_metadata" | "benchmark" | "rule_hardware" | "telemetry"
    evidence_type: str = "static"       # "static" | "runtime" | "empirical"
    confidence: float = 1.0             # 0.0 - 1.0 confidence score
    reliability: str = "HIGH"           # "LOW" | "MEDIUM" | "HIGH"
    sample_count: int = 1
    details: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


@dataclass
class SuitabilityScore:
    """Suitability score computed by Governance SuitabilityEngine (Capability vs Context vs Resource vs Risk)."""
    eligible: bool = True
    eligibility_reason: str = "Eligible"
    capability_match: float = 0.5
    resource_fit: float = 0.5
    latency_fit: float = 0.5
    empirical_reliability: float = 0.5
    suitability_score: float = 0.5
    rationale: str = ""


class SuitabilityEngine:
    """
    Governance Suitability Engine.
    HARD CONSTRAINT RULE:
        Only candidates that PASS Hard Constraints (Context limit, Modality, Tool support)
        are ranked by suitability_score. Ineligible candidates have suitability_score = 0.0.
    """

    def filter_hard_constraints(
        self,
        candidate_name: str,
        context_limit: int,
        has_vision: bool,
        has_tools: bool,
        task_req: TaskRequirement,
    ) -> Tuple[bool, str]:
        """Filters hard constraints. Returns (eligible: bool, reason: str)."""
        if context_limit < task_req.min_ctx:
            return False, f"Ineligible: context_limit ({context_limit}) < min_ctx ({task_req.min_ctx})"
        if task_req.requires_vision and not has_vision:
            return False, "Ineligible: requires_vision but model lacks vision capability"
        if task_req.requires_tools and not has_tools:
            return False, "Ineligible: requires_tools but model lacks tool_calling capability"
        return True, "Eligible"

    def compute_suitability(
        self,
        vector: CapabilityVector,
        perf: ModelPerformanceProfile,
        context_limit: int = 32768,
        has_vision: bool = False,
        has_tools: bool = True,
        task_req: Optional[TaskRequirement] = None,
    ) -> SuitabilityScore:
        # Step 1: Hard Constraint Filter
        if task_req is not None:
            eligible, reason = self.filter_hard_constraints(
                perf.model_name, context_limit, has_vision, has_tools, task_req
            )
            if not eligible:
                return SuitabilityScore(
                    eligible=False,
                    eligibility_reason=reason,
                    suitability_score=0.0,
                    rationale=reason
                )

        # Step 2: Suitability Ranking for Eligible Candidates
        cap_match = (vector.reasoning + vector.coding + vector.instruction_following if hasattr(vector, "instruction_following") else vector.general) / 3.0
        res_fit = 0.9 if perf.failure_rate < 0.05 else 0.5
        lat_fit = 0.9 if perf.latency_p50 < 3.0 else 0.7
        emp_rel = perf.quality_score * (1.0 - perf.failure_rate)

        final_score = (cap_match * 0.35) + (res_fit * 0.25) + (lat_fit * 0.20) + (emp_rel * 0.20)

        return SuitabilityScore(
            eligible=True,
            eligibility_reason="Eligible",
            capability_match=cap_match,
            resource_fit=res_fit,
            latency_fit=lat_fit,
            empirical_reliability=emp_rel,
            suitability_score=round(final_score, 4),
            rationale=f"Eligible Suitability: cap={cap_match:.2f}, emp={emp_rel:.2f}",
        )


class CapabilityInference:
    """Infers composite capability scores from multiple CapabilityEvidence entries."""

    def infer_score(self, evidence_list: List[CapabilityEvidence], feature: str) -> float:
        feature_evidence = [e for e in evidence_list if e.feature.lower() == feature.lower()]
        if not feature_evidence:
            return 0.5  # default neutral score

        weighted_sum = sum(
            e.confidence * (1.0 if e.reliability == "HIGH" else 0.7) * (1.2 if e.evidence_type == "empirical" else 1.0)
            for e in feature_evidence
        )
        weight_total = sum(
            (1.0 if e.reliability == "HIGH" else 0.7) * (1.2 if e.evidence_type == "empirical" else 1.0)
            for e in feature_evidence
        )

        return min(1.0, max(0.0, weighted_sum / weight_total)) if weight_total > 0 else 0.5
