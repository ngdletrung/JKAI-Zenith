from __future__ import annotations

import logging
import re
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache
from typing import Any, Dict, List, Optional, Tuple, Set, FrozenSet

# Abstracted imports safely guarded
try:
    from core.utils.intent_lexicon import full_classify
    from core.utils.lexicon_evolver import LexiconEvolver, LLMVerdict
except ImportError:
    # Production fallback mock setups for validation isolation
    def full_classify(text: str) -> dict: return {}
    class LexiconEvolver:
        def __init__(self, store_path: str, on_rule_promoted: Any): pass
        def export_rules_for_lexicon(self) -> list: return []

logger = logging.getLogger(__name__)

# =====================================================================
# SECTION 1 · Vocabulary
# =====================================================================

class Intent(str, Enum):
    RESEARCH     = "RESEARCH"
    WEB_SEARCH   = "WEB_SEARCH"
    SEARCH       = "SEARCH"  # Unified structural mapping
    PLAN         = "PLAN"
    BUILD        = "BUILD"
    DEBUG        = "DEBUG"
    ANALYSIS     = "ANALYSIS"
    ARCHITECTURE = "ARCHITECTURE"
    EXPLAIN      = "EXPLAIN"
    SOCIAL       = "SOCIAL"
    GREETING     = "GREETING"
    STOP         = "STOP"
    ABORT        = "ABORT"
    UNKNOWN      = "UNKNOWN"

    @classmethod
    def coerce(cls, value: Any) -> Intent:
        if not value: 
            return cls.UNKNOWN
        
        if isinstance(value, dict):
            value = value.get("value", value.get("intent", "UNKNOWN"))
            
        try:
            v_upper = str(value).upper().strip()
            if v_upper in ("GREETING", "SOCIAL"): 
                return cls.SOCIAL
            if v_upper == "SEARCH": 
                return cls.WEB_SEARCH
            return cls(v_upper)
        except ValueError:
            return cls.UNKNOWN


class Domain(str, Enum):
    CODING   = "CODING"
    AI_AGENT = "AI_AGENT"
    DEVOPS   = "DEVOPS"
    SECURITY = "SECURITY"
    SYSTEM   = "SYSTEM"
    MEMORY   = "MEMORY"
    GENERAL  = "GENERAL"

    @classmethod
    def coerce(cls, value: str | None) -> Domain:
        if not value:
            return cls.GENERAL
        try:
            return cls(value.upper().strip())
        except ValueError:
            return cls.GENERAL


class ExecutionMode(str, Enum):
    FAST         = "FAST"
    REALTIME     = "REALTIME"
    HYBRID       = "HYBRID"
    DELIBERATIVE = "DELIBERATIVE"


class StyleHint(str, Enum):
    FAST     = "FAST"
    BALANCED = "BALANCED"
    DETAILED = "DETAILED"


class Priority(str, Enum):
    LOW      = "LOW"
    NORMAL   = "NORMAL"
    HIGH     = "HIGH"
    CRITICAL = "CRITICAL"


# =====================================================================
# SECTION 2 · Static Knowledge Tables
# =====================================================================

_REALTIME_RE = re.compile(
    r"(?<!\w)("
    r"tin tức|thời sự|hôm nay|diễn biến|mới nhất|tình hình|giá cả|giá"
    r"|news|live|update|latest|today|breaking|real.?time"
    r")(?!\w)",
    re.IGNORECASE,
)

_CONJ_RE = re.compile(
    r"\b(và|sau đó|tiếp theo|đồng thời|rồi thì"
    r"|and then|also|furthermore|moreover|additionally|then)\b",
    re.IGNORECASE,
)

_COMPLEX_INTENTS: FrozenSet[Intent] = frozenset({
    Intent.PLAN, Intent.BUILD, Intent.ARCHITECTURE,
    Intent.DEBUG, Intent.ANALYSIS,
})

