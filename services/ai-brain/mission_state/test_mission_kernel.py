# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/mission_state/test_mission_kernel.py
# - Role: Automated test script verifying Event Sourcing, TMS, and Rollbacks
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v1.0

import asyncio
import os
import sys

# Ensure project paths are resolved
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mission_state import (
    MissionRuntime,
    FactManager,
    ScopedMemoryManager,
    ReferenceManager,
    EntityResolver,
    PromptAssembler,
    MissionScheduler,
)

async def mock_tool_execution(x: int, y: int) -> int:
    return x + y

async def run_tests():
    print("[STARTING TEST]: JKAI Zenith Mission Kernel (v2) Test Run")
    
    # 1. Initialize Runtime
    goal = "Optimize the deep pipeline execution by resolving connection issues."
    runtime = MissionRuntime(user_goal=goal, constraints=["No performance loss", "Latency < 200ms"])
    
    assert runtime.state.metadata.user_goal == goal
    assert runtime.state.lifecycle == "READY"
    print("[OK] Runtime initialized correctly.")

    # 2. Lifecycle Transition
    scheduler = MissionScheduler()
    success = scheduler.transition_to(runtime.state, "RUNNING", "Started processing goal")
    assert success
    assert runtime.state.lifecycle == "RUNNING"
    print("[OK] Scheduler successfully transition to RUNNING.")

    # 3. Register and Exec capability
    runtime.register_capability("add", mock_tool_execution)
    result = await runtime.execute_capability("add", 15, 30)
    assert result == 45
    assert runtime.state.budget.tool_calls_count == 1
    print("[OK] Capability registry & execution works.")

    # 4. Scoped Memory Updates
    mem_mgr = ScopedMemoryManager()
    mem_mgr.set_val(runtime.state.memory, "mission", "connection_port", 5432)
    mem_mgr.set_val(runtime.state.memory, "tool", "temp_token", "XYZ")
    assert mem_mgr.get_val(runtime.state.memory, "mission", "connection_port") == 5432
    assert mem_mgr.get_val(runtime.state.memory, "tool", "temp_token") == "XYZ"
    
    # Clear tool memory
    mem_mgr.clear_tool_memory(runtime.state.memory)
    assert mem_mgr.get_val(runtime.state.memory, "tool", "temp_token") is None
    print("[OK] Scoped Memory management verified.")

    # 5. Truth Maintenance System (TMS) Test
    fact_mgr = FactManager()
    fact_mgr.add_fact(runtime.state.facts, "F1", "Database host is localhost")
    fact_mgr.add_fact(runtime.state.facts, "F2", "Database port is 5432", dependencies=["F1"])
    fact_mgr.add_fact(runtime.state.facts, "F3", "Database connection successful", dependencies=["F2"])
    
    assert runtime.state.facts.facts_db["F1"].valid is True
    assert runtime.state.facts.facts_db["F3"].valid is True
    
    # Invalidate F2 (port is incorrect), and downstream F3 should automatically become invalid
    fact_mgr.invalidate_fact(runtime.state.facts, "F2", "Port is actually 5433")
    assert runtime.state.facts.facts_db["F2"].valid is False
    assert runtime.state.facts.facts_db["F3"].valid is False  # Invalidated recursively!
    assert runtime.state.facts.facts_db["F1"].valid is True   # Unrelated remain valid
    print("[OK] Truth Maintenance System (TMS) cascading invalidation verified.")

    # 6. Entity Resolver
    resolver = EntityResolver()
    # Add entities to active stack
    await runtime.emit("EntityResolved", {"entity": "deep_pipeline.py", "confidence": 0.95})
    await runtime.emit("EntityResolved", {"entity": "ConnectionError", "confidence": 0.90})
    
    resolved_entity, conf = resolver.resolve("Please fix that file", runtime.state.active_entity_stack)
    assert resolved_entity == "deep_pipeline.py"
    assert conf > 0.8
    print("[OK] Entity Resolver resolved file from active context stack.")

    # 7. Prompt Assembly and Priority Queue
    assembler = PromptAssembler()
    sys_prompt, fingerprint = assembler.assemble(
        runtime.state, 
        system_rules="Be extra precise.", 
        extra_kb=["Extra chunk details about connection config."],
        token_limit=1000
    )
    assert "Be extra precise" in sys_prompt
    assert "deep_pipeline.py" in sys_prompt
    assert fingerprint is not None
    print("[OK] Prompt Assembler generated system prompt successfully under budget.")

    # 8. Event Sourcing & Time Travel Rollback
    # Record current cost
    await runtime.emit("CostIncurred", {"cost": 0.05, "prompt_tokens": 100})
    assert runtime.state.budget.current_cost_usd == 0.05
    step_before_cost = len(runtime.event_log) - 1 # Step before CostIncurred
    
    # Time travel rollback
    await runtime.rollback(step_before_cost)
    assert runtime.state.budget.current_cost_usd == 0.0
    print("[OK] Event Sourcing rollback (Time Travel) verified.")

    print("\n[ALL TESTS PASSED SUCCESSFULLY!]")

if __name__ == "__main__":
    asyncio.run(run_tests())
