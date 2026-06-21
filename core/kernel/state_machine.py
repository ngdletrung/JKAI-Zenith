from enum import Enum
from typing import List, Dict, Set

class StateInvariantViolation(Exception):
    """Exception raised when an illegal state transition is attempted."""
    pass

class TaskState(str, Enum):
    """
    🌀 Unified Task State Machine Enum
    Defines the precise, audit-friendly, finite states of a cognitive task process.
    """
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    ANALYZED = "ANALYZED"
    POLICY_CHECKED = "POLICY_CHECKED"
    PLANNED = "PLANNED"
    SANDBOX_PREPARED = "SANDBOX_PREPARED"
    EXECUTING = "EXECUTING"
    WAITING_APPROVAL = "WAITING_APPROVAL"
    RETRYING = "RETRYING"
    VERIFYING = "VERIFYING"
    VERIFIED = "VERIFIED"
    COMMITTING = "COMMITTING"
    COMMITTED = "COMMITTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    QUARANTINED = "QUARANTINED"

class StateTransitionGraph:
    """
    🛤️ Deterministic State Transition Graph (Invariant Enforcer)
    Prevents hallucinated state jumps.
    """
    ALLOWED_TRANSITIONS: Dict[TaskState, List[TaskState]] = {
        TaskState.RECEIVED: [
            TaskState.VALIDATED,
            TaskState.FAILED,
            TaskState.QUARANTINED
        ],
        TaskState.VALIDATED: [
            TaskState.ANALYZED,
            TaskState.POLICY_CHECKED,
            TaskState.FAILED,
            TaskState.QUARANTINED
        ],
        TaskState.ANALYZED: [
            TaskState.PLANNED,
            TaskState.POLICY_CHECKED,
            TaskState.FAILED,
            TaskState.QUARANTINED
        ],
        TaskState.POLICY_CHECKED: [
            TaskState.PLANNED,
            TaskState.SANDBOX_PREPARED,
            TaskState.FAILED,
            TaskState.QUARANTINED
        ],
        TaskState.PLANNED: [
            TaskState.SANDBOX_PREPARED,
            TaskState.EXECUTING,
            TaskState.FAILED,
            TaskState.QUARANTINED
        ],
        TaskState.SANDBOX_PREPARED: [
            TaskState.EXECUTING,
            TaskState.FAILED,
            TaskState.QUARANTINED
        ],
        TaskState.EXECUTING: [
            TaskState.VERIFYING,
            TaskState.WAITING_APPROVAL,
            TaskState.COMMITTING,
            TaskState.FAILED,
            TaskState.QUARANTINED
        ],
        TaskState.WAITING_APPROVAL: [
            TaskState.EXECUTING,
            TaskState.FAILED,
            TaskState.QUARANTINED
        ],
        TaskState.VERIFYING: [
            TaskState.VERIFIED,
            TaskState.COMMITTING,
            TaskState.FAILED,
            TaskState.QUARANTINED
        ],
        TaskState.VERIFIED: [
            TaskState.COMMITTING,
            TaskState.FAILED
        ],
        TaskState.COMMITTING: [
            TaskState.COMMITTED,
            TaskState.FAILED,
            TaskState.ROLLED_BACK
        ],
        TaskState.COMMITTED: [
            TaskState.COMPLETED,
            TaskState.FAILED
        ],
        TaskState.COMPLETED: [],  # Terminal
        TaskState.FAILED: [
            TaskState.RETRYING,
            TaskState.ROLLED_BACK,
            TaskState.QUARANTINED,
            TaskState.COMPLETED  # Allow transitioning to completed via recovery or manual override
        ],
        TaskState.RETRYING: [
            TaskState.EXECUTING,
            TaskState.FAILED,
            TaskState.QUARANTINED
        ],
        TaskState.ROLLED_BACK: [
            TaskState.RETRYING,
            TaskState.FAILED,
            TaskState.QUARANTINED
        ],
        TaskState.QUARANTINED: []  # Terminal
    }

    TERMINAL_STATES: Set[TaskState] = {
        TaskState.COMPLETED,
        TaskState.QUARANTINED
    }

    @classmethod
    def validate_transition(cls, current: TaskState, target: TaskState):
        """Enforces that the current state can transition to target state."""
        # Check terminal states first
        if current in cls.TERMINAL_STATES and current != target:
            raise StateInvariantViolation(
                f"Terminal State Violation: Cannot transition out of terminal state '{current.name}' to '{target.name}'"
            )
            
        allowed = cls.ALLOWED_TRANSITIONS.get(current, [])
        if target not in allowed and current != target:
            raise StateInvariantViolation(
                f"Illegal State Transition: '{current.name}' -> '{target.name}'. Allowed targets from '{current.name}' are: {[s.name for s in allowed]}"
            )
