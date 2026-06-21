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
from pathlib import Path
from typing import Any, Dict, List, Optional, Set

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


_DEFAULT_AGENT_SOUL = "agent_executor_alpha.md"
_HARDWARE_AGENT_MAP = {
    HardwareTarget.ALPHA: "agent_executor_alpha.md",
    HardwareTarget.BETA: "agent_executor_beta.md",
}
_AGENT_ROLE_SOUL_HINTS = [
    (("security", "bảo mật", "bao mat"), "agent_security_architect.md"),
    (("research", "scholar", "nghiên cứu", "nghien cuu"), "agent_scholar.md"),
    (("strateg", "chiến lược", "chien luoc", "market"), "agent_strategist.md"),
    (("graphic", "design", "thiết kế", "thiet ke", "hình ảnh", "hinh anh"), "agent_master_graphic.md"),
    (("memory", "bộ nhớ", "bo nho"), "agent_memory_specialist.md"),
    (("critic", "phản biện", "phan bien", "audit"), "agent_critic.md"),
    (("plan", "lập kế hoạch", "lap ke hoach"), "agent_planner.md"),
    (("coordinator", "điều phối", "dieu phoi"), "agent_coordinator.md"),
    (("performance", "hiệu năng"), "agent_performance_engineer.md"),
    (("coordinator", "điều phối"), "agent_coordinator.md"),
]


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
    thought:              str            = Field("", description="MECE chain-of-thought before generating steps")
    optimization_review:  str            = Field("", description="Self-Critique BEFORE writing steps: Are there redundant steps? Can steps be batched or merged? Are there duplicate tools? Consolidate aggressively.")
    steps:                List[PlanStep] = Field(..., description="Ordered, parallelised execution steps")
    rationale:           str            = Field("", description="Strategic rationale for this approach")
    failure_speculation: str            = Field("", description="Failure modes and pivot strategies")
    ambiguous:           bool           = Field(False, description="True if goal requires clarification")
    question:            Optional[str]  = Field(None,  description="Clarification question when ambiguous=True")
    complexity_score:    int            = Field(1, ge=1, le=10, description="Task complexity 1-10")
    estimated_duration:  Optional[str]  = Field(None,  description="Rough wall-clock estimate, e.g. '3-5 min'")
    # 💰 [COST-ESTIMATOR]: Cho phép hệ thống cân nhắc ngân sách trước khi chạy
    estimated_tokens:     Optional[int]  = Field(None,  description="Estimated total LLM tokens for this plan")
    estimated_runtime_s:  Optional[int]  = Field(None,  description="Estimated wall-clock seconds to complete")
    estimated_api_cost:   Optional[str]  = Field(None,  description="Rough API cost estimate, e.g. '$0.05'")
    team_pattern:         str            = Field(
        "pipeline",
        description="Harness-style team pattern: pipeline|fan_out_fan_in|expert_pool|producer_reviewer|supervisor|hierarchical_delegation",
    )
    recommended_critic:   bool           = Field(
        False,
        description="True when producer_reviewer pattern — DEEP T5 CRITIC should run after plan",
    )


# ══════════════════════════════════════════════════════════════════════════════
#  FEW-SHOT LIBRARY — Thư viện mẫu chiến lược thực chiến
# ══════════════════════════════════════════════════════════════════════════════

_FEW_SHOT_EXAMPLES = """
[A1] Goal: "Xây dựng REST API quản lý nhân sự bằng FastAPI + PostgreSQL, có JWT auth"
thought: Scaffold → models ∥ routes → tests → Docker.
steps (each item is a PlanStep JSON object):
  {"id": "step_01", "tool": "scaffold_project", "args": {}, "description": "Scaffold FastAPI project",
   "assigned_agent": "agent_executor_alpha.md", "hardware_target": "ALPHA", "parallel": true,
   "expert_mindset": "Scaffold with JWT-ready layout.", "verification": "Project tree exists with main.py"}
  {"id": "step_02", "tool": "SEARCH_WEB_GLOBAL", "args": {"query": "FastAPI JWT best practices"},
   "description": "Research JWT patterns", "assigned_agent": "agent_executor_beta.md", "hardware_target": "BETA",
   "parallel": false, "expert_mindset": "Collect authoritative references only.", "verification": "Notes captured"}
Agent routing: ALPHA (GPU/reasoning) → agent_executor_alpha.md | BETA (I/O) → agent_executor_beta.md
"""

# ══════════════════════════════════════════════════════════════════════════════
#  PLANNER — Kiến trúc sư Chiến lược Tối thượng
# ══════════════════════════════════════════════════════════════════════════════

