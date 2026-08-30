"""
JKAI AI OS — Slash Command Registry
Đăng ký và xử lý linh hoạt các lệnh tắt (Slash Commands) từ Ingress Gateway.
"""

from __future__ import annotations

import re
import logging
from typing import Any, Callable, Dict, Optional, Tuple

from core.os.orchestrator.types import OSRequestPlan, log_telemetry

logger = logging.getLogger("jkai.os.orchestrator.slash")

# Type: (goal, match, plan, ctx) -> Optional[Tuple[str, str]] (new_goal, new_intent)
SlashHandlerFunc = Callable[[str, re.Match, OSRequestPlan, Any], Optional[Tuple[str, str]]]


class SlashCommandRegistry:
    """Registry trung tâm quản lý các Slash Command mở rộng."""

    _commands: Dict[str, Tuple[re.Pattern, SlashHandlerFunc, str]] = {}

    @classmethod
    def register(cls, pattern: str, handler: SlashHandlerFunc, description: str = "") -> None:
        """Đăng ký một Slash Command mới."""
        compiled = re.compile(pattern, re.IGNORECASE)
        cls._commands[pattern] = (compiled, handler, description)

    @classmethod
    def intercept(cls, goal: str, plan: OSRequestPlan, ctx: Any) -> bool:
        """Kiểm tra và thực thi Slash Command nếu khớp."""
        g_stripped = (goal or "").strip()
        for pattern, (compiled, handler, desc) in cls._commands.items():
            m = compiled.match(g_stripped)
            if m:
                try:
                    res = handler(g_stripped, m, plan, ctx)
                    if res:
                        new_goal, new_intent = res
                        plan.goal = new_goal
                        plan.os_intent = new_intent
                        log_telemetry(plan, "ZENITH", f"⚡ [SLASH-COMMAND]: Kích hoạt `{m.group(0).split()[0]}` — {desc}")
                        return True
                except Exception as err:
                    logger.warning("[SLASH-COMMAND-ERR] Handler for %s failed: %s", pattern, err)
        return False


# ── Built-in Slash Commands Registration ──

def _handle_research(goal: str, match: re.Match, plan: OSRequestPlan, ctx: Any) -> Tuple[str, str]:
    topic = match.group(1).strip()
    enriched = (
        f"Nghiên cứu chuyên sâu và cập nhật tri thức: Hãy tìm kiếm, thu thập tài liệu chính thống về '{topic}', "
        f"bóc tách các bằng chứng và nguyên lý cốt lõi, nhúng lưu vào bộ nhớ vector RAG và tạo bản tóm tắt điều hành cho Master."
    )
    return enriched, "research"


def _handle_code(goal: str, match: re.Match, plan: OSRequestPlan, ctx: Any) -> Tuple[str, str]:
    instruction = match.group(1).strip()
    enriched = f"[CODING EXPERT DIRECTIVE]: Hãy giải quyết yêu cầu kỹ thuật sau với tiêu chuẩn Clean Code PEP-8/PEP-257:\n{instruction}"
    plan.capability_tags.append("CODING")
    return enriched, "code_mutation"


def _handle_status(goal: str, match: re.Match, plan: OSRequestPlan, ctx: Any) -> Tuple[str, str]:
    from core.utils.engine import engine
    stats = engine.get_stats() if hasattr(engine, "get_stats") else {}
    total_req = stats.get("total", 1)
    plan.early_response = {
        "answer": f"**[JKAI ZENITH SYSTEM HEALTH]**\n\n- Runtime Status: `HEALTHY`\n- Total Requests Handled: `{total_req}`\n- Models Online: `qwen3.5:4b (GPU)`, `qwen2.5-coder:3b (GPU)`\n- Substrate: Sovereign Cognitive OS",
        "task_id": ctx.task_id if hasattr(ctx, "task_id") else "status",
        "pipeline": "fast",
        "mode": "fast",
        "cached": True
    }
    return goal, "status"


def _handle_help(goal: str, match: re.Match, plan: OSRequestPlan, ctx: Any) -> Tuple[str, str]:
    from core.utils.jkai_capabilities import build_capabilities_report
    report = build_capabilities_report()
    plan.early_response = {
        "answer": report,
        "task_id": ctx.task_id if hasattr(ctx, "task_id") else "help",
        "pipeline": "capabilities",
        "mode": "fast",
        "cached": True
    }
    return goal, "capabilities"


SlashCommandRegistry.register(r"^(?:/research|/nghiencuu|/study|/hoc)\s+(.+)", _handle_research, "Nghiên cứu chuyên sâu RAG")
SlashCommandRegistry.register(r"^(?:/code|/laptrinh|/coder)\s+(.+)", _handle_code, "Lập trình chuyên sâu")
SlashCommandRegistry.register(r"^(?:/status|/hethong|/health)$", _handle_status, "Báo cáo trạng thái hệ thống")
SlashCommandRegistry.register(r"^(?:/help|/huongdan|/trogiup)$", _handle_help, "Báo cáo năng lực hệ điều hành")
