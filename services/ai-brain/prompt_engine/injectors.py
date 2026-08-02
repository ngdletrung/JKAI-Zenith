import datetime
import logging
from typing import Optional

logger = logging.getLogger("JKAI.PromptEngine.Injectors")


class IdentityInjector:
    def inject(self, compress: bool = False) -> str:
        return (
            "You are JKAI Zenith — an autonomous AI agent system created by Master LeeTrung. "
            "You pair-program with the user to solve software engineering tasks with precision, "
            "honesty, and robustness."
        )


class BehaviorInjector:
    def inject(self) -> str:
        return ""


class ContextInjector:
    def __init__(self, root_dir: str = None, geo_location: str = "Hue"):
        self._root_dir = root_dir or ""
        self._geo_location = geo_location

    def inject_response_contract(self, extra_context: dict = None) -> str:
        extra = extra_context or {}
        lang = extra.get("lang", "vi")
        json_mode = extra.get("json_mode", False)
        return (
            f"## Response Contract\n"
            f"- Language: {lang}\n"
            f"- Format: Markdown\n"
            f"- JSON mode: {json_mode}\n"
            f"- Be concise and direct."
        )

    def inject(self, extra_context: dict = None) -> str:
        now = datetime.datetime.now()
        days = ["Thứ Hai", "Thứ Ba", "Thứ Tư", "Thứ Năm", "Thứ Sáu", "Thứ Bảy", "Chủ Nhật"]
        time_str = f"{now.strftime('%H:%M')}, {days[now.weekday()]}, {now.strftime('%d/%m/%Y')}"
        return (
            f"## Context\n"
            f"- Time: {time_str} (GMT+7)\n"
            f"- Location: {self._geo_location}\n"
            f"- Workspace: {self._root_dir}"
        )


class ToolInjector:
    def inject(self, skills_dna: str = "", extra_tools: list[dict] = None) -> str:
        parts = []
        if skills_dna and len(skills_dna.strip()) > 0:
            clean_dna = skills_dna.strip()
            if len(clean_dna) > 1000:
                clean_dna = clean_dna[:1000] + "\n... [Active Skills summary capped]"
            parts.append("## Active Skills\n" + clean_dna)
        if extra_tools:
            for t in extra_tools[:4]:  # Cap at top 4 tools per SOTA 2026 Tool Masking
                parts.append(f"- {t.get('name', 'unknown')}: {t.get('description', '')}")
        return "\n".join(parts)


identity_injector = IdentityInjector()
behavior_injector = BehaviorInjector()
context_injector = ContextInjector()
tool_injector = ToolInjector()
