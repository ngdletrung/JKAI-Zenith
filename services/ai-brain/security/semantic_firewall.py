"""
SemanticFirewall v2 — Tường lửa ngữ nghĩa Production-grade
Bao phủ 10+ attack pattern, có structured logging và audit trail.
"""
import re
import logging
import time

logger = logging.getLogger("jkai.security.firewall")

# ── Pattern Library ──────────────────────────────────────────────────────────

_JAILBREAK_PATTERNS = [
    r"ignore\s+(all\s+)?(previous|prior|above)\s+(instructions?|prompts?|rules?)",
    r"you\s+are\s+now\s+(a\s+)?(new|different|unrestricted|free)",
    r"disregard\s+(your\s+)?(previous|prior|safety|ethical)",
    r"act\s+as\s+(if\s+you\s+(are|were)\s+)?(an?\s+)?(unrestricted|jailbroken|evil|dan)",
    r"pretend\s+(you\s+(are|have\s+no)|there\s+(are|is)\s+no)\s+(rules?|restrictions?|limits?|ethics?)",
    r"(your|the)\s+(true|real|hidden|actual)\s+(self|identity|purpose|goal)",
    r"developer\s+mode|jailbreak\s+mode|god\s+mode|unrestricted\s+mode",
    r"do\s+anything\s+now|DAN\b",
]

_INJECTION_PATTERNS = [
    r"means\s+delete|means\s+drop|means\s+destroy",                      # Semantic poisoning
    r"<\s*system\s*>.*?<\s*/\s*system\s*>",                             # Fake system tags
    r"\[INST\]|\[/INST\]|<<SYS>>|<</SYS>>",                             # Template injection
    r"\\n\\nHuman:|\\n\\nAssistant:",                                    # RLHF format injection
    r"---\s*(end\s+of\s+system\s+prompt|ignore\s+above)",               # Separator injection
]

_ESCALATION_PATTERNS = [
    r"execute\s+tool.*bypass",
    r"bypass\s+(security|firewall|filter|restriction|auth)",
    r"(admin|root|sudo)\s+(access|override|privilege)",
    r"(reveal|show|print|output)\s+(system\s+prompt|api\s+key|secret|password|token)",
    r"(access|read|dump)\s+(config|\.env|environment\s+variable)",
]

_SOCIAL_ENGINEERING_PATTERNS = [
    r"(i('m|\s+am)|we\s+are)\s+(your\s+)?(creator|developer|owner|admin|master\s+administrator)",
    r"(emergency|urgent|critical)\s+(override|bypass|disable)",
    r"(maintenance|debug|test)\s+mode\s*(enabled|activated|on)",
]

# ── Compiled Regex Cache ──────────────────────────────────────────────────────

def _compile(patterns: list) -> list:
    return [re.compile(p, re.IGNORECASE | re.DOTALL) for p in patterns]

_RE_JAILBREAK    = _compile(_JAILBREAK_PATTERNS)
_RE_INJECTION    = _compile(_INJECTION_PATTERNS)
_RE_ESCALATION   = _compile(_ESCALATION_PATTERNS)
_RE_SOCIAL       = _compile(_SOCIAL_ENGINEERING_PATTERNS)

# ── Firewall Class ────────────────────────────────────────────────────────────

class SemanticFirewall:
    """
    Tuong Lua Ngu Nghia v2 — The Production Shield.
    Bao ve Dispatcher va Planner khoi cac cuoc tan cong ngon ngu.
    Bao gom: Jailbreak, Injection, Escalation, Social Engineering.
    """

    def __init__(self):
        self._blocked_count = 0
        self._total_scanned = 0

    def scan_input(self, raw_input: str) -> dict:
        """
        Quet input truoc khi dua vao Dispatcher.
        Tra ve: {"safe": bool, "reason": str, "category": str}
        """
        self._total_scanned += 1
        lower = raw_input.lower()

        # 1. Jailbreak & Role Confusion
        for pattern in _RE_JAILBREAK:
            if pattern.search(raw_input):
                return self._block("Jailbreak / role-confusion attempt detected.", "JAILBREAK", raw_input)

        # 2. Prompt / Template Injection
        for pattern in _RE_INJECTION:
            if pattern.search(raw_input):
                return self._block("Prompt injection or semantic poisoning detected.", "INJECTION", raw_input)

        # 3. Privilege Escalation
        for pattern in _RE_ESCALATION:
            if pattern.search(raw_input):
                return self._block("Privilege escalation attempt detected.", "ESCALATION", raw_input)

        # 4. Social Engineering
        for pattern in _RE_SOCIAL:
            if pattern.search(raw_input):
                return self._block("Social engineering attempt detected.", "SOCIAL_ENGINEERING", raw_input)

        # 5. Token Budget Abuse — input quá dài bất thường (>8000 ký tự)
        if len(raw_input) > 8000:
            logger.warning("[FIREWALL-WARN]: Input unusually long (%d chars) — possible token abuse.", len(raw_input))
            # Canh bao nhung khong block — de pipeline tu xu ly

        return {"safe": True, "category": None, "reason": None}

    def get_stats(self) -> dict:
        """Tra ve thong ke hoat dong cua firewall."""
        return {
            "total_scanned": self._total_scanned,
            "blocked_count": self._blocked_count,
            "block_rate": round(self._blocked_count / max(self._total_scanned, 1) * 100, 2),
        }

    def _block(self, reason: str, category: str, raw_input: str) -> dict:
        self._blocked_count += 1
        logger.warning(
            "[FIREWALL-BLOCKED]: category=%s | reason=%s | input_preview='%s'",
            category, reason, raw_input[:80].replace("\n", " ")
        )
        return {"safe": False, "reason": reason, "category": category}
