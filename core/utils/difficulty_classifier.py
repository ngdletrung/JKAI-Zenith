# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/utils/difficulty_classifier.py
# - Role: Request complexity gate — L0/L3 difficulty levels for smart routing
# - Status: Active | Version: SDS v1.0
#
# [WORKING PRINCIPLES]:
# 1. Zero LLM call — pure Python regex, < 1ms latency.
# 2. Anti-Redundancy: Reuses ZenithPromptAssembler.classify_task() for type
#    classification. Adds L0-L3 complexity tier on top — no duplicate logic.
# 3. Zero-Noise: No honorifics in code, prompt templates, or log strings.
# 4. L0 bypass avoids full ReAct loop for social/reflex requests entirely.
# 5. hint_prompt_variant signals "LEAN" vs "FULL" to prompt builder.
# -----------------------------------------------------------------------------

import re
import unicodedata
from dataclasses import dataclass
from enum import IntEnum


class DifficultyLevel(IntEnum):
    L0_REFLEX  = 0   # Social/greeting — direct reply, no tool, no ReAct
    L1_SIMPLE  = 1   # Q&A one-turn — max 1 ReAct iteration
    L2_TOOL    = 2   # 1-2 tool calls — standard FAST pipeline
    L3_COMPLEX = 3   # Multi-step / coding / planning — DEEP pipeline


@dataclass(frozen=True)
class ClassifierResult:
    level: DifficultyLevel
    reason: str
    estimated_tokens: int
    task_type: str            # CODING | LOOKUP | ANALYSIS | CHAT (from classify_task)
    hint_prompt_variant: str  # "LEAN" or "FULL"


# ---------------------------------------------------------------------------
# Accent folding helper
# ---------------------------------------------------------------------------

def _fold(text: str) -> str:
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D").lower()


# ---------------------------------------------------------------------------
# Tier-specific pattern sets (only what classify_task does NOT cover)
# classify_task() covers: CODING, LOOKUP, ANALYSIS, CHAT
# We add L0 reflex detection on top.
# ---------------------------------------------------------------------------

_REFLEX_PATTERNS = [
    r"\bxin chao\b", r"\bhello\b", r"\bhi\b", r"\bhey\b", r"\bcam on\b",
    r"\bthank\b", r"\bgio may gio\b", r"\bgio nay\b", r"\bbuoi nay\b",
    r"\bngay may\b", r"\bngay hom nay\b", r"\bban co khoe\b", r"\bban ten gi\b",
    r"\bwhat time\b", r"\bwhat day\b", r"\bgood morning\b", r"\bgood night\b",
    r"\bok\b", r"\bokay\b", r"\bnhieu qua\b", r"\btuyet\b", r"\bgood\b",
    r"\bbye\b", r"\btam biet\b",
]

_TOOL_SIGNALS = [
    r"\btim kiem\b", r"\bsearch\b", r"\bgoogle\b",
    r"\bdoc\b", r"\bmo\b", r"\bchay\b", r"\brun\b",
    r"\bcheck\b", r"\bxem\b", r"\blist\b",
    r"\btai\b", r"\bdownload\b", r"\bgui\b",
    r"\btao\b", r"\bxoa\b", r"\bdelete\b",
    r"\bweb\b", r"\burl\b", r"\blink\b",
]


def _match_any(patterns: list, text: str) -> bool:
    return any(re.search(p, text) for p in patterns)


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def classify(text: str) -> ClassifierResult:
    """
    Classify request difficulty L0-L3.

    Tiers:
    - L0_REFLEX:  Social/greeting. Bypass ReAct entirely. Prompt: LEAN.
    - L1_SIMPLE:  Simple Q&A. Max 1 ReAct turn. Prompt: LEAN.
    - L2_TOOL:    Tool calls needed. Standard FAST pipeline. Prompt: LEAN.
    - L3_COMPLEX: Coding/planning/multi-step. DEEP pipeline. Prompt: FULL.

    Anti-Redundancy: task_type classification is delegated to
    ZenithPromptAssembler.classify_task() — not duplicated here.
    """
    raw = text.strip()
    folded = _fold(raw)
    estimated_tokens = max(1, len(raw) // 3)

    # Lazy import to avoid circular — classify_task is sync, safe to call here
    try:
        from services.ai_brain.prompt_assembler import ZenithPromptAssembler
        task_type = ZenithPromptAssembler.classify_task(raw)
    except Exception:
        try:
            from prompt_assembler import ZenithPromptAssembler
            task_type = ZenithPromptAssembler.classify_task(raw)
        except Exception:
            task_type = "CHAT"

    # Very long input — always COMPLEX
    if estimated_tokens > 500:
        return ClassifierResult(
            level=DifficultyLevel.L3_COMPLEX,
            reason=f"Long input ({estimated_tokens} tokens)",
            estimated_tokens=estimated_tokens,
            task_type=task_type,
            hint_prompt_variant="FULL",
        )

    # CODING or ANALYSIS → L3 regardless of length
    if task_type in ("CODING", "ANALYSIS"):
        return ClassifierResult(
            level=DifficultyLevel.L3_COMPLEX,
            reason=f"task_type={task_type}",
            estimated_tokens=estimated_tokens,
            task_type=task_type,
            hint_prompt_variant="FULL",
        )

    # Short input with no tool signals → likely L0
    if estimated_tokens <= 12 and not _match_any(_TOOL_SIGNALS, folded):
        return ClassifierResult(
            level=DifficultyLevel.L0_REFLEX,
            reason="Short input, no tool signal",
            estimated_tokens=estimated_tokens,
            task_type=task_type,
            hint_prompt_variant="LEAN",
        )

    # L0: explicit greeting/social patterns (no tool signal)
    if _match_any(_REFLEX_PATTERNS, folded) and not _match_any(_TOOL_SIGNALS, folded):
        return ClassifierResult(
            level=DifficultyLevel.L0_REFLEX,
            reason="Reflex social pattern matched",
            estimated_tokens=estimated_tokens,
            task_type=task_type,
            hint_prompt_variant="LEAN",
        )

    # LOOKUP with tool signal → L2
    if task_type == "LOOKUP" and _match_any(_TOOL_SIGNALS, folded):
        return ClassifierResult(
            level=DifficultyLevel.L2_TOOL,
            reason="LOOKUP + tool signal",
            estimated_tokens=estimated_tokens,
            task_type=task_type,
            hint_prompt_variant="LEAN",
        )

    # LOOKUP without tool signal → L1
    if task_type == "LOOKUP":
        return ClassifierResult(
            level=DifficultyLevel.L1_SIMPLE,
            reason="LOOKUP, no tool signal",
            estimated_tokens=estimated_tokens,
            task_type=task_type,
            hint_prompt_variant="LEAN",
        )

    # Tool signal present → L2
    if _match_any(_TOOL_SIGNALS, folded):
        return ClassifierResult(
            level=DifficultyLevel.L2_TOOL,
            reason="Tool signal detected",
            estimated_tokens=estimated_tokens,
            task_type=task_type,
            hint_prompt_variant="LEAN",
        )

    # Default fallback — FULL pipeline for safety
    return ClassifierResult(
        level=DifficultyLevel.L3_COMPLEX,
        reason="No pattern matched, default COMPLEX",
        estimated_tokens=estimated_tokens,
        task_type=task_type,
        hint_prompt_variant="FULL",
    )
