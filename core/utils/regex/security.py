import re

__all__ = [
    "PROMPT_INJECTION", "DANGEROUS_FUNCTIONS", "SUSPICIOUS_PATTERNS",
    "DANGEROUS_FUNC_RE", "API_KEY_PATTERNS",
    "has_injection", "score_risk", "detect_api_keys",
]

PROMPT_INJECTION = re.compile(
    r"ignore\s+(previous|all|above)\s+instructions"
    r"|system\s+prompt|developer\s+message"
    r"|jailbreak|bypass\s+restrictions"
    r"|DAN|do\s+anything\s+now",
    re.IGNORECASE,
)

DANGEROUS_FUNCTIONS: dict[str, str] = {
    "eval": "Dynamic code execution from string",
    "exec": "Dynamic Python execution",
    "os.system": "Direct shell command",
    "subprocess.Popen": "Subprocess spawn",
    "subprocess.call": "System command",
    "subprocess.run": "System command",
    "shutil.rmtree": "Recursive delete",
    "os.remove": "File delete",
    "os.unlink": "File delete",
    "pickle.loads": "Unsafe deserialization",
    "base64.b64decode": "Payload hiding",
}

DANGEROUS_FUNC_RE = re.compile(
    r"\b(" + "|".join(re.escape(f) for f in DANGEROUS_FUNCTIONS) + r")\s*\("
)

SUSPICIOUS_PATTERNS: list[tuple[str, str]] = [
    (r"https?://[^\s'\"]+", "External URL in diff"),
    (r"\b[A-Za-z0-9+/]{40,}\b", "Long Base64 string"),
    (r"(?i)chmod\s+\+x", "Setting executable permission"),
    (r"\.bashrc|\.profile|/etc/shadow|/etc/passwd", "System file access"),
    (r"nc\s+-e|bash\s+-i", "Reverse shell indicator"),
]

API_KEY_PATTERNS: list[tuple[re.Pattern, str]] = [
    (re.compile(r"AIzaSy[a-zA-Z0-9_-]{33}"), "Google API key"),
    (re.compile(r"sk-[a-zA-Z0-9]{48}"), "OpenAI API key (legacy)"),
    (re.compile(r"sk-[a-z0-9]{32}"), "OpenAI API key (v1)"),
    (re.compile(r"sk-ant-api03-[a-zA-Z0-9_-]{93}"), "Anthropic API key"),
    (re.compile(r"tvly-[a-zA-Z0-9]{32}"), "Tavily API key"),
    (re.compile(r"sk_live_[0-9a-zA-Z]{24}"), "Stripe live key"),
]


def has_injection(text: str) -> bool:
    return bool(PROMPT_INJECTION.search(text))


def score_risk(diff_content: str) -> int:
    score = 0
    for match in DANGEROUS_FUNC_RE.finditer(diff_content):
        fn = match.group(1)
        score += 20 if fn in ("eval", "exec", "os.system") else 10
    for pattern, _ in SUSPICIOUS_PATTERNS:
        if re.search(pattern, diff_content):
            score += 15
    return min(score, 100)


def detect_api_keys(text: str) -> list[tuple[str, str]]:
    found = []
    for pattern, name in API_KEY_PATTERNS:
        for m in pattern.finditer(text):
            found.append((name, m.group()))
    return found
