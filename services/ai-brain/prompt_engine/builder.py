import os
import logging

logger = logging.getLogger("JKAI.PromptEngine.Builder")


class PromptBuilder:
    def __init__(self):
        self._behavioral_lines = self._load_behavioral()

    def _load_behavioral(self) -> str:
        path = os.path.join(os.path.dirname(__file__), "behavioral_core.md")
        if os.path.exists(path):
            with open(path, "r", encoding="utf-8") as f:
                return f.read().strip()
        return ""

    def build_system(
        self,
        identity_xml: str,
        behavioral_xml: str = "",
        response_contract_xml: str = "",
        context_xml: str = "",
        tools_xml: str = "",
        task_type: str = "CHAT",
        task_instruction: str = "",
        memory_xml: str = "",
        cognitive_bridge: str = "",
        kb_sufficient: bool = False,
        extra_sections: list[str] = None,
    ) -> str:
        parts = []

        # Identity
        if identity_xml:
            parts.append(identity_xml)

        # Behavioral guidelines (from file)
        if self._behavioral_lines:
            parts.append(self._behavioral_lines)

        # Task instruction
        if task_instruction:
            parts.append(f"## Task Mode: {task_type}\n{task_instruction}")

        # Context
        if context_xml:
            parts.append(context_xml)

        # Memory
        if memory_xml:
            parts.append(memory_xml)

        # Tools
        if tools_xml:
            parts.append(tools_xml)

        # Cognitive bridge (model-specific)
        if cognitive_bridge:
            parts.append(cognitive_bridge)

        # Extra sections
        if extra_sections:
            parts.extend(extra_sections)

        return "\n\n---\n\n".join(parts)

    def build_user(self, goal: str, kb_context: str = "", max_kb_chars: int = 3500) -> str:
        import html
        sanitized = html.escape(goal or "").replace("</goal>", "&lt;/goal&gt;")
        parts = [f"## Goal\n{sanitized}"]
        if kb_context:
            truncated = kb_context[:max_kb_chars]
            parts.append(f"## Knowledge Context\n{truncated}")
        return "\n\n".join(parts)

    @staticmethod
    def get_task_instruction(task_type: str) -> str:
        instructions = {
            "LOOKUP": (
                "You are a factual knowledge retriever. Extract precise answers from the provided context.\n"
                "- Refer strictly to context. Do not extrapolate.\n"
                "- If the answer is not in context, state that clearly.\n"
                "- Cite sources with [source_file] notation."
            ),
            "CODING": (
                "You are a senior software engineer.\n"
                "- Plan first: outline approach, identify files, document assumptions.\n"
                "- Doubt-driven: challenge your logic for edge cases before output.\n"
                "- No placeholders: every line of code must be complete and real.\n"
                "- Verify: run tests before declaring completion."
            ),
            "ANALYSIS": (
                "You are a strategic systems analyst.\n"
                "- Define evaluation framework before diving in.\n"
                "- Highlight anomalies, bottlenecks, opportunities.\n"
                "- Cross-check conclusions against evidence."
            ),
        }
        return instructions.get(task_type, (
            "You are JKAI Zenith, an intelligent assistant.\n"
            "- Answer directly and concisely.\n"
            "- If multi-step reasoning is needed, plan first."
        ))

    @staticmethod
    def get_critic_instruction(task_type: str) -> str:
        rules = {
            "LOOKUP": (
                "1. Check if output cites source files.\n"
                "2. Check for hallucinations not backed by context.\n"
                "3. Verify answer directly addresses the query."
            ),
            "CODING": (
                "1. Verify code is syntactically valid.\n"
                "2. Check for logic errors, security flaws, unhandled exceptions.\n"
                "3. Confirm implementation solves the entire requirement."
            ),
            "ANALYSIS": (
                "1. Verify evaluation is structured and multi-dimensional.\n"
                "2. Ensure claims are consistent with execution data.\n"
                "3. Check if contradictions are identified and resolved."
            ),
        }
        base = rules.get(task_type, "1. Ensure output is natural and correctly answers user intent.\n2. Check for formatting errors.")
        return f"## Critic Rules ({task_type})\n{base}"


prompt_builder = PromptBuilder()