class Planner:
    _MAX_RETRIES       = 3
    _CACHE_THRESHOLD   = 0.88
    _HISTORY_THRESHOLD = 15
    _HISTORY_TAIL      = 30
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

    @staticmethod
    def list_agent_soul_files() -> List[str]:
        agents_dir = Path(Planner._resolve_intel_path()) / "agents"
        if not agents_dir.is_dir():
            return [_DEFAULT_AGENT_SOUL, _HARDWARE_AGENT_MAP[HardwareTarget.BETA]]
        names = sorted(
            p.name for p in agents_dir.iterdir()
            if p.is_file() and p.name.startswith("agent_") and p.suffix == ".md"
        )
        return names or [_DEFAULT_AGENT_SOUL, _HARDWARE_AGENT_MAP[HardwareTarget.BETA]]

    @staticmethod
    def soul_for_hardware(hardware: HardwareTarget) -> str:
        return _HARDWARE_AGENT_MAP.get(hardware, _DEFAULT_AGENT_SOUL)

    @classmethod
    def soul_for_agent_role(cls, agent_role: Optional[str], valid: Optional[Set[str]] = None) -> Optional[str]:
        if not agent_role:
            return None
        allowed = valid or set(cls.list_agent_soul_files())
        lower = agent_role.lower()
        for keywords, soul in _AGENT_ROLE_SOUL_HINTS:
            if soul in allowed and any(k in lower for k in keywords):
                return soul
        return None

    def _format_agent_registry(self, agent_role: Optional[str] = None) -> str:
        agents = self.list_agent_soul_files()
        lines = [
            "<AGENT_REGISTRY>",
            "AVAILABLE agent soul files (use exact names in assigned_agent):",
        ]
        lines.extend(f"  - {name}" for name in agents[:50])
        lines.append("Routing: ALPHA → agent_executor_alpha.md | BETA → agent_executor_beta.md")
        hint = self.soul_for_agent_role(agent_role, set(agents))
        if agent_role and hint:
            lines.append(f"Meta-planner role '{agent_role}' → prefer {hint} for ALPHA reasoning steps.")
        lines.append("</AGENT_REGISTRY>")
        return "\n".join(lines)

    def _inject_plan_schema_enums(self, schema: dict, tool_ids: List[str]) -> None:
        agents = self.list_agent_soul_files()
        try:
            props = schema["$defs"]["PlanStep"]["properties"]
            props["tool"]["enum"] = tool_ids
            props["assigned_agent"]["enum"] = agents
            props["hardware_target"]["enum"] = [HardwareTarget.ALPHA.value, HardwareTarget.BETA.value]
        except Exception as e:
            logger.debug(f"[DYNAMIC-SCHEMA] Failed to inject enums: {e}")

    def _verify_agent_souls(self, plan: dict) -> List[str]:
        valid = set(self.list_agent_soul_files())
        errors: List[str] = []
        for step in plan.get("steps", []):
            if not isinstance(step, dict):
                continue
            agent = step.get("assigned_agent")
            if not agent:
                errors.append("Missing assigned_agent field.")
            elif agent not in valid:
                errors.append(f"Ghost agent soul: {agent}")
        return errors

    def _normalize_blueprint_agents(self, blueprint: Blueprint, agent_role: Optional[str] = None) -> None:
        valid = set(self.list_agent_soul_files())
        role_hint = self.soul_for_agent_role(agent_role, valid)
        for step in blueprint.steps:
            if step.assigned_agent not in valid:
                step.assigned_agent = self.soul_for_hardware(step.hardware_target)
            if role_hint and step.hardware_target == HardwareTarget.ALPHA:
                if step.assigned_agent in (_DEFAULT_AGENT_SOUL, "agent_executor.md"):
                    step.assigned_agent = role_hint

    async def _attach_policies(self, blueprint_dict: dict, context: dict, task_id: str) -> dict:
        mode = context.get("mode", "deep")
        for step in blueprint_dict.get("steps", []):
            if isinstance(step, dict) and "policy" not in step:
                step["policy"] = {"task_id": task_id, "mode": mode}
        return blueprint_dict

    def _inject_prevention_steps(self, blueprint: Blueprint, pre_flight: list) -> Blueprint:
        if not pre_flight:
            return blueprint
        existing = {s.id for s in blueprint.steps}
        insert_at = 0
        for i, item in enumerate(pre_flight[:3]):
            if isinstance(item, dict):
                warn = item.get("warning") or item.get("message") or item.get("risk") or str(item)
            else:
                warn = str(item)
            warn = (warn or "").strip()
            if not warn:
                continue
            step_id = f"prevention_{i + 1:02d}"
            if step_id in existing:
                continue
            step = PlanStep(
                id=step_id,
                tool="SYSTEM_CORE_EXECUTOR",
                args={"instruction": f"Pre-flight: {warn[:500]}"},
                description=f"Prevention check: {warn[:180]}",
                assigned_agent=self.soul_for_hardware(HardwareTarget.BETA),
                hardware_target=HardwareTarget.BETA,
                expert_mindset="Address known risks before main steps.",
                verification="Pre-flight risks reviewed.",
            )
            blueprint.steps.insert(insert_at, step)
            insert_at += 1
            existing.add(step_id)
        return blueprint

    async def generate_plan_via_pipeline(
        self,
        goal: str,
        context: dict,
        history: Optional[List[dict]] = None,
        task_id: str = "system",
        images: Optional[List[str]] = None,
        domain: str = None,
        trace_id: str = "system",
        mode: str = "deep",
    ) -> dict:
        from planning_pipeline import (
            ReconStage,
            ContextStage,
            ForgeStage,
            DAGOptimizerStage,
            PolicyStage,
            PlanningPipeline,
        )

        pipeline = PlanningPipeline(
            stages=[
                ReconStage(),
                ContextStage(),
                ForgeStage(),
                DAGOptimizerStage(),
                PolicyStage(),
            ]
        )
        state = {
            "goal": goal,
            "task_id": task_id,
            "trace_id": trace_id,
            "planner_instance": self,
            "context": context,
            "mode": mode,
            "domain": domain,
            "history": history or [],
            "images": images,
        }
        try:
            plan_state = await pipeline.execute(state)
            final = plan_state.get("final_plan")
            if final and final.get("steps"):
                return final
            return final or {"status": "failed", "steps": []}
        except Exception as e:
            logger.error(f"[PLANNING-PIPELINE] {e}")
            return {"status": "failed", "error": str(e), "steps": []}

    def _log(self, tag: str, msg: str, task_id: str = "system") -> None:
        try:
            payload = json.dumps({"tag": tag, "msg": msg, "ts": time.time(), "task_id": task_id, "hlc": str(hlc.now())}, ensure_ascii=False)
            self._get_redis().publish("monitor:log_channel", payload)
        except Exception as e:
            logger.debug("[PLANNER-LOG] redis publish failed: %s", e)

    def _is_aborted(self) -> bool:
        try:
            return self._get_redis().get(self._STOP_SIGNAL_KEY) in ("true", "1")
        except Exception as e:
            logger.debug("[PLANNER] abort check failed: %s", e)
            return False

    def _estimate_complexity(self, goal: str, context: dict = None, images: list = None) -> dict:
        goal_lower = goal.lower()
        complexity_signals = {
            "complex": ["multi_file", "codebase", "report", "báo cáo", "kiến trúc", "architecture", "research", "nghiên cứu", "danh mục", "tổng hợp"],
            "extreme": ["toàn bộ", "hệ thống", "system", "erp", "microservice", "deploy", "production", "framework"]
        }
        
        score = 0
        for word in complexity_signals["complex"]:
            if word in goal_lower: score += 2
        for word in complexity_signals["extreme"]:
            if word in goal_lower: score += 4
            
        words = len(goal.split())
        score += min(words / 10, 5)
        
        # --- Context Signals ---
        if images: score += 2
        if context:
            if context.get("files"): score += 3
            if context.get("history"): score += 2
        
        if score >= 8:
            return {"level": "extreme", "budget": 15}
        elif score >= 4:
            return {"level": "complex", "budget": 8}
        elif score >= 2:
            return {"level": "medium", "budget": 5}
        else:
            return {"level": "simple", "budget": 3}

    async def _search_cache(self, goal: str) -> Optional[dict]:
        try:
            vector = await embed.get_embedding_async(goal[: self._EMBED_MAX_CHARS])
            if not vector: return None
            results = await qdrant_client.search_similar(vector, limit=1, collection="jkai_blueprint_cache")
            if results and results[0].get("score", 0) > self._CACHE_THRESHOLD:
                return results[0].get("payload")
        except Exception as e:
            logger.debug("[PLANNER-CACHE] search failed: %s", e)
        return None

    async def _recon_skills(self, goal: str, skills_summary: str, task_id: str, domain: str = None) -> tuple[str, list[str]]:
        """
        🚀 [HYBRID-RECON v3.5]: Kết hợp Vector Search + Keyword Matching + Domain Filtering + Top-K.
        Sử dụng registry_Map_skills.json (Manifest) thay vì load source code logic.py
        để giảm tối đa context bloat cho LLM. Trả về (Skill DNA String, Top K Skill IDs).
        """
        all_skills = self.orchestrator.get_all_skills_dict()
        
        # Filter skills by domain if specified
        if domain:
            filtered_skills = {k: v for k, v in all_skills.items() if v.get("domain", "GENERAL").upper() == domain.upper()}
            # Fallback to all skills if the domain is empty (e.g. unknown domain)
            if filtered_skills:
                all_skills = filtered_skills
                
        skill_dna = ""
        found_ids = set()

        # 1. TIER 1: Keyword Matching cơ bản (BM25-lite)
        import re
        keywords = set(re.findall(r'\w+', goal.lower()))
        scores = {}
        for s_id, s_data in all_skills.items():
            text = f"{s_data.get('name_vn', '')} {s_data.get('description', '')}".lower()
            text_words = set(re.findall(r'\w+', text))
            match_count = len(keywords.intersection(text_words))
            if match_count > 0:
                scores[s_id] = match_count
        
        bm25_top = sorted(scores.items(), key=lambda x: x[1], reverse=True)[:3]
        for s_id, _ in bm25_top:
            found_ids.add(s_id)

        # 2. TIER 2: Semantic Vector Search
        try:
            goal_vector = await embed.get_embedding_async(goal[:self._EMBED_MAX_CHARS])
            if goal_vector:
                results = await qdrant_client.search_similar(
                    goal_vector,
                    limit=self._RECON_LIMIT,
                    collection="jkai_skill_registry"
                )
                if results:
                    for hit in results:
                        s_id = hit.get("payload", {}).get("skill_id") or hit.get("id", "")
                        if s_id and s_id in all_skills:
                            found_ids.add(s_id)
        except Exception as e:
            logger.debug(f"[VECTOR-RECON]: Qdrant miss ({e}), falling back to summary.")
            
        # [TOP-K INJECTION]: Đảm bảo các tool sinh tồn cốt lõi luôn có mặt (Universal Core Tools)
        UNIVERSAL_CORE_TOOLS = ["SEARCH_WEB_GLOBAL", "SYSTEM_CORE_EXECUTOR", "SKILL_ZENITH_OFFICE_MASTER"]
        core_ids = set()
        for t in UNIVERSAL_CORE_TOOLS:
            if t in self.orchestrator.get_all_skills_dict():
                core_ids.add(t)
                
        # Top-K (Mặc định 8)
        top_k_ids = list(found_ids)[:8]
        
        # [FALLBACK-K]: Lấy ngẫu nhiên vài skill trong domain để tránh kẹt nếu Vector Search trượt
        import random
        remaining_domain_skills = list(set(all_skills.keys()) - set(top_k_ids) - core_ids)
        fallback_k_count = 4
        fallback_k_ids = random.sample(remaining_domain_skills, min(fallback_k_count, len(remaining_domain_skills)))
        
        # Tổng hợp danh sách cuối cùng (~15 skills)
        final_skill_ids = list(set(top_k_ids + fallback_k_ids + list(core_ids)))
            
        # 3. BUILD RICH MANIFEST DNA — trích xuất toàn bộ metadata để Planner hiểu sâu
        DNA_TOKEN_BUDGET = 2500  # Kí tự tối đa cho skill_dna tránh phình context
        for s_id in final_skill_ids:
            if len(skill_dna) >= DNA_TOKEN_BUDGET: break
            s_data = all_skills[s_id]
            
            # --- Các trường cơ bản ---
            desc = s_data.get("description") or s_data.get("semantic_guidance", "No description.")
            schema_info = s_data.get("schema", {}).get("parameters", {})
            required_args = schema_info.get("required", [])
            category = s_data.get("domain", s_data.get("category", ""))
            
            # --- Các trường Affinity & Planning ---
            batch_capable   = s_data.get("batch_capable", None)
            workflow_pos    = s_data.get("workflow_position", None)
            commonly_after  = s_data.get("commonly_after", [])
            commonly_before = s_data.get("commonly_before", [])
            planning_hints  = s_data.get("planning_hints", [])
            typical_wf      = s_data.get("typical_workflow", [])
            cost_level      = s_data.get("cost_level", None)
            input_types     = s_data.get("input_type", [])
            output_types    = s_data.get("output_type", [])
            
            # --- Xây dựng DNA block ---
            dna_lines = [f"\n--- [SKILL: {s_id}] ---"]
            dna_lines.append(f"Purpose: {desc}")
            if category:       dna_lines.append(f"Category: {category}")
            if batch_capable is not None: dna_lines.append(f"Batch Capable: {batch_capable}")
            if cost_level:     dna_lines.append(f"Cost Level: {cost_level}")
            if workflow_pos:   dna_lines.append(f"Workflow Position: {workflow_pos}")
            if commonly_after: dna_lines.append(f"Commonly After: {commonly_after}")
            if commonly_before:dna_lines.append(f"Commonly Before: {commonly_before}")
            if input_types:    dna_lines.append(f"Accepts Input: {input_types}")
            if output_types:   dna_lines.append(f"Produces Output: {output_types}")
            if planning_hints: dna_lines.append(f"Planning Hints: {planning_hints}")
            if typical_wf:     dna_lines.append(f"Typical Workflow: {typical_wf}")
            
            dna_lines.append(f"Required Args: {', '.join(required_args) if required_args else 'None'}")
            skill_dna += "\n".join(dna_lines) + "\n"
            
        if not skill_dna.strip():
            skill_dna = "[SKILL DNA]: Fallback to general skills based on summary."
            
        return skill_dna, final_skill_ids

    async def _prepare_neural_context(self, goal: str, task_id: str, complexity: str = "medium") -> dict:
        manifesto = await asyncio.to_thread(engine.get_intel_file, "JKAI_ZENITH_CORP.md")
        complexity_data = self._estimate_complexity(goal)
        return {
            "manifesto": manifesto or "",
            "complexity": complexity,
            "level": complexity_data["level"],
            "budget": complexity_data["budget"],
        }

    async def _compress_history(self, history: List[dict], task_id: str) -> List[dict]:
        summary_prompt = "Tóm tắt lịch sử:\n" + json.dumps(history[-15:], ensure_ascii=False)
        try:
            dna = await engine.call_chat([{"role": "user", "content": summary_prompt}], role="SUMMARIZER", task_id=task_id)
            return [{"role": "system", "content": f"🧬 [HISTORY DNA]: {dna}"}]
        except Exception: return history[-self._HISTORY_TAIL:]

    async def _verify_integrity(self, plan: dict, task_id: str) -> List[str]:
        all_skills = self.orchestrator.get_all_skills_dict()
        errors = []
        steps = plan.get("steps", [])
        
        # 1. Signature & Ghost Tool Validation
        for step in steps:
            tool = step.get("tool")
            if not tool:
                errors.append("Missing tool field.")
                continue
            if tool not in all_skills:
                errors.append(f"Ghost tool detected: {tool}")
                continue
                
            schema = all_skills[tool].get("schema", {}).get("parameters", {})
            required = schema.get("required", [])
            args = step.get("args", {})
            missing = [r for r in required if r not in args]
            if missing:
                errors.append(f"Tool '{tool}' missing required args: {missing}")

        # 2. DAG Cycle Detection (DFS)
        graph = {s["id"]: set(s.get("depends_on", [])) for s in steps if "id" in s}
        visited = set()
        path = set()
        
        def has_cycle(node):
            if node in path: return True
            if node in visited: return False
            path.add(node)
            for neighbor in graph.get(node, []):
                if has_cycle(neighbor): return True
            path.remove(node)
            visited.add(node)
            return False
            
        for node in graph:
            if has_cycle(node):
                errors.append("DAG Cycle detected in depends_on fields.")
                break
                
        # 3. Tool Consolidation Validator
        tool_groups: Dict[str, list] = {}
        for step in steps:
            if isinstance(step, dict):
                tool = step.get("tool", "")
                if tool:
                    tool_groups.setdefault(tool, []).append(step)
        for tool, group in tool_groups.items():
            independent = [s for s in group if not s.get("depends_on")]
            if len(independent) > 2:
                errors.append(f"[TOOL CONSOLIDATION]: Tool '{tool}' used {len(independent)} times independently. These steps MUST be merged into 1 batched step.")

        errors.extend(self._verify_agent_souls(plan))
        return errors

    def _build_system_prompt(self, manifesto: str, specialist_prompt: str, active_skills_dna: str, complexity: str = "medium", step_budget: int = 5, has_cache: bool = False, reasoning_samples: str = "") -> str:
        reasoning_block = f"\n<REASONING_MEMORIES>\n{reasoning_samples}\n</REASONING_MEMORIES>" if reasoning_samples else ""
        
        # Read the external physical memory task board (task.md)
        task_board_content = ""
        # 🌍 [PORTABLE-PATH]: Dùng biến môi trường thay vì hardcode Windows path
        task_md_path = os.getenv("TASK_BOARD_PATH", "/workspace/task.md")
        if os.path.exists(task_md_path):
            try:
                with open(task_md_path, "r", encoding="utf-8") as f:
                    task_board_content = f.read().strip()
            except Exception:
                pass

        rolling_context_block = ""
        if task_board_content:
            rolling_context_block = f"""
<ROLLING_TASK_BOARD_STATE>
Nội dung bảng công việc hiện tại (task.md):
```markdown
{task_board_content}
```
NGUYÊN TẮC LẬP KẾ HOẠCH BẮT BUỘC (KIẾN TRÚC TỔNG QUÁT):
- Dựa trên các bước đã hoàn thành ([x]) để tránh làm lại.
- Bắt buộc tuân thủ 5 Đạo luật Lập kế hoạch (EXECUTION GRAPH, BATCH-FIRST, HIERARCHICAL, COST AWARE, PLAN MINIMIZATION) được định nghĩa ở phần GOLDEN_RULES.
</ROLLING_TASK_BOARD_STATE>
"""
        else:
            rolling_context_block = """
<ROLLING_TASK_BOARD_STATE>
Chưa có bảng công việc. Sinh kế hoạch theo nguyên tắc:
- Bắt buộc tuân thủ 5 Đạo luật Lập kế hoạch (EXECUTION GRAPH, BATCH-FIRST, HIERARCHICAL, COST AWARE, PLAN MINIMIZATION) được định nghĩa ở phần GOLDEN_RULES.
</ROLLING_TASK_BOARD_STATE>
"""

        PROTOCOL = f"""
<IDENTITY>Kiến trúc sư Chiến lược JKAI Zenith.</IDENTITY>
<THINKING_PROTOCOL>Tư duy MECE. Hardware Routing: ALPHA (GPU) | BETA (CPU).</THINKING_PROTOCOL>
<PLANNING_BUDGET>
Complexity Level: {complexity.upper()}
Recommended Step Budget: {step_budget}
Do NOT exceed this budget unless there is a hard technical dependency.
If you find yourself exceeding it, revisit optimization_review and consolidate.
</PLANNING_BUDGET>
<ACTIVE_SKILLS_INSTRUCTIONS>
⚡ [SKILL-AS-SYSTEM-PROMPT]: Chỉ nạp nơ-ron liên quan thưa Master.
{active_skills_dna}
</ACTIVE_SKILLS_INSTRUCTIONS>
{reasoning_block}
{rolling_context_block}
<METHODOLOGY_LAYER>
[IRON LAW 1: SYSTEMATIC DEBUGGING]
- NO FIXES WITHOUT ROOT CAUSE INVESTIGATION FIRST.
- Khi gặp lỗi, không đoán bừa (guess-and-check). Trích xuất error log -> Phân tích pattern -> Đặt giả thuyết -> Fix.
- Nếu fix hỏng 3 lần liên tiếp: STOP và chất vấn lại Kiến trúc, không được thử bừa thêm.

[IRON LAW 2: VERIFICATION BEFORE COMPLETION]
- NO COMPLETION CLAIMS WITHOUT FRESH VERIFICATION EVIDENCE.
- Không bao giờ được phép thông báo "Đã sửa xong", "Hoàn tất" nếu chưa chạy lệnh kiểm tra (pytest, curl, build...) và có bằng chứng terminal (exit 0, tests pass).

[IRON LAW 3: WRITING PLANS & TDD]
- Cấm sử dụng placeholder (TODO, TBD, implement later) trong các bước kế hoạch. Phải có đường dẫn file chính xác và mã nguồn cụ thể.
- Nhiệm vụ lập trình phải tuân theo luồng: Viết Test Fail (RED) -> Viết Code Pass (GREEN) -> Refactor.

[IRON LAW 4: SUBAGENT-DRIVEN DEVELOPMENT]
- Đối với tính năng phức tạp, thay vì ôm đồm thực thi trong 1 luồng, hãy lập kế hoạch chia nhỏ cho các Subagent chạy song song (sử dụng HardwareTarget ALPHA).

[IRON LAW 5: ANTI-HALLUCINATION FOR STEPS]
- CẤM TUYỆT ĐỐI việc sinh danh sách chuỗi (Array of Strings) cho trường `steps`.
- Ví dụ SAI: `["Bước 1: Làm A", "Bước 2: Làm B"]` -> BỊ TỪ CHỐI (CRASH).
- Ví dụ ĐÚNG: `[{{"id": "step_1", "tool": "tool_name", "args": {{...}}}}]`.
</METHODOLOGY_LAYER>
<SELF_HEALING_PROTOCOL>
NẾU BẠN GẶP LỖI HOẶC THIẾU THÔNG TIN (hoặc có feedback báo lỗi), bạn có toàn quyền sử dụng các công cụ hệ thống (như shell, cmd, powershell, patch, write, replace) để tự động kiểm tra log, tìm nguyên nhân lỗi, và sinh các bước (PlanStep) sửa code khắc phục lỗi thay vì dừng lại. Bạn là thực thể TỰ CHỦ (AUTONOMOUS) - Hãy tự chẩn đoán và tự chữa lành (Self-Healing).
</SELF_HEALING_PROTOCOL>
<DYNAMIC_STRATEGY_ROUTER>
Vì bạn là Trí tuệ Trung tâm (AI OS) của JKAI, hãy tự động nhận diện bản chất Task và áp dụng chiến lược phù hợp:
- [HỆ_THỐNG & LẬP_TRÌNH]: Tuân thủ IRON LAW 1 & 3. Ưu tiên Trinh sát -> Viết Test -> Sửa chữa -> Kiểm thử.
- [BÁO_CÁO & TÀI_LIỆU_DÀI]: Áp dụng chiến lược Chunk-and-Append. Lập dàn ý -> Viết phần 1 -> Ghi nối -> Viết phần 2.
- [NGHIÊN_CỨU & TÌM_KIẾM]: Áp dụng chiến lược Map-Reduce.
</DYNAMIC_STRATEGY_ROUTER>
<GOLDEN_RULES>
[EXECUTION GRAPH LAW]
- PlanStep đại diện cho một Tool Invocation hoặc một Milestone kỹ thuật.
- KHÔNG đại diện cho: một dòng dữ liệu, một record, một thiết bị, một sản phẩm, hay một mục trong danh sách.
- Nếu Tool có khả năng xử lý tập dữ liệu: Truyền toàn bộ tập dữ liệu vào args. KHÔNG tạo thêm PlanStep.

[BATCH-FIRST LAW]
- Trước khi tạo bước mới, tự hỏi: "Công cụ hiện tại có thể xử lý nhiều phần tử cùng lúc không?"
- Nếu CÓ: Batch (Gom nhóm dữ liệu truyền vào 1 bước). Nếu KHÔNG: mới tạo thêm PlanStep.

[HIERARCHICAL PLANNING LAW]
- Planner chỉ tạo: Strategic Milestones, Tool Invocations, Dependency Graph.
- Executor mới là thực thể xử lý: vòng lặp, chunking, batching, retry, pagination, phân chia dữ liệu.
- Tuyệt đối không lập kế hoạch ở mức quá chi tiết (Ví dụ: Không sinh 300 bước cho 300 thiết bị. Chỉ sinh 1 bước "analyze_catalog" chứa 300 items).

[COST AWARE LAW]
- Mỗi PlanStep đều tiêu tốn token, VRAM, CPU, và latency.
- Ưu tiên: Ít bước hơn, Ít token hơn, Ít agent hơn - miễn là đạt mục tiêu. Planner tự tránh sinh 18 bước khi 4 bước là đủ.

[PLAN MINIMIZATION PRINCIPLE]
- Sinh số lượng PlanStep ÍT NHẤT CÓ THỂ nhưng vẫn đảm bảo hoàn thành nhiệm vụ.
- Ưu tiên Batching, Chunk Processing, Map-Reduce, Parallel Execution, Tool Reuse trước khi tạo PlanStep mới.
- Mỗi bước PHẢI có 'tool' hợp lệ. Sử dụng parallel=true cho các bước độc lập.

[AGENT ASSIGNMENT LAW]
- Mỗi PlanStep BẮT BUỘC có assigned_agent (file .md từ AGENT_REGISTRY) và hardware_target (ALPHA|BETA).
- ALPHA (suy luận/code) → agent_executor_alpha.md | BETA (I/O, search, file) → agent_executor_beta.md.

[TOOL CONSOLIDATION LAW]
- Nếu 2+ PlanStep dùng cùng tool, không có dependency, và có thể xử lý chung: BẮT BUỘC gộp thành 1 bước.
- SAI: step_01 analyze(file_A), step_02 analyze(file_B) | ĐÚNG: step_01 analyze(files=[A,B])
</GOLDEN_RULES>
"""
        return "\n\n".join([specialist_prompt, manifesto, PROTOCOL])

    async def generate_plan(self, goal: str, context: dict, history: Optional[List[dict]] = None, task_id: str = "system", images: Optional[List[str]] = None, domain: str = None) -> dict:
        context = dict(context or {})
        trace_id = context.get("trace_id", "system")

        try:
            from core.utils.skill_deck_index import SkillDeckIndex
            enriched_goal, deck_entries = SkillDeckIndex.get().enrich_goal(goal)
            if deck_entries:
                goal = enriched_goal
                context["skill_deck_resolved"] = [
                    {"deck": e.display_id, "registry_id": e.registry_id, "title": e.title}
                    for e in deck_entries
                ]
        except Exception as e:
            logger.debug(f"[SKILL-DECK] planner enrich skipped: {e}")

        try:
            from core.utils.skill_references import enrich_goal_with_skill_references

            ref_ids = context.get("resolved_skill_ids") or []
            goal, loaded_refs = enrich_goal_with_skill_references(goal, ref_ids)
            if loaded_refs:
                context["skill_references_loaded"] = loaded_refs
        except Exception as ref_err:
            logger.debug("[SKILL-REFERENCES] planner: %s", ref_err)

        if context.get("use_planning_pipeline"):
            return await self.generate_plan_via_pipeline(
                goal, context, history, task_id, images, domain, trace_id, context.get("mode", "deep")
            )

        if domain is None or not context.get("agent_role"):
            try:
                from meta_planner import MetaPlanner
                routing = await MetaPlanner().route_task(goal, context, task_id)
                domain = domain or routing.get("domain")
                context.setdefault("agent_role", routing.get("agent_role"))
                context.setdefault("domain", domain)
            except Exception as e:
                logger.debug(f"[META-PLANNER] skipped: {e}")

        agent_role = context.get("agent_role")

        complexity_data = self._estimate_complexity(goal, context=context, images=images)
        complexity_level = complexity_data["level"]
        step_budget = complexity_data["budget"]
        try:
            from core.utils.team_patterns import infer_team_pattern, pattern_prompt_block

            team_pat = infer_team_pattern(goal)
            context["team_pattern"] = team_pat.id
        except Exception as tp_err:
            logger.debug("[TEAM-PATTERN] skipped: %s", tp_err)
            team_pat = None
        skills_summary = self.orchestrator.get_all_skills_summary()
        
        # Filter available skills for the prompt if domain is provided
        if domain:
            all_valid_skill_ids = sorted([k for k, v in self.orchestrator.get_all_skills_dict().items() if v.get("domain", "GENERAL").upper() == domain.upper()])
            if not all_valid_skill_ids:
                all_valid_skill_ids = sorted(self.orchestrator.get_all_skills_dict().keys())
        else:
            all_valid_skill_ids = sorted(self.orchestrator.get_all_skills_dict().keys())

        # 🧠 [KNOWLEDGE-FUSION]: Chạy 4 tác vụ song song, tiết kiệm tối đa thời gian
        skill_dna_task = self._recon_skills(goal, skills_summary, task_id, domain)
        cache_task = self._search_cache(goal)
        manifesto_task = asyncio.to_thread(engine.get_intel_file, "JKAI_ZENITH_CORP.md")
        reasoning_task = reasoning_bank.recall(goal)
        smart_retrieve_task = self.orchestrator.smart_retrieve(goal, task_id)

        skill_dna_tuple, cached_blueprint, manifesto, reasoning_samples, smart_intel = await asyncio.gather(
            skill_dna_task, cache_task, manifesto_task, reasoning_task, smart_retrieve_task
        )
        skill_dna, top_k_ids = skill_dna_tuple
        
        all_valid_skill_ids = top_k_ids if top_k_ids else ["SEARCH_WEB_GLOBAL", "SYSTEM_CORE_EXECUTOR"]

        context.update(smart_intel)
        reasoning_str = "\n".join([f"- Goal: {r['goal']}\n  Thought: {r['thought']}" for r in reasoning_samples])

        specialist_prompt = await self._forge.forge_specialist_prompt(goal=goal, context=context, skills_summary=skills_summary, fast_mode=bool(cached_blueprint))
        # 🔒 [GHOST-TOOL-SHIELD]: Nhúng danh sách ID hợp lệ trực tiếp vào system_prompt để Pydantic/LLM không bao giờ bịa tool
        valid_ids_block = "AVAILABLE SKILL IDs (ONLY use these exact IDs in 'tool' field):\n" + "\n".join(f"  - {sid}" for sid in all_valid_skill_ids[:80])
        system_prompt = self._build_system_prompt(manifesto or "", specialist_prompt, skill_dna or skills_summary, complexity_level, step_budget, bool(cached_blueprint), reasoning_str)
        team_pattern_block = ""
        try:
            from core.utils.team_patterns import pattern_prompt_block

            team_pattern_block = "\n\n" + pattern_prompt_block(team_pat, goal)
        except Exception:
            pass
        system_prompt = (
            system_prompt
            + team_pattern_block
            + f"\n\n<SKILL_REGISTRY>\n{valid_ids_block}\n</SKILL_REGISTRY>"
            + f"\n\n{self._format_agent_registry(agent_role)}"
            + f"\n\n<FEW_SHOT>\n{_FEW_SHOT_EXAMPLES}\n</FEW_SHOT>"
        )

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

            if attempt == 1:
                active_role = "MINI_PLANNER" if complexity_level == "simple" else "PLANNER"
            else:
                active_role = "RESERVE_AGENT"
            
            schema = Blueprint.model_json_schema()
            self._inject_plan_schema_enums(schema, all_valid_skill_ids)
                
            raw_plan = await engine.call_chat(messages=messages, role=active_role, schema=schema, task_id=task_id, images=images)
            try:
                if isinstance(raw_plan, str): raw_plan = json.loads(raw_plan)
                blueprint = Blueprint.model_validate(raw_plan)
                if blueprint.ambiguous: return blueprint.model_dump()
                
                if blueprint.steps and len(blueprint.steps) > 50:
                    blueprint.steps = blueprint.steps[:50]

                self._normalize_blueprint_agents(blueprint, agent_role)
                
                ghosts = await self._verify_integrity(blueprint.model_dump(), task_id)
                if ghosts:
                    messages.append({"role": "system", "content": f"Plan integrity errors: {ghosts}. Sửa lại thưa Master."})
                    continue
                
                review = await self._critic.review_plan(goal, blueprint.model_dump().get("steps"))
                if review.get("approved"):
                    asyncio.create_task(reasoning_bank.memorize(goal, blueprint.thought))
                    try:
                        from core.utils.team_patterns import (
                            annotate_blueprint_dict,
                            apply_pattern_to_steps,
                            infer_team_pattern,
                        )

                        pat = team_pat or infer_team_pattern(goal)
                        dumped = blueprint.model_dump()
                        dumped = annotate_blueprint_dict(dumped, pat, goal)
                        steps = apply_pattern_to_steps(
                            dumped.get("steps") or [], pat
                        )
                        dumped["steps"] = steps
                        return dumped
                    except Exception as ann_err:
                        logger.debug("[TEAM-PATTERN] annotate skipped: %s", ann_err)
                    return blueprint.model_dump()
                messages.append({"role": "system", "content": f"Feedback: {review.get('feedback')}"})
            except Exception as e:
                messages.append({"role": "system", "content": f"Schema error: {e}"})
        
        return {"status": "failed"}