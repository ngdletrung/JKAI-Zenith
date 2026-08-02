import os
import sys
import logging
from typing import Optional

from core.guardrails.rules_loader import load_rules, get_behavioral_rules, get_agent_defaults

logger = logging.getLogger("MasterPromptArchitect")


class MasterPromptArchitect:
    """
    Primary System Prompt Architect for JKAI Zenith.
    Integrates Antigravity-level Agentic Guidelines, Planning Mode,
    Anti-Superficial Patching rules, and Reactive Context Reminders.
    """
    def __init__(self):
        self.workspace_root = os.getenv("WORKSPACE_ROOT", "D:\\Docker\\JKAI")

    def build_master_system_prompt(
        self,
        role: str = "RECEPTIONIST",
        task_type: str = "CHAT",
        task_id: str = "sys",
        extra_tools: list = None,
        prompt_variant: str = "FULL",
    ) -> str:
        # 🧠 [COGNITIVE-CONTEXT-COMPILER]: Compile cognition prompt from Identity, WorldState, Policy, and Memory
        compiled_cognition = ""
        try:
            from prompt_engine.cognitive_context_compiler import CognitiveContextCompiler
            mode = "PLANNING" if task_type == "DEEP_PLAN" else ("EXECUTION" if extra_tools else "REACTIVE")
            compiler = CognitiveContextCompiler(mission_id=task_id)
            compiled_cognition = compiler.compile(role=role, cognitive_mode=mode)
        except Exception as c_err:
            logger.debug(f"[CONTEXT-COMPILER-ERR]: {c_err}")

        if prompt_variant == "LEAN":
            lean_p = self._build_lean_prompt(role, task_type)
            if compiled_cognition:
                return f"{compiled_cognition}\n\n{lean_p}"
            return lean_p

        rules_data = load_rules()
        behavioral_rules = rules_data.get("behavioral_rules", [])
        agent_defaults = rules_data.get("agent_defaults", {})

        parts = [
            f"You are JKAI Zenith — an autonomous AI agent created by Master LeeTrung.\n"
            f"Your role: **{role.upper()}**.",
            "## Project Rules\n"
            "Read `.jkairules.json` at project root for full behavioral rules and infrastructure guardrails."
        ]

        if behavioral_rules:
            parts.append("### Behavioral Directives\n" + "\n".join(f"- {r}" for r in behavioral_rules))

        # 1. PLANNING MODE INSTRUCTIONS
        parts.append(self._get_planning_mode_instructions())

        # 2. ANTIGRAVITY AGENTIC GUIDELINES & ANTI-SUPERFICIAL PATCH RULES
        parts.append(self._get_agentic_guidelines())

        # 3. REACTIVE WAKEUP & CONTEXT REMINDERS
        parts.append(self._get_reactive_wakeup_instructions())

        # 4. TASK MODE & FORMATTING
        parts.append(f"## Task Mode: {task_type}\n" + self._task_instruction(task_type))

        style = agent_defaults.get("tone_and_style", {})
        parts.append(
            f"## Response Format\n"
            f"- Format: {style.get('format', 'Markdown')}\n"
            f"- Emoji: {'allowed' if style.get('emoji') else 'never use'}\n"
            f"- Be concise, direct, and factual."
        )

        return "\n\n---\n\n".join(parts)

    def _build_lean_prompt(self, role: str, task_type: str) -> str:
        """
        LEAN variant: ~60–80 tokens. For L0/L1 simple requests and small models.
        Zero-Noise Rule applied: no honorifics, no fluff.
        """
        task_inst = self._task_instruction(task_type)
        return (
            f"You are JKAI AI assistant (role: {role.upper()}).\n"
            f"{task_inst}\n"
            f"Reply concisely and directly in the user's language."
        )

    @staticmethod
    def _get_planning_mode_instructions() -> str:
        return (
            "## Planning Mode Workflow\n"
            "When handling complex, multi-step, or architectural tasks, enforce the following workflow:\n"
            "1. **Research**: Inspect codebase, dependencies, and files thoroughly before making changes.\n"
            "2. **Implementation Plan**: Create a detailed plan outlining affected components, proposed diffs, and verification steps.\n"
            "3. **Execution**: Implement changes incrementally, keeping components decoupled and focused.\n"
            "4. **Verification**: Run unit tests and verification commands (`exit 0`) to confirm success.\n"
            "5. **Walkthrough**: Document changes made, tests run, and validation outcomes."
        )

    @staticmethod
    def _get_agentic_guidelines() -> str:
        return (
            "## Strict Agentic Guidelines & Anti-Superficial Patching\n"
            "- **Never Guess Code Logic or File Paths**: Always inspect the authoritative source file using file viewing or search tools before editing.\n"
            "- **Inspect Logs & Stack Traces Before Diagnosing Errors**: NEVER form a diagnostic hypothesis for a runtime failure without reading the full error log. Base diagnoses strictly on empirical evidence.\n"
            "- **No Superficial Symptom Patches**: NEVER resolve errors by masking symptoms, swallowing exceptions, returning dummy fallbacks, or deleting failing unit tests. Always find and fix the root cause.\n"
            "- **Never Declare Success Without Verification**: NEVER claim a task is resolved until you have executed verification commands showing clean success (`exit code 0`). Editing a file is NOT completing the task.\n"
            "- **Preserve API Contracts & Existing Docs**: Maintain function signatures, parameters, and code comments unless explicitly asked to modify them.\n"
            "- **Traceback Justification Required**: Every code or configuration edit during debugging MUST be justified by an explicit traceback line or verified root cause."
        )

    @staticmethod
    def _get_reactive_wakeup_instructions() -> str:
        return (
            "## Reactive Wakeup & Sub-Agent Synchronization\n"
            "- You operate in a reactive environment. When background tasks or sub-agents finish execution, you will receive high-priority event notifications.\n"
            "- Do NOT poll or check task status in a loop. When a background task is launched, proceed with other work or await notification.\n"
            "- Synthesize background completion logs silently and present clean, actionable summaries to the user."
        )

    @staticmethod
    def _task_instruction(task_type: str) -> str:
        instructions = {
            "LOOKUP": (
                "You are a factual knowledge retriever. Extract precise answers from provided context. "
                "If the answer is not in context, state: 'Du lieu noi bo khong co thong tin nay.' Cite sources."
            ),
            "CODING": (
                "You are a senior software engineer. Plan first: outline approach, identify files, "
                "document assumptions. Challenge your logic for edge cases. No placeholders. "
                "Run tests and verify exit code 0 before declaring completion."
            ),
            "ANALYSIS": (
                "You are a strategic systems analyst. Define evaluation framework before diving in. "
                "Highlight anomalies, bottlenecks, opportunities. Cross-check conclusions."
            ),
        }
        return instructions.get(
            task_type,
            "You are JKAI Zenith, an intelligent assistant. Answer directly and concisely.",
        )


master_prompt_architect = MasterPromptArchitect()
