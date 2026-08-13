"""
JKAI ZENITH AI OS — DEEP v2.2 GUARDED FSM STATE MACHINES (PHASE 2)
File: core/os/cognition/deep_fsm.py

Implements deterministic, guarded state machines for:
- MissionFSM (D29, C10, P1-3)
- WaveFSM (D2, D8, D14, D23)
- RecoveryFSM (D24, D30, C8, P0-7)

Enforces:
1. Zero arbitrary jumps (Unauthorized transitions raise ContractViolationException("D29")).
2. Every transition automatically emits structured FSM_TRANSITION event (C10).
3. Recovery depth containment (D30).
"""

from __future__ import annotations
from enum import Enum
from typing import Dict, List, Set, Optional, Any
import time

from core.os.cognition.event_model import emit_fsm_transition, emit_contract_violation


class ContractViolationException(Exception):
    def __init__(self, contract_id: str, message: str):
        super().__init__(f"[{contract_id}] {message}")
        self.contract_id = contract_id


# ============================================================================
# 1. MISSION FSM
# ============================================================================

class MissionState(str, Enum):
    CREATED = "CREATED"
    ADMITTED = "ADMITTED"
    PLANNING = "PLANNING"
    WAVE_READY = "WAVE_READY"
    WAVE_EXECUTING = "WAVE_EXECUTING"
    WAVE_VERIFICATION = "WAVE_VERIFICATION"
    BELIEF_UPDATE = "BELIEF_UPDATE"
    WAVE_DECISION = "WAVE_DECISION"
    COMPLETION_CHECK = "COMPLETION_CHECK"
    MERGING = "MERGING"
    COMPLETED = "COMPLETED"
    BLOCKED = "BLOCKED"
    QUARANTINED = "QUARANTINED"
    FAILED = "FAILED"
    ABORTED = "ABORTED"
    ESCALATED = "ESCALATED"


class MissionFSM:
    """Guarded Finite State Machine for Mission Lifecycle (D29, C10)."""

    ALLOWED_TRANSITIONS: Dict[MissionState, Set[MissionState]] = {
        MissionState.CREATED: {MissionState.ADMITTED, MissionState.ABORTED},
        MissionState.ADMITTED: {MissionState.PLANNING, MissionState.BLOCKED, MissionState.ABORTED},
        MissionState.PLANNING: {MissionState.WAVE_READY, MissionState.FAILED, MissionState.ABORTED},
        MissionState.WAVE_READY: {MissionState.WAVE_EXECUTING, MissionState.BLOCKED, MissionState.ABORTED},
        MissionState.WAVE_EXECUTING: {MissionState.WAVE_VERIFICATION, MissionState.FAILED, MissionState.ABORTED},
        MissionState.WAVE_VERIFICATION: {MissionState.BELIEF_UPDATE, MissionState.FAILED, MissionState.ABORTED},
        MissionState.BELIEF_UPDATE: {MissionState.WAVE_DECISION, MissionState.FAILED, MissionState.ABORTED},
        MissionState.WAVE_DECISION: {
            MissionState.WAVE_READY,          # Proceed to next wave
            MissionState.PLANNING,            # Corrective/Progressive replan
            MissionState.COMPLETION_CHECK,    # Finished all waves
            MissionState.FAILED,
            MissionState.ABORTED,
        },
        MissionState.COMPLETION_CHECK: {
            MissionState.MERGING,             # All criteria verified
            MissionState.PLANNING,            # Need more waves/evidence
            MissionState.FAILED,
            MissionState.QUARANTINED,
        },
        MissionState.MERGING: {MissionState.COMPLETED, MissionState.FAILED},
        MissionState.BLOCKED: {MissionState.WAVE_READY, MissionState.ABORTED},
        MissionState.QUARANTINED: {MissionState.PLANNING, MissionState.FAILED, MissionState.ABORTED},
        # Terminal states
        MissionState.COMPLETED: set(),
        MissionState.FAILED: set(),
        MissionState.ABORTED: set(),
        MissionState.ESCALATED: set(),
    }

    def __init__(self, mission_id: str, trace_id: str = "trace_default"):
        self.mission_id = mission_id
        self.trace_id = trace_id
        self._state = MissionState.CREATED

    @property
    def current_state(self) -> MissionState:
        return self._state

    def transition_to(self, next_state: MissionState, trigger: str = "USER_ACTION") -> None:
        allowed = self.ALLOWED_TRANSITIONS.get(self._state, set())
        if next_state not in allowed:
            err_msg = f"Forbidden Mission FSM transition from {self._state.value} to {next_state.value}!"
            emit_contract_violation(
                contract_id="D29",
                mission_id=self.mission_id,
                trace_id=self.trace_id,
                expected=f"One of {[s.value for s in allowed]}",
                actual=next_state.value,
                recovery_policy="ABORT",
                enforcement_point="MissionFSM.transition_to"
            )
            raise ContractViolationException("D29", err_msg)

        prev_state = self._state
        self._state = next_state
        emit_fsm_transition(
            mission_id=self.mission_id,
            trace_id=self.trace_id,
            from_state=prev_state.value,
            to_state=next_state.value,
            trigger=trigger,
            fsm_type="MISSION_FSM"
        )


