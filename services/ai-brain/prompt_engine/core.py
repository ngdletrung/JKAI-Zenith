import logging
from typing import Optional

from .injectors import (
    identity_injector,
    context_injector,
    tool_injector,
)
from .builder import prompt_builder
from .cache import prompt_cache
from .context import context_compressor
from .master_prompt_architect import master_prompt_architect
from .models import T, SCHEMA_REGISTRY
from .validators import schema_validator
from .injected_reminders import inject_reminder

logger = logging.getLogger("JKAI.PromptEngine.Core")


class PromptCore:
    def __init__(self):
        self.behavior_version = "1.1"

    def build(
        self,
        goal: str,
        role: str = "RECEPTIONIST",
        task_type: Optional[str] = None,
        manifesto: str = "",
        skills_dna: str = "",
        kb_context: str = "",
        kb_sufficient: bool = False,
        memory_context: str = "",
        task_id: str = "sys",
        extra_context: dict = None,
        reminders: Optional[list[str]] = None,
        prompt_variant: str = "FULL",
    ) -> tuple[str, str, str]:
        extra = extra_context or {}

        if task_type is None:
            from prompt_assembler import ZenithPromptAssembler
            task_type = ZenithPromptAssembler.classify_task(goal)

        # Use master_prompt_architect as primary builder
        system_prompt = master_prompt_architect.build_master_system_prompt(
            role=role,
            task_type=task_type,
            task_id=task_id,
            extra_tools=None,
            prompt_variant=prompt_variant,
        )

        # Append context sections
        ctx_lines = []
        if context_xml := context_injector.inject(extra):
            ctx_lines.append(context_xml)
        if memory_context:
            ctx_lines.append(f"## Memory Context\n{memory_context}")
        if skills_dna:
            if tools_xml := tool_injector.inject(skills_dna):
                ctx_lines.append(tools_xml)
        if ctx_lines:
            system_prompt += "\n\n---\n\n" + "\n\n".join(ctx_lines)

        # Mission state v2 integration
        if task_id and task_id != "sys":
            try:
                from context import mission_context as ctx_mgr
                from mission_state import PromptAssembler
                mc = ctx_mgr.get_or_create(task_id)
                num_ctx = 4096
                try:
                    from core.utils.engine import engine
                    role_cfg = engine.get_role_config(role)
                    num_ctx = int(role_cfg.get("options", {}).get("num_ctx", 4096))
                except Exception:
                    pass
                assembler = PromptAssembler()
                assembled_sys, _ = assembler.assemble(
                    mc.mission_state_v2.state,
                    system_rules=system_prompt,
                    extra_kb=[kb_context] if kb_context else [],
                    token_limit=int(num_ctx * 0.8),
                )
                system_prompt = assembled_sys
            except Exception as pe_err:
                logger.warning(f"[MISSION-STATE] Integration failed: {pe_err}")

        # User prompt
        compressed_kb = context_compressor.compress_kb_chunks(
            [kb_context] if kb_context else []
        )
        user_prompt = prompt_builder.build_user(goal, compressed_kb)

        return task_type, system_prompt, user_prompt

    def inject_to_messages(
        self,
        messages: list,
        role: str = "RECEPTIONIST",
        task_type: Optional[str] = None,
        kb_context: str = "",
        kb_sufficient: bool = False,
        skills_dna: str = "",
        memory_context: str = "",
        task_id: str = "sys",
        extra_context: dict = None,
        skip_identity: bool = False,
    ) -> list:
        goal = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                goal = msg["content"]
                break

        if not task_type:
            from prompt_assembler import ZenithPromptAssembler
            task_type = ZenithPromptAssembler.classify_task(goal)

        extra = extra_context or {}

        system_prompt = master_prompt_architect.build_master_system_prompt(
            role=role,
            task_type=task_type,
            task_id=task_id,
            extra_tools=None,
            prompt_variant="FULL",
        )

        ctx_lines = []
        if context_xml := context_injector.inject(extra):
            ctx_lines.append(context_xml)
        if memory_context:
            ctx_lines.append(f"## Memory Context\n{memory_context}")
        if skills_dna:
            if tools_xml := tool_injector.inject(skills_dna):
                ctx_lines.append(tools_xml)
        if ctx_lines:
            system_prompt += "\n\n---\n\n" + "\n\n".join(ctx_lines)

        if messages and messages[0].get("role") == "system":
            messages[0]["content"] = system_prompt
        else:
            messages.insert(0, {"role": "system", "content": system_prompt})

        return messages

    def build_final(
        self,
        messages: list,
        role: str = "RECEPTIONIST",
        model: str = "",
        task_type: Optional[str] = None,
        kb_context: str = "",
        kb_sufficient: bool = False,
        skills_dna: str = "",
        memory_context: str = "",
        task_id: str = "sys",
        extra_context: dict = None,
        skip_identity: bool = False,
        prompt_variant: Optional[str] = None,
    ) -> list:
        exec_roles = {"PLANNER", "RESERVE_AGENT", "CRITIC", "SUMMARIZER", "EXECUTOR",
                      "EXECUTOR_ALPHA", "EXECUTOR_BETA", "EXECUTOR_GAMMA", "META_PLANNER"}
        if role and str(role).upper() in exec_roles:
            return messages

        goal = ""
        for msg in reversed(messages):
            if msg.get("role") == "user":
                goal = msg["content"]
                break

        if not task_type:
            from prompt_assembler import ZenithPromptAssembler
            task_type = ZenithPromptAssembler.classify_task(goal)

        extra = extra_context or {}
        model_lower = model.lower() if model else ""

        variant = prompt_variant or "FULL"
        if model_lower and any(k in model_lower for k in ['0.5b', '1.5b', '3b', '4b', '7b', '8b']):
            variant = "LEAN"

        system_prompt = master_prompt_architect.build_master_system_prompt(
            role=role,
            task_type=task_type,
            task_id=task_id,
            extra_tools=None,
            prompt_variant=variant,
        )

        ctx_lines = []
        if context_xml := context_injector.inject(extra):
            ctx_lines.append(context_xml)
        if memory_context:
            ctx_lines.append(f"## Memory Context\n{memory_context}")
        if skills_dna:
            if tools_xml := tool_injector.inject(skills_dna):
                ctx_lines.append(tools_xml)
        if ctx_lines:
            system_prompt += "\n\n---\n\n" + "\n\n".join(ctx_lines)

        # Cognitive bridge
        cog_bridge = self._get_cognitive_bridge(model)
        if cog_bridge:
            system_prompt += "\n\n" + cog_bridge

        # Mission state v2
        if task_id and task_id != "sys":
            try:
                from context import mission_context as ctx_mgr
                from mission_state import PromptAssembler
                mc = ctx_mgr.get_or_create(task_id)
                num_ctx = 4096
                try:
                    from core.utils.engine import engine
                    role_cfg = engine.get_role_config(role)
                    num_ctx = int(role_cfg.get("options", {}).get("num_ctx", 4096))
                except Exception:
                    pass
                assembler = PromptAssembler()
                assembled_sys, _ = assembler.assemble(
                    mc.mission_state_v2.state,
                    system_rules=system_prompt,
                    extra_kb=[kb_context] if kb_context else [],
                    token_limit=int(num_ctx * 0.8),
                )
                system_prompt = assembled_sys
            except Exception as pe_err:
                logger.warning(f"[MISSION-STATE-FINAL] Integration failed: {pe_err}")

        if messages and messages[0].get("role") == "system":
            messages[0]["content"] = system_prompt
        else:
            messages.insert(0, {"role": "system", "content": system_prompt})

        return messages

    @staticmethod
    def _get_cognitive_bridge(model: str) -> str:
        model_lower = model.lower() if model else ""
        instructions = {
            "qwen": "[COGNITIVE-BRIDGE: QWEN]: Structure your thoughts and response systematically. Use clean Markdown headers and precise bullet points.",
            "gemini": "[COGNITIVE-BRIDGE: GEMINI]: Maintain a professional, academic, clear presentation format.",
            "llama": "[COGNITIVE-BRIDGE: LLAMA]: Respond directly. Avoid conversational filler or unnecessary elaboration.",
            "deepseek": "[COGNITIVE-BRIDGE: DEEPSEEK]: Be factual, objective, and structured. Avoid repeating raw thoughts.",
            "gemma": "[COGNITIVE-BRIDGE: GEMMA]: Structure answers with clear reasoning. Avoid verbose preamble.",
            "phi": "[COGNITIVE-BRIDGE: PHI]: Break down complex topics into clear, progressive steps.",
        }
        for key, instr in instructions.items():
            if key in model_lower:
                return f"\n\n{instr}"
        return ""

    async def call_with_validation(
        self,
        model_class: type[T],
        messages: list,
        engine_call_fn,
        role: str = "RECEPTIONIST",
        task_id: str = "sys",
        **kwargs,
    ) -> T:
        return await schema_validator.validate_with_retry(
            model_class=model_class,
            messages=messages,
            engine_call_fn=engine_call_fn,
            role=role,
            task_id=task_id,
            **kwargs,
        )


prompt_core = PromptCore()
