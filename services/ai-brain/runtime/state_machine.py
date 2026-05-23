from enum import Enum
from typing import List

class TaskState(Enum):
    """
    🌀 Terminal Guarantees State Machine
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
    
    # Terminal States (Forward-only, không thể quay đầu)
    COMMITTED = "COMMITTED"
    COMPLETED = "COMPLETED"
    FAILED = "FAILED"
    ROLLED_BACK = "ROLLED_BACK"
    QUARANTINED = "QUARANTINED"

class StateMachine:
    """Quản lý vòng đời chặt chẽ. Đảm bảo Terminal States."""
    TERMINAL_STATES = {
        TaskState.COMMITTED, TaskState.COMPLETED, 
        TaskState.FAILED, TaskState.ROLLED_BACK, TaskState.QUARANTINED
    }

    def __init__(self, initial_state: TaskState = TaskState.RECEIVED):
        self.current_state = initial_state
        self.history: List[TaskState] = [initial_state]

    def transition(self, new_state: TaskState) -> bool:
        if self.current_state in self.TERMINAL_STATES:
            # Ngoại lệ: Chỉ được tạo Trace mới, không được quay đầu state cũ
            raise Exception(f"Transition Error: Cannot transition from Terminal State {self.current_state.name}")
        
        self.current_state = new_state
        self.history.append(new_state)
        return True
