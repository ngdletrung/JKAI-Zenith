# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — CONTEXT ASSEMBLER v5.0 (INTELLIGENT ORCHESTRATOR)║
║   Điều Phối Ngữ Cảnh Đa Nhãn, Action-Aware & Pipeline Parameters ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Bộ Ghép Nối Ngữ Cảnh Thông Minh. 🎯⚡🧠*
"""

import time
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, List, Optional, Tuple, Union

from prompt_engine.core import prompt_core
from prompt_engine.builder import prompt_builder
from core.os.routing.intent_router import intent_router, IntentMode, ActionType, RouteDecision

logger = logging.getLogger("JKAI.ContextAssembler")


@dataclass
class PromptParams:
    """Tham số điều phối ngữ cảnh và pipeline hoàn chỉnh."""
    task_type: str
    tags: List[str] = field(default_factory=list)
    max_turns: int = 5
    mode: IntentMode = IntentMode.GENERAL
    action_type: Optional[str] = None
    confidence: float = 1.0
    kb_top_k: int = 3
    need_web: bool = False
    need_kb: bool = False


class ZenithPromptAssembler:
    """
    🧬 Zenith Context Assembler (ZCA v5.0 - Intelligent Context Orchestrator)
    Điều phối toàn diện Multi-Label Tags, ActionType, Pipeline Parameters và Observability.
    """

    @classmethod
    def get_prompt_params(cls, goal: str) -> PromptParams:
        """Trích xuất trọn vẹn tham số định tuyến và điều khiển pipeline từ CentralIntentRouter."""
        t0 = time.perf_counter()
        decision: RouteDecision = intent_router.route(goal)
        
        # Ánh xạ primary task_type tương thích ngược
        if decision.mode == IntentMode.CODING:
            primary_task = "CODING"
        elif decision.mode in (IntentMode.REALTIME, IntentMode.INTERNAL):
            primary_task = "LOOKUP"
        elif decision.mode == IntentMode.REASONING:
            primary_task = "ANALYSIS"
        else:
            primary_task = "CHAT"

        elapsed_ms = (time.perf_counter() - t0) * 1000

        # Tích hợp Observability Metrics
        try:
            from core.telemetry.observability_engine import observability_engine
            observability_engine.record_span(
                name="context_assembler_classify",
                category="PROMPT",
                duration_ms=elapsed_ms,
                metadata={"mode": decision.mode.value, "tags": decision.tags, "action": decision.action_type.value}
            )
        except Exception:
            pass

        return PromptParams(
            task_type=primary_task,
            tags=decision.tags or [primary_task],
            max_turns=decision.max_turns,
            mode=decision.mode,
            action_type=decision.action_type.value if hasattr(decision.action_type, "value") else str(decision.action_type),
            confidence=decision.confidence,
            kb_top_k=decision.kb_top_k,
            need_web=decision.need_web,
            need_kb=decision.need_kb
        )

    @classmethod
    async def classify_task_fast(cls, goal: str, task_id: str = "sys") -> str:
        """Phân loại tác vụ siêu tốc (<0.05ms) không tiêu tốn GPU."""
        params = cls.get_prompt_params(goal)
        return params.task_type

    @classmethod
    async def classify_task_llm(cls, goal: str, task_id: str = "sys") -> str:
        """Alias tương thích ngược."""
        return await cls.classify_task_fast(goal, task_id)

    @staticmethod
    def classify_task(goal: str) -> str:
        """Hàm phân loại đồng bộ tương thích ngược hoàn hảo."""
        params = ZenithPromptAssembler.get_prompt_params(goal)
        return params.task_type

    @staticmethod
    def get_task_instruction(task_type: str) -> str:
        return prompt_builder.get_task_instruction(task_type)

    @staticmethod
    def get_critic_instruction(task_type: str) -> str:
        return prompt_builder.get_critic_instruction(task_type)

    @classmethod
    async def assemble_context(
        cls,
        goal: str,
        manifesto: str,
        skills_dna: str,
        kb_context: str,
        kb_sufficient: bool = False,
        task_id: str = "sys",
        extra_context: Dict[str, Any] = None
    ) -> Tuple[str, str]:
        if extra_context is None:
            extra_context = {}
        params = cls.get_prompt_params(goal)

        # Bổ sung các thông số điều phối hành động vào extra_context
        extra_context["action_type"] = params.action_type
        extra_context["max_turns"] = params.max_turns
        extra_context["mode"] = params.mode.value
        extra_context["task_tags"] = params.tags

        _, sys_prompt, user_prompt = prompt_core.build(
            goal=goal,
            task_type=params.task_type,
            manifesto=manifesto or "You are JKAI Zenith, designed by Master LeeTrung.",
            skills_dna=skills_dna,
            kb_context=kb_context,
            kb_sufficient=kb_sufficient,
            memory_context=extra_context.get("memory_context", ""),
            task_id=task_id,
            extra_context=extra_context,
        )
        return sys_prompt, user_prompt

    @classmethod
    def assemble_prompt(
        cls,
        goal: str,
        manifesto: str,
        skills_dna: str,
        kb_context: str,
        kb_sufficient: bool = False,
        extra_context: Dict[str, Any] = None,
        task_id: str = "sys",
    ) -> Tuple[str, str]:
        if extra_context is None:
            extra_context = {}
        params = cls.get_prompt_params(goal)

        extra_context["action_type"] = params.action_type
        extra_context["max_turns"] = params.max_turns
        extra_context["mode"] = params.mode.value
        extra_context["task_tags"] = params.tags

        _, sys_prompt, user_prompt = prompt_core.build(
            goal=goal,
            task_type=params.task_type,
            manifesto=manifesto or "You are JKAI Zenith, designed by Master LeeTrung.",
            skills_dna=skills_dna,
            kb_context=kb_context,
            kb_sufficient=kb_sufficient,
            extra_context=extra_context,
            task_id=task_id,
        )
        return sys_prompt, user_prompt


prompt_assembler = ZenithPromptAssembler()