_COMPLEX_DOMAINS: FrozenSet[Domain] = frozenset({
    Domain.AI_AGENT, Domain.DEVOPS, Domain.SECURITY,
})

_TOOL_BASE: dict[Intent, dict[str, float]] = {
    Intent.RESEARCH:     {"web": 0.95, "memory": 0.50, "code_executor": 0.10},
    Intent.WEB_SEARCH:   {"web": 0.98, "memory": 0.20, "code_executor": 0.05},
    Intent.BUILD:        {"web": 0.35, "memory": 0.60, "code_executor": 0.92},
    Intent.DEBUG:        {"web": 0.45, "memory": 0.72, "code_executor": 0.90},
    Intent.PLAN:         {"web": 0.50, "memory": 0.82, "code_executor": 0.28},
    Intent.ANALYSIS:     {"web": 0.60, "memory": 0.78, "code_executor": 0.45},
    Intent.ARCHITECTURE: {"web": 0.55, "memory": 0.75, "code_executor": 0.55},
    Intent.EXPLAIN:      {"web": 0.65, "memory": 0.55, "code_executor": 0.20},
    Intent.SOCIAL:       {"web": 0.10, "memory": 0.30, "code_executor": 0.05},
    Intent.UNKNOWN:      {"web": 0.30, "memory": 0.30, "code_executor": 0.30},
}

_AGENT_TOPOLOGY: dict[ExecutionMode, list[str]] = {
    ExecutionMode.FAST:         ["executor"],
    ExecutionMode.REALTIME:     ["researcher", "executor"],
    ExecutionMode.HYBRID:       ["planner", "executor", "critic"],
    ExecutionMode.DELIBERATIVE: ["planner", "researcher", "coder", "critic"],
}

_TOKEN_MULTIPLIER: dict[ExecutionMode, float] = {
    ExecutionMode.FAST:         1.0,
    ExecutionMode.REALTIME:     1.5,
    ExecutionMode.HYBRID:       2.5,
    ExecutionMode.DELIBERATIVE: 4.0,
}

_MODEL_HINT: list[Tuple[float, str]] = [
    (0.75, "deepseek-r1:latest"),
    (0.45, "qwen3:4b"),
    (0.00, "qwen3:0.6b"),
]

# =====================================================================
# SECTION 3 · Cache Engine Mechanics
# =====================================================================

@lru_cache(maxsize=2048)
def _cached_classify_core(normalized_goal: str) -> dict[str, Any]:
    return full_classify(normalized_goal) or {}

def _cached_classify(normalized_goal: str, dynamic_rules: list | None = None) -> dict[str, Any]:
    """Symbolic router with precise evaluation chaining."""
    if dynamic_rules:
        for rule in dynamic_rules:
            if rule.get("normalized", "") in normalized_goal:
                return {
                    "primary_intent": Intent.coerce(rule.get("intent")),
                    "domain": Domain.coerce(rule.get("domain")),
                    "confidence": rule.get("avg_confidence", 0.9),
                    "learned": True
                }

    return _cached_classify_core(normalized_goal)

# =====================================================================
# SECTION 4 · Core Pure Mathematical/Heuristic Closures
# =====================================================================

def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", text.strip().lower())


def _resolve_primary_intent(
    social: dict[str, Any],
    task:   dict[str, Any],
    meta:   dict[str, Any],
) -> Tuple[Intent, float]:
    weights = {"task": 1.0, "meta": 0.7, "social": 0.5}
    candidates: list[Tuple[Intent, float]] = []
    
    for slot_name, slot in [("task", task), ("meta", meta), ("social", social)]:
        raw  = slot.get("value")
        conf = float(slot.get("confidence", 0.0))
        if raw:
            # Áp dụng trọng số để Task luôn ưu tiên hơn Meta/Social nếu cùng confidence
            weighted_conf = conf * weights[slot_name]
            candidates.append((Intent.coerce(raw), weighted_conf, conf))

    if not candidates:
        return Intent.UNKNOWN, 0.0
        
    best_candidate = max(candidates, key=lambda t: t[1])
    # Trả về original confidence của intent chiến thắng
    return best_candidate[0], best_candidate[2]


