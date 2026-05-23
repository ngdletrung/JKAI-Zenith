"""
╔══════════════════════════════════════════════════════════════════════════════╗
║        JKAI ZENITH — BỘ NÃO LẬP KẾ HOẠCH CHIẾN LƯỢC (Elite Edition v3)    ║
║   Lập trình Ứng dụng  •  Báo cáo & Thuyết minh  •  Nghiệp vụ Văn phòng   ║
╚══════════════════════════════════════════════════════════════════════════════╝
* Sovereign Property of Master LeeTrung. Developed by Antigravity AI. 🌌🏛️🔥
"""

import asyncio
import json
import logging
import os
import time
from typing import Any, Dict, List, Optional

import redis
from pydantic import BaseModel, Field
from enum import Enum

from core.qdrant_client import qdrant_client
from core.utils.embed import embed
from core.utils.engine import engine
from knowledge_manager import JKAIKnowledgeOrchestrator
from redis_client import redis_safe
from core.utils.hlc import hlc
from core.utils.reasoning_bank import reasoning_bank

logger = logging.getLogger("JKAI.Planner")


# ══════════════════════════════════════════════════════════════════════════════
#  SCHEMA — Bộ khung dữ liệu tuyệt đối (Pydantic v2)
# ══════════════════════════════════════════════════════════════════════════════

class HardwareTarget(str, Enum):
    """
    ALPHA = GPU : Reasoning sâu, viết code, phân tích ngữ nghĩa, sinh văn bản.
    BETA  = CPU : I/O bound — đọc/ghi file, web search, gọi API, convert format.
    """
    ALPHA = "ALPHA"
    BETA  = "BETA"


class PlanStep(BaseModel):
    id:               str             = Field(..., description="Unique step ID — e.g. 'step_01'")
    tool:             str             = Field(..., description="Exact skill ID from registry. NEVER invent.")
    args:             Dict[str, Any]  = Field(default_factory=dict, description="Tool arguments matching skill signature")
    description:      str             = Field(..., description="One-line plain-language summary")
    assigned_agent:   str             = Field(..., description="Agent Soul .md file, e.g. agent_executor_alpha.md")
    hardware_target:  HardwareTarget  = Field(..., description="ALPHA=GPU reasoning | BETA=CPU I/O")
    expert_mindset:   str             = Field(..., description="Elite execution instruction for the agent")
    verification:     str             = Field(..., description="Concrete, testable success criterion")
    parallel:         bool            = Field(False, description="True if independent of all other steps")
    depends_on:       List[str]       = Field(default_factory=list, description="IDs of prerequisite steps")
    fallback_tool:    Optional[str]   = Field(None, description="Backup skill if primary fails")


class Blueprint(BaseModel):
    thought:             str            = Field(..., description="MECE chain-of-thought before generating steps")
    steps:               List[PlanStep] = Field(..., description="Ordered, parallelised execution steps")
    rationale:           str            = Field(..., description="Strategic rationale for this approach")
    failure_speculation: str            = Field(..., description="Failure modes and pivot strategies")
    ambiguous:           bool           = Field(False, description="True if goal requires clarification")
    question:            Optional[str]  = Field(None,  description="Clarification question when ambiguous=True")
    complexity_score:    int            = Field(1, ge=1, le=10, description="Task complexity 1-10")
    estimated_duration:  Optional[str]  = Field(None,  description="Rough wall-clock estimate, e.g. '3-5 min'")


# ══════════════════════════════════════════════════════════════════════════════
#  FEW-SHOT LIBRARY — Thư viện mẫu chiến lược thực chiến
# ══════════════════════════════════════════════════════════════════════════════

_FEW_SHOT_EXAMPLES = """
[A1] Goal: "Xây dựng REST API quản lý nhân sự bằng FastAPI + PostgreSQL, có JWT auth"
thought: Cần scaffold → models → routes → tests → Docker. Models và routes viết song song.
steps:
  step_01 | scaffold_project | ALPHA | parallel:true
  ...
"""

# ══════════════════════════════════════════════════════════════════════════════
#  PLANNER — Kiến trúc sư Chiến lược Tối thượng
# ══════════════════════════════════════════════════════════════════════════════

