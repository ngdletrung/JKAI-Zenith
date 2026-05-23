from runtime.state_machine import StateMachine, TaskState
from runtime.tool_registry import ToolRegistry
from runtime.sandbox import SandboxedExecutor
from runtime.execution_journal import JournalStore
from runtime.idempotency_layer import IdempotencyLayer
from runtime.verifier import VerifierLayer
from runtime.commit_manager import CommitManager
from runtime.scheduler import RuntimeScheduler
from runtime.circuit_breaker import CircuitBreaker
from runtime.execution_context import ExecutionProposal
from runtime.capability_validator import CapabilityToken

class ExecutionFabric:
    """
    ⚡ KHÔNG GIAN THỰC THI (Cognitive Execution Fabric)
    Nơi Runtime tước quyền điều khiển của LLM và tự ra quyết định.
    LLM đề xuất (Proposal) -> Runtime duyệt và chạy.
    """
    def __init__(self, 
                 registry: ToolRegistry,
                 sandbox: SandboxedExecutor,
                 journal: JournalStore,
                 idempotency: IdempotencyLayer,
                 verifier: VerifierLayer,
                 commit_manager: CommitManager,
                 scheduler: RuntimeScheduler,
                 circuit_breaker: CircuitBreaker):
        
        self.registry = registry
        self.sandbox = sandbox
        self.journal = journal
        self.idempotency = idempotency
        self.verifier = verifier
        self.commit_manager = commit_manager
        self.scheduler = scheduler
        self.circuit_breaker = circuit_breaker

    def run_proposal(self, proposal: ExecutionProposal, token: CapabilityToken):
        """Hành quyết bản đề xuất của Planner."""
        trace_id = proposal.trace_id
        
        # 1. State: RECEIVED
        state = StateMachine(TaskState.RECEIVED)
        self.scheduler.init_trace(trace_id)
        
        for step in proposal.proposed_steps:
            self.scheduler.record_step(trace_id)
            
            tool_name = step.get("tool")
            args = step.get("args", {})
            
            # Kiểm tra Cầu Dao
            if self.circuit_breaker.is_open(tool_name):
                state.transition(TaskState.QUARANTINED)
                raise Exception(f"Subsystem {tool_name} is QUARANTINED due to consecutive failures.")
            
            # 2. State: VALIDATED & ANALYZED
            state.transition(TaskState.VALIDATED)
            tool_def = self.registry.resolve(tool_name)
            if not tool_def:
                state.transition(TaskState.QUARANTINED)
                raise Exception(f"Hallucinated Tool: {tool_name}")
            
            # 3. State: POLICY_CHECKED
            state.transition(TaskState.POLICY_CHECKED)
            # Kiểm tra quyền tối thiểu (Sẽ throw Error nếu vi phạm)
            for perm in tool_def.permissions:
                if perm not in token.permissions:
                    state.transition(TaskState.QUARANTINED)
                    raise Exception(f"Capability Violation: Missing {perm}")
            
            # 4. State: SANDBOX_PREPARED (Kèm check chống Double Execute)
            state.transition(TaskState.SANDBOX_PREPARED)
            idem_key = self.idempotency.generate_key(trace_id, tool_name, args)
            
            if tool_def.idempotent and not self.idempotency.check_and_lock(idem_key, timeout=tool_def.timeout):
                # Đã thực thi rồi, bỏ qua
                continue

            self.scheduler.record_tool_call(trace_id)
            
            try:
                # 5. State: EXECUTING
                state.transition(TaskState.EXECUTING)
                result = self.sandbox.execute(tool_def, token, args, trace_id)
                self.circuit_breaker.record_success(tool_name)
                
                # 6. State: VERIFYING
                state.transition(TaskState.VERIFYING)
                verify_res = self.verifier.verify_tool_output(tool_name, str(result))
                
                # 7. State: COMMITTING
                commit_success = self.commit_manager.attempt_commit(state, verify_res, result)
                
                if commit_success:
                    self.idempotency.mark_completed(idem_key)
                    # Ghi Journal
                    self.journal.append(
                        trace_id=trace_id,
                        actor="RUNTIME",
                        action=tool_name,
                        input_payload=args,
                        output_payload=result,
                        state_before=TaskState.EXECUTING.name,
                        state_after=TaskState.COMMITTED.name
                    )
            except Exception as e:
                self.circuit_breaker.record_failure(tool_name)
                state.transition(TaskState.FAILED)
                # TODO: Trigger Rollback Manager nếu cần
                raise e
                
        state.transition(TaskState.COMPLETED)
        return True
