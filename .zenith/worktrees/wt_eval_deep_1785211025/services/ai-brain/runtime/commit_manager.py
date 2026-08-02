from runtime.state_machine import StateMachine, TaskState
from runtime.verifier import VerifierResult

class CommitManager:
    """
    💾 Lớp Chốt Chặn (Commit Authority)
    Không Verified -> Không Commit -> Không Poisoning.
    """
    def __init__(self, memory_gateway):
        self.memory_gateway = memory_gateway

    def attempt_commit(self, state_machine: StateMachine, verifier_result: VerifierResult, data: dict):
        if state_machine.current_state != TaskState.VERIFYING:
            raise Exception("Chưa đi qua bước Verifying.")
            
        if not verifier_result.valid:
            state_machine.transition(TaskState.QUARANTINED)
            # Log cảnh báo nghiêm trọng
            return False
            
        # Nếu OK, tiến hành chốt trạng thái
        state_machine.transition(TaskState.COMMITTING)
        
        # TODO: Ghi vào Memory (EPISODIC zone)
        # self.memory_gateway.write("EPISODIC", data)
        
        state_machine.transition(TaskState.COMMITTED)
        return True
