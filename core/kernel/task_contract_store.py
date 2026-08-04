# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/kernel/task_contract_store.py
# - Role: Session-Level TaskContract & Policy Store
# - Ownership: Master LeeTrung
# - Status: Active | Version: SDS v26.2
#
# [WORKING PRINCIPLES]:
# 1. Lightweight in-memory store keyed by task_id.
# 2. Thread-safe via threading.Lock.
# 3. executor_gateway reads contract here before authorizing any tool call.
# 4. mission_runtime writes contract here when task is initialized.
# -----------------------------------------------------------------------------

import logging
import threading
from typing import Dict, Optional, Any

logger = logging.getLogger("JKAI.TaskContractStore")

_lock = threading.RLock()
_contract_store: Dict[str, Any] = {}   # task_id → TaskContract
_policy_store: Dict[str, Any] = {}     # task_id → CognitivePolicy

# --------------------------------------------------------------------------- #
# Contract Store                                                               #
# --------------------------------------------------------------------------- #

def set_active_contract(task_id: str, contract: Any) -> None:
    """Register a TaskContract for the given task_id."""
    with _lock:
        _contract_store[task_id] = contract
    logger.debug(f"[CONTRACT-STORE] Registered TaskContract for task_id={task_id}")


def get_active_contract(task_id: str) -> Optional[Any]:
    """Retrieve the active TaskContract for the given task_id. Auto-initializes default authority if missing."""
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
                        can_execute_shell=True
                    )
                )
                _contract_store[task_id] = contract
                logger.info(f"[CONTRACT-STORE] Auto-created default TaskContract for task_id={task_id}")
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
    """Remove both contract and policy for the given task_id."""
    clear_contract(task_id)
    clear_policy(task_id)


def list_active_tasks() -> list:
    """Return list of all task_ids with registered contracts (for introspection/debugging)."""
    with _lock:
        return list(_contract_store.keys())
