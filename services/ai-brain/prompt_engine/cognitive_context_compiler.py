# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/prompt_engine/cognitive_context_compiler.py
# - Role: Cognitive Context Compiler & Provenance Engine (v26.1)
# - Ownership: Master LeeTrung
# - Status: Active | Version: SDS v26.1 (Compiled Cognition Substrate)
#
# [WORKING PRINCIPLES]:
# 1. Provenance Tagging: Explicitly tags source (UCWS, Core Memory, Policy).
# 2. Context Diffing: Tracks ADDED, REMOVED, CHANGED state across cycles.
# 3. Hardware Budgeter: Caps context to prevent GPU VRAM bloat.
# -----------------------------------------------------------------------------

import json
import logging
from typing import Dict, Any, List, Optional
from core.os.ucws import get_ucws, UCWS
from core.utils.active_core_memory import get_all_blocks_prompt
from prompt_engine.task_contract import TaskContract
from prompt_engine.cognitive_policy import CognitivePolicy

logger = logging.getLogger("JKAI.CognitiveContextCompiler")

_LAST_COMPILED_SNAPSHOT: Dict[str, Dict[str, Any]] = {}


class CognitiveContextCompiler:
    """
    Cognitive Context Compiler v26.1
    Compiles dynamic cognition context with Provenance Tagging & Context Diffing.
    """

    def __init__(self, mission_id: str = "default_mission"):
        self.mission_id = mission_id
        self.policy = CognitivePolicy()

    def compute_context_diff(self, current_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        """Computes Context Diff (ADDED, REMOVED, CHANGED) relative to previous cycle."""
        previous = _LAST_COMPILED_SNAPSHOT.get(self.mission_id, {})
        diff = {"ADDED": [], "REMOVED": [], "CHANGED": []}

        for k, v in current_snapshot.items():
            if k not in previous:
                diff["ADDED"].append(k)
            elif previous[k] != v:
                diff["CHANGED"].append(k)

        for k in previous:
            if k not in current_snapshot:
                diff["REMOVED"].append(k)

        _LAST_COMPILED_SNAPSHOT[self.mission_id] = current_snapshot
        return diff

    def compile(
        self,
        role: str = "RECEPTIONIST",
        cognitive_mode: str = "REACTIVE",
        contract: Optional[TaskContract] = None,
        max_context_chars: int = 4000
    ) -> str:
        """
        Compiles structured cognitive context prompt with Context Provenance Tags & Diffing.
        """
        ucws: UCWS = get_ucws(self.mission_id)
        core_memory_text = get_all_blocks_prompt()

        # 1. Identity Section
        identity_sec = (
            "<identity source=\"system_kernel\">\n"
            "  runtime = JKAI Zenith OS v43.0\n"
            f"  role = {role.upper()}\n"
            f"  cognitive_mode = {cognitive_mode.upper()}\n"
            "</identity>"
        )

        # 2. Mission & Provenance Tagged WorldState (with Entity & State Context Projection)
        entities_projection = {}
        for eid, edata in ucws.current_state.entities.items():
            edict = edata if isinstance(edata, dict) else (edata.dict() if hasattr(edata, 'dict') else {})
            data_inner = edict.get("data", edict)
            entities_projection[str(eid)] = {
                "name": data_inner.get("name", str(eid)),
                "type": data_inner.get("type", "entity"),
                "status": data_inner.get("status", "active"),
            }

        state_snapshot = {
            "world_version": ucws.world_version,
            "mission_id": self.mission_id,
            "entities_count": len(ucws.current_state.entities),
            "stage": ucws.current_state.state.get("stage", "ACTIVE"),
            "last_cycle": ucws.current_state.state.get("last_cycle_id", "none"),
            "entities": entities_projection,
            "system_state": ucws.current_state.state
        }
        diff = self.compute_context_diff(state_snapshot)

        world_sec = (
            f"<world_state source=\"UCWS\" version=\"v{ucws.world_version}\" confidence=\"0.99\">\n"
            f"  <current_state>{json.dumps(state_snapshot, ensure_ascii=False)}</current_state>\n"
            f"  <compiled_context_snapshot_diff>{json.dumps(diff, ensure_ascii=False)}</compiled_context_snapshot_diff>\n"
            "</world_state>"
        )

        # 3. Policy & Task Contract Section
        policy_sec = (
            f"<cognitive_policy source=\"policy_engine\" priority=\"critical\">\n"
            f"  {self.policy.to_prompt_text()}\n"
            "</cognitive_policy>"
        )

        contract_sec = (
            f"<task_contract source=\"execution_contract\">\n"
            f"  {contract.to_prompt_text() if contract else TaskContract(objective=f'Execute turn for {role}').to_prompt_text()}\n"
            "</task_contract>"
        )

        # 4. Mode Instruction — all 9 modes defined, none fallback to REACTIVE implicitly
        mode_instructions = {
            "REACTIVE":    "Respond directly and concisely. Minimize unnecessary tool calls.",
            "ANALYTICAL":  "Analyze relationships, bottlenecks, and anomalies before concluding. Output structured findings.",
            "PLANNING":    "Formulate a DAG execution plan with clear step dependencies and risk assessments.",
            "EXECUTION":   "Execute tool calls step-by-step. Inspect every observation before proceeding. Evidence required.",
            "DEBUGGING":   "Isolate root cause of failure. Trace tool results, state changes, and causality chain. Output diagnosis.",
            "REFLECTION":  "Review completed trajectory. Identify what succeeded, failed, and what should be remembered. Output structured reflection schema.",
            "RECOVERY":    "Analyze failure root cause, check alternative tools, estimate risk, and output a concrete recovery plan.",
            "LEARNING":    "Extract durable knowledge from this mission. Identify patterns, successful heuristics, and failure modes worth persisting to memory.",
            "EXPLORATION": "Survey the problem space broadly. Generate hypotheses, identify unknowns, and map out possible approaches before committing to one.",
        }
        mode_sec = f"<mode_directive source=\"adaptive_mode\">\n{mode_instructions.get(cognitive_mode.upper(), mode_instructions['REACTIVE'])}\n</mode_directive>"

        memory_tagged = f"<memory source=\"active_core_memory\">\n{core_memory_text}\n</memory>" if core_memory_text else ""

        full_compiled = f"{identity_sec}\n\n{mode_sec}\n\n{world_sec}\n\n{policy_sec}\n\n{contract_sec}\n\n{memory_tagged}"

        if len(full_compiled) > max_context_chars:
            logger.debug(f"[CONTEXT-COMPILER] Truncating compiled context from {len(full_compiled)} to {max_context_chars} chars.")
            return full_compiled[:max_context_chars] + "\n... [Context Budget Capped]"

        return full_compiled
