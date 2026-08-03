"""
JKAI ZENITH — EVALUATION SUBSTRATE (MISSION ASSURANCE)
Package: core/evaluation/

Responsibility:
    Evaluates ExecutionResult / Observation against MissionContract & SuccessCriteria.
    Emits EvaluationResult & MissionOutcome.
"""

from core.evaluation.evaluator import MissionEvaluator

__all__ = [
    "MissionEvaluator",
]
