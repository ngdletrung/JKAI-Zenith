# Improved JKAI Zenith Dispatcher (Production-Grade Version)
import os
import re
import json
import time
import asyncio
import logging
import unicodedata
from pathlib import Path
from dataclasses import dataclass
from typing import Optional
from collections import Counter
import uuid
from core.utils.routing_manifest import RoutingManifest, ActionType

from core.utils.engine import engine

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# 💎 [UTILITY] — Vietnamese Accent Folding + Text Cleanup
# ---------------------------------------------------------------------------

def remove_accents(text: str) -> str:
    """Chuẩn hóa unicode + loại bỏ dấu tiếng Việt."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")


_NOISE_RE = re.compile(r"\(.*?\)|\[.*?]")
_MULTI_SPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
# 💎 [SKILL-TRIGGER-MAP]
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TriggerRule:
    id: str
    skill: str
    keywords: tuple[str, ...]
    priority: int = 50
    mode: str = "fast"
    negative_patterns: tuple[str, ...] = ()
    semantic_hints: tuple[str, ...] = ()
    domain: str = "GENERAL"
    intent: str = "EXECUTION"
    action_type: ActionType = ActionType.EXECUTION


SKILL_TRIGGER_MAP: list[TriggerRule] = [
    TriggerRule(
        "00-S",
        "GREETING",
        ("chào", "chao", "hi", "hello", "helo", "hey", "alo"),
        priority=10,
    ),

    TriggerRule(
        "05",
        "skill_self_healing",
        (
            "chiến binh zenith",
            "chien binh zenith",
            "sửa chữa hệ thống",
            "kiem tra he thong",
            "kiểm tra hệ thống",
        ),
        priority=20,
        mode="deep",
    ),

    TriggerRule(
        "26",
        "skill_dongbotrithuc",
        (
            "đồng bộ",
            "dong bo",
            "đồng hóa",
            "dong hoa",
            "assimilate",
            "sync",
            "nạp tri thức",
            "nap tri thuc",
            "nạp data",
        ),
        priority=30,
        mode="deep",
    ),

    TriggerRule(
        "32",
        "skill_kiemtrasuckhoe",
        (
            "sức khỏe",
            "suc khoe",
            "health check",
            "trạng thái hệ thống",
            "trang thai he thong",
        ),
        priority=30,
    ),

    TriggerRule(
        "30",
        "skill_giam_sat_he_thong",
        (
            "giám sát",
            "giam sat",
            "monitor",
            "pulse",
            "tài nguyên",
            "tai nguyen",
            "cpu",
            "ram",
        ),
        priority=30,
    ),

    TriggerRule(
        "28",
        "skill_host_control",
        (
            "docker",
            "restart container",
            "khởi động lại",
            "khoi dong lai",
            "vram",
            "gpu lock",
        ),
        priority=20,
        mode="deep",
    ),

    TriggerRule(
        "29",
        "skill_quantrihethong",
        (
            "quản trị",
            "quan tri",
            "thư mục",
            "thu muc",
            "file system",
            "folder",
            "directory",
            "phân quyền",
            "phan quyen",
        ),
        priority=40,
        mode="deep",
    ),

    TriggerRule(
        "27",
        "skill_sieutimkiem",
        (
            "tìm kiếm",
            "tim kiem",
            "tìm",
            "tim",
            "quét",
            "quet",
            "tin tức",
            "tin tuc",
            "search",
        ),
        priority=50,
    ),

    TriggerRule(
        "03",
        "skill_autonomous_researcher",
        (
            "nghiên cứu",
            "nghien cuu",
            "research",
            "tìm hiểu",
            "tim hieu",
        ),
        priority=60,
        mode="deep",
    ),

    TriggerRule(
        "04",
        "skill_code_audit_elite",
        (
            "audit code",
            "kiểm tra code",
            "kiem tra code",
            "tối ưu code",
            "toi uu code",
            "refactor",
            "bug",
            "fix code",
        ),
        priority=30,
        mode="deep",
    ),

    TriggerRule(
        "19",
        "skill_strategic_recon",
        (
            "browser",
            "duyệt web",
            "duyet web",
            "mở trang",
            "mo trang",
            "url",
        ),
        priority=40,
    ),

    TriggerRule(
        "18",
        "skill_agentic_debate",
        (
            "phản biện",
            "phan bien",
            "tranh luận",
            "tranh luan",
            "debate",
            "hội đồng",
            "hoi dong",
            "xung đột",
            "xung dot",
        ),
        priority=40,
        mode="deep",
    ),

    TriggerRule(
        "107",
        "skill_council_of_minds",
        (
            "hội đồng tư duy",
            "hoi dong tu duy",
            "council of minds",
            "hợp nhất ý kiến",
            "hop nhat y kien",
        ),
        priority=20,
        mode="deep",
    ),

    TriggerRule(
        "108",
        "skill_generate_image",
        (
            "vẽ ảnh",
            "ve anh",
            "tạo ảnh",
            "tao anh",
            "generate image",
            "dall-e",
            "midjourney",
        ),
        priority=20,
    ),
]


# ---------------------------------------------------------------------------
# 💎 [COMPILED RULE ENGINE]
# ---------------------------------------------------------------------------
_SORTED_RULES = sorted(SKILL_TRIGGER_MAP, key=lambda r: r.priority)


_RULE_PATTERNS: list[tuple[TriggerRule, list[re.Pattern], list[re.Pattern]]] = []

for rule in _SORTED_RULES:
    compiled_patterns = []
    compiled_negative = []

    for kw in rule.keywords:
        escaped = re.escape(remove_accents(kw.lower()))
        if re.fullmatch(r"[\w\s]+", escaped):
            pattern = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
        else:
            pattern = re.compile(escaped, re.IGNORECASE)
        compiled_patterns.append(pattern)

    for kw in rule.negative_patterns:
        escaped = re.escape(remove_accents(kw.lower()))
        if re.fullmatch(r"[\w\s]+", escaped):
            pattern = re.compile(rf"\b{escaped}\b", re.IGNORECASE)
        else:
            pattern = re.compile(escaped, re.IGNORECASE)
        compiled_negative.append(pattern)

    _RULE_PATTERNS.append((rule, compiled_patterns, compiled_negative))


# ---------------------------------------------------------------------------
# 💎 [DISPATCHER]
# ---------------------------------------------------------------------------
class Dispatcher:
    """
    🏗️ JKAI ZENITH DISPATCHER

    Architecture:

    Layer 1 → Reflex Matcher
    Layer 2 → Weighted Intent Ranking
    Layer 3 → LLM Arbitration
    Layer 4 → Failsafe Recovery
    """

    _SKILLS_MAP_CANDIDATES = [
        Path.cwd() / "intelligence" / "MAP_SKILLS.md",
        Path("/intelligence/MAP_SKILLS.md"),
        Path(__file__).resolve().parents[2] / "intelligence" / "MAP_SKILLS.md"
        if len(Path(__file__).resolve().parents) > 2
        else Path("/intelligence/MAP_SKILLS.md"),
    ]

    _MAX_SKILLS_CONTEXT = 20_000
    _LLM_TIMEOUT = 30

    _skills_context: Optional[str] = None
    _skills_context_lock = asyncio.Lock()

    # Semantic dispatch cache
    _dispatch_cache: dict[str, tuple[float, RoutingManifest]] = {}
    _CACHE_TTL = 300

    # -----------------------------------------------------------------------
    # PUBLIC API
    # -----------------------------------------------------------------------

    async def dispatch(self, goal: str, task_id: str = "sys") -> RoutingManifest:
        start = time.perf_counter()

        try:
            norm = self._normalize(goal)

            # -------------------------------------------------------------------
            # CACHE CHECK
            # -------------------------------------------------------------------
            cached = self._get_cached_dispatch(norm)
            if cached:
                engine.publish_mission_log(
                    "DISPATCHER",
                    "⚡ [CACHE-HIT]: Sử dụng cached dispatch.",
                    task_id,
                )
                return cached

            # -------------------------------------------------------------------
            # REFLEX MATCH
            # -------------------------------------------------------------------
            reflex_result = self._reflex_match(norm, task_id)
            if reflex_result:
                self._cache_dispatch(norm, reflex_result)
                return reflex_result

            # -------------------------------------------------------------------
            # LLM FALLBACK
            # -------------------------------------------------------------------
            engine.publish_mission_log(
                "DISPATCHER",
                "🧠 [LLM-FALLBACK]: Reflex không chắc chắn. Đang gọi LLM...",
                task_id,
            )

            result = await self._llm_dispatch(goal, task_id)
            self._cache_dispatch(norm, result)
            return result

        finally:
            latency = round((time.perf_counter() - start) * 1000, 2)

            engine.publish_mission_log(
                "DISPATCHER",
                f"📊 [LATENCY]: {latency} ms",
                task_id,
            )

    # -----------------------------------------------------------------------
    # NORMALIZATION
    # -----------------------------------------------------------------------

    @staticmethod
    def _normalize(text: str) -> str:
        text = _NOISE_RE.sub(" ", text)
        text = remove_accents(text)
        text = text.lower()
        text = _MULTI_SPACE_RE.sub(" ", text)
        return text.strip()

    # -----------------------------------------------------------------------
    # CACHE
    # -----------------------------------------------------------------------

    @classmethod
    def _get_cached_dispatch(cls, key: str) -> Optional[RoutingManifest]:
        item = cls._dispatch_cache.get(key)
        if not item:
            return None

        ts, data = item

        if time.time() - ts > cls._CACHE_TTL:
            cls._dispatch_cache.pop(key, None)
            return None

        return data

    @classmethod
    def _cache_dispatch(cls, key: str, value: RoutingManifest):
        cls._dispatch_cache[key] = (time.time(), value)

    # -----------------------------------------------------------------------
    # REFLEX MATCHER
    # -----------------------------------------------------------------------

    @staticmethod
    def _calculate_rule_score(
        norm: str,
        rule: TriggerRule,
        patterns: list[re.Pattern],
        negative_patterns: list[re.Pattern],
    ) -> tuple[int, list[str]]:
        for neg in negative_patterns:
            if neg.search(norm):
                return -1, []
        score = 0
        matched_keywords = []

        for keyword, pattern in zip(rule.keywords, patterns):
            if pattern.search(norm):
                matched_keywords.append(keyword)

                # Ưu tiên keyword dài hơn
                keyword_weight = max(1, len(keyword.split()))
                score += keyword_weight * 10

        # Priority bonus
        score += max(0, 100 - rule.priority)

        return score, matched_keywords

    @classmethod
    def _reflex_match(cls, norm: str, task_id: str) -> Optional[RoutingManifest]:
        candidates = []

        for rule, patterns, neg_patterns in _RULE_PATTERNS:
            score, matched_keywords = cls._calculate_rule_score(
                norm,
                rule,
                patterns,
                neg_patterns
            )

            if score > 0:
                candidates.append((score, rule, matched_keywords))

        if not candidates:
            return None

        # Sort theo score giảm dần
        candidates.sort(key=lambda x: x[0], reverse=True)

        best_score, best_rule, matched_keywords = candidates[0]

        confidence = min(0.99, best_score / 150)

        engine.publish_mission_log(
            "DISPATCHER",
            (
                f"⚡ [REFLEX]: skill={best_rule.skill} | "
                f"score={best_score} | "
                f"confidence={confidence:.2f} | "
                f"matched={matched_keywords}"
            ),
            task_id,
        )

        if confidence < 0.65:
            return None

        return RoutingManifest(
            trace_id=str(uuid.uuid4()),
            parent_trace_id=None,
            intent=best_rule.intent,
            action_type=best_rule.action_type,
            mode=best_rule.mode,
            skill=best_rule.skill,
            confidence=round(confidence, 2),
            reasoning=f"reflex_match: {matched_keywords}",
            requires_planner=False,
            requires_memory=False,
            requires_llm=False,
            risk="LOW",
            domain=best_rule.domain,
            complexity=0.1,
            telemetry={"source": "reflex", "matched": matched_keywords}
        )

    # -----------------------------------------------------------------------
    # LLM DISPATCH
    # -----------------------------------------------------------------------

    async def _llm_dispatch(self, goal: str, task_id: str) -> RoutingManifest:
        # LLM Dispatch has been upgraded to Native Tool Calling ReAct Loop in receptionist_core.py
        # Here we just return a manifest indicating LLM is required.
        return RoutingManifest(
            trace_id=str(uuid.uuid4()),
            parent_trace_id=None,
            intent="UNKNOWN",
            action_type=ActionType.QUERY,
            mode="deep",
            skill=None,
            confidence=0.0,
            reasoning="Requires ReAct Loop",
            requires_planner=False,
            requires_memory=False,
            requires_llm=True,
            risk="LOW",
            domain="GENERAL",
            complexity=0.8,
            telemetry={"source": "llm_delegated"}
        )

        # -------------------------------------------------------------------
        # FAILSAFE
        # -------------------------------------------------------------------
        engine.publish_mission_log(
            "DISPATCHER",
            "🛡️ [FAILSAFE]: Chuyển sang skill_self_healing.",
            task_id,
        )

        return RoutingManifest(
            trace_id=str(uuid.uuid4()),
            parent_trace_id=None,
            intent="EXECUTION",
            action_type=ActionType.EXECUTION,
            mode="deep",
            skill="skill_self_healing",
            confidence=0.25,
            reasoning="failsafe",
            requires_planner=False,
            requires_memory=False,
            requires_llm=False,
            risk="LOW",
            domain="SYSTEM",
            complexity=0.5,
            telemetry={"source": "failsafe"}
        )

    # -----------------------------------------------------------------------
    # SKILLS CONTEXT CACHE
    # -----------------------------------------------------------------------

    @classmethod
    async def _get_skills_context(cls) -> str:
        if cls._skills_context is not None:
            return cls._skills_context

        async with cls._skills_context_lock:
            if cls._skills_context is not None:
                return cls._skills_context

            for candidate in cls._SKILLS_MAP_CANDIDATES:
                if candidate.exists():
                    text = candidate.read_text(encoding="utf-8")
                    text = text[: cls._MAX_SKILLS_CONTEXT]

                    cls._skills_context = text

                    logger.info(
                        "[DISPATCHER] Cached MAP_SKILLS.md (%d chars)",
                        len(text),
                    )

                    return text

            logger.warning("[DISPATCHER] MAP_SKILLS.md not found")

            cls._skills_context = ""
            return ""

    # -----------------------------------------------------------------------
    # PROMPT
    # -----------------------------------------------------------------------

    @staticmethod
    def _build_prompt(goal: str, skills_context: str) -> str:
        return f"""
