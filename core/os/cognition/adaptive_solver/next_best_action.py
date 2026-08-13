"""
core/os/cognition/adaptive_solver/next_best_action.py
P0-2: Next Best Action Selector (Multi-Objective Decision Engine).

Evaluates candidate execution actions across 6 mathematical dimensions:
1. Information Gain (Uncertainty reduction)
2. Mission Progress (Criterion satisfaction)
3. Evidence Value (Physical testability)
4. Reversibility (Rollback ease)
5. Execution Cost (Token / turn / latency footprint)
6. Risk (Side-effects & blast radius)

Selects the cheapest action that yields maximum uncertainty reduction and genuine progress.
"""

from __future__ import annotations
import enum
import time
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Tuple


class ActionType(str, enum.Enum):
    MICRO_PROBE = "MICRO_PROBE"         # Read minimal symbol/slice (<5 lines)
    PROBE = "PROBE"                     # Read 1-2 representative files
    INSPECT_FILE = "INSPECT_FILE"       # Full inspection of target file
    SEARCH_REPO = "SEARCH_REPO"         # Grep / pattern search in workspace
    EDIT_FILE = "EDIT_FILE"             # Surgical modification of a single file
    BATCH_EDIT = "BATCH_EDIT"           # Concurrent modification of verified homogenous files
    RUN_TEST = "RUN_TEST"               # Execute unit tests or verification command
    VERIFY_ARTIFACT = "VERIFY_ARTIFACT" # AST / format / visual audit of output
    SURGICAL_REPAIR = "SURGICAL_REPAIR" # Targeted fix for a specific unsatisfied criterion
    SAFE_STOP = "SAFE_STOP"             # Graceful termination on security/authority limit


@dataclass
class ActionCandidate:
    """A proposed execution step to be evaluated by the Next Best Action engine."""
    candidate_id: str
    action_type: ActionType
    target: str
    description: str
    arguments: Dict[str, Any] = field(default_factory=dict)
    information_gain: float = 0.50  # 0.0 (know nothing new) to 1.0 (eliminates major unknown)
    mission_progress: float = 0.50  # 0.0 (no direct progress) to 1.0 (completes requirement)
    evidence_value: float = 0.50    # 0.0 (untestable assertion) to 1.0 (verifiable on disk)
    reversibility: float = 1.00     # 1.0 (read-only/easy undo) to 0.0 (irreversible deletion)
    execution_cost: float = 0.20    # 0.0 (trivial local call) to 1.0 (heavy long-running job)
    risk_score: float = 0.10        # 0.0 (safe) to 1.0 (dangerous mutation)


@dataclass
class ScoredAction:
    """An action candidate with calculated utility score and selection rationale."""
    candidate: ActionCandidate
    utility_score: float
    rank: int
    selection_rationale: str


class NextBestActionSelector:
    """Ranks and selects the optimal Next Best Action based on multi-objective optimization."""

    # Multi-Objective Weights
    W_INFO_GAIN = 0.25
    W_PROGRESS = 0.30
    W_EVIDENCE = 0.20
    W_REVERSIBILITY = 0.15
    W_COST_PENALTY = 0.10
    W_RISK_PENALTY = 0.20

    @classmethod
    def calculate_utility(cls, candidate: ActionCandidate, situation: Optional[Any] = None) -> float:
        """Calculates utility score for an action candidate."""
        score = (
            (cls.W_INFO_GAIN * candidate.information_gain)
            + (cls.W_PROGRESS * candidate.mission_progress)
            + (cls.W_EVIDENCE * candidate.evidence_value)
            + (cls.W_REVERSIBILITY * candidate.reversibility)
            - (cls.W_COST_PENALTY * candidate.execution_cost)
            - (cls.W_RISK_PENALTY * candidate.risk_score)
        )

        # If uncertainty is high, boost Information Gain & Reversibility weight
        if situation and hasattr(situation, "uncertainty_budget"):
            if not situation.uncertainty_budget.is_mutation_permitted:
                if candidate.action_type in (ActionType.MICRO_PROBE, ActionType.PROBE, ActionType.INSPECT_FILE, ActionType.SEARCH_REPO):
                    score += 0.30  # Strong boost for exploratory probes when uncertainty is high
                elif candidate.action_type in (ActionType.BATCH_EDIT, ActionType.EDIT_FILE):
                    score -= 0.40  # Heavy penalty on mass mutations when uncertainty is unbudgeted

        return round(score, 4)

    @classmethod
    def rank_actions(
        cls,
        candidates: List[ActionCandidate],
        situation: Optional[Any] = None
    ) -> List[ScoredAction]:
        """Scores and ranks candidate actions in descending order of utility."""
        scored = []
        for cand in candidates:
            utility = cls.calculate_utility(cand, situation)
            scored.append((cand, utility))

        # Sort descending by utility
        scored.sort(key=lambda x: x[1], reverse=True)

        results = []
        for i, (cand, utility) in enumerate(scored, start=1):
            rationale = (
                f"Rank #{i} | Utility: {utility:.3f} | Action: {cand.action_type.value} on '{cand.target}' | "
                f"InfoGain={cand.information_gain:.2f}, Progress={cand.mission_progress:.2f}, "
                f"Evidence={cand.evidence_value:.2f}, Risk={cand.risk_score:.2f}"
            )
            results.append(ScoredAction(candidate=cand, utility_score=utility, rank=i, selection_rationale=rationale))

        return results

    @classmethod
    def select_next_best_action(
        cls,
        candidates: List[ActionCandidate],
        situation: Optional[Any] = None
    ) -> Optional[ScoredAction]:
        """Returns the single top-ranked action."""
        ranked = cls.rank_actions(candidates, situation)
        return ranked[0] if ranked else None


next_best_action_selector = NextBestActionSelector()
