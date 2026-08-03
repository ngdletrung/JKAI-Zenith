"""
JKAI ZENITH — CONTRACT KERNEL: OBSERVATION & EVALUATION RESULT
File: core/contracts/observation.py

Contracts for Observation, Telemetry, and EvaluationResult feedback loops.
Distinguishes raw execution telemetry (Observation) from semantic evaluation (EvaluationResult).
"""

from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional
import time


@dataclass
class Telemetry:
    """Raw execution telemetry data."""
    latency_ms: float = 0.0
    vram_used_mb: float = 0.0
    ram_used_mb: float = 0.0
    tokens_generated: int = 0
    tokens_per_second: float = 0.0
    error_count: int = 0


@dataclass
class Observation:
    """
    Raw Execution/Runtime -> Evaluation feedback contract.
    Delivered via EventBus. Contains un-evaluated execution facts.
    """
    task_id: str
    status_code: int
    content: str
    success: bool = True
    quality_signal: float = 1.0
    failure_signal: bool = False
    decision_trace_id: str = ""
    telemetry: Telemetry = field(default_factory=Telemetry)
    metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)



@dataclass
class EvaluationResult:
    """
    Observation -> Evaluation Layer contract.
    Evaluates Observation against SuccessCriteria and TaskRequirement to produce empirical evidence.
    """
    mission_id: str
    task_id: str
    execution_succeeded: bool = True
    task_succeeded: bool = True
    mission_succeeded: bool = True
    quality_score: float = 1.0
    hallucination_score: float = 0.0
    criteria_results: Dict[str, bool] = field(default_factory=dict)
    evaluator: str = "SuccessCriteriaEvaluator"
    evidence_summary: str = ""
    timestamp: float = field(default_factory=time.time)
