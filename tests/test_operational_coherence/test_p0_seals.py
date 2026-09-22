# -*- coding: utf-8 -*-
"""
tests/test_operational_coherence/test_p0_seals.py
Unit & Invariant Verification Suite for Operational Coherence (5 P0 Seals).
Verifies that all 5 critical operational failure modes are sealed.
"""

import os
import tempfile
import pytest

# P0.1
from core.kernel.cognitive_memory_buffer import CognitiveMemoryBuffer
from core.kernel.context_manager import ContextManager

# P0.2
from core.kernel.tool_contracts import (
    ToolContractRegistry,
    WriteFileContract,
    RunCommandContract
)
from core.kernel.capability_broker import capability_broker
from core.kernel.action_validator import validate_action, ActionDecision

# P0.3
from core.contracts.execution_receipt import (
    ExecutionReceipt,
    ExecutionStatus,
    CompletionStatus,
    CompletionCertificate
)
from core.verification.verifier import CompletionAuthority, VerificationResult
from core.contracts.verification_contract import FailureClassification, RecoveryStrategy

# P0.4
from core.os.routing.entity_extractor import IngressEntityExtractor
from core.os.routing.intent_router import CentralIntentRouter

# P0.5
from core.kernel.models import (
    MissionPlan,
    MissionNode,
    MissionNodeState,
    MissionContext
)
from core.kernel.dag_scheduler import DAGScheduler
from core.kernel.event_store import EventStore


# =========================================================================
# 1. P0.1: STATE CONTAMINATION & CACHE LEAK TESTS
# =========================================================================

def test_cognitive_memory_buffer_scoped_isolation():
    buf = CognitiveMemoryBuffer(max_history_turns=1, max_token_budget=10)
    messages_a = [
        {"role": "user", "content": "User input in mission A with secret A"},
        {"role": "assistant", "content": "Assistant output in mission A"},
        {"role": "user", "content": "Recent turn in mission A"}
    ]
    messages_b = [
        {"role": "user", "content": "User input in mission B with secret B"},
        {"role": "assistant", "content": "Assistant output in mission B"},
        {"role": "user", "content": "Recent turn in mission B"}
    ]

    buf.compress_messages(messages_a, mission_id="mission_A")
    buf.compress_messages(messages_b, mission_id="mission_B")

    engram_a = buf.get_mission_engram("mission_A")
    engram_b = buf.get_mission_engram("mission_B")

    assert "mission A" in engram_a
    assert "secret B" not in engram_a

    assert "mission B" in engram_b
    assert "secret A" not in engram_b


def test_cache_key_trace_generation():
    key_1 = CognitiveMemoryBuffer.generate_cache_key("mission_1", {"query": "test"})
    key_2 = CognitiveMemoryBuffer.generate_cache_key("mission_2", {"query": "test"})
    key_1_dup = CognitiveMemoryBuffer.generate_cache_key("mission_1", {"query": "test"})

    assert key_1 == key_1_dup
    assert key_1 != key_2  # Different missions MUST have different cache keys


def test_clear_mission_purges_ephemeral_state():
    buf = CognitiveMemoryBuffer(max_history_turns=1, max_token_budget=10)
    buf.compress_messages([
        {"role": "user", "content": "Ephemeral task data that contains extensive context " * 5},
        {"role": "assistant", "content": "Response with lots of detail " * 5},
        {"role": "user", "content": "Recent turn in mission"}
    ], mission_id="mission_to_clean")

    assert buf.get_mission_engram("mission_to_clean") != ""
    buf.clear_mission("mission_to_clean")
    assert buf.get_mission_engram("mission_to_clean") == ""


# =========================================================================
# 2. P0.2: CAPABILITY BROKER CONTRACT ENFORCEMENT TESTS
# =========================================================================

def test_tool_contract_valid_invocation():
    is_valid, err, parsed = ToolContractRegistry.validate_tool_call(
        "write_to_file",
        {"TargetFile": "test.txt", "CodeContent": "print(1)"}
    )
    assert is_valid is True
    assert err is None
    assert isinstance(parsed, WriteFileContract)
    assert parsed.TargetFile == "test.txt"


def test_tool_contract_missing_field_fail_closed():
    is_valid, err, parsed = ToolContractRegistry.validate_tool_call(
        "write_to_file",
        {"TargetFile": "test.txt"}  # Missing CodeContent!
    )
    assert is_valid is False
    assert err["error_type"] == "CONTRACT_VIOLATION"
    assert "CodeContent" in err["missing_fields"]
    assert parsed is None


def test_capability_broker_validate_tool_call():
    is_valid, err, _ = capability_broker.validate_tool_call(
        "run_command",
        {"CommandLine": "echo hello"}
    )
    assert is_valid is True

    # Missing CommandLine
    is_valid, err, _ = capability_broker.validate_tool_call(
        "run_command",
        {"Cwd": "/tmp"}
    )
    assert is_valid is False
    assert err["error_type"] == "CONTRACT_VIOLATION"


def test_action_validator_unknown_tool_and_schema_invalid():
    # Unknown tool
    verdict = validate_action("non_existent_tool_xyz", {}, known_tools={"write_to_file"})
    assert verdict.decision == ActionDecision.UNKNOWN_TOOL

    # Schema invalid
    verdict = validate_action("write_to_file", {"TargetFile": "abc.txt"}, known_tools={"write_to_file"}, check_firewall=False)
    assert verdict.decision == ActionDecision.SCHEMA_INVALID


# =========================================================================
# 3. P0.3: EXECUTION SUCCESS VS COMPLETION TRUTH TESTS
# =========================================================================

def test_execution_receipt_cannot_declare_completed():
    receipt = ExecutionReceipt(
        task_id="task-1",
        tool_name="write_to_file",
        exit_code=0
    )
    assert receipt.status == ExecutionStatus.EXECUTED
    # ExecutionReceipt has no COMPLETED status
    assert receipt.status != "COMPLETED"


def test_completion_authority_fails_on_empty_file():
    with tempfile.NamedTemporaryFile(delete=False) as f:
        empty_path = f.name
    
    try:
        # File is 0 bytes
        receipt = ExecutionReceipt(
            task_id="task-1",
            tool_name="write_to_file",
            exit_code=0,
            output_artifact_path=empty_path
        )
        cert = CompletionAuthority.evaluate_completion(
            mission_id="mission-empty-test",
            receipts=[receipt],
            target_path=empty_path
        )
        assert cert.status == CompletionStatus.FAILED_VERIFICATION
        assert cert.artifact_exists is False
        assert any("0 bytes" in r for r in cert.reasons)
    finally:
        if os.path.exists(empty_path):
            os.remove(empty_path)


def test_completion_authority_fails_on_unchanged_checksum():
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
        f.write("unchanged initial content")
        file_path = f.name

    try:
        import hashlib
        with open(file_path, "rb") as f:
            initial_sha = hashlib.sha256(f.read()).hexdigest()

        receipt = ExecutionReceipt(
            task_id="task-1",
            tool_name="write_to_file",
            exit_code=0,
            output_artifact_path=file_path
        )
        cert = CompletionAuthority.evaluate_completion(
            mission_id="mission-unchanged-test",
            receipts=[receipt],
            target_path=file_path,
            initial_checksum=initial_sha
        )
        assert cert.status == CompletionStatus.FAILED_VERIFICATION
        assert cert.state_changed is False
        assert any("checksum identical" in r for r in cert.reasons)
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


def test_completion_authority_passes_on_valid_evidence():
    with tempfile.NamedTemporaryFile(delete=False, mode="w") as f:
        f.write("freshly mutated and verified content")
        file_path = f.name

    try:
        receipt = ExecutionReceipt(
            task_id="task-1",
            tool_name="write_to_file",
            exit_code=0,
            output_artifact_path=file_path
        )
        cert = CompletionAuthority.evaluate_completion(
            mission_id="mission-valid-test",
            receipts=[receipt],
            target_path=file_path,
            initial_checksum="old_different_checksum"
        )
        assert cert.status == CompletionStatus.COMPLETED
        assert cert.artifact_exists is True
        assert cert.schema_valid is True
        assert cert.state_changed is True
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)


