"""
Injected reminders — context-specific instructions appended to system prompt
when certain events occur. Pattern inspired by Claude Code's injected-reminders.
"""

import logging

logger = logging.getLogger("JKAI.PromptEngine.Reminders")


REMINDERS = {
    "brief_mode": "[BRIEF MODE] Output only the essential result. No explanations, no planning, no analysis.",
    "model_switched": "[MODEL SWITCHED] The underlying model has changed mid-session. Re-read recent context to re-establish state.",
    "container_restart": "[CONTAINER RESTART] The system container was restarted. Previous session state may be incomplete.",
    "non_interactive": "[NON-INTERACTIVE] Running in non-interactive mode. Output must be parseable. No conversational text.",
}


def get_reminder(key: str) -> str:
    return REMINDERS.get(key, "")


def inject_reminder(system_prompt: str, key: str) -> str:
    reminder = get_reminder(key)
    if reminder:
        system_prompt += f"\n\n{reminder}"
        logger.debug(f"[REMINDER] Injected '{key}'")
    return system_prompt