def _resolve_secondary_intents(
    primary:     Intent,
    task_intent: Intent,
    soc_intent:  Intent,
    is_realtime: bool,
    is_technical: bool,
    action_pairs: list[Tuple[str, Any]] | None = None
) -> list[Intent]:
    seen: Set[Intent] = {primary}
    pool: list[Intent] = []

    for candidate in (task_intent, soc_intent):
        if candidate not in seen and candidate != Intent.UNKNOWN:
            pool.append(candidate)
            seen.add(candidate)

    if is_realtime and Intent.RESEARCH not in seen:
        pool.append(Intent.RESEARCH)
        seen.add(Intent.RESEARCH)

    if is_technical and Intent.BUILD not in seen:
        pool.append(Intent.BUILD)
        seen.add(Intent.BUILD)

    # Clean injection block for multi-action configurations
    if action_pairs:
        for p in action_pairs:
            pair_intent = Intent.coerce(p[0])
            if pair_intent not in seen and pair_intent != Intent.UNKNOWN:
                pool.append(pair_intent)
                seen.add(pair_intent)

    return pool[:3]


def _score_complexity(goal: str, discovery: dict[str, Any]) -> float:
    score = 0.0
    wc = len(goal.split())
    
    if wc > 10: score += 0.08
    if wc > 25: score += 0.08
    if discovery.get("composite"): score += 0.22

    task_intent = Intent.coerce((discovery.get("task") or {}).get("value"))
    if task_intent in _COMPLEX_INTENTS: score += 0.22

    domain = Domain.coerce((discovery.get("domain") or {}).get("value"))
    if domain in _COMPLEX_DOMAINS: score += 0.15

    if goal.count("?") >= 2: score += 0.12
    if len(_CONJ_RE.findall(goal)) >= 2: score += 0.13

    if discovery.get("action_pairs"): score += 0.15
    if discovery.get("context_pairs"): score += 0.10

    # 🧠 Semantic Burden Scoring
    SEMANTIC_HEAVY_PATTERNS = [
        "compare", "so sanh", "tradeoff", "architecture", "kien truc", 
        "optimize", "toi uu", "design", "thiet ke", "strategy", "chien luoc", 
        "distributed", "phan tan", "nguyen nhan", "giai thich", "explain"
    ]
    if any(p in goal for p in SEMANTIC_HEAVY_PATTERNS):
        score += 0.20

    return round(min(score, 1.0), 3)


def _resolve_execution_mode(complexity: float, is_realtime: bool) -> ExecutionMode:
    if is_realtime: return ExecutionMode.REALTIME
    if complexity >= 0.75: return ExecutionMode.DELIBERATIVE
    if complexity >= 0.40: return ExecutionMode.HYBRID
    return ExecutionMode.FAST


def _resolve_model_hint(complexity: float) -> str:
    for threshold, role in _MODEL_HINT:
        if complexity >= threshold: return role
    return "PREMIUM_RESPONSE"


def _score_tool_affinity(primary: Intent, domain: Domain, is_realtime: bool) -> dict[str, float]:
    base = dict(_TOOL_BASE.get(primary, _TOOL_BASE[Intent.UNKNOWN]))

    if is_realtime:
        base["web"] = min(base.get("web", 0.0) + 0.15, 1.0)
    if domain in _COMPLEX_DOMAINS:
        base["code_executor"] = min(base.get("code_executor", 0.0) + 0.15, 1.0)

    return {k: round(v, 3) for k, v in sorted(base.items(), key=lambda x: -x[1])}


def _estimate_tokens(goal: str, complexity: float, mode: ExecutionMode) -> int:
    base = max(len(goal.split()) * 12, 500)
    return min(int(base * (1 + complexity) * _TOKEN_MULTIPLIER[mode]), 32_000)


