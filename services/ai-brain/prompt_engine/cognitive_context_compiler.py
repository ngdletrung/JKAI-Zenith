# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/prompt_engine/cognitive_context_compiler.py
# - Role: Cognitive Context Compiler (Compiled Cognition Substrate)
# - Ownership: Master LeeTrung
# - Status: Active | Version: SDS v26.0 (Cognitive Context Compiler Layer)
#
# [WORKING PRINCIPLES]:
# 1. Compiled Cognition: Prompt = Compile(Identity, Mission, WorldState, Memory, Mode, Policy, Contract).
# 2. Context Budgeter: Caps context budget to prevent prompt bloat on local GPUs.
# 3. Adaptive Cognitive Modes: REACTIVE, ANALYTICAL, PLANNING, EXECUTION, RECOVERY, etc.
# -----------------------------------------------------------------------------

import json
import logging
from typing import Dict, Any, List, Optional
from core.os.ucws import get_ucws, UCWS
from core.utils.active_core_memory import get_all_blocks_prompt
from prompt_engine.task_contract import TaskContract
from prompt_engine.cognitive_policy import CognitivePolicy

logger = logging.getLogger("JKAI.CognitiveContextCompiler")


class CognitiveContextCompiler:
    """
    Cognitive Context Compiler
    Compiles dynamic cognition contexts from Identity, Mission, UCWS, Memory, Policy, and Task Contract.
    """

    def __init__(self, mission_id: str = "default_mission"):
        self.mission_id = mission_id
        self.policy = CognitivePolicy()

    def compile(
        self,
        role: str = "RECEPTIONIST",
        cognitive_mode: str = "REACTIVE",
        contract: Optional[TaskContract] = None,
        max_context_chars: int = 4000
    ) -> str:
        """
        Compiles the complete structured cognitive context prompt for LLM execution.
        """
        ucws: UCWS = get_ucws(self.mission_id)
        core_memory_text = get_all_blocks_prompt()

        # 1. Identity Section
        identity_sec = (
            "<identity>\n"
            "  runtime = JKAI Zenith OS v43.0\n"
            f"  role = {role.upper()}\n"
            f"  cognitive_mode = {cognitive_mode.upper()}\n"
            "</identity>"
        )

        # 2. Mission & WorldState Section (UCWS vN)
        state_info = {
            "world_version": ucws.world_version,
            "mission_id": self.mission_id,
            "entities_count": len(ucws.current_state.entities),
            "stage": ucws.current_state.state.get("stage", "ACTIVE"),
            "last_cycle": ucws.current_state.state.get("last_cycle_id", "none")
        }
        world_sec = (
            "<world_state>\n"
            f"  {json.dumps(state_info, ensure_ascii=False)}\n"
            "</world_state>"
        )

        # 3. Policy & Task Contract Section
        policy_sec = self.policy.to_prompt_text()
        contract_sec = contract.to_prompt_text() if contract else (
            "<task_contract>\n"
            f"  <objective>Execute turn for role {role}</objective>\n"
            "  <risk_level>0.1</risk_level>\n"
            "</task_contract>"
        )

        # 4. Mode Instruction
        mode_instructions = {
            "REACTIVE": "Respond directly and concisely. Minimize unnecessary tool calls.",
            "ANALYTICAL": "Analyze relationships, bottlenecks, and anomalies before concluding.",
            "PLANNING": "Formulate a DAG execution plan with clear step dependencies.",
            "EXECUTION": "Execute tool calls step-by-step and inspect observation outputs.",
            "RECOVERY": "Analyze failure root cause, check alternative tools, estimate risk, and attempt recovery."
        }
        mode_sec = f"<mode_directive>\n{mode_instructions.get(cognitive_mode.upper(), mode_instructions['REACTIVE'])}\n</mode_directive>"

        # Assembly with Context Budgeting
        full_compiled = f"{identity_sec}\n\n{mode_sec}\n\n{world_sec}\n\n{policy_sec}\n\n{contract_sec}\n\n{core_memory_text}"

        if len(full_compiled) > max_context_chars:
            logger.debug(f"[CONTEXT-COMPILER] Truncating compiled context from {len(full_compiled)} to {max_context_chars} chars.")
            return full_compiled[:max_context_chars] + "\n... [Context Budget Capped]"

        return full_compiled
