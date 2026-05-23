import os
import re
import json
import asyncio
import logging
from pathlib import Path
from dataclasses import dataclass, field
from typing import Optional
from core.utils.engine import engine

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# 💎 [SKILL-TRIGGER-MAP] — Tầng 1: Phản xạ keyword thưa Master
#    priority: số càng nhỏ → ưu tiên càng cao khi nhiều rule cùng match.
#    Dùng word-boundary (\b) để tránh false-positive giữa các từ liên quan.
# ---------------------------------------------------------------------------
@dataclass(frozen=True)
class TriggerRule:
    id: str
    skill: str
    keywords: tuple[str, ...]
    priority: int = 50          # 0 = cao nhất, 100 = thấp nhất
    mode: str = "fast"


SKILL_TRIGGER_MAP: list[TriggerRule] = [
    TriggerRule("00-S", "GREETING",               ("chào", "chảo", "hi", "hello", "helo", "hey", "alo"), priority=10),
    TriggerRule("05",   "skill_self_healing",      ("chiến binh zenith", "sửa chữa hệ thống", "kiểm tra hệ thống"), priority=20),
    TriggerRule("26",   "skill_dongbotrithuc",     ("đồng bộ", "đồng hóa", "nhập tâm", "assimilate", "sync", "nạp tri thức", "nạp data"), priority=30),
    TriggerRule("32",   "skill_kiemtrasuckhoe",    ("sức khỏe", "health check", "trạng thái hệ thống"), priority=30),
    TriggerRule("30",   "skill_giam_sat_he_thong", ("giám sát", "monitor", "pulse", "tài nguyên", "cpu", "ram"), priority=30),
    TriggerRule("28",   "skill_host_control",      ("docker", "restart container", "khởi động lại", "vram", "gpu lock"), priority=20),
    TriggerRule("29",   "skill_quantrihethong",    ("quản trị", "thư mục", "file system", "folder", "directory", "phân quyền"), priority=40),
    TriggerRule("27",   "skill_sieutimkiem",       ("tìm kiếm", "tìm", "quét", "tin tức", "search"), priority=50),
    TriggerRule("03",   "skill_autonomous_researcher", ("nghiên cứu", "research", "tìm hiểu"), priority=60),
    TriggerRule("04",   "skill_code_audit_elite",  ("audit code", "kiểm tra code", "tối ưu code"), priority=30),
    TriggerRule("19",   "skill_strategic_recon",   ("browser", "duyệt web", "mở trang", "url"), priority=40),
    TriggerRule("18",   "skill_agentic_debate",    ("phản biện", "tranh luận", "debate", "hội đồng", "xung đột"), priority=40),
    TriggerRule("107",  "skill_council_of_minds",  ("hội đồng tư duy", "council of minds", "hợp nhất ý kiến"), priority=20),
    TriggerRule("108",  "skill_generate_image",    ("vẽ ảnh", "tạo ảnh", "generate image", "dall-e", "midjourney"), priority=20),
]

# Sắp xếp theo priority một lần tại startup thưa Master
_SORTED_RULES = sorted(SKILL_TRIGGER_MAP, key=lambda r: r.priority)

# Precompile regex patterns → tránh recompile mỗi lần dispatch
_RULE_PATTERNS: list[tuple[TriggerRule, re.Pattern]] = [
    (rule, re.compile(
        "|".join(
            # Keyword nhiều từ: khớp chuỗi ký tự chính xác
            # Keyword một từ:   thêm word-boundary để tránh partial match
            kw if " " in kw else rf"\b{re.escape(kw)}\b"
            for kw in rule.keywords
        ),
        re.IGNORECASE,
    ))
    for rule in _SORTED_RULES
]

_NOISE_RE = re.compile(r"\(.*?\)|\[.*?]")


