# -*- coding: utf-8 -*-
"""
Acceptance Test Suite for AI_TEAM Bootstrap Engine
File: tests/test_bootstrap_ai_team.py
Governed by SOP-MULTI-AI-V10 & Opencode Turn 524 Directives
Ownership: Master LeeTrung | Swarm: Antigravity (Builder) & Opencode (Auditor)
"""

import os
import sys
import json
import pytest
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts.bootstrap_ai_team import (
    AITeamController,
    TASK_ID,
    PROTOCOL_VERSION,
    SOP_VERSION
)


def test_bootstrap_idempotent_without_overwrite(tmp_path: Path):
    """
    Opencode Directive 3 (Test 1): Bootstrap is idempotent and never blindly overwrites
    existing user files on subsequent runs.
    """
    controller = AITeamController(base_dir=tmp_path / "AI_TEAM")
    res1 = controller.bootstrap(force=False)
    assert res1["status"] == "BOOTSTRAPPED"
    assert res1["created_paths_count"] > 0

    # User modifies a file
    custom_msg = tmp_path / "AI_TEAM" / "control" / "THONG_BAO.md"
    custom_msg.write_text("# USER CUSTOM ANNOUNCEMENT - DO NOT OVERWRITE", encoding="utf-8")

    # Second bootstrap run
    res2 = controller.bootstrap(force=False)
    assert res2["status"] == "BOOTSTRAPPED"
    assert res2["preserved_paths_count"] > 0
    # Custom content must be preserved
    assert custom_msg.read_text(encoding="utf-8") == "# USER CUSTOM ANNOUNCEMENT - DO NOT OVERWRITE"


def test_bootstrap_rejects_schema_mismatch(tmp_path: Path):
    """
    Opencode Directive 3 (Test 2): Schema or manifest tampering is detected and fails closed.
    """
    controller = AITeamController(base_dir=tmp_path / "AI_TEAM")
    controller.bootstrap(force=False)

    # Tamper with schema file
    schema_path = tmp_path / "AI_TEAM" / "system" / "schemas" / "task_contract.schema.json"
    schema_path.write_text('{"tampered": true}', encoding="utf-8")

    is_valid, err = controller.verify_manifest()
    assert is_valid is False
    assert "Checksum mismatch" in err


def test_registry_stays_unknown_before_probe(tmp_path: Path):
    """
    Opencode Directive 3 (Test 3): Registry agents start as UNKNOWN and cannot self-proclaim READY.
    """
    controller = AITeamController(base_dir=tmp_path / "AI_TEAM")
    controller.bootstrap(force=False)

    reg_path = tmp_path / "AI_TEAM" / "system" / "agents_registry.json"
    assert reg_path.exists()
    reg = json.loads(reg_path.read_text(encoding="utf-8"))

    for agent in reg["agents"]:
        assert agent["status"] == "UNKNOWN", f"Agent {agent['agent_id']} improperly claimed {agent['status']}"
        assert agent["last_probe_at"] is None


def test_single_writer_control_lock(tmp_path: Path):
    """
    Opencode Directive 3 (Test 4): Single-writer orchestrator lock with pid & heartbeat metadata.
    """
    controller = AITeamController(base_dir=tmp_path / "AI_TEAM")
    controller.bootstrap(force=False)

    # Writer 1 acquires lock
    assert controller.acquire_control_lock(orchestrator_id="antigravity", pid=1001) is True

    # Writer 2 attempts lock while Writer 1 holds it -> must fail
    assert controller.acquire_control_lock(orchestrator_id="cursor", pid=2002, timeout_sec=0.2) is False

    # Writer 1 releases lock
    assert controller.release_control_lock(orchestrator_id="antigravity", pid=1001) is True

    # Writer 2 can now acquire lock
    assert controller.acquire_control_lock(orchestrator_id="cursor", pid=2002) is True
    assert controller.release_control_lock(orchestrator_id="cursor", pid=2002) is True


def test_stop_race_recheck_before_mutation(tmp_path: Path):
    """
    Opencode Directive 3 (Test 5): Re-checks STOP.flag right under lock before mutating.
    Aborts mutation immediately if STOP signal arrives.
    """
    controller = AITeamController(base_dir=tmp_path / "AI_TEAM")
    controller.bootstrap(force=False)

    # Create STOP.flag
    stop_flag = tmp_path / "AI_TEAM" / "control" / "STOP.flag"
    stop_flag.write_text("STOP_ORDER_BY_MASTER_LEETRUNG", encoding="utf-8")

    mutated = [False]
    def mutation_action():
        mutated[0] = True

    with pytest.raises(InterruptedError):
        controller.execute_mutation_under_lock(
            orchestrator_id="antigravity",
            pid=1001,
            mutation_fn=mutation_action
        )

    assert mutated[0] is False, "Mutation was executed despite active STOP flag!"


def test_stop_acknowledgement_receipt(tmp_path: Path):
    """
    Opencode Directive 3 (Test 6): STOP signal generates an immutable acknowledgement receipt.
    """
    controller = AITeamController(base_dir=tmp_path / "AI_TEAM")
    controller.bootstrap(force=False)

    stop_flag = tmp_path / "AI_TEAM" / "control" / "STOP.flag"
    stop_flag.write_text("EMERGENCY_HALT", encoding="utf-8")

    is_stopped, receipt = controller.check_stop_signal(agent_id="antigravity")
    assert is_stopped is True
    assert receipt is not None
    assert receipt["status"] == "STOPPED"
    assert receipt["acknowledged"] is True
    assert receipt["agent_id"] == "antigravity"

    receipts = list((tmp_path / "AI_TEAM" / "runtime" / "receipts").glob("stop_receipt_*.json"))
    assert len(receipts) == 1