class Planner:
    _MAX_RETRIES       = 3
    _CACHE_THRESHOLD   = 0.88
    _HISTORY_THRESHOLD = 5
    _HISTORY_TAIL      = 8
    _RECON_LIMIT       = 5
    _EMBED_MAX_CHARS   = 1000
    _STOP_SIGNAL_KEY   = "agent:stop_signal"

    def __init__(self) -> None:
        intel_path = self._resolve_intel_path()
        self.orchestrator = JKAIKnowledgeOrchestrator(intel_path)
        self._redis_host = os.getenv("REDIS_HOST", "redis-ai")
        self.__redis: Optional[redis.Redis] = None

        from critic import Critic
        from prompt_forge import prompt_forge as _forge
        self._critic = Critic()
        self._forge  = _forge

    def _get_redis(self) -> redis.Redis:
        if self.__redis is None:
            self.__redis = redis.Redis(host=self._redis_host, port=6379, db=0, decode_responses=True)
        return self.__redis

    @staticmethod
    def _resolve_intel_path() -> str:
        cwd = os.path.join(os.getcwd(), "intelligence")
        if os.path.exists(cwd): return cwd
        return os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "intelligence")

    def _log(self, tag: str, msg: str, task_id: str = "system") -> None:
        try:
            payload = json.dumps({"tag": tag, "msg": msg, "ts": time.time(), "task_id": task_id, "hlc": str(hlc.now())}, ensure_ascii=False)
            self._get_redis().publish("monitor:log_channel", payload)
        except: pass

    def _is_aborted(self) -> bool:
        try: return self._get_redis().get(self._STOP_SIGNAL_KEY) in ("true", "1")
        except: return False

    def _estimate_complexity(self, goal: str) -> str:
        words = len(goal.split())
        if words > 30: return "complex"
        if words < 10: return "simple"
        return "medium"

    async def _search_cache(self, goal: str) -> Optional[dict]:
        try:
            vector = embed(goal[: self._EMBED_MAX_CHARS])
            if not vector: return None
            results = await qdrant_client.search_similar(vector, limit=1, collection="jkai_blueprint_cache")
            if results and results[0].get("score", 0) > self._CACHE_THRESHOLD:
                return results[0].get("payload")
        except: pass
        return None

    async def _recon_skills(self, goal: str, skills_summary: str, task_id: str) -> str:
        recon_prompt = f"Yêu cầu: '{goal}'\nLiệt kê tối đa {self._RECON_LIMIT} skill ID phù hợp nhất từ:\n{skills_summary}\nTrả về JSON array."
        try:
            recon_res = await engine.call_chat([{"role": "user", "content": recon_prompt}], role="DATA_SCOUT", task_id=task_id, json_mode=True)
            skill_dna = ""
            if isinstance(recon_res, list):
                for s_id in recon_res:
                    logic = engine.get_intel_file(f"skills/{s_id}/logic.py") or engine.get_intel_file(f"skills/{s_id}.py")
                    if logic: skill_dna += f"\n--- [SKILL: {s_id}] ---\n{logic[:1500]}\n"
            return skill_dna
        except: return ""

    async def _compress_history(self, history: List[dict], task_id: str) -> List[dict]:
        summary_prompt = "Tóm tắt lịch sử:\n" + json.dumps(history[-15:], ensure_ascii=False)
        try:
            dna = await engine.call_chat([{"role": "user", "content": summary_prompt}], role="SUMMARIZER", task_id=task_id)
            return [{"role": "system", "content": f"🧬 [HISTORY DNA]: {dna}"}]
        except: return history[-self._HISTORY_TAIL:]

    async def _verify_integrity(self, plan: dict, task_id: str) -> List[str]:
        all_skills = self.orchestrator.get_all_skills_dict()
        ghosts = [s["tool"] for s in plan.get("steps", []) if s.get("tool") and s["tool"] not in all_skills]
        return ghosts

    def _build_system_prompt(self, manifesto: str, specialist_prompt: str, active_skills_dna: str, complexity: str, has_cache: bool, reasoning_samples: str = "") -> str:
        reasoning_block = f"\n<REASONING_MEMORIES>\n{reasoning_samples}\n</REASONING_MEMORIES>" if reasoning_samples else ""
        PROTOCOL = f"""
<IDENTITY>Kiến trúc sư Chiến lược JKAI Zenith.</IDENTITY>
<THINKING_PROTOCOL>Tư duy MECE. Hardware Routing: ALPHA (GPU) | BETA (CPU).</THINKING_PROTOCOL>
<ACTIVE_SKILLS_INSTRUCTIONS>
⚡ [SKILL-AS-SYSTEM-PROMPT]: Chỉ nạp nơ-ron liên quan thưa Master.
{active_skills_dna}
</ACTIVE_SKILLS_INSTRUCTIONS>
{reasoning_block}
<SELF_HEALING_PROTOCOL>
NẾU BẠN GẶP LỖI HOẶC THIẾU THÔNG TIN (hoặc có feedback báo lỗi), bạn có toàn quyền sử dụng các công cụ hệ thống (như shell, cmd, powershell, patch, write, replace) để tự động kiểm tra log, tìm nguyên nhân lỗi, và sinh các bước (PlanStep) sửa code khắc phục lỗi thay vì dừng lại. Bạn là thực thể TỰ CHỦ (AUTONOMOUS) - Hãy tự chẩn đoán và tự chữa lành (Self-Healing).
</SELF_HEALING_PROTOCOL>
<GOLDEN_RULES>Chỉ dùng tool ID hợp lệ. Parallel:true cho bước độc lập.</GOLDEN_RULES>
"""
        return "\n\n".join([specialist_prompt, manifesto, PROTOCOL])

    async def generate_plan(self, goal: str, context: dict, history: Optional[List[dict]] = None, task_id: str = "system", images: Optional[List[str]] = None) -> dict:
        complexity = self._estimate_complexity(goal)
        skills_summary = self.orchestrator.get_all_skills_summary()

        skill_dna_task = self._recon_skills(goal, skills_summary, task_id)
        cache_task = self._search_cache(goal)
        manifesto_task = asyncio.to_thread(engine.get_intel_file, "JKAI_ZENITH_CORP.md")
        reasoning_task = reasoning_bank.recall(goal)
        smart_retrieve_task = self.orchestrator.smart_retrieve(goal, task_id)

        skill_dna, cached_blueprint, manifesto, reasoning_samples, smart_intel = await asyncio.gather(
            skill_dna_task, cache_task, manifesto_task, reasoning_task, smart_retrieve_task
        )

        context.update(smart_intel)
        reasoning_str = "\n".join([f"- Goal: {r['goal']}\n  Thought: {r['thought']}" for r in reasoning_samples])

        specialist_prompt = await self._forge.forge_specialist_prompt(goal=goal, context=context, skills_summary=skills_summary, fast_mode=bool(cached_blueprint))
        system_prompt = self._build_system_prompt(manifesto or "", specialist_prompt, skill_dna or skills_summary, complexity, bool(cached_blueprint), reasoning_str)

        # 🛡️ [TYPE-SAFETY]: Đảm bảo history luôn là list để tránh lỗi "unhashable type: 'slice'"
        if history is not None and not isinstance(history, list):
            history = [history] if history else []

        messages = [{"role": "system", "content": system_prompt}]
        if history and len(history) > self._HISTORY_THRESHOLD:
            messages.extend(await self._compress_history(history, task_id))
        elif history: messages.extend(history)
        messages.append({"role": "user", "content": goal})

        for attempt in range(1, self._MAX_RETRIES + 1):
            if self._is_aborted(): return {"status": "aborted"}
            raw_plan = await engine.call_chat(messages=messages, role="PLANNER", schema=Blueprint.model_json_schema(), task_id=task_id, images=images)
            try:
                if isinstance(raw_plan, str): raw_plan = json.loads(raw_plan)
                blueprint = Blueprint.model_validate(raw_plan)
                if blueprint.ambiguous: return blueprint.model_dump()
                
                ghosts = await self._verify_integrity(blueprint.model_dump(), task_id)
                if ghosts:
                    messages.append({"role": "system", "content": f"Ghost tools: {ghosts}. Sửa lại thưa Master."})
                    continue
                
                review = await self._critic.review_plan(goal, blueprint.model_dump().get("steps"))
                if review.get("approved"):
                    asyncio.create_task(reasoning_bank.memorize(goal, blueprint.thought))
                    return blueprint.model_dump()
                messages.append({"role": "system", "content": f"Feedback: {review.get('feedback')}"})
            except Exception as e:
                messages.append({"role": "system", "content": f"Schema error: {e}"})
        
        return {"status": "failed"}