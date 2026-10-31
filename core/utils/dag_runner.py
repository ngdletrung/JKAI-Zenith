# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/utils/dag_runner.py
# - Role: DAG Parallel Step Execution Engine (SOTA 2026)
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v1.0
#
# [WORKING PRINCIPLES]:
# 1. Zero LLM call — Pure Python Topological Sorting (< 0.2ms latency).
# 2. Parallel Acceleration: Groups independent PlanSteps into concurrent waves.
# 3. Dependency Sovereignty: Guarantees prerequisite steps complete before dependents run.
# -----------------------------------------------------------------------------

import logging
from typing import List, Dict, Any, Set

logger = logging.getLogger("JKAI.DAGRunner")


def build_dag_waves(steps: List[Dict[str, Any]]) -> List[List[Dict[str, Any]]]:
    """
    Groups plan steps into execution waves based on 'id', 'depends_on', and 'parallel'.
    Steps in the same wave can be executed concurrently via asyncio.gather().

    Args:
        steps: List of dict step objects (or Pydantic dumps with id, depends_on, parallel).

    Returns:
        List of step lists, where each inner list represents a parallel wave.
    """
    if not steps:
        return []

    # Map step_id -> step_dict. Invalid graphs fail closed; never invent execution order.
    step_map = {}
    for s in steps:
        s_id = s.get("id")
        if not s_id or s_id in step_map:
            raise ValueError("DAG requires unique non-empty step ids")
        deps = s.get("depends_on", [])
        if isinstance(deps, str):
            deps = [deps]
            s["depends_on"] = deps
        if not isinstance(deps, list) or any(dep not in step_map and dep != s_id for dep in deps):
            # Validate references after map construction below.
            pass
        step_map[s_id] = s

    for s_id, step in step_map.items():
        deps = step.get("depends_on") or []
        if not isinstance(deps, list) or s_id in deps or any(dep not in step_map for dep in deps):
            raise ValueError(f"DAG step '{s_id}' has invalid dependencies")

    completed: Set[str] = set()
    remaining = set(step_map.keys())
    waves: List[List[Dict[str, Any]]] = []

    while remaining:
        current_wave = []
        for s_id in list(remaining):
            step = step_map[s_id]
            deps = step.get("depends_on") or []
            # Normalize deps to list
            if isinstance(deps, str):
                deps = [deps]

            # A step is ready if all its dependencies are completed
            if all(dep in completed for dep in deps):
                current_wave.append(step)

        if not current_wave:
            raise ValueError("DAG contains cycle or unreachable dependency")

        waves.append(current_wave)
        for step in current_wave:
            s_id = step.get("id") or ""
            completed.add(s_id)
            remaining.discard(s_id)

    logger.debug(f"[DAG-RUNNER] Generated {len(waves)} execution wave(s) for {len(steps)} steps.")
    return waves
