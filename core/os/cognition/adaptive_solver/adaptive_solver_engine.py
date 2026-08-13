"""
core/os/cognition/adaptive_solver/adaptive_solver_engine.py
Adaptive Task Solver Engine — Governed Cognitive Strategy Orchestrator.

Enforces:
1. Mission Immutability (Mission & Requirements cannot be mutated or dropped).
2. Governed Adaptation (Adapts strategy, granularity, depth, and topology).
3. Strategy Invalidation (Rejects stale hypotheses when observation diverges from expectation).
4. Safe Stop on Insufficient Evidence.
"""

from __future__ import annotations
import hashlib
import time
from typing import Any, Dict, List, Optional
from core.os.cognition.adaptive_solver.models import (
    ActionGranularity,
    ArtifactOutcome,
    ExecutionTruth,
    MissionImmutabilityViolationError,
    MissionOutcome,
    RequirementStatus,
    SituationModel,
    StrategyAdaptation,
    StrategyDecision,
    ToolOutcome,
)
from core.os.cognition.escl.canonical_mission import CanonicalMissionSpec


class AdaptiveTaskSolverEngine:
    """The central intelligence coordinating adaptive strategy and execution budgets."""

    def evaluate_and_adapt(
        self,
        mission: CanonicalMissionSpec,
        situation: SituationModel,
        last_truth: ExecutionTruth,
    ) -> StrategyAdaptation:
        # Invariant 1: Enforce Mission Immutability
        req_repr = "".join([f"{sc.criterion_id}:{sc.description}" for sc in mission.success_criteria])
        current_hash = hashlib.sha256(f"{mission.mission_id}:{mission.raw_goal}:{req_repr}".encode()).hexdigest()
        if current_hash != situation.immutable_mission_hash:
            raise MissionImmutabilityViolationError(
                f"FATAL: Mission '{mission.mission_id}' requirements were mutated during execution! "
                f"Expected hash {situation.immutable_mission_hash}, got {current_hash}."
            )

        # Invariant 2: Divergence detected -> STRATEGY_INVALIDATED
        recent_divergence = next((ev for ev in reversed(situation.expected_vs_actual) if ev.is_divergent), None)
        if recent_divergence:
            return StrategyAdaptation(
                decision=StrategyDecision.STRATEGY_INVALIDATED,
                recommended_granularity=ActionGranularity.PRECISION,
                rationale=f"Observation diverged from expectation: {recent_divergence.divergence_reason}. Stale batch hypothesis invalidated.",
                reason_codes=["DIVERGENCE_DETECTED", "HYPOTHESIS_FALSIFIED"],
                supporting_evidence=[f"Expected: {recent_divergence.expected_state}", f"Observed: {recent_divergence.observed_reality}"],
                invalidated_assumptions=[situation.initial_hypothesis],
                confidence=0.95,
                expected_outcome="Isolate anomalous items and inspect each individually",
                budget_cost=0.1,
                authority_scope="AUTONOMOUS",
                replan_instructions="Switch from batch strategy to individual precision inspection.",
                provenance_trace={
                    "mission_id": mission.mission_id,
                    "trigger_type": "EXPECTED_VS_ACTUAL_DIVERGENCE",
                    "divergence_reason": recent_divergence.divergence_reason
                },
                timestamp=time.time()
            )

        # Invariant 3: Genuine Full Success -> TERMINATE_WITH_PROOF
        if last_truth.is_genuine_success and last_truth.mission_outcome == MissionOutcome.COMPLETED:
            return StrategyAdaptation(
                decision=StrategyDecision.TERMINATE_WITH_PROOF,
                recommended_granularity=ActionGranularity.VERIFY,
                rationale="All success criteria proven satisfied on physical storage with genuine artifacts.",
                reason_codes=["ALL_CRITERIA_VERIFIED", "ARTIFACT_NON_ZERO"],
                supporting_evidence=[f"Artifact: {last_truth.artifact_path}", f"ExecutionTime: {last_truth.execution_time_ms}ms"],
                confidence=1.0,
                expected_outcome="Emit final verified completion ledger",
                authority_scope="AUTONOMOUS",
                provenance_trace={
                    "mission_id": mission.mission_id,
                    "artifact_path": last_truth.artifact_path,
                    "verdicts": {k: v.value for k, v in last_truth.requirement_verdicts.items()}
                },
                timestamp=time.time()
            )

        # Invariant 4: Security / Permission Denial -> SAFE_STOP
        if last_truth.tool_outcome == ToolOutcome.PERMISSION_DENIED or last_truth.mission_outcome == MissionOutcome.SAFE_STOP:
            return StrategyAdaptation(
                decision=StrategyDecision.SAFE_STOP,
                recommended_granularity=ActionGranularity.PROBE,
                rationale="Security boundary or permission limit reached. Safely halting execution.",
                reason_codes=["SECURITY_BOUNDARY_REACHED", "PERMISSION_DENIED"],
                supporting_evidence=[last_truth.error_message or "Unauthorized action target"],
                confidence=1.0,
                expected_outcome="Safely halt with zero side effects and emit diagnostic report",
                authority_scope="FAIL_CLOSED",
                safe_stop_reason=last_truth.error_message or "Permission denied",
                provenance_trace={
                    "mission_id": mission.mission_id,
                    "action": last_truth.tool_name,
                    "denial_reason": last_truth.error_message
                },
                timestamp=time.time()
            )

        # Invariant 5: Tool Failure requiring Strategy Pivot
        if last_truth.tool_outcome in (ToolOutcome.FAILED, ToolOutcome.TIMEOUT):
            err_lower = (last_truth.error_message or "").lower()
            is_dep_err = "modulenotfound" in err_lower or "importerror" in err_lower or "no module" in err_lower
            return StrategyAdaptation(
                decision=StrategyDecision.PIVOT_STRATEGY,
                recommended_granularity=ActionGranularity.PRECISION,
                rationale=f"Missing library detected ({last_truth.error_message}). Pivoting strategy to alternative capability." if is_dep_err else f"Tool failure detected ({last_truth.error_message or 'execution failed'}). Pivoting strategy to alternative capability.",
                reason_codes=["DEPENDENCY_MISSING" if is_dep_err else "TOOL_EXECUTION_FAILURE"],
                supporting_evidence=[last_truth.error_message or "Tool execution failed"],
                invalidated_assumptions=["Assumed target tool or library was available in runtime"],
                confidence=0.85,
                expected_outcome="Compose alternative workflow using built-in / verified capabilities",
                authority_scope="AUTONOMOUS",
                replan_instructions="Switch to available standard library or compose alternative tool.",
                provenance_trace={
                    "mission_id": mission.mission_id,
                    "tool_error": last_truth.error_message
                },
                timestamp=time.time()
            )

        # Invariant 6: Specific Requirement Unsatisfied -> TARGETED_REPAIR
        failed_reqs = [k for k, v in last_truth.requirement_verdicts.items() if v == RequirementStatus.UNSATISFIED]
        if failed_reqs:
            return StrategyAdaptation(
                decision=StrategyDecision.TARGETED_REPAIR,
                recommended_granularity=ActionGranularity.TARGETED_REPAIR,
                rationale=f"Artifact created but failed requirements {failed_reqs}. Kicking off surgical repair.",
                reason_codes=["REQUIREMENT_UNSATISFIED", "PARTIAL_ARTIFACT_DELIVERY"],
                supporting_evidence=[f"Failed criteria: {failed_reqs}", f"Artifact: {last_truth.artifact_path}"],
                confidence=0.9,
                expected_outcome=f"Surgically patch artifact {last_truth.artifact_path} to fulfill {failed_reqs}",
                authority_scope="AUTONOMOUS",
                next_action_target=last_truth.artifact_path,
                replan_instructions=f"Targeted repair needed: Inject missing requirement {failed_reqs} into {last_truth.artifact_path}",
                provenance_trace={
                    "mission_id": mission.mission_id,
                    "failed_requirements": failed_reqs,
                    "target_artifact": last_truth.artifact_path
                },
                timestamp=time.time()
            )

        # Invariant 7: Probe Succeeded on Homogenous Group -> Promote to Batch
        if (situation.current_granularity == ActionGranularity.PROBE or "verified:" in str(situation.known_facts)) and last_truth.tool_outcome == ToolOutcome.SUCCEEDED:
            if situation.homogenous_groups and not situation.anomalous_items:
                return StrategyAdaptation(
                    decision=StrategyDecision.REFINE_GRANULARITY,
                    recommended_granularity=ActionGranularity.BATCH,
                    rationale="Small probe verified successfully. Promoting execution to high-confidence batch transformation.",
                    reason_codes=["PROBE_VERIFIED", "HOMOGENOUS_GROUP_CONFIRMED"],
                    supporting_evidence=[f"Probe target verified: {list(situation.homogenous_groups.keys())}"],
                    confidence=0.95,
                    expected_outcome="Process remaining homogenous items concurrently in batch",
                    authority_scope="AUTONOMOUS",
                    provenance_trace={
                        "mission_id": mission.mission_id,
                        "batch_group_count": sum(len(v) for v in situation.homogenous_groups.values())
                    },
                    timestamp=time.time()
                )

        # Invariant 8: High Complexity discovered -> Escalate Reasoning Budget to DEEP DAG
        if situation.complexity_score >= 0.8:
            return StrategyAdaptation(
                decision=StrategyDecision.DEEPEN_REASONING,
                recommended_granularity=ActionGranularity.PRECISION,
                rationale="High complexity discovered. Escalating reasoning budget and activating DEEP DAG.",
                reason_codes=["HIGH_COMPLEXITY_DISCOVERED", "REASONING_BUDGET_ESCALATION"],
                supporting_evidence=[f"Complexity score: {situation.complexity_score} >= 0.8"],
                confidence=0.9,
                expected_outcome="Decompose mission into parallel multi-agent DAG",
                budget_cost=0.5,
                authority_scope="BOUNDED_AUTONOMOUS",
                escalate_to_deep=True,
                provenance_trace={
                    "mission_id": mission.mission_id,
                    "complexity_score": situation.complexity_score
                },
                timestamp=time.time()
            )

        # Default: Continue current strategy with precision
        return StrategyAdaptation(
            decision=StrategyDecision.CONTINUE_CURRENT_STRATEGY,
            recommended_granularity=ActionGranularity.PRECISION,
            rationale="Continuing current strategy with precision focus.",
            reason_codes=["CONTINUE_STEP_EXECUTION"],
            confidence=0.8,
            authority_scope="AUTONOMOUS",
            provenance_trace={"mission_id": mission.mission_id},
            timestamp=time.time()
        )


adaptive_solver_engine = AdaptiveTaskSolverEngine()
