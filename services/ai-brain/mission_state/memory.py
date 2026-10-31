# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/mission_state/memory.py
# - Role: Scoped Memory Manager (Global, Mission, Agent, Tool)
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v1.1 (Phase R0 Hardened)

import json
import logging
from typing import Any, Dict, Optional
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
    async def distill(
        memory: ScopedMemory,
        task_log_text: str,
        task_id: Optional[str] = None,
        trace_id: Optional[str] = None,
        use_llm: bool = False,
    ) -> str:
        """
        Consolidates verbose task logs into concise episodic memory.
        Phase R0 Invariant:
          1. Never allows task_id=None (prevents '[SUMMARIZER] [Task: None]' leaks).
          2. Default deterministic distillation (use_llm=False) avoids 60-77s duplicate
             SUMMARIZER GPU calls between T4 and T5 Critic.
          3. Respects STOP cancellation and discards late output.
        """
        if task_id is None or not str(task_id).strip() or str(task_id).strip().lower() == "none":
            raise ValueError("TASK_ID_REQUIRED: ScopedMemoryManager.distill requires a non-empty task_id (got None).")

        clean_task_id = str(task_id).strip()
        clean_trace_id = str(trace_id).strip() if (trace_id and str(trace_id).strip().lower() != "none") else clean_task_id

        if not task_log_text or not task_log_text.strip():
            return ""

        from core.utils.engine import engine, should_stop, MasterAbortException
        from core.utils.log_engine import log_engine

        if should_stop(clean_task_id, engine._get_redis()):
            log_engine.mark_task_stopped(clean_task_id)
            raise MasterAbortException(f"Mission {clean_task_id} stopped before memory distillation.")

        if not use_llm:
            # Deterministic sub-millisecond consolidation (Zero duplicate SUMMARIZER call before T5)
            digest_parts = []
            try:
                parsed = json.loads(task_log_text)
                if isinstance(parsed, dict):
                    for step_id, step_res in parsed.items():
                        if isinstance(step_res, dict):
                            st = step_res.get("status", "unknown")
                            out_preview = str(step_res.get("output", step_res.get("msg", "")))[:160].replace("\n", " ")
                            digest_parts.append(f"{step_id}({st}): {out_preview}")
                        else:
                            digest_parts.append(f"{step_id}: {str(step_res)[:120]}")
            except Exception:
                pass

            if digest_parts:
                summary = f"[task_id={clean_task_id} trace_id={clean_trace_id}] " + " | ".join(digest_parts[:5])
            else:
                summary = f"[task_id={clean_task_id} trace_id={clean_trace_id}] {task_log_text.strip()[:280]}"

            if "lessons_learned" not in memory.mission_memory:
                memory.mission_memory["lessons_learned"] = []
            memory.mission_memory["lessons_learned"].append(summary)
            memory.tool_memory.clear()
            logger.info("[MEMORY-CONSOLIDATED] Deterministic digest recorded for task_id=%s.", clean_task_id)
            return summary

        prompt = (
            "Bạn là bộ chắt lọc bộ nhớ của hệ thống JKAI. Hãy phân tích các log thực thi công cụ và tóm tắt "
            "những gì đã học được hoặc hoàn thành trong đúng 2-3 câu ngắn gọn bằng tiếng Việt để lưu trữ trí nhớ sống. "
            "Không đưa các chi tiết kỹ thuật dài dòng.\n\n"
            f"Logs:\n{task_log_text}\n\n"
            "Tóm tắt (Trí nhớ phân đoạn):"
        )
        try:
            summary = await engine.call_chat(
                messages=[{"role": "user", "content": prompt}],
                role="SUMMARIZER",
                options={"temperature": 0.2},
                task_id=clean_task_id,
                trace_id=clean_trace_id,
            )
            if should_stop(clean_task_id, engine._get_redis()):
                log_engine.mark_task_stopped(clean_task_id)
                raise MasterAbortException(f"Mission {clean_task_id} stopped after memory distillation LLM call.")

            summary = str(summary).strip()
            if "lessons_learned" not in memory.mission_memory:
                memory.mission_memory["lessons_learned"] = []
            memory.mission_memory["lessons_learned"].append(summary)
            memory.tool_memory.clear()
            logger.info("[MEMORY-CONSOLIDATED] Verbose logs distilled and tool memory cleared for task_id=%s.", clean_task_id)
            return summary
        except MasterAbortException:
            raise
        except Exception as e:
            logger.error("[MEMORY-CONSOLIDATION-ERR] Failed to distill memory: %s", e)
            return ""
