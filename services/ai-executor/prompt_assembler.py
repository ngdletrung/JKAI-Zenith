import re
import json
import logging
from typing import Dict, Any, List, Optional

from prompt_engine.core import prompt_core
from prompt_engine.builder import prompt_builder

logger = logging.getLogger("JKAI.ContextAssembler")

class ZenithPromptAssembler:
    """
    🧬 Zenith Context Assembler (ZCA v3 - Elite Edition)
    Thin wrapper around prompt_engine. Maintains backward compatibility.
    """
    
    @classmethod
    async def classify_task_llm(cls, goal: str, task_id: str = "sys") -> str:
        """
        🧠 [LLM-INTENT-ROUTER]: Router phân loại tác vụ bằng mô hình ngôn ngữ nhỏ.
        """
        from core.utils.engine import engine
        from prompt_engine.models import TaskClassification
        prompt = (
            "Analyze this user request and classify it into exactly ONE of these categories:\n"
            "- LOOKUP: Factual questions, checking information, seeking definitions, credentials, IPs, rules, guides.\n"
            "- CODING: Writing code, fixing bugs, optimization, refactoring, script writing, Docker/Git/Python issues.\n"
            "- ANALYSIS: Comparison, systems audit, writing reports, calculating metrics, benchmarking.\n"
            "- CHAT: Casual talk, general explanations, greetings, small talk.\n\n"
            f"User request: \"{goal}\"\n\n"
            "Respond with ONLY a JSON object having the key 'category'. Example: {\"category\": \"CODING\"}"
        )
        try:
            res = await engine.call_chat(
                messages=[{"role": "user", "content": prompt}],
                role="PLANNER",
                json_mode=True,
                task_id=task_id
            )
            if isinstance(res, str):
                res = json.loads(res)
            category = res.get("category", "CHAT").upper()
            if category in ("LOOKUP", "CODING", "ANALYSIS", "CHAT"):
                return category
        except Exception as e:
            logger.warning("[IntentRouter] LLM classification failed, falling back: %s", e)
        return cls.classify_task(goal)

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
    ) -> tuple[str, str]:
        extra = extra_context or {}
        task_type = await cls.classify_task_llm(goal, task_id)
        _, sys_prompt, user_prompt = prompt_core.build(
            goal=goal,
            task_type=task_type,
            manifesto=manifesto or "You are JKAI Zenith, designed by Master LeeTrung.",
            skills_dna=skills_dna,
            kb_context=kb_context,
            kb_sufficient=kb_sufficient,
            memory_context=extra.get("memory_context", ""),
            task_id=task_id,
            extra_context=extra,
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
    ) -> tuple[str, str]:
        extra = extra_context or {}
        _, sys_prompt, user_prompt = prompt_core.build(
            goal=goal,
            task_type=cls.classify_task(goal),
            manifesto=manifesto or "You are JKAI Zenith, designed by Master LeeTrung.",
            skills_dna=skills_dna,
            kb_context=kb_context,
            kb_sufficient=kb_sufficient,
            extra_context=extra,
            task_id=task_id,
        )
        return sys_prompt, user_prompt

    @staticmethod
    def classify_task(goal: str) -> str:
        g = goal.lower().strip()
        coding_patterns = [
            r"\b(code|coder|sua loi|cai tien|viet code|refactor|script|docker|python|javascript|c\+\+|java|golang|html|css|sql)\b",
            r"\b(sua file|chinh sua file|tao file|viet ham|class|struct|interface|function|api endpoint)\b"
        ]
        if any(re.search(pat, g) for pat in coding_patterns):
            return "CODING"
        if any(w in g for w in ["la gi", "o dau", "tra cuu", "quy trinh", "mat khau", "ip", "tim", "mua gi"]):
            return "LOOKUP"
        if re.search(r"\w+\s+gi\b|\w+\s+gi\b", g):
            return "LOOKUP"
        if any(w in g for w in ["phan tich", "so sanh", "bao cao", "tong hop", "danh gia"]):
            return "ANALYSIS"
        return "CHAT"