# =========================================================================
# 4. P0.4: INGRESS ENTITY EXTRACTION & MULTI-FILE ASSERTION
# =========================================================================

def test_entity_extractor_single_file():
    extracted = IngressEntityExtractor.extract("Vui lòng đọc file report.json và tóm tắt.")
    assert extracted.is_multi_resource is False
    assert extracted.scope == "SINGLE_RESOURCE"
    assert "report.json" in extracted.target_paths


def test_entity_extractor_multi_file():
    extracted = IngressEntityExtractor.extract(
        "Refactor hai file core/kernel/models.py và core/os/routing/intent_router.py ngay."
    )
    assert extracted.is_multi_resource is True
    assert extracted.scope == "MULTI_RESOURCE"
    assert len(extracted.target_paths) >= 2


def test_entity_extractor_glob_pattern():
    extracted = IngressEntityExtractor.extract("Kiểm tra và sửa toàn bộ code trong src/**/*.py")
    assert extracted.is_multi_resource is True
    assert extracted.scope == "MULTI_RESOURCE"
    assert any("**/*.py" in g for g in extracted.glob_patterns)


def test_intent_router_enforces_multi_resource_scope():
    router = CentralIntentRouter()
    decision = router.route("Sửa hai file a.py và b.py đồng thời")
    assert decision.scope == "MULTI_RESOURCE"
    assert decision.is_compound is True
    assert "MULTI_RESOURCE" in decision.tags


# =========================================================================
# 5. P0.5: TASKGRAPH DELIVERY GUARANTEE & CONSERVATION
# =========================================================================

@pytest.mark.asyncio
async def test_dag_scheduler_orphan_detection_and_partial_failure():
    from core.kernel.models import MissionEdge
    event_store = EventStore()
    scheduler = DAGScheduler(event_store=event_store, capability_broker=capability_broker)

    # Create 3 sequential nodes: node 1 -> node 2 -> node 3
    node1 = MissionNode(id="node_1", name="Task 1", capability="write_code", state=MissionNodeState.PENDING)
    node2 = MissionNode(id="node_2", name="Task 2", capability="write_code", state=MissionNodeState.PENDING)
    node3 = MissionNode(id="node_3", name="Task 3", capability="write_code", state=MissionNodeState.PENDING)

    edges = [
        MissionEdge(source="node_1", target="node_2"),
        MissionEdge(source="node_2", target="node_3")
    ]
    plan = MissionPlan(nodes={"node_1": node1, "node_2": node2, "node_3": node3}, edges=edges)
    context = MissionContext(goal="Test DAG orphan handling")

    async def mock_executor(node: MissionNode, ctx: dict):
        if node.id == "node_1":
            node.state = MissionNodeState.SUCCESS
            return True
        elif node.id == "node_2":
            raise RuntimeError("Task 2 failed deliberately")
        # node_3 won't be reached because node 2 fails

    success = await scheduler.execute_plan("mission_orphan_test", plan, context, mock_executor)

    assert success is False
    # Node 3 was never scheduled; it must be converted to ABORTED (Orphan task)
    assert node3.state in (MissionNodeState.ABORTED, MissionNodeState.CANCELLED)
    assert "ORPHAN" in (node3.error or "")

    # Check conservation: planned == verified + aborted
    planned = len(plan.nodes)
    verified = sum(1 for n in plan.nodes.values() if n.state == MissionNodeState.SUCCESS)
    aborted = sum(1 for n in plan.nodes.values() if n.state in (MissionNodeState.FAILED, MissionNodeState.ABORTED, MissionNodeState.CANCELLED))
    assert planned == verified + aborted == 3
