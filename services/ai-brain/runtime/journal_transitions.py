from enum import Enum

class StateInvariantViolation(Exception):
    pass

class TaskState(Enum):
    RECEIVED = "RECEIVED"
    VALIDATED = "VALIDATED"
    POLICY_CHECKED = "POLICY_CHECKED"
    SANDBOX_PREPARED = "SANDBOX_PREPARED"
    EXECUTING = "EXECUTING"
    VERIFYING = "VERIFYING"
    COMMITTING = "COMMITTING"
    COMMITTED = "COMMITTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    QUARANTINED = "QUARANTINED"
    ROLLED_BACK = "ROLLED_BACK"

class StateTransitionGraph:
    """
    🛤️ Đồ Thị Trạng Thái Nguyên Tử (Atomic State Invariants)
    Tuyệt đối không cho phép chuyển trạng thái bừa bãi.
    """
    ALLOWED_TRANSITIONS = {
        TaskState.RECEIVED: [TaskState.VALIDATED, TaskState.FAILED, TaskState.QUARANTINED],
        TaskState.VALIDATED: [TaskState.POLICY_CHECKED, TaskState.FAILED, TaskState.QUARANTINED],
        TaskState.POLICY_CHECKED: [TaskState.SANDBOX_PREPARED, TaskState.FAILED, TaskState.QUARANTINED],
        TaskState.SANDBOX_PREPARED: [TaskState.EXECUTING, TaskState.FAILED],
        TaskState.EXECUTING: [TaskState.VERIFYING, TaskState.FAILED, TaskState.QUARANTINED],
        TaskState.VERIFYING: [TaskState.COMMITTING, TaskState.FAILED, TaskState.QUARANTINED],
        TaskState.COMMITTING: [TaskState.COMMITTED, TaskState.FAILED, TaskState.ROLLED_BACK],
        TaskState.COMMITTED: [TaskState.COMPLETED],
        TaskState.COMPLETED: [], # Terminal
        TaskState.FAILED: [TaskState.ROLLED_BACK],
        TaskState.QUARANTINED: [], # Terminal
        TaskState.ROLLED_BACK: [] # Terminal
    }

    @staticmethod
    def validate_transition(current: TaskState, target: TaskState):
        if target not in StateTransitionGraph.ALLOWED_TRANSITIONS.get(current, []):
            raise StateInvariantViolation(f"Illegal transition: {current.name} -> {target.name}")