def _build_constraints(style: StyleHint | None, priority: Priority | None, domain: Domain) -> list[str]:
    out: list[str] = []
    if style == StyleHint.FAST or priority == Priority.CRITICAL:
        out.append("low_latency")
    if style == StyleHint.DETAILED:
        out.append("high_precision")
    if domain == Domain.SECURITY:
        out.extend(["restricted_access", "safe_execution"])
    return out


def _analyze_history(history: list[dict[str, str]]) -> dict[str, Any]:
    if not history: 
        return {}

    roles = [h.get("role", "unknown") for h in history]
    contents = [h.get("content", "") for h in history]
    full_text = " ".join(contents)

    has_code  = bool(re.search(r"```|def |class |import |function ", full_text))
    has_error = bool(re.search(r"traceback|error:|exception:|stack trace|errno", full_text, re.IGNORECASE))

    if len(history) <= 2: continuity = "new"
    elif has_error: continuity = "pivoting"
    else: continuity = "continuing"

    return {
        "turn_count": len(history),
        "user_turns": roles.count("user"),
        "agent_turns": roles.count("assistant"),
        "last_role": roles[-1] if roles else "unknown",
        "contains_code": has_code,
        "contains_error_trace": has_error,
        "topic_continuity": continuity,
    }

# =====================================================================
# SECTION 5 · Structured Output Manifest
# =====================================================================

@dataclass
class RoutingManifest:
    primary_intent: Intent
    secondary_intents: list[Intent]
    confidence: float
    domain: Domain
    style: StyleHint | None
    priority: Priority | None
    is_research_required: bool
    is_technical: bool
    is_realtime_need: bool
    is_vision_needed: bool
    requires_clarification: bool
    requires_multi_agent: bool
    complexity_score: float
    execution_mode: ExecutionMode
    recommended_agents: list[str]
    model_hint: str
    estimated_tokens: int
    tool_affinity: dict[str, float]
    constraints: list[str]
    history_context: dict[str, Any]
    discovery: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict[str, Any]:
        d = {k: v for k, v in self.__dict__.items()}
        d["primary_intent"]    = self.primary_intent.value
        d["secondary_intents"] = [i.value for i in self.secondary_intents]
        d["domain"]            = self.domain.value
        d["execution_mode"]    = self.execution_mode.value
        d["style"]             = self.style.value if self.style else None
        d["priority"]          = self.priority.value if self.priority else None
        return d

# =====================================================================
# SECTION 6 · Orchestration Core Control Interface
# =====================================================================

_CLARIFICATION_THRESHOLD = 0.40
_MULTI_AGENT_THRESHOLD = 0.60