[JKAI ZENITH DISPATCH CORE]

OBJECTIVE:
Choose the best matching skill for the user request.

USER REQUEST:
{goal}

AVAILABLE SKILLS:
{skills_context}

STRICT RULES:
1. Return ONLY valid JSON.
2. Do not explain.
3. Schema:
{{
  "skill": "skill_name",
  "id": "skill_id",
  "mode": "fast|deep",
  "confidence": 0.0
}}

4. confidence must be between 0.0 and 1.0
5. Use mode='deep' for:
   - code analysis
   - infrastructure
   - debugging
   - orchestration
   - multi-step reasoning

EXAMPLES:

Input:
"Fix Docker GPU issue"

Output:
{{
  "skill": "skill_host_control",
  "id": "28",
  "mode": "deep",
  "confidence": 0.91
}}
"""

    # -----------------------------------------------------------------------
    # SAFE JSON PARSER
    # -----------------------------------------------------------------------

    @staticmethod
    def _parse_json(text: str) -> Optional[RoutingManifest]:
        text = text.strip()

        # Trường hợp text đã là JSON chuẩn
        try:
            parsed = json.loads(text)
            if isinstance(parsed, dict):
                return parsed
        except Exception:
            pass

        # Trích object đầu tiên an toàn hơn
        start = text.find("{")
        end = text.rfind("}")

        if start == -1 or end == -1:
            return None

        candidate = text[start:end + 1]

        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict):
                return parsed
        except Exception as exc:
            logger.warning("[DISPATCHER] JSON parse failed: %s", exc)

        return None


# ---------------------------------------------------------------------------
# 🚀 GLOBAL SINGLETON
# ---------------------------------------------------------------------------
dispatcher = Dispatcher()


# ---------------------------------------------------------------------------
# 🌌 Sovereign Property of Master LeeTrung.
# Developed by Antigravity AI.
# ---------------------------------------------------------------------------