"""
JKAI ZENITH — EVALUATION SUBSTRATE (MISSION ASSURANCE)
File: core/evaluation/evaluator.py

First-class Evaluation Substrate.
Evaluates ExecutionResult / Observation against MissionContract & SuccessCriteria.
Emits EvaluationResult and MissionOutcome (COMPLETE | REPLAN | RECOVER | ABORT).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
from core.contracts import MissionContract, SuccessCriteria, Observation, EvaluationResult


class MissionEvaluator:
    """Evaluates execution observations against MissionContract rules."""

    def evaluate(
        self,
        contract: MissionContract,
        observation: Observation
    ) -> EvaluationResult:
        criteria = contract.success_criteria
        
        # Check execution status
        exec_ok = observation.success and observation.status_code == 200

        # Quality check against threshold
        quality_score = getattr(observation, "quality_signal", 1.0)
        quality_ok = quality_score >= criteria.min_quality_score

        # Hallucination check
        failure_sig = getattr(observation, "failure_signal", False)
        hallucination_ok = not failure_sig

        mission_ok = exec_ok and quality_ok and hallucination_ok

        summary = "Evaluation PASSED" if mission_ok else f"Evaluation FAILED: exec={exec_ok}, quality={quality_ok}"

        return EvaluationResult(
            mission_id=getattr(observation, "mission_id", "mission_default"),
            task_id=observation.task_id,
            execution_succeeded=exec_ok,
            task_succeeded=mission_ok,
            mission_succeeded=mission_ok,
            quality_score=quality_score,
            criteria_results={
                "execution_200": exec_ok,
                "quality_threshold": quality_ok,
                "hallucination_threshold": hallucination_ok,
            },
            evaluator="MissionEvaluator",
            evidence_summary=summary
        )
