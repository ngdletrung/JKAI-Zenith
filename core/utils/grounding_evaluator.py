# -----------------------------------------------------------------------------
# [ZENITH FILE DIRECTIVE]
# - File: core/utils/grounding_evaluator.py
# - Role: Output Grounding Evaluator & Secret Scrubber (SOTA 2026)
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v1.0
#
# [WORKING PRINCIPLES]:
# 1. Zero LLM call — Pure Python regex & state inspection (< 0.5ms latency).
# 2. Secret Scrubbing: Redacts sensitive keys, tokens, or credentials before user display.
# 3. Grounding Verification: Verifies code fences and structural markdown validity.
# -----------------------------------------------------------------------------

import re
import logging
from typing import Dict, Any, Tuple

logger = logging.getLogger("JKAI.GroundingEvaluator")

# Patterns for sensitive credentials/keys
_SECRET_PATTERNS = [
    (r"(?i)(api[_-]?key|secret[_-]?key|password|token)\s*[:=]\s*['\"]?([a-zA-Z0-9_\-\.\/]{16,})['\"]?", r"\1= [REDACTED_SECRET]"),
    (r"\b(AKIA[0-9A-Z]{16})\b", "[REDACTED_AWS_KEY]"),
    (r"\b(sk-[a-zA-Z0-9]{32,})\b", "[REDACTED_OPENAI_KEY]"),
]


def scrub_secrets(text: str) -> str:
    """Scrub sensitive keys or passwords from output text."""
    if not text:
        return ""
    clean_text = text
    for pat, repl in _SECRET_PATTERNS:
        clean_text = re.sub(pat, repl, clean_text)
    return clean_text


def evaluate_grounding(text: str) -> Tuple[float, Dict[str, Any]]:
    """
    Evaluates structural markdown grounding & balance.

    Returns:
        (score: float 0.0-1.0, report: Dict)
    """
    if not text or not text.strip():
        return 0.0, {"valid": False, "reason": "Empty text"}

    issues = []
    
    # 1. Balanced code fences
    fence_count = len(re.findall(r"```", text))
    if fence_count % 2 != 0:
        issues.append("Unclosed markdown code fence ```")

    # 2. Check for stub placeholder markers
    if re.search(r"\[TODO|YOUR_CODE_HERE|INSERT_HERE\]", text, re.IGNORECASE):
        issues.append("Contains unfulfilled placeholder stub")

    score = 1.0 if not issues else max(0.5, 1.0 - (len(issues) * 0.25))
    return score, {"valid": len(issues) == 0, "issues": issues, "fence_count": fence_count}
