# -*- coding: utf-8 -*-
# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/kernel/task_contract_store.py
# - Role: Session-Level TaskContract & PolicySnapshot Store
# - Ownership: Master LeeTrung
# - Status: Active | Version: SDS v26.3 (Immutable Policy Snapshot)
# -----------------------------------------------------------------------------

import logging
import threading
from typing import Dict, Optional, Any
from core.kernel.policy_snapshot import PolicySnapshot, create_policy_snapshot

logger = logging.getLogger("JKAI.TaskContractStore")

_lock = threading.RLock()
_contract_store: Dict[str, Any] = {}          # task_id → TaskContract
_policy_store: Dict[str, Any] = {}            # task_id → CognitivePolicy
_snapshot_store: Dict[str, PolicySnapshot] = {} # task_id → PolicySnapshot


# --------------------------------------------------------------------------- #
# Policy Snapshot Store (P0 Immutable Governance)                             #
# --------------------------------------------------------------------------- #

def set_policy_snapshot(task_id: str, snapshot: PolicySnapshot) -> None:
    """Register an immutable PolicySnapshot for the given task_id."""
    with _lock:
        _snapshot_store[task_id] = snapshot
    logger.debug(f"[SNAPSHOT-STORE] Registered PolicySnapshot id={snapshot.snapshot_id} for task_id={task_id}")


def get_policy_snapshot(task_id: str) -> Optional[PolicySnapshot]:
    """Retrieve the PolicySnapshot for the given task_id."""
    with _lock:
        return _snapshot_store.get(task_id)


def get_or_create_policy_snapshot(task_id: str) -> PolicySnapshot:
    """Retrieve active PolicySnapshot or auto-create a default snapshot if missing."""
    with _lock:
        snap = _snapshot_store.get(task_id)
        if not snap:
            snap = create_policy_snapshot(mission_id=task_id)
            _snapshot_store[task_id] = snap
            logger.info(f"[SNAPSHOT-STORE] Auto-initialized default PolicySnapshot id={snap.snapshot_id} for task_id={task_id}")
        return snap


# --------------------------------------------------------------------------- #
# Contract Store                                                               #
# --------------------------------------------------------------------------- #

def set_active_contract(task_id: str, contract: Any) -> None:
    """Register a TaskContract for the given task_id."""
    with _lock:
        _contract_store[task_id] = contract
    logger.debug(f"[CONTRACT-STORE] Registered TaskContract for task_id={task_id}")


def get_active_contract(task_id: str) -> Optional[Any]:
    """Retrieve the active TaskContract for the given task_id. Returns None if not set."""
    with _lock:
        return _contract_store.get(task_id)


def get_or_create_default_contract(task_id: str) -> Any:
    """Retrieve active contract or create default contract if missing."""
    with _lock:
        contract = _contract_store.get(task_id)
        if not contract:
            try:
                from prompt_engine.task_contract import TaskContract, DecisionAuthority
                contract = TaskContract(
                    objective="Default Runtime Execution",
                    decision_authority=DecisionAuthority(
                        can_modify_files=True,
                        can_delete_files=False,
                        can_send_external_message=True,
                        can_execute_shell=False
                    )
                )
                _contract_store[task_id] = contract
                logger.info(f"[CONTRACT-STORE] Registered default TaskContract for task_id={task_id}")
            except Exception as e:
                logger.warning(f"[CONTRACT-STORE] Auto-init default contract failed: {e}")
        return _contract_store.get(task_id)


def clear_contract(task_id: str) -> None:
    """Remove the TaskContract for the given task_id (e.g., on task completion)."""
    with _lock:
        _contract_store.pop(task_id, None)
    logger.debug(f"[CONTRACT-STORE] Cleared TaskContract for task_id={task_id}")


# --------------------------------------------------------------------------- #
# Policy Store                                                                 #
# --------------------------------------------------------------------------- #

def set_active_policy(task_id: str, policy: Any) -> None:
    """Register a CognitivePolicy for the given task_id."""
    with _lock:
        _policy_store[task_id] = policy
    logger.debug(f"[POLICY-STORE] Registered CognitivePolicy for task_id={task_id}")


def get_active_policy(task_id: str) -> Optional[Any]:
    """Retrieve the active CognitivePolicy for the given task_id. Returns None if not set."""
    with _lock:
        return _policy_store.get(task_id)


def clear_policy(task_id: str) -> None:
    """Remove the CognitivePolicy for the given task_id."""
    with _lock:
        _policy_store.pop(task_id, None)
    logger.debug(f"[POLICY-STORE] Cleared CognitivePolicy for task_id={task_id}")


# --------------------------------------------------------------------------- #
# Convenience: clear everything for a task                                     #
# --------------------------------------------------------------------------- #

def clear_task(task_id: str) -> None:
    """Remove contract, snapshot, and policy for the given task_id."""
    with _lock:
        clear_contract(task_id)
        clear_policy(task_id)
        _snapshot_store.pop(task_id, None)


def list_active_tasks() -> list:
    """Return list of all task_ids with registered contracts (for introspection/debugging)."""
    with _lock:
        return list(_contract_store.keys())