def test_fast_path_rejects_forbidden_scope():
    """
    Opencode Directive 3 (Test 7): Fast Path rejects schema, policy, security, FSM, and cross-module scopes.
    """
    # 1. Schema modification -> rejected
    allowed, reason = AITeamController.validate_fast_path_scope(["core/memory/completion_authority.py"])
    assert allowed is False
    assert "Forbidden Fast Path scope" in reason

    # 2. Security / Policy -> rejected
    allowed, reason = AITeamController.validate_fast_path_scope(["rules/SECURITY.md"], "update security policy")
    assert allowed is False
    assert "Forbidden Fast Path scope" in reason

    # 3. Too many files -> rejected
    allowed, reason = AITeamController.validate_fast_path_scope(["f1.py", "f2.py", "f3.py", "f4.py"])
    assert allowed is False
    assert "exceed Fast Path limit" in reason

    # 4. Safe single micro-task file -> allowed
    allowed, reason = AITeamController.validate_fast_path_scope(["services/formatting_helper.py"], "fix string indent")
    assert allowed is True
    assert reason is None


def test_bootstrap_manifest_hash(tmp_path: Path):
    """
    Opencode Directive 3 (Test 8): Generates bootstrap_manifest.json with SHA-256 for all files.
    """
    controller = AITeamController(base_dir=tmp_path / "AI_TEAM")
    res = controller.bootstrap(force=False)
    assert "manifest_hash" in res

    is_valid, err = controller.verify_manifest()
    assert is_valid is True
    assert err is None


def test_no_contract_denies_source_write(tmp_path: Path):
    """
    Turn 526 Directive 4 (Test 9): Denies source modification if task contract is missing
    or target path is outside owned_paths.
    """
    controller = AITeamController(base_dir=tmp_path / "AI_TEAM")

    # Missing contract
    with pytest.raises(PermissionError) as exc_info:
        controller.validate_source_write_permission(
            agent_id="antigravity",
            target_path="core/memory/some_file.py",
            task_contract=None
        )
    assert "no approved task contract" in str(exc_info.value)

    # Path outside owned_paths
    contract = {"owned_paths": ["services/calculator.py"]}
    with pytest.raises(PermissionError) as exc_info:
        controller.validate_source_write_permission(
            agent_id="antigravity",
            target_path="core/memory/some_file.py",
            task_contract=contract
        )
    assert "outside contract owned_paths" in str(exc_info.value)

    # Path inside owned_paths -> succeeds
    assert controller.validate_source_write_permission(
        agent_id="antigravity",
        target_path="services/calculator.py",
        task_contract=contract
    ) is True


def test_dead_or_unknown_lock_owner_fails_closed(tmp_path: Path):
    """
    Turn 526 Directive 4 (Test 10): Stale lock from a dead PID fails closed without blind overwrite.
    """
    controller = AITeamController(base_dir=tmp_path / "AI_TEAM")
    controller.bootstrap(force=False)

    # Write a fake lock with non-existent PID (e.g. 999999)
    lock_file = tmp_path / "AI_TEAM" / "runtime" / "locks" / "orchestrator.lock"
    lock_file.write_text(json.dumps({
        "orchestrator_agent_id": "ghost_process",
        "pid": 999999,
        "created_at": "2026-10-19T00:00:00Z"
    }), encoding="utf-8")

    # Attempt to acquire lock -> must fail closed
    assert controller.acquire_control_lock(orchestrator_id="antigravity", pid=1001, timeout_sec=0.2) is False


def test_manual_sync_is_explicit_when_dispatch_missing(tmp_path: Path):
    """
    Turn 526 Directive 4 (Test 11): When agent wake_method is human_or_session (e.g. Cursor),
    sync mode is explicitly declared as MANUAL_SYNC_REQUIRED.
    """
    controller = AITeamController(base_dir=tmp_path / "AI_TEAM")
    controller.bootstrap(force=False)

    cursor_mode = controller.get_agent_sync_mode("cursor")
    assert cursor_mode == "MANUAL_SYNC_REQUIRED"

    opencode_mode = controller.get_agent_sync_mode("opencode")
    assert opencode_mode == "AUTOMATED_DISPATCH"


def test_probe_failure_cannot_set_ready(tmp_path: Path):
    """
    Turn 526 Directive 4 (Test 12): Agent probe failure transitions to PROBE_FAILED,
    and NEVER sets status to READY.
    """
    controller = AITeamController(base_dir=tmp_path / "AI_TEAM")
    controller.bootstrap(force=False)

    # Probe with 1 failure
    result = controller.probe_agent(
        agent_id="cursor",
        read_success=True,
        write_success=True,
        dispatch_success=False,  # Failed dispatch
        stop_ack_success=True
    )
    assert result["status"] == "PROBE_FAILED"
    assert result["status"] != "READY"

    # Successful probe
    success_result = controller.probe_agent(
        agent_id="antigravity",
        read_success=True,
        write_success=True,
        dispatch_success=True,
        stop_ack_success=True
    )
    assert success_result["status"] == "READY"