class Dispatcher:
    """
    🏗️ [ZENITH-DISPATCHER] — Hệ thống Điều phối 3 tầng thưa Master.

    Tầng 1 (Reflex)   : Regex word-boundary + priority scoring — ~0 ms.
    Tầng 2 (LLM)      : Claude với skills_context được cache — chỉ gọi khi cần.
    Tầng 3 (Failsafe)  : Trả về skill_self_healing để không bao giờ crash.
    """

    _SKILLS_MAP_CANDIDATES = [
        Path.cwd() / "intelligence" / "MAP_SKILLS.md",
        Path("/intelligence/MAP_SKILLS.md"),
        Path(__file__).resolve().parents[2] / "intelligence" / "MAP_SKILLS.md" if len(Path(__file__).resolve().parents) > 2 else Path("/intelligence/MAP_SKILLS.md"),
    ]
    _MAX_SKILLS_CONTEXT = 20_000   # ký tự tối đa gửi vào LLM
    _LLM_TIMEOUT = 30              # giây

    # Cache skills_context giữa các lần gọi (load lười)
    _skills_context: Optional[str] = None
    _skills_context_lock = asyncio.Lock()

    # ---------------------------------------------------------------------------
    # Public API
    # ---------------------------------------------------------------------------

    async def dispatch(self, goal: str, task_id: str = "sys") -> dict:
        """🎯 Phân luồng nhiệm vụ thưa Master. Luôn trả về dict hợp lệ."""
        norm = self._normalize(goal)

        # — Tầng 1: Reflex —
        result = self._reflex_match(norm, task_id)
        if result:
            return result

        # — Tầng 2: LLM —
        engine.publish_mission_log(
            "DISPATCHER",
            "🧠 [FALLBACK]: Tầng 1 không khớp. Đang triệu hồi LLM thưa Master...",
            task_id,
        )
        return await self._llm_dispatch(goal, task_id)

    # ---------------------------------------------------------------------------
    # Tầng 1 — Reflex match
    # ---------------------------------------------------------------------------

    @staticmethod
    def _normalize(text: str) -> str:
        """Xóa noise (chú thích nguồn gốc) và chuẩn hóa thưa Master."""
        text = _NOISE_RE.sub("", text)
        return text.lower().strip()

    @staticmethod
    def _reflex_match(norm: str, task_id: str) -> Optional[dict]:
        """
        Duyệt qua các rule đã được sort theo priority.
        Rule đầu tiên match (priority cao nhất) thắng thưa Master.
        """
        for rule, pattern in _RULE_PATTERNS:
            if pattern.search(norm):
                engine.publish_mission_log(
                    "DISPATCHER",
                    f"⚡ [REFLEX]: Khớp `{rule.skill}` (id={rule.id}, priority={rule.priority}) thưa Master.",
                    task_id,
                )
                return {"skill": rule.skill, "id": rule.id, "mode": rule.mode}
        return None

    # ---------------------------------------------------------------------------
    # Tầng 2 — LLM dispatch
    # ---------------------------------------------------------------------------

    async def _llm_dispatch(self, goal: str, task_id: str) -> dict:
        try:
            context = await self._get_skills_context()
            prompt = self._build_prompt(goal, context)

            response = await engine.call_chat(
                messages=[{"role": "user", "content": prompt}],
                role="RECEPTIONIST",
                lock_timeout=self._LLM_TIMEOUT,
                json_mode=True
            )

            # [FIX]: engine.call_chat() co the tra ve dict — ep kieu str truoc khi parse
            if isinstance(response, dict):
                response = json.dumps(response, ensure_ascii=False)
            elif not isinstance(response, str):
                response = str(response) if response else ""

            parsed = self._parse_json(response)
            if parsed and "skill" in parsed and "id" in parsed:
                return parsed

            logger.warning("[DISPATCHER] LLM tra ve JSON khong hop le: %s", response[:200])

        except Exception as exc:
            engine.publish_mission_log("SYSTEM", f"❌ [DISPATCH-ERR]: {exc}", task_id)
            logger.exception("[DISPATCHER] Lỗi Tầng 2")

        # — Tầng 3: Failsafe —
        engine.publish_mission_log(
            "DISPATCHER",
            "🛡️ [FAILSAFE]: Chuyển sang skill_self_healing thưa Master.",
            task_id,
        )
        return {"skill": "skill_self_healing", "id": "05", "mode": "deep"}

    @classmethod
    async def _get_skills_context(cls) -> str:
        """Load và cache skills_context — chỉ đọc disk một lần thưa Master."""
        if cls._skills_context is not None:
            return cls._skills_context

        async with cls._skills_context_lock:
            # Double-check sau khi acquire lock
            if cls._skills_context is not None:
                return cls._skills_context

            for candidate in cls._SKILLS_MAP_CANDIDATES:
                if candidate.exists():
                    text = candidate.read_text(encoding="utf-8")[: cls._MAX_SKILLS_CONTEXT]
                    cls._skills_context = text
                    logger.info("[DISPATCHER] Đã cache skills_context (%d ký tự) từ %s", len(text), candidate)
                    return text

            logger.warning("[DISPATCHER] Không tìm thấy MAP_SKILLS.md — tiếp tục với context rỗng.")
            cls._skills_context = ""
            return ""

    @staticmethod
    def _build_prompt(goal: str, skills_context: str) -> str:
        return f"""[HỆ THỐNG ĐIỀU PHỐI JKAI ZENITH]

Nhiệm vụ: Chọn kỹ năng phù hợp nhất cho mục tiêu dưới đây.

MỤC TIÊU:
{goal}

DANH SÁCH KỸ NĂNG:
{skills_context}

QUY TẮC:
1. Chỉ trả về đúng một JSON object, không có thêm bất kỳ văn bản nào.
2. Schema bắt buộc: {{"skill": "<tên_kỹ_năng>", "id": "<số_id>", "mode": "fast|deep"}}
3. Dùng mode "deep" cho tác vụ kỹ thuật phức tạp hoặc khi không chắc chắn.

VÍ DỤ:
- "Tìm lỗi trong module X"  → {{"skill": "skill_code_audit_elite", "id": "04", "mode": "deep"}}
- "Mở trang anthropic.com"  → {{"skill": "skill_strategic_recon",  "id": "19", "mode": "fast"}}
"""

    @staticmethod
    def _parse_json(text: str) -> Optional[dict]:
        """Trích xuất JSON object đầu tiên từ chuỗi trả về thưa Master."""
        match = re.search(r"\{[^{}]*\}", text, re.DOTALL)
        if match:
            try:
                return json.loads(match.group())
            except json.JSONDecodeError as exc:
                logger.warning("[DISPATCHER] JSON parse lỗi: %s", exc)
        return None


# *Sovereign Property of Master LeeTrung. Developed by Antigravity AI. 🌌🏛️🔥🦾👑🔗*