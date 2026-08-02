# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: intelligence/skills/CORE/ZENITH_CHRONOS_ROUTINES/logic.py
# - Role: Autonomic Nervous System - Background Task Orchestrator
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v1.0
# [WORKING PRINCIPLES]:
# 1. Manages a registry of background tasks (routines).
# 2. Checks and executes tasks based on schedule or system pulse.
# 3. Integrates with SYSTEM_CORE_EXECUTOR for physical execution.
# -----------------------------------------------------------------------------
import os
import json
import time
from datetime import datetime
from typing import Dict, Any, List

ROUTINE_REGISTRY_PATH = "d:/Docker/JKAI/intelligence/routine_registry.json"

async def execute(params: Dict[str, Any]) -> Dict[str, Any]:
    action = params.get("action", "list")
    routine_id = params.get("routine_id")
    schedule = params.get("schedule")
    task_payload = params.get("task_payload")

    if action == "add":
        return await add_routine(routine_id, schedule, task_payload)
    elif action == "remove":
        return await remove_routine(routine_id)
    elif action == "list":
        return await list_routines()
    elif action == "trigger":
        return await trigger_routine(routine_id)
    else:
        return {"status": "error", "message": f"Unknown action: {action}"}

async def _load_registry() -> List[Dict[str, Any]]:
    if not os.path.exists(ROUTINE_REGISTRY_PATH):
        return []
    try:
        with open(ROUTINE_REGISTRY_PATH, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return []

async def _save_registry(data: List[Dict[str, Any]]):
    with open(ROUTINE_REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

async def add_routine(routine_id: str, schedule: str, task_payload: Any) -> Dict[str, Any]:
    if not routine_id or not schedule or not task_payload:
        return {"status": "error", "message": "Missing required parameters for adding routine."}
    
    registry = await _load_registry()
    # Remove if exists
    registry = [r for r in registry if r["id"] != routine_id]
    
    new_routine = {
        "id": routine_id,
        "schedule": schedule,
        "payload": task_payload,
        "created_at": datetime.now().isoformat(),
        "last_run": None,
        "status": "active"
    }
    registry.append(new_routine)
    await _save_registry(registry)
    
    return {"status": "success", "message": f"Routine '{routine_id}' added successfully.", "data": new_routine}

async def remove_routine(routine_id: str) -> Dict[str, Any]:
    registry = await _load_registry()
    new_registry = [r for r in registry if r["id"] != routine_id]
    
    if len(new_registry) == len(registry):
        return {"status": "error", "message": f"Routine '{routine_id}' not found."}
    
    await _save_registry(new_registry)
    return {"status": "success", "message": f"Routine '{routine_id}' removed."}

async def list_routines() -> Dict[str, Any]:
    registry = await _load_registry()
    return {"status": "success", "data": registry}

async def trigger_routine(routine_id: str) -> Dict[str, Any]:
    # In a real implementation, this would involve sending the payload to the executor.
    # For now, we simulate the trigger.
    registry = await _load_registry()
    for r in registry:
        if r["id"] == routine_id:
            r["last_run"] = datetime.now().isoformat()
            await _save_registry(registry)
            return {
                "status": "success", 
                "message": f"Routine '{routine_id}' triggered successfully.",
                "execution_payload": r["payload"]
            }
    
    return {"status": "error", "message": f"Routine '{routine_id}' not found."}
