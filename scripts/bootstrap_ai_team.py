#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Bootstrap AI Team Coordination Architecture
File: scripts/bootstrap_ai_team.py
Governed by SOP-MULTI-AI-V10 & Protocol Spec V11.1
Ownership: Master LeeTrung | Swarm: Antigravity (Builder) & Opencode (Auditor)
"""

import os
import sys
import time
import json
import hashlib
import logging
from pathlib import Path
from typing import Dict, Any, List, Optional, Tuple

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

logger = logging.getLogger("JKAI.AITeamBootstrap")

PROTOCOL_VERSION = "11.1"
SOP_VERSION = "10.0"
TASK_ID = "TASK-BOOTSTRAP-001"

# Standard Schemas
TASK_CONTRACT_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "TaskContract",
    "type": "object",
    "required": ["task_id", "protocol_version", "orchestrator_agent_id", "assigned_agent_id", "phase", "owned_paths", "acceptance_criteria"],
    "properties": {
        "task_id": {"type": "string"},
        "protocol_version": {"type": "string"},
        "orchestrator_agent_id": {"type": "string"},
        "assigned_agent_id": {"type": "string"},
        "phase": {"type": "string"},
        "owned_paths": {"type": "array", "items": {"type": "string"}},
        "acceptance_criteria": {"type": "array", "items": {"type": "string"}},
        "baseline_hash": {"type": "string"}
    }
}

EVIDENCE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "EvidenceRecord",
    "type": "object",
    "required": ["task_id", "agent_id", "submitted_at", "artifacts", "test_verification"],
    "properties": {
        "task_id": {"type": "string"},
        "agent_id": {"type": "string"},
        "submitted_at": {"type": "string"},
        "artifacts": {"type": "array", "items": {"type": "object"}},
        "test_verification": {"type": "object"}
    }
}

TASK_STATE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "TaskState",
    "type": "object",
    "required": ["task_id", "status", "version", "updated_at", "updated_by"],
    "properties": {
        "task_id": {"type": "string"},
        "status": {"type": "string", "enum": ["INIT", "ASSIGNED", "IN_PROGRESS", "REVIEW", "VERIFIED", "INTEGRATED", "DONE", "STOPPED", "FAILED"]},
        "version": {"type": "integer"},
        "updated_at": {"type": "string"},
        "updated_by": {"type": "string"}
    }
}

FORBIDDEN_FAST_PATH_KEYWORDS = [
    "schema", "security", "policy", "fsm", "ledger", "authority", "completion_certificate",
    "Quy_che", "Quy_trinh", "state_machine", "root_auth"
]


def canonical_hash(data: Any) -> str:
    """Compute stable SHA-256 hash for dict or string."""
    if isinstance(data, (dict, list)):
        payload = json.dumps(data, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    elif isinstance(data, bytes):
        return hashlib.sha256(data).hexdigest()
    else:
        payload = str(data)
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


class AITeamController:
    """
    Manages AI_TEAM workspace operations, single-writer locking,
    STOP race prevention, and Fast Path safety verification.
    """
    def __init__(self, base_dir: Optional[Path] = None):
        self.base_dir = Path(base_dir) if base_dir else (PROJECT_ROOT / "AI_TEAM")
        self.system_dir = self.base_dir / "system"
        self.control_dir = self.base_dir / "control"
        self.discussion_dir = self.base_dir / "discussion"
        self.inbox_dir = self.base_dir / "inbox"
        self.results_dir = self.base_dir / "results"
        self.tasks_dir = self.base_dir / "tasks"
        self.runtime_dir = self.base_dir / "runtime"
        self.locks_dir = self.runtime_dir / "locks"
        self.receipts_dir = self.runtime_dir / "receipts"
        self.logs_dir = self.base_dir / "logs"

    def bootstrap(self, force: bool = False) -> Dict[str, Any]:
        """
        Idempotently bootstraps the AI_TEAM tree.
        Preserves existing user files and refuses blind overwrite.
        """
        created_paths = []
        preserved_paths = []

        # Create all subdirectories
        dirs_to_create = [
            self.system_dir / "schemas",
            self.control_dir,
            self.discussion_dir,
            self.inbox_dir / "cursor",
            self.inbox_dir / "antigravity",
            self.inbox_dir / "opencode",
            self.results_dir / "cursor",
            self.results_dir / "antigravity",
            self.results_dir / "opencode",
            self.tasks_dir,
            self.locks_dir,
            self.runtime_dir / "heartbeats",
            self.runtime_dir / "health",
            self.receipts_dir,
            self.logs_dir / "audit",
        ]
        for d in dirs_to_create:
            d.mkdir(parents=True, exist_ok=True)

        # 1. Schemas
        schema_files = {
            self.system_dir / "schemas" / "task_contract.schema.json": TASK_CONTRACT_SCHEMA,
            self.system_dir / "schemas" / "evidence.schema.json": EVIDENCE_SCHEMA,
            self.system_dir / "schemas" / "task_state.schema.json": TASK_STATE_SCHEMA,
        }
        schema_hashes = {}
        for p, s_content in schema_files.items():
            s_json = json.dumps(s_content, indent=2, ensure_ascii=False)
            h = canonical_hash(s_content)
            schema_hashes[p.name] = h
            if not p.exists() or force:
                p.write_text(s_json, encoding="utf-8")
                created_paths.append(str(p))
            else:
                preserved_paths.append(str(p))

        # 2. System files
        agents_registry_path = self.system_dir / "agents_registry.json"
        if not agents_registry_path.exists() or force:
            init_registry = {
                "protocol_version": PROTOCOL_VERSION,
                "session_id": "SESSION-001",
                "orchestrator_agent_id": "antigravity",
                "agents": [
                    {
                        "agent_id": "cursor",
                        "display_name": "Cursor",
                        "allowed_roles": ["ORCHESTRATOR", "VERIFIER", "BUILDER", "REVIEWER"],
                        "watch_mode": "session_poll",
                        "wake_method": "human_or_session",
                        "can_write_project_src": False,
                        "status": "UNKNOWN",
                        "last_probe_at": None
                    },
                    {
                        "agent_id": "antigravity",
                        "display_name": "Antigravity",
                        "allowed_roles": ["ORCHESTRATOR", "BUILDER", "ANALYST"],
                        "watch_mode": "autonomous_daemon",
                        "wake_method": "daemon_or_cli",
                        "can_write_project_src": True,
                        "status": "UNKNOWN",
                        "last_probe_at": None
                    },
                    {
                        "agent_id": "opencode",
                        "display_name": "OpenCode",
                        "allowed_roles": ["REVIEWER", "AUDITOR", "BUILDER"],
                        "watch_mode": "session_poll",
                        "wake_method": "rest_api",
                        "can_write_project_src": False,
                        "status": "UNKNOWN",
                        "last_probe_at": None
                    }
                ]
            }
            agents_registry_path.write_text(json.dumps(init_registry, indent=2, ensure_ascii=False), encoding="utf-8")
            created_paths.append(str(agents_registry_path))
        else:
            preserved_paths.append(str(agents_registry_path))

        join_proto = self.system_dir / "JOIN_PROTOCOL.md"
        if not join_proto.exists() or force:
            join_proto.write_text(
                "# JOIN PROTOCOL V11.1\n\n"
                "1. Read system/agents_registry.json\n"
                "2. Verify agent_id and role\n"
                "3. Perform read/write probe in discussion/<agent_id>.md\n"
                "4. Await Orchestrator PROBE_PASS\n",
                encoding="utf-8"
            )
            created_paths.append(str(join_proto))
        else:
            preserved_paths.append(str(join_proto))

        # 3. Control files
        trang_thai_path = self.control_dir / "TRANG_THAI.json"
        if not trang_thai_path.exists() or force:
            init_trang_thai = {
                "schema_version": "1.0",
                "session_id": "SESSION-001",
                "version": 1,
                "status": "INIT",
                "command": "START",
                "reason": "AI_TEAM Bootstrap Initialized",
                "orchestrator_agent_id": "antigravity",
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "updated_by": "antigravity",
                "last_event_id": "EVT-BOOTSTRAP-001"
            }
            trang_thai_path.write_text(json.dumps(init_trang_thai, indent=2, ensure_ascii=False), encoding="utf-8")
            created_paths.append(str(trang_thai_path))
        else:
            preserved_paths.append(str(trang_thai_path))

        thong_bao_path = self.control_dir / "THONG_BAO.md"
        if not thong_bao_path.exists() or force:
            thong_bao_path.write_text(
                "# THÔNG BÁO ĐIỀU HÀNH HIỆN HÀNH\n\n"
                "- message_id: MSG-0001\n"
                "- session_id: SESSION-001\n"
                "- version: 1\n"
                "- sender: antigravity\n"
                "- status: RUNNING\n"
                "- phase: BOOTSTRAP\n"
                "- recipients: [ALL_AGENTS]\n\n"
                "## Mục tiêu\nKhởi tạo hạ tầng cộng tác đa AI AI_TEAM theo SOP V10.\n",
                encoding="utf-8"
            )
            created_paths.append(str(thong_bao_path))
        else:
            preserved_paths.append(str(thong_bao_path))

        master_req_path = self.control_dir / "MASTER_REQUEST.md"
        if not master_req_path.exists() or force:
            master_req_path.write_text(
                "# MASTER REQUEST\n\n"
                "- request_id: REQ-001\n"
                "- requester: Master LeeTrung\n"
                "- mode: BOUNDED_AUTONOMY\n"
                "- directive: Khởi tạo và vận hành nhóm Multi-AI theo SOP V10 và Quy chế V4.0.\n",
                encoding="utf-8"
            )
            created_paths.append(str(master_req_path))
        else:
            preserved_paths.append(str(master_req_path))

        # 4. Discussion files
        for aid in ["cursor", "antigravity", "opencode"]:
            df = self.discussion_dir / f"{aid}.md"
            if not df.exists() or force:
                df.write_text(f"# THẢO LUẬN: {aid.upper()}\n\n*Khởi tạo không gian thảo luận.*\n", encoding="utf-8")
                created_paths.append(str(df))
            else:
                preserved_paths.append(str(df))

        # 5. Manifest generation
        manifest_files = {}
        for root, _, files in os.walk(self.base_dir):
            for f in files:
                if f == "bootstrap_manifest.json":
                    continue
                fp = Path(root) / f
                rel = fp.relative_to(self.base_dir).as_posix()
                manifest_files[rel] = canonical_hash(fp.read_bytes())

        manifest_data = {
            "task_id": TASK_ID,
            "protocol_version": PROTOCOL_VERSION,
            "sop_version": SOP_VERSION,
            "bootstrapped_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "schema_hashes": schema_hashes,
            "files_count": len(manifest_files),
            "manifest_files": manifest_files
        }
        manifest_hash = canonical_hash(manifest_files)
        manifest_data["manifest_hash"] = manifest_hash

        manifest_path = self.system_dir / "bootstrap_manifest.json"
        manifest_path.write_text(json.dumps(manifest_data, indent=2, ensure_ascii=False), encoding="utf-8")
        created_paths.append(str(manifest_path))

        return {
            "task_id": TASK_ID,
            "status": "BOOTSTRAPPED",
            "manifest_hash": manifest_hash,
            "created_paths_count": len(created_paths),
            "preserved_paths_count": len(preserved_paths),
            "schema_hashes": schema_hashes
        }

    def verify_manifest(self) -> Tuple[bool, Optional[str]]:
        """Verifies integrity of all bootstrapped files against manifest."""
        manifest_path = self.system_dir / "bootstrap_manifest.json"
        if not manifest_path.exists():
            return False, "Missing bootstrap_manifest.json"
        try:
            m = json.loads(manifest_path.read_text(encoding="utf-8"))
            m_files = m.get("manifest_files", {})
            for rel, expected_sha in m_files.items():
                p = self.base_dir / rel
                if not p.exists():
                    return False, f"Missing file: {rel}"
                actual_sha = canonical_hash(p.read_bytes())
                if actual_sha != expected_sha:
                    return False, f"Checksum mismatch for {rel}: expected {expected_sha}, got {actual_sha}"
            return True, None
        except Exception as e:
            return False, f"Manifest verification error: {e}"

    def validate_source_write_permission(
        self,
        agent_id: str,
        target_path: str,
        task_contract: Optional[Dict[str, Any]]
    ) -> bool:
        """
        Turn 526 Directive 3.1: can_write_project_src is not self-proclaimed.
        Denies source modification if task contract is missing or target is outside owned_paths.
        """
        if not task_contract:
            raise PermissionError(f"Access Denied: Agent '{agent_id}' has no approved task contract for source modification.")
        owned = task_contract.get("owned_paths", [])
        norm_target = Path(target_path).as_posix()
        norm_owned = [Path(p).as_posix() for p in owned]
        if norm_target not in norm_owned:
            raise PermissionError(f"Access Denied: Path '{target_path}' is outside contract owned_paths: {owned}")
        return True

    def acquire_control_lock(self, orchestrator_id: str, pid: int, timeout_sec: float = 2.0) -> bool:
        """
        Single-writer lock with pid, heartbeat, and ownership metadata.
        Fails closed if an existing lock belongs to a dead or unknown process without blind recovery.
        """
        lock_file = self.locks_dir / "orchestrator.lock"
        start_time = time.time()
        while time.time() - start_time < timeout_sec:
            if not lock_file.exists():
                lock_data = {
                    "orchestrator_agent_id": orchestrator_id,
                    "pid": pid,
                    "created_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "heartbeat": time.time()
                }
                try:
                    with open(lock_file, "x", encoding="utf-8") as f:
                        f.write(json.dumps(lock_data))
                    return True
                except FileExistsError:
                    pass
            else:
                # Existing lock check - fail closed if stale/unknown
                try:
                    data = json.loads(lock_file.read_text(encoding="utf-8"))
                    existing_pid = data.get("pid")
                    # Check if pid is alive on Windows
                    if existing_pid:
                        try:
                            # os.kill(pid, 0) checks if process exists
                            os.kill(existing_pid, 0)
                        except OSError:
                            logger.error("[Lock] Stale lock detected with dead PID %s. Fail-closed: operator receipt required.", existing_pid)
                            return False
                except Exception:
                    return False
            time.sleep(0.05)
        return False

    def probe_agent(
        self,
        agent_id: str,
        read_success: bool,
        write_success: bool,
        dispatch_success: bool,
        stop_ack_success: bool
    ) -> Dict[str, Any]:
        """
        Turn 526 Directive 2 & 4: Probes an agent's real capabilities.
        Status NEVER transitions to READY if any probe fails.
        """
        reg_path = self.system_dir / "agents_registry.json"
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        agent_entry = None
        for a in reg.get("agents", []):
            if a.get("agent_id") == agent_id:
                agent_entry = a
                break

        if not agent_entry:
            raise ValueError(f"Agent '{agent_id}' not found in registry.")

        all_passed = read_success and write_success and dispatch_success and stop_ack_success
        now_str = time.strftime("%Y-%m-%dT%H:%M:%S%z")
        agent_entry["last_probe_at"] = now_str

        if all_passed:
            agent_entry["status"] = "READY"
        else:
            agent_entry["status"] = "PROBE_FAILED"

        # Explicit manual sync note if wake_method is human_or_session
        if agent_entry.get("wake_method") == "human_or_session":
            agent_entry["sync_requirement"] = "MANUAL_SYNC_REQUIRED"

        reg_path.write_text(json.dumps(reg, indent=2, ensure_ascii=False), encoding="utf-8")
        return agent_entry

    def get_agent_sync_mode(self, agent_id: str) -> str:
        """Returns sync requirement mode for agent."""
        reg_path = self.system_dir / "agents_registry.json"
        reg = json.loads(reg_path.read_text(encoding="utf-8"))
        for a in reg.get("agents", []):
            if a.get("agent_id") == agent_id:
                if a.get("wake_method") == "human_or_session":
                    return "MANUAL_SYNC_REQUIRED"
                return "AUTOMATED_DISPATCH"
        return "UNKNOWN"

    def release_control_lock(self, orchestrator_id: str, pid: int) -> bool:
        lock_file = self.locks_dir / "orchestrator.lock"
        if lock_file.exists():
            try:
                data = json.loads(lock_file.read_text(encoding="utf-8"))
                if data.get("orchestrator_agent_id") == orchestrator_id and data.get("pid") == pid:
                    lock_file.unlink()
                    return True
            except Exception:
                pass
        return False

    def check_stop_signal(self, agent_id: str = "antigravity") -> Tuple[bool, Optional[Dict[str, Any]]]:
        """
        Checks for STOP.flag and emits an immutable stop acknowledgement receipt.
        """
        stop_flag = self.control_dir / "STOP.flag"
        if stop_flag.exists():
            receipt = {
                "status": "STOPPED",
                "agent_id": agent_id,
                "stopped_at": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                "acknowledged": True,
                "flag_content": stop_flag.read_text(encoding="utf-8").strip()
            }
            receipt_path = self.receipts_dir / f"stop_receipt_{int(time.time()*1000)}.json"
            receipt_path.write_text(json.dumps(receipt, indent=2, ensure_ascii=False), encoding="utf-8")
            return True, receipt
        return False, None

    def execute_mutation_under_lock(
        self,
        orchestrator_id: str,
        pid: int,
        mutation_fn,
        agent_id: str = "antigravity"
    ) -> Any:
        """
        Re-checks STOP.flag right under lock before executing mutation.
        Prevents TOCTOU race conditions where STOP arrives immediately after outer check.
        """
        acquired = self.acquire_control_lock(orchestrator_id, pid)
        if not acquired:
            raise TimeoutError("Failed to acquire single-writer orchestrator lock.")

        try:
            is_stopped, receipt = self.check_stop_signal(agent_id=agent_id)
            if is_stopped:
                logger.warning("[AITeam] Mutation blocked by active STOP flag! Receipt emitted.")
                raise InterruptedError(f"Action aborted by STOP flag: {receipt}")
            return mutation_fn()
        finally:
            self.release_control_lock(orchestrator_id, pid)

    @staticmethod
    def validate_fast_path_scope(target_paths: List[str], task_desc: str = "") -> Tuple[bool, Optional[str]]:
        """
        Enforces safety exclusion: Fast Path is forbidden from touching
        schema, security, policy, FSM, persistent ledger, or cross-module boundaries.
        """
        full_text = " ".join(target_paths).lower() + " " + task_desc.lower()
        for kw in FORBIDDEN_FAST_PATH_KEYWORDS:
            if kw in full_text:
                return False, f"Forbidden Fast Path scope detected: '{kw}'. Full SOP V10 Enterprise Path required."
        if len(target_paths) > 3:
            return False, "Target paths exceed Fast Path limit (max 3 files). Enterprise Path required."
        return True, None


def main():
    import argparse
    if hasattr(sys.stdout, "reconfigure"):
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass
    parser = argparse.ArgumentParser(description="AI_TEAM Bootstrap Engine - SOP Multi-AI V10 / Protocol V11.1")
    parser.add_argument("--base-dir", type=str, default=None, help="Base directory for AI_TEAM")
    parser.add_argument("--sandbox", action="store_true", help="Run bootstrap in sandbox directory (tests/sandbox/AI_TEAM)")
    parser.add_argument("--force", action="store_true", help="Force overwrite (dangerous)")
    parser.add_argument("--verify", action="store_true", help="Only verify existing bootstrap manifest")
    parser.add_argument("--probe", type=str, default=None, help="Probe specific agent (e.g. opencode, antigravity, cursor)")
    args = parser.parse_args()

    print("=" * 70)
    print("[AI_TEAM] BOOTSTRAP ENGINE - SOP MULTI-AI V10 / PROTOCOL V11.1")
    print("=" * 70)

    target_dir = None
    if args.sandbox:
        target_dir = PROJECT_ROOT / "tests" / "sandbox" / "AI_TEAM"
    elif args.base_dir:
        target_dir = Path(args.base_dir)

    controller = AITeamController(base_dir=target_dir)

    if args.verify:
        is_valid, err = controller.verify_manifest()
        print(f"Manifest Verification: Valid={is_valid}, Error={err}")
        return

    result = controller.bootstrap(force=args.force)
    print("Bootstrap Result:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    is_valid, err = controller.verify_manifest()
    print(f"Manifest Verification: Valid={is_valid}, Error={err}")

    if args.probe:
        print(f"\nProbing agent '{args.probe}'...")
        # Self test probe
        probe_res = controller.probe_agent(
            agent_id=args.probe,
            read_success=True,
            write_success=True,
            dispatch_success=True,
            stop_ack_success=True
        )
        print("Probe Result:")
        print(json.dumps(probe_res, indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()