# ============================================================================
# 2. WAVE FSM
# ============================================================================

class WaveState(str, Enum):
    WAVE_CREATED = "WAVE_CREATED"
    WAVE_PLANNED = "WAVE_PLANNED"
    ADMISSION_PENDING = "ADMISSION_PENDING"
    ADMITTED = "ADMITTED"
    EXECUTING = "EXECUTING"
    EVIDENCE_COLLECTING = "EVIDENCE_COLLECTING"
    BELIEF_EVALUATING = "BELIEF_EVALUATING"
    DECIDED = "DECIDED"
    PRUNED = "PRUNED"
    REPLANNED = "REPLANNED"
    COMPLETED = "COMPLETED"


class WaveFSM:
    """Guarded Finite State Machine for individual Wave execution (D2, D8, D14, D23)."""

    ALLOWED_TRANSITIONS: Dict[WaveState, Set[WaveState]] = {
        WaveState.WAVE_CREATED: {WaveState.WAVE_PLANNED, WaveState.PRUNED},
        WaveState.WAVE_PLANNED: {WaveState.ADMISSION_PENDING, WaveState.PRUNED},
        WaveState.ADMISSION_PENDING: {WaveState.ADMITTED, WaveState.PRUNED, WaveState.REPLANNED},
        WaveState.ADMITTED: {WaveState.EXECUTING, WaveState.PRUNED},
        WaveState.EXECUTING: {WaveState.EVIDENCE_COLLECTING, WaveState.PRUNED},
        WaveState.EVIDENCE_COLLECTING: {WaveState.BELIEF_EVALUATING},
        WaveState.BELIEF_EVALUATING: {WaveState.DECIDED},
        WaveState.DECIDED: {WaveState.COMPLETED, WaveState.PRUNED, WaveState.REPLANNED},
        WaveState.PRUNED: set(),
        WaveState.REPLANNED: set(),
        WaveState.COMPLETED: set(),
    }

    def __init__(self, wave_id: int, mission_id: str, trace_id: str = "trace_default"):
        self.wave_id = wave_id
        self.mission_id = mission_id
        self.trace_id = trace_id
        self._state = WaveState.WAVE_CREATED

    @property
    def current_state(self) -> WaveState:
        return self._state

    def transition_to(self, next_state: WaveState, trigger: str = "WAVE_CONTROLLER") -> None:
        allowed = self.ALLOWED_TRANSITIONS.get(self._state, set())
        if next_state not in allowed:
            err_msg = f"Forbidden Wave FSM transition from {self._state.value} to {next_state.value} in Wave {self.wave_id}!"
            emit_contract_violation(
                contract_id="D23",
                mission_id=self.mission_id,
                trace_id=self.trace_id,
                expected=f"One of {[s.value for s in allowed]}",
                actual=next_state.value,
                recovery_policy="PRUNE",
                enforcement_point="WaveFSM.transition_to"
            )
            raise ContractViolationException("D23", err_msg)

        prev_state = self._state
        self._state = next_state
        emit_fsm_transition(
            mission_id=f"{self.mission_id}:wave_{self.wave_id}",
            trace_id=self.trace_id,
            from_state=prev_state.value,
            to_state=next_state.value,
            trigger=trigger,
            fsm_type="WAVE_FSM"
        )


# ============================================================================
# 3. RECOVERY FSM
# ============================================================================

class RecoveryFSMState(str, Enum):
    IDLE = "IDLE"
    CLASSIFYING = "CLASSIFYING"
    RECONCILING = "RECONCILING"
    RETRYING = "RETRYING"
    ROLLING_BACK = "ROLLING_BACK"
    REPLANNING = "REPLANNING"
    PRUNING = "PRUNING"
    ESCALATING = "ESCALATING"
    ABORTING = "ABORTING"
    RECOVERED = "RECOVERED"
    FAILED = "FAILED"


class RecoveryFSM:
    """Bounded Recovery State Machine with depth containment (D24, D30, C8, P0-7)."""

    def __init__(self, mission_id: str, max_recovery_depth: int = 3, trace_id: str = "trace_default"):
        self.mission_id = mission_id
        self.max_recovery_depth = max_recovery_depth
        self.trace_id = trace_id
        self.current_depth = 0
        self._state = RecoveryFSMState.IDLE

    @property
    def current_state(self) -> RecoveryFSMState:
        return self._state

    def start_recovery(self, failure_class: str) -> RecoveryFSMState:
        self.current_depth += 1
        if self.current_depth > self.max_recovery_depth:
            emit_contract_violation(
                contract_id="D30",
                mission_id=self.mission_id,
                trace_id=self.trace_id,
                expected=f"depth <= {self.max_recovery_depth}",
                actual=f"depth = {self.current_depth}",
                recovery_policy="ABORT",
                enforcement_point="RecoveryFSM.start_recovery"
            )
            self._state = RecoveryFSMState.ABORTING
            return self._state

        self._state = RecoveryFSMState.CLASSIFYING
        emit_fsm_transition(
            mission_id=self.mission_id,
            trace_id=self.trace_id,
            from_state=RecoveryFSMState.IDLE.value,
            to_state=self._state.value,
            trigger=f"FAILURE_{failure_class}",
            fsm_type="RECOVERY_FSM"
        )
        return self._state
