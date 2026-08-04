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
from core.utils.difficulty_classifier import classify, DifficultyLevel

from core.utils.engine import engine
from plugin_manager import plugin_manager

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
#  [UTILITY] — Vietnamese Accent Folding + Text Cleanup
# ---------------------------------------------------------------------------

def remove_accents(text: str) -> str:
    """Chuẩn hóa unicode + loại bỏ dấu tiếng Việt."""
    text = unicodedata.normalize("NFD", text)
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    return text.replace("đ", "d").replace("Đ", "D")


_NOISE_RE = re.compile(r"\(.*?\)|\[.*?]")
_MULTI_SPACE_RE = re.compile(r"\s+")


# ---------------------------------------------------------------------------
#  [SKILL-TRIGGER-MAP]
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
        intent="GREETING",
        action_type=ActionType.SOCIAL,
    ),

    TriggerRule(
        "01-S",
        "SEARCH_WEB_GLOBAL",
        (
            "tim kiem",
            "tìm kiếm",
            "search",
            "google",
            "tra cuu",
            "tra cứu",
            "tin tuc",
            "tin tức",
            "trending github",
            "github trending",
            "github",
            "top 5",
            "top 10",
            "news",
        ),
        priority=15,
        intent="EXECUTION",
        action_type=ActionType.EXECUTION,
        # [FIX-DISPATCH-001]: Exclude code-specific GitHub queries to prevent false routing.
        # e.g. "github actions", "github repo", "pull request", "clone repo" should NOT trigger web search.
        negative_patterns=(
            "github actions",
            "github repo",
            "pull request",
            "clone",
            "git clone",
            "git commit",
            "git push",
            "git pull",
            "merge request",
        ),
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
        "META-01",
        "skill_strategic_recon",
        (
            "bạn làm việc thế nào",
            "how do you work",
            "khả năng của bạn",
            "capabilities",
            "tự nghiên cứu chính mình",
            "research yourself",
            "học hỏi kiến thức",
            "learn more",
        ),
        priority=60,
        mode="deep",
        domain="CORE",
        intent="LEARNING"
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
            "thiên nhãn",
            "thien nhan",
            "truy cập",
            "truy cap",
            "xem link",
        ),
        priority=40,
    ),

    TriggerRule(
        "18",
        "HOI_DONG_CHUYEN_GIA",
        (
            "hội đồng chuyên gia",
            "hoi dong chuyen gia",
            "hội đồng chuyên gia ai",
            "hoi dong chuyen gia ai",
            "cognitive council",
            "multi expert consensus",
            "thảo luận đa model",
            "thao luan da model",
            "phản biện chéo",
            "phan bien cheo",
            "triệu hồi hội đồng",
            "trieu hoi hoi dong",
            "expert debate",
            "tranh luận chuyên gia",
            "tranh luan chuyen gia",
            "dùng skill hội đồng",
            "dung skill hoi dong",
        ),
        priority=90,
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
#  [COMPILED RULE ENGINE]
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
#  [DISPATCHER]
# ---------------------------------------------------------------------------
class Dispatcher:
    """
    ️ JKAI ZENITH DISPATCHER

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

    _MAX_SKILLS_CONTEXT = 160_000
    _LLM_TIMEOUT = 30

    _skills_context: Optional[str] = None
    _skills_context_lock = asyncio.Lock()

    # Semantic dispatch cache
    _dispatch_cache: dict[str, tuple[float, RoutingManifest]] = {}
    _CACHE_TTL = 300

    # -----------------------------------------------------------------------
    # PUBLIC API
    # -----------------------------------------------------------------------

    async def dispatch(self, goal: str, task_id: str = "sys", history: list = None) -> RoutingManifest:
        start = time.perf_counter()

        try:
            if "<ZENITH_SKILL_ACTIVATED>" not in goal:
                try:
                    from core.utils.ingress_skill_gate import try_semantic_skill_match
                    ssm = try_semantic_skill_match(goal, threshold=0.70)
                    if ssm and ssm.get("status") == "success":
                        goal = ssm.get("enriched_goal")
                        engine.publish_mission_log(
                            "DISPATCHER",
                            "[SSM-AUTO-ACTIVATE] Match found. Enriched goal.",
                            task_id,
                            stealth=True
                        )
                except Exception:
                    pass

            deck_manifest = self._skill_deck_reflex(goal, task_id)
            if deck_manifest:
                return deck_manifest

            norm = self._normalize(goal)

            # -------------------------------------------------------------------
            # [DIFFICULTY-GATE]: Classify request complexity before any dispatch
            # L0_REFLEX → instant conversational reply, zero tool overhead
            # -------------------------------------------------------------------
            difficulty = classify(goal)
            if difficulty.level == DifficultyLevel.L0_REFLEX:
                engine.publish_mission_log(
                    "DISPATCHER",
                    f"[L0-REFLEX] Direct reply path — {difficulty.reason}",
                    task_id,
                    stealth=True,
                )
                return RoutingManifest(
                    trace_id=str(uuid.uuid4()),
                    parent_trace_id=None,
                    intent="SOCIAL",
                    action_type=ActionType.SOCIAL,
                    mode="fast",
                    skill="GREETING",
                    confidence=0.97,
                    reasoning=f"L0_REFLEX: {difficulty.reason}",
                    requires_planner=False,
                    requires_memory=False,
                    requires_llm=True,
                    risk="LOW",
                    domain="SOCIAL",
                    complexity=0.0,
                    telemetry={"source": "difficulty_classifier", "level": "L0",
                               "prompt_variant": difficulty.hint_prompt_variant},
                )

            #  [Z-SOS]: Đảm bảo Plugin Registry luôn mới nhất
            if not plugin_manager.plugins:
                await plugin_manager.scan_plugins()

            # -------------------------------------------------------------------
            # CACHE CHECK
            # -------------------------------------------------------------------
            cached = self._get_cached_dispatch(norm)
            if cached:
                engine.publish_mission_log(
                    "DISPATCHER",
                    "[CACHE-HIT] Sử dụng cached dispatch.",
                    task_id,
                    stealth=True
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
                "[LLM-FALLBACK] Reflex không chắc chắn. Đang gọi LLM...",
                task_id,
            )

            result = await self._llm_dispatch(goal, task_id, history, norm)
            self._cache_dispatch(norm, result)
            return result

        finally:
            latency = round((time.perf_counter() - start) * 1000, 2)

            engine.publish_mission_log(
                "DISPATCHER",
                f"[LATENCY] {latency} ms",
                task_id,
                stealth=True
            )

    @classmethod
    def _skill_deck_reflex(cls, goal: str, task_id: str) -> Optional[RoutingManifest]:
        """Resolve MAP_SKILLS deck numbers (#7001) before generic reflex."""
        try:
            from core.utils.skill_deck_index import SkillDeckIndex

            deck = SkillDeckIndex.get()
            deck.ensure_loaded()
            entries = deck.resolve_all_in_text(goal)
            if not entries:
                return None

            primary = entries[0]
            if not primary.registry_id:
                return None

            run_signals = (
                "chay", "run", "kich hoat", "dung skill", "su dung skill",
                "goi skill", "thuc thi", "execute",
            )
            norm_goal = remove_accents(goal.lower())
            wants_run = any(s in norm_goal for s in run_signals)
            inspect_only = deck.is_inspect_intent(goal) and not wants_run

            engine.publish_mission_log(
                "DISPATCHER",
                f"[DECK-REFLEX] {primary.display_id} → `{primary.registry_id}`",
                task_id,
                stealth=True,
            )

            return RoutingManifest(
                trace_id=str(uuid.uuid4()),
                parent_trace_id=None,
                intent="INSPECT" if inspect_only else "EXECUTION",
                action_type=ActionType.EXECUTION,
                mode="fast" if wants_run or inspect_only else "deep",
                skill=primary.registry_id,
                confidence=0.92,
                reasoning=f"skill_deck:{primary.display_id}",
                requires_planner=not wants_run and not inspect_only,
                requires_memory=False,
                requires_llm=not wants_run and not inspect_only,
                risk="LOW",
                domain="SKILLS",
                complexity=0.2,
                telemetry={"source": "skill_deck", "deck_id": primary.deck_id},
            )
        except Exception as e:
            logger.debug("[SKILL-DECK-REFLEX] %s", e)
        return None

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

        if not matched_keywords:
            return 0, []

        # Priority bonus
        score += max(0, 100 - rule.priority)

        return score, matched_keywords

    @classmethod
    def _reflex_match(cls, norm: str, task_id: str) -> Optional[RoutingManifest]:
        #  [URL-REFLEX]: Phát hiện URL trực tiếp (Bypass LLM)
        url_pattern = re.compile(r'https?://[^\s/$.?#].[^\s]*', re.IGNORECASE)
        if url_pattern.search(norm):
             return RoutingManifest(
                trace_id=str(uuid.uuid4()),
                parent_trace_id=None,
                intent="EXECUTION",
                action_type=ActionType.EXECUTION,
                mode="fast",
                skill="SEARCH_WEB_GLOBAL",
                confidence=1.0,
                reasoning="Direct URL detected via regex reflex.",
                requires_planner=False,
                requires_memory=False,
                requires_llm=False,
                risk="LOW",
                domain="WEB",
                complexity=0.1,
                telemetry={"source": "url_reflex"}
            )

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
                f"[REFLEX] skill={best_rule.skill} | "
                f"score={best_score} | "
                f"confidence={confidence:.2f} | "
                f"matched={matched_keywords}"
            ),
            task_id,
        )

        if confidence < 0.30:
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

    async def _llm_dispatch(self, goal: str, task_id: str, history: list = None, norm: str = "") -> RoutingManifest:
        """
        [SOVEREIGN-LLM-DISPATCH]: Triệu tập trí tuệ nơ-ron để định tuyến khi Reflex thất bại.
        Bỏ qua trạng thái UNKNOWN hèn nhát, ép buộc tìm ra ý định thực thi thưa Master.
        """
        try:
            # skills_context = await self._get_skills_context() # Lược bỏ nạp nguyên file 160KB thưa Master
            history_text = ""
            if history:
                history_text = "\n".join([f"{m.get('role', 'user')}: {m.get('content', '')}" for m in history[-5:]])
            
            #  [COGNITIVE-INTENT-CORE]: Tìm kiếm chuyên gia phù hợp nhất từ Registry
            from core.utils.knowledge_manager import knowledge_orchestrator
            all_skills = await knowledge_orchestrator.get_all_skills_dict()
            
            # Tính toán điểm liên quan ngữ nghĩa (Semantic Relevance)
            semantic_candidates = []
            for s_id, s_info in all_skills.items():
                # Lấy toàn bộ text để so khớp: Triggers + Description + Name
                triggers = " ".join(s_info.get("triggers", []))
                desc = s_info.get("description", "")
                final_desc = s_info.get("final_desc_vn", "")
                search_space = f"{s_id} {triggers} {desc} {final_desc}".lower()
                
                # Điểm số dựa trên mật độ từ khóa và độ khớp ngữ nghĩa cơ bản
                score = 0
                goal_words = set(norm.split())
                for word in goal_words:
                    if len(word) > 2 and word in search_space:
                        score += 10
                
                if score > 0:
                    semantic_candidates.append((score, s_id, s_info))
            
            # Lấy top 5 chuyên gia tiềm năng nhất
            semantic_candidates.sort(key=lambda x: x[0], reverse=True)
            
            dossier_context = ""
            for score, s_id, s_info in semantic_candidates[:5]:
                dossier_context += f"\n--- EXPERT CANDIDATE: {s_id} (Relevance: {score}) ---\n"
                dossier_context += f"Description: {s_info.get('description', '')}\n"
                dossier_context += f"Intent: {s_info.get('final_desc_vn', '')}\n"
                dossier_context += f"Triggers: {', '.join(s_info.get('triggers', []))}\n"

            if not semantic_candidates:
                skills_context = "\n".join([f"- {s_id}: {s_info.get('description', '')[:100]}" for s_id, s_info in all_skills.items()])
            else:
                skills_context = "Vui lòng tập trung chọn 1 trong các EXPERT CANDIDATES ở trên thưa Master."

            prompt = self._build_prompt(goal, skills_context, history_text, dossier_context)
            
            # Sử dụng model nhanh để phân loại ý định
            response = await engine.call_chat(
                messages=[{"role": "user", "content": prompt}],
                role="PLANNER",
                task_id=task_id,
                json_mode=True,
                options={"temperature": 0.0}
            )
            
            data = response if isinstance(response, dict) else self._parse_json(str(response))
            
            if data and data.get("skill"):
                skill_id = data.get("skill")
                confidence = float(data.get("confidence", 0.8))
                mode = data.get("mode", "fast")
                reasoning = data.get("reasoning", "No reasoning provided.")
                
                engine.publish_mission_log(
                    "DISPATCHER",
                    f"[LLM-DECISION] Chốt kỹ năng `{skill_id}` (Conf: {confidence}). Lý do: {reasoning}",
                    task_id
                )
                
                return RoutingManifest(
                    trace_id=str(uuid.uuid4()),
                    parent_trace_id=None,
                    intent="EXECUTION",
                    action_type=ActionType.EXECUTION,
                    mode=mode,
                    skill=skill_id,
                    confidence=confidence,
                    reasoning=f"llm_dispatch_success: {skill_id}",
                    requires_planner=(mode == "deep"),
                    requires_memory=True,
                    requires_llm=True,
                    risk="LOW",
                    domain="GENERAL",
                    complexity=0.5,
                    telemetry={"source": "llm_brain", "model": "dispatcher"}
                )
        except Exception as e:
            logger.error("[DISPATCHER] LLM dispatch error: %s", e)

        # Fallback cuối cùng nếu cả LLM cũng lỗi
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
    def _build_prompt(goal: str, skills_context: str, history: str = "", dossier_context: str = "") -> str:
        return f"""
#  JKAI ZENITH: GIAO THỨC ĐỊNH TUYẾN CHỦ QUYỀN (SOVEREIGN DISPATCHER)

Bạn là Ban Điều Phối của JKAI Zenith. Nhiệm vụ của bạn là phân tích yêu cầu và định tuyến đến kỹ năng chính xác.

## ️ TƯ DUY TÁC CHIẾN:
1. **Tuyệt đối KHÔNG CHAT**: Không chào hỏi, không giải thích, không xin lỗi.
2. **Quyền hạn tối thượng**: Bạn có toàn quyền truy cập hệ thống qua các Skill. Đừng bao giờ nói 'Tôi không thể'.
3. **Phân tích hàm ý**: Dựa vào lịch sử để hiểu các từ thay thế (nó, cái đó).
{history}

##  NHIỆM VỤ:
1. **Thấu thị Ý định**: Phân tích xem Master thực sự muốn làm gì (tìm kiếm, code, quản trị, hay sáng tạo?).
2. **Chọn 01 kỹ năng DUY NHẤT**: Ưu tiên các **EXPERT CANDIDATES** vì chúng có mô tả chi tiết và độ liên quan cao. Nếu không thấy phù hợp, hãy quét toàn bộ **AVAILABLE SKILLS**.
3. **Lý luận (Reasoning)**: Giải thích rõ tại sao kỹ năng này là lựa chọn tối ưu nhất dựa trên các tính năng của nó.
4. **Bypass UNKNOWN**: Luôn tìm ra kỹ năng gần nhất. Không được phép từ chối nếu yêu cầu nằm trong khả năng của các Skill.

USER REQUEST:
{goal}

{f"### ️ TOP EXPERT CANDIDATES (HIGH RELEVANCE):{dossier_context}" if dossier_context else ""}

AVAILABLE SKILLS SUMMARY:
{skills_context}

##  OUTPUT FORMAT (STRICT JSON ONLY):
{{
  "skill": "skill_id_name",
  "mode": "fast|deep",
  "confidence": 0.0-1.0,
  "implicit_intent": "Giải mã ý định ẩn",
  "reasoning": "Tại sao chọn kỹ năng này?"
}}
"""

    # -----------------------------------------------------------------------
    # SAFE JSON PARSER
    # -----------------------------------------------------------------------

    @staticmethod
    def _parse_json(text: str) -> Optional[dict]:
        if not text: return None
        text = text.strip()

        # 1. Thuật toán tìm JSON Block cuối cùng (Ưu tiên cho Thinking Models)
        # Tìm các cặp ngoặc {} gần nhất ở cuối chuỗi
        try:
            # Loại bỏ Markdown blocks nếu có
            clean_text = re.sub(r"```json\s*|\s*```", "", text)
            
            # Tìm tất cả các JSON candidate
            matches = list(re.finditer(r"\{(?:[^{}]|(?R))*\}", clean_text))
            if matches:
                # Lấy match cuối cùng (thường là kết quả sau khi 'thinking')
                candidate = matches[-1].group()
                return json.loads(candidate)
        except Exception:
            pass

        # 2. Fallback: Regex đơn giản nếu đệ quy thất bại
        try:
            start = text.rfind("{")
            end = text.rfind("}")
            if start != -1 and end != -1 and end > start:
                candidate = text[start:end+1]
                return json.loads(candidate)
        except Exception:
            pass

        return None


# ---------------------------------------------------------------------------
#  GLOBAL SINGLETON
# ---------------------------------------------------------------------------
dispatcher = Dispatcher()


# ---------------------------------------------------------------------------
#  Sovereign Property of Master LeeTrung.
# Developed by Antigravity AI.
# ---------------------------------------------------------------------------