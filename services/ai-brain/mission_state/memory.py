# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/mission_state/memory.py
# - Role: Scoped Memory Manager (Global, Mission, Agent, Tool)
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v1.0

import logging
from typing import Any, Dict
from .schema import ScopedMemory

logger = logging.getLogger("JKAI.MemoryManager")

class ScopedMemoryManager:
    """Manages multi-tiered scoping of memories."""
    @staticmethod
    def set_val(memory: ScopedMemory, scope: str, key: str, value: Any):
        """Sets value in corresponding memory scope."""
        if scope == "global":
            memory.global_memory[key] = value
        elif scope == "mission":
            memory.mission_memory[key] = value
        elif scope == "tool":
            memory.tool_memory[key] = value
        else:
            # Agent scope
            agent_name = scope
            if agent_name not in memory.agent_memory:
                memory.agent_memory[agent_name] = {}
            memory.agent_memory[agent_name][key] = value

    @staticmethod
    def get_val(memory: ScopedMemory, scope: str, key: str, default: Any = None) -> Any:
        """Retrieves value from memory scope."""
        if scope == "global":
            return memory.global_memory.get(key, default)
        elif scope == "mission":
            return memory.mission_memory.get(key, default)
        elif scope == "tool":
            return memory.tool_memory.get(key, default)
        else:
            # Agent scope
            agent_name = scope
            if agent_name in memory.agent_memory:
                return memory.agent_memory[agent_name].get(key, default)
            return default

    @staticmethod
    def clear_tool_memory(memory: ScopedMemory):
        """Volatile memory manager: cleans up temporary execution variables to save token budget."""
        memory.tool_memory.clear()
        logger.info("[MEM-CLEARED] Scoped Tool memory cleared successfully.")

    @staticmethod
    async def distill(memory: ScopedMemory, task_log_text: str, task_id: str = "sys") -> str:
        """
        Consolidates verbose task logs into 2-3 sentences of episodic memory.
        Appends it to mission_memory, and clears tool_memory to avoid context bloat.
        """
        if not task_log_text.strip():
            return ""

        from core.utils.engine import engine
        prompt = (
            "You are the memory distiller. Analyze the following verbose tool execution logs and summarize "
            "what was learned/accomplished in exactly 2-3 concise sentences (episodic memory) to prevent "
            "context bloat. Do not include verbose details.\n\n"
            f"Logs:\n{task_log_text}\n\n"
            "Summary (episodic memory):"
        )
        try:
            summary = await engine.call_chat(
                messages=[{"role": "user", "content": prompt}],
                role="SUMMARIZER",
                options={"temperature": 0.3},
                task_id=task_id
            )
            summary = str(summary).strip()
            
            if "lessons_learned" not in memory.mission_memory:
                memory.mission_memory["lessons_learned"] = []
            memory.mission_memory["lessons_learned"].append(summary)
            
            # Clear tool memory
            memory.tool_memory.clear()
            logger.info("[MEMORY-CONSOLIDATED] Verbose logs distilled and tool memory cleared.")
            return summary
        except Exception as e:
            logger.error("[MEMORY-CONSOLIDATION-ERR] Failed to distill memory: %s", e)
            return ""
