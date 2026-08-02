# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/runtime/execution_loop.py
# - Role: Cognitive Execution Fabric Loop
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v18.0
# [WORKING PRINCIPLES]:
# - Tuan thu nghiem ngat No-Emoji va Zero-Noise.
# - Ket noi dong bo voi RollbackManager de tu dong kich hoat Saga compensating actions khi gap su co.

from core.kernel.state_machine import TaskState, StateTransitionGraph
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
from runtime.rollback_manager import RollbackManager

class StateMachine:
    """Backward-compatible StateMachine wrapper leveraging StateTransitionGraph."""
    def __init__(self, initial_state: TaskState = TaskState.RECEIVED):
        self.current_state = initial_state
        self.history = [initial_state]

    def transition(self, new_state: TaskState) -> bool:
        StateTransitionGraph.validate_transition(self.current_state, new_state)
        self.current_state = new_state
        self.history.append(new_state)
        return True

class ExecutionFabric:
    """
    KHOANG THUC THI (Cognitive Execution Fabric)
    Noi Runtime tuoc quyen dieu khien cua LLM va tu quyet dinh thuc thi.
    LLM de xuat (Proposal) -> Runtime duyet va chay.
    """
    def __init__(self, 
                 registry: ToolRegistry,
                 sandbox: SandboxedExecutor,
                 journal: JournalStore,
                 idempotency: IdempotencyLayer,
                 verifier: VerifierLayer,
                 commit_manager: CommitManager,
                 scheduler: RuntimeScheduler,
                 circuit_breaker: CircuitBreaker,
                 rollback_manager: RollbackManager = None):
        
        self.registry = registry
        self.sandbox = sandbox
        self.journal = journal
        self.idempotency = idempotency
        self.verifier = verifier
        self.commit_manager = commit_manager
        self.scheduler = scheduler
        self.circuit_breaker = circuit_breaker
        self.rollback_manager = rollback_manager or RollbackManager(sandbox)

    def run_proposal(self, proposal: ExecutionProposal, token: CapabilityToken):
        """Hanh quyet ban de xuat cua Planner."""
        trace_id = proposal.trace_id
        
        # 1. State: RECEIVED
        state = StateMachine(TaskState.RECEIVED)
        self.scheduler.init_trace(trace_id)
        
        for step in proposal.proposed_steps:
            self.scheduler.record_step(trace_id)
            
            tool_name = step.get("tool")
            args = step.get("args", {})
            
            # Kiem tra Cau Dao
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
            # Kiem tra quyen toi thieu (Se throw Error neu vi pham)
            for perm in tool_def.permissions:
                if perm not in token.permissions:
                    state.transition(TaskState.QUARANTINED)
                    raise Exception(f"Capability Violation: Missing {perm}")
            
            # 4. State: SANDBOX_PREPARED (Kem check chong Double Execute)
            state.transition(TaskState.SANDBOX_PREPARED)
            idem_key = self.idempotency.generate_key(trace_id, tool_name, args)
            
            if tool_def.idempotent and not self.idempotency.check_and_lock(idem_key, timeout=tool_def.timeout):
                # Da thuc thi roi, bo qua
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
                    # Publish successful event to real-time cognitive bus
                    try:
                        import json
                        from redis_client import get_redis
                        r_conn = get_redis()
                        if r_conn:
                            r_conn.publish("zenith:cognitive_events", json.dumps({"intent": tool_name, "is_success": True}))
                    except Exception as publish_err:
                        print(f"[EXECUTION-LOOP-WARN] Failed to publish event: {publish_err}")
            except Exception as e:
                self.circuit_breaker.record_failure(tool_name)
                state.transition(TaskState.FAILED)
                # Publish failure event to real-time cognitive bus
                try:
                    import json
                    from redis_client import get_redis
                    r_conn = get_redis()
                    if r_conn:
                        r_conn.publish("zenith:cognitive_events", json.dumps({"intent": tool_name, "is_success": False}))
                except Exception as publish_err:
                    print(f"[EXECUTION-LOOP-WARN] Failed to publish failure event: {publish_err}")
                # Kich hoat Saga compensation hoan tac giao dich hoac don dep khi co su co
                try:
                    self.rollback_manager.execute_compensation(trace_id, tool_name)
                except Exception as rollback_err:
                    print(f"[ROLLBACK-ERROR]: Failed to execute compensation for '{tool_name}' on trace {trace_id}: {rollback_err}")
                raise e
                
        state.transition(TaskState.COMPLETED)
        return True
