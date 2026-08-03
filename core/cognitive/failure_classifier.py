"""
JKAI ZENITH — COGNITIVE DOMAIN: FAILURE CLASSIFIER
File: core/cognitive/failure_classifier.py

Classifies evaluation failures into distinct semantic categories:
- CAPABILITY_FAILURE: Candidate model lacked tools/vision/context
- KNOWLEDGE_FAILURE: Insufficient grounding or context retrieved
- MODEL_FAILURE: Model generated invalid syntax or failed reasoning
- RESOURCE_FAILURE: OOM, VRAM pressure, or execution timeout
- QUALITY_FAILURE: Quality score below threshold or hallucination detected
"""

from dataclasses import dataclass
from typing import Dict, Any, Optional
from core.contracts import EvaluationResult, Observation


@dataclass
class FailureClassification:
    """Classification of an execution / evaluation failure."""
    category: str = "QUALITY_FAILURE"    # CAPABILITY_FAILURE | KNOWLEDGE_FAILURE | MODEL_FAILURE | RESOURCE_FAILURE | QUALITY_FAILURE
    severity: str = "MEDIUM"             # LOW | MEDIUM | HIGH | CRITICAL
    recommended_recovery: str = "REPLAN" # REPLAN | FALLBACK_MODEL | MORE_CONTEXT | DEGRADE | ABORT
    reason: str = ""


class FailureClassifier:
    """Policy-driven failure classification engine."""

    def classify(self, eval_result: EvaluationResult, observation: Optional[Observation] = None) -> FailureClassification:
        if observation and observation.status_code == 504:
            return FailureClassification(
                category="RESOURCE_FAILURE",
                severity="HIGH",
                recommended_recovery="DEGRADE",
                reason="Execution timeout (504). Reduce context or request lightweight model."
            )

        if observation and observation.status_code == 507:
            return FailureClassification(
                category="RESOURCE_FAILURE",
                severity="HIGH",
                recommended_recovery="FALLBACK_MODEL",
                reason="Insufficient VRAM (507). Evicting model and falling back."
            )

        criteria = eval_result.criteria_results
        if not criteria.get("hallucination_threshold", True):
            return FailureClassification(
                category="KNOWLEDGE_FAILURE",
                severity="HIGH",
                recommended_recovery="MORE_CONTEXT",
                reason="Hallucination detected. Need stronger RAG grounding and citations."
            )

        if not criteria.get("quality_threshold", True):
            return FailureClassification(
                category="QUALITY_FAILURE",
                severity="MEDIUM",
                recommended_recovery="FALLBACK_MODEL",
                reason=f"Quality score {eval_result.quality_score} below threshold. Re-assigning to higher-tier model."
            )

        return FailureClassification(
            category="MODEL_FAILURE",
            severity="MEDIUM",
            recommended_recovery="REPLAN",
            reason=eval_result.evidence_summary
        )