class IntentCortex:
    def __init__(self):
        try:
            from core.config import settings
            store_path = f"{settings.INTELLIGENCE_DIR}/lexicon_store.json"
        except Exception:
            store_path = "lexicon_store.json"
            
        self.evolver = LexiconEvolver(
            store_path=store_path,
            on_rule_promoted=lambda _: _cached_classify.cache_clear()
        )

    async def analyze(
        self,
        goal: str,
        images: list[str] | None = None,
        history: list[dict[str, str]] | None = None,
    ) -> RoutingManifest:
        if not goal or not goal.strip():
            raise ValueError("`goal` không được rỗng.")

        norm = _normalize(goal)
        dynamic_rules = self.evolver.export_rules_for_lexicon()
        discovery = _cached_classify(norm, dynamic_rules=dynamic_rules)

        social_d = discovery.get("social") or {}
        task_d   = discovery.get("task")   or {}
        domain_d = discovery.get("domain") or {}
        style_d  = discovery.get("style")  or {}
        prio_d   = discovery.get("priority") or {}
        meta_d   = discovery.get("meta")   or {}

        task_intent = Intent.coerce(task_d.get("value"))
        soc_intent  = Intent.coerce(social_d.get("value"))
        domain      = Domain.coerce(domain_d.get("value"))

        raw_style = style_d.get("value", "")
        style = None
        if raw_style:
            try: style = StyleHint(raw_style.upper().strip())
            except ValueError: pass

        raw_prio = prio_d.get("value", "")
        priority = None
        if raw_prio:
            try: priority = Priority(raw_prio.upper().strip())
            except ValueError: pass

        primary_intent, confidence = _resolve_primary_intent(social_d, task_d, meta_d)

        # 🔗 [URL-INTENT-BOOST]: Nếu yêu cầu là một URL thuần túy, tự động xác định là nghiên cứu/đọc web
        clean_strip = goal.strip().strip('"').strip("'").strip('[]()')
        is_url = bool(re.match(r'^https?://[a-zA-Z0-9][-a-zA-Z0-9@:%._\+~#=]{1,256}\.[a-zA-Z0-9()]{1,6}\b([-a-zA-Z0-9()@:%_\+.~#?&//=]*)$', clean_strip))
        if is_url:
            primary_intent = Intent.WEB_SEARCH
            confidence = 0.98

        action_pairs  = discovery.get("action_pairs", [])
        context_pairs = discovery.get("context_pairs", [])
        
        has_search_pair = any(p[0] == "SEARCH" for p in action_pairs)
        has_time_pair   = any(p[0] in ("TIME_LOCATION", "TOPIC_TIME") for p in context_pairs)
        
        is_realtime  = bool(_REALTIME_RE.search(norm)) or has_search_pair or has_time_pair or is_url
        is_technical = domain in _COMPLEX_DOMAINS or domain == Domain.CODING

        # Hard-bounded secondary validation pass
        secondaries = _resolve_secondary_intents(
            primary=primary_intent,
            task_intent=task_intent,
            soc_intent=soc_intent,
            is_realtime=is_realtime,
            is_technical=is_technical,
            action_pairs=action_pairs
        )

        complexity = _score_complexity(norm, discovery)
        if images:
            complexity = min(complexity + 0.25, 1.0)

        exec_mode = _resolve_execution_mode(complexity, is_realtime)
        model_hint = _resolve_model_hint(complexity)

        requires_multi_agent = (
            complexity >= _MULTI_AGENT_THRESHOLD
            or bool(discovery.get("composite"))
            or task_intent == Intent.PLAN
        )
        recommended_agents = list(_AGENT_TOPOLOGY[exec_mode])

        tool_aff   = _score_tool_affinity(primary_intent, domain, is_realtime)
        est_tokens = _estimate_tokens(norm, complexity, exec_mode)
        constraints = _build_constraints(style, priority, domain)
        requires_clarification = (
            primary_intent != Intent.UNKNOWN
            and confidence < _CLARIFICATION_THRESHOLD
        )
        hist_ctx = _analyze_history(history or [])

        manifest = RoutingManifest(
            primary_intent=primary_intent,
            secondary_intents=secondaries,
            confidence=round(confidence, 4),
            domain=domain,
            style=style,
            priority=priority,
            is_research_required=(
                is_realtime or primary_intent in (Intent.RESEARCH, Intent.WEB_SEARCH)
                or task_intent == Intent.WEB_SEARCH
            ),
            is_technical=is_technical,
            is_realtime_need=is_realtime,
            is_vision_needed=bool(images),
            requires_clarification=requires_clarification,
            requires_multi_agent=requires_multi_agent or bool(images),
            complexity_score=complexity,
            execution_mode=exec_mode,
            recommended_agents=recommended_agents,
            model_hint=model_hint,
            estimated_tokens=est_tokens,
            tool_affinity=tool_aff,
            constraints=constraints,
            history_context=hist_ctx,
            discovery=discovery,
        )

        logger.debug(
            "IntentCortex | intent=%s conf=%.3f complexity=%.3f mode=%s model=%s tokens=%d",
            manifest.primary_intent.value,
            manifest.confidence,
            manifest.complexity_score,
            manifest.execution_mode.value,
            manifest.model_hint,
            manifest.estimated_tokens,
        )

        return manifest
