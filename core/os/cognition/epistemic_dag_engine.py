"""
JKAI ZENITH AI OS — READ-ONLY EPISTEMIC DAG ENGINE (PHASE 6)
File: core/os/cognition/epistemic_dag_engine.py

Implements:
- Epistemic Wave Control (D2)
- Contradiction Wave Pruning (D8)
- Wave Causality & Wave Admission Gate (D14, D23)
- PlanDeltaContract validation (D6, C4)
- Read-Only Tool Execution (Mutations strictly disallowed in this phase)
"""

from __future__ import annotations
import logging
from dataclasses import dataclass, field
from typing import Dict, List, Any, Optional, Callable

from core.os.cognition.deep_schemas import (
    CognitiveDecision,
    CognitiveDecisionType,
    BeliefState,
    BeliefFreshnessStatus,
    PlanDelta,
    AdmissionStatus
)
from core.os.cognition.deep_fsm import WaveFSM, WaveState
from core.os.cognition.substrate_bridge import substrate_bridge
from core.os.cognition.event_model import emit_contract_violation, event_store

logger = logging.getLogger("jkai.cognition.epistemic_dag")


@dataclass
class WavePlanNode:
    node_id: str
    agent_role: str
    tool_name: str
    params: Dict[str, Any]
    expected_output_claim: str
    is_mutation: bool = False # Must be False in Read-Only Engine


@dataclass
class EpistemicWave:
    wave_id: int
    mission_id: str
    premise_hypothesis_id: str
    nodes: List[WavePlanNode]
    status: WaveState = WaveState.WAVE_CREATED


class EpistemicDAGEngine:
    """
    4-Loop Epistemic Wave Controller for DEEP v2.2:
    WAVE CONTROLLER -> AGENT EXECUTION -> EVIDENCE FUSION -> REASONING JUDGE
    """

    def __init__(self, mission_id: str, trace_id: str = "trace_default"):
        self.mission_id = mission_id
        self.trace_id = trace_id
        self.waves: List[EpistemicWave] = []
        self.current_wave_index = 0
        self.replans_count = 0
        self.max_replans = 2

    def add_wave(self, wave: EpistemicWave) -> None:
        self.waves.append(wave)

    def check_wave_admission(self, wave: EpistemicWave, belief_state: BeliefState) -> bool:
        """D14 & D23: Wave Admission Gate checking prerequisite belief freshness."""
        premise_id = wave.premise_hypothesis_id
        if premise_id:
            # Check if premise is validated or active
            conf = belief_state.hypotheses.get(premise_id, 0.5)
            staleness = belief_state.staleness_map.get(premise_id, BeliefFreshnessStatus.FRESH)

            if staleness == BeliefFreshnessStatus.STALE or conf < 0.2:
                logger.warning("[WaveAdmissionGate] Wave %d DENIED: Premise %s is stale/refuted (conf=%.2f)",
                               wave.wave_id, premise_id, conf)
                emit_contract_violation(
                    contract_id="D23",
                    mission_id=self.mission_id,
                    trace_id=self.trace_id,
                    expected=f"Premise {premise_id} FRESH and conf >= 0.2",
                    actual=f"conf = {conf}, status = {staleness.value}",
                    recovery_policy="PRUNE",
                    enforcement_point="EpistemicDAGEngine.check_wave_admission"
                )
                return False
        return True

    def evaluate_wave_outcome(self, wave: EpistemicWave, belief_state: BeliefState) -> CognitiveDecision:
        """Epistemic Checkpoint (D2, D8): Evaluate whether to PROCEED, PRUNE, or REPLAN."""
        premise_id = wave.premise_hypothesis_id
        conf = belief_state.hypotheses.get(premise_id, 0.5)

        if conf <= 0.2: # Premise falsified
            return CognitiveDecision(
                decision_id=f"dec_prune_{wave.wave_id}",
                decision_type=CognitiveDecisionType.PRUNE,
                supporting_claims=[f"Premise {premise_id} refuted"],
                supporting_evidence=[],
                justification=f"Wave {wave.wave_id} discovered evidence refuting premise {premise_id}.",
                pruned_waves=[w.wave_id for w in self.waves if w.wave_id > wave.wave_id],
                replan_required=True
            )

        return CognitiveDecision(
            decision_id=f"dec_proceed_{wave.wave_id}",
            decision_type=CognitiveDecisionType.PROCEED,
            supporting_claims=[],
            supporting_evidence=[],
            justification=f"Wave {wave.wave_id} executed successfully with validated premise."
        )

    def request_replan(self, delta: PlanDelta) -> bool:
        """D6 & C4: Validate PlanDeltaContract and enforce MAX_REPLANS <= 2."""
        if self.replans_count >= self.max_replans:
            logger.warning("[D6-REPLAN-LIMIT] Max replans %d reached for mission %s", self.max_replans, self.mission_id)
            return False

        if not delta.is_valid_structural_delta:
            logger.warning("[C4-FAKE-REPLAN] Replan rejected: insufficient structural delta (sim=%.2f)", delta.semantic_similarity)
            emit_contract_violation(
                contract_id="C4",
                mission_id=self.mission_id,
                trace_id=self.trace_id,
                expected="Structural delta > 0 or similarity < 0.85",
                actual=f"similarity = {delta.semantic_similarity}",
                recovery_policy="ABORT",
                enforcement_point="EpistemicDAGEngine.request_replan"
            )
            return False

        self.replans_count += 1
        event_store.append(
            aggregate_id=self.mission_id,
            event_type="REPLAN_ADMITTED",
            payload={"replan_no": self.replans_count, "semantic_similarity": delta.semantic_similarity}
        )
        return True
