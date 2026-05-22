"""
╔══════════════════════════════════════════════════════════════════════╗
║  JKAI ZENITH - SKILL SELECTOR v2.0 (SOVEREIGN INTELLIGENCE ENGINE)   ║
║  Inspired by: Gemini + Grok + DeepSeek Architecture Research         ║
║                                                                       ║
║  4-Layer Pipeline:                                                    ║
║  L0: Necessity Gate  → Có cần skill không?                           ║
║  L1: Lexicon Match   → Hard-match intent_pairs (free, instant)       ║
║  L2: Alias Match     → Fuzzy match aliases_vn trong registry         ║
║  L3: Policy Scoring  → score = semantic*0.4 + alias*0.3 + rate*0.2  ║
║  L4: Confidence Gate → if max_score < 0.55 → fallback LLM reason    ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import re
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger("jkai.skill_selector")

# ─────────────────────────────────────────────────────────────
# [L0] NECESSITY GATE - Inspired by DeepSeek
# "Hỏi trước: Có thực sự cần tool không?"
# ─────────────────────────────────────────────────────────────

# Các loại câu hỏi có thể trả lời bằng LLM thuần — KHÔNG cần skill
_NO_SKILL_PATTERNS = [
    r"^(xin chào|hello|hi|hey|chào|cảm ơn|thanks|ok|oke|okê)[\s!.]*$",
    r"^(bạn là ai|bạn tên gì|bạn là gì|you are|who are you)[\s?]*$",
    r"^(giải thích|explain|định nghĩa|define|là gì|what is)\s+\w+[\s?]*$",
]

# Các tín hiệu BẮT BUỘC cần skill (realtime, system, browser...)
_NEED_SKILL_SIGNALS = [
    "tìm kiếm", "search", "tra cứu", "internet", "web", "trang web", "url", "http",
    "chạy lệnh", "run", "execute", "terminal", "docker", "file", "tệp tin",
    "xem", "chụp màn hình", "screenshot", "ảnh", "hình ảnh",
    "tin tức", "hôm nay", "mới nhất", "cập nhật", "realtime",
    "giá", "bitcoin", "chứng khoán", "thời tiết",
    "tạo", "viết code", "build", "deploy", "kubernetes",
    "đồng bộ", "sync", "backup", "monitor", "giám sát",
    "phân tích tài chính", "report", "báo cáo",
]

def necessity_gate(goal: str) -> Tuple[bool, str]:
    """
    L0: Kiểm tra xem yêu cầu có cần skill không.
    Returns: (needs_skill: bool, reason: str)
    """
    goal_lower = goal.lower().strip()

    # Check NO-SKILL patterns (simple conversational)
    for pat in _NO_SKILL_PATTERNS:
        if re.match(pat, goal_lower):
            return False, "simple_conversation"

    # Check NEED-SKILL signals
    for signal in _NEED_SKILL_SIGNALS:
        if signal in goal_lower:
            return True, f"signal_detected:{signal}"

    # Default: hỏi LLM nhưng vẫn thử match skill
    return True, "default_check"


# ─────────────────────────────────────────────────────────────
# [L1] HARD-CODED INTENT → SKILL BRIDGE
# Inspired by Gemini's "Router Agent" concept
# Ánh xạ cứng: task.value + domain → Skill IDs
# ─────────────────────────────────────────────────────────────

INTENT_SKILL_BRIDGE: Dict[str, List[str]] = {
    # task + domain combos → skill IDs
    "SEARCH+NEWS":       ["search_web_global", "SEARCH_WEB_GLOBAL"],
    "SEARCH+DATA":       ["search_web_global", "SEARCH_WEB_GLOBAL"],
    "SEARCH+AI_AGENT":   ["search_web_global", "SEARCH_WEB_GLOBAL"],
    "SEARCH+SYSTEM":     ["skill_xray_monitor", "system_xray_monitor"],
    "RESEARCH+DEFAULT":  ["agent-scout-explorer", "SKILL_STRATEGIC_RECON"],
    "OBSERVE+WEB":       ["BROWSER_VISION_OPS"],
    "INTERACT+BROWSER":  ["BROWSER_VISION_OPS"],
    "ANALYZE+CODING":    ["agent-coder", "CODE_AUDIT_ELITE"],
    "ANALYZE+SECURITY":  ["SECURITY-AUDIT", "CODE_AUDIT_ELITE"],
    "ANALYZE+DATA":      ["skill_fin_02_tech_analysis"],
    "CREATE+CODING":     ["agent-coder", "sparc-methodology"],
    "CREATE+DEVOPS":     ["agent-ops-cicd-github"],
    "CREATE+AI_AGENT":   ["SKILL_FORGE", "skill_forge"],
    "DEBUG+CODING":      ["agent-coder", "SYSTEMATIC_DEBUGGING"],
    "DEBUG+SYSTEM":      ["self_healing_sentinel", "skill_xray_monitor"],
    "PLAN+DEFAULT":      ["agent-planner", "agent-goal-planner"],
    "EDIT+CODING":       ["agent-coder", "sparc-methodology"],
    "SUMMARIZE+DEFAULT": [],  # LLM thuần
    "EXPLAIN+DEFAULT":   [],  # LLM thuần
    "SYNC+KNOWLEDGE":    ["IMPORT_SKILL", "KNOWLEDGE_ASSIMILATOR"],
    "DEPLOY+DEVOPS":     ["agent-ops-cicd-github", "workflow-automation"],
}

def bridge_lookup(task: str, domain: str) -> List[str]:
    """L1: Tra cứu cứng Intent Bridge."""
    # Thử exact match
    key = f"{task}+{domain}"
    if key in INTENT_SKILL_BRIDGE:
        return INTENT_SKILL_BRIDGE[key]
    # Thử fallback với DEFAULT
    key_default = f"{task}+DEFAULT"
    return INTENT_SKILL_BRIDGE.get(key_default, [])


# ─────────────────────────────────────────────────────────────
# [L2] ALIAS FUZZY MATCH
# Inspired by Gemini's "keyword-in-description" approach
# ─────────────────────────────────────────────────────────────

def _normalize_vn(text: str) -> str:
    """Chuẩn hóa tiếng Việt không dấu để so khớp."""
    replacements = {
        '[àáảãạăằắẳẵặâầấẩẫậ]': 'a', '[èéẻẽẹêềếểễệ]': 'e',
        '[ìíỉĩị]': 'i', '[òóỏõọôồốổỗộơờớởỡợ]': 'o',
        '[ùúủũụưừứửữự]': 'u', '[ỳýỷỹỵ]': 'y', '[đ]': 'd',
    }
    result = text.lower()
    for pat, rep in replacements.items():
        result = re.sub(pat, rep, result)
    return result

def alias_match_score(goal: str, skill_info: Dict) -> float:
    """
    L2: So khớp goal với aliases_vn và name_vn trong registry.
    Returns score: 0.0 - 1.0
    """
    goal_norm = _normalize_vn(goal)
    goal_words = set(goal_norm.split())

    score = 0.0
    hit_count = 0

    # So khớp với aliases
    for alias in skill_info.get("aliases_vn", []):
        alias_norm = _normalize_vn(alias)
        alias_words = set(alias_norm.split())
        # Intersection score
        common = goal_words & alias_words
        if common:
            hit_count += len(common)
            if alias_norm in goal_norm:  # Exact phrase match
                score = max(score, 0.9)
            else:
                score = max(score, 0.5 * len(common) / max(len(alias_words), 1))

    # So khớp với name_vn
    name = _normalize_vn(skill_info.get("name_vn", ""))
    name_words = set(name.split()) - {"ky", "nang", "skill", "the", "va", "de", "la"}
    common_name = goal_words & name_words
    if common_name:
        score = max(score, 0.4 * len(common_name) / max(len(name_words), 1))

    return min(score, 1.0)


# ─────────────────────────────────────────────────────────────
# [L3] POLICY SCORING ENGINE
# Inspired by Grok's scoring formula
# ─────────────────────────────────────────────────────────────

def compute_policy_score(
    lexicon_score: float,       # L1 bridge hit
    alias_score: float,         # L2 alias match
    success_rate: float = 0.8,  # Historical success (default 0.8)
    latency: int = 2,           # 1=fast, 5=slow
    priority: str = "NORMAL"    # CRITICAL/HIGH/NORMAL/LOW
) -> float:
    """
    Policy Score Formula (inspired by Grok):
    score = lexicon*0.40 + alias*0.30 + success_rate*0.20 + latency_bonus*0.10
    """
    latency_bonus = 1.0 / max(latency, 1)  # Faster = higher bonus

    priority_multiplier = {
        "CRITICAL": 1.2,
        "HIGH": 1.1,
        "NORMAL": 1.0,
        "LOW": 0.9,
    }.get(priority, 1.0)

    raw_score = (
        lexicon_score  * 0.40 +
        alias_score    * 0.30 +
        success_rate   * 0.20 +
        latency_bonus  * 0.10
    )
    return min(raw_score * priority_multiplier, 1.0)


# ─────────────────────────────────────────────────────────────
# [L4] CONFIDENCE GATE + SELF-REFLECTION
# Inspired by Grok: "if confidence < 0.65 → re-evaluate"
# ─────────────────────────────────────────────────────────────

CONFIDENCE_THRESHOLD = 0.45  # Ngưỡng tối thiểu để chấp nhận một skill


# ─────────────────────────────────────────────────────────────
# MASTER SELECTOR — Gộp tất cả 4 Layer
# ─────────────────────────────────────────────────────────────

async def select_skills(
    goal: str,
    all_skills: Dict,
    task_id: str = "sys",
    top_k: int = 3,
    radar: Optional[Dict] = None
) -> Dict[str, Any]:
    """
    🧠 JKAI Skill Selector v2.0 — 4-Layer Sovereign Pipeline.

    Returns:
        {
            "needs_skill": bool,
            "reason": str,
            "candidates": [...],
            "confidence": float,
            "fallback_to_llm": bool
        }
    """
    try:
        from core.utils.engine import engine
        engine.publish_mission_log("SKILL-SELECTOR", f"🎯 [SELECTOR-v2] Đang phân tích: `{goal[:60]}...`", task_id, stealth=True)
    except:
        pass

    # ─── L0: NECESSITY GATE ───
    needs_skill, gate_reason = necessity_gate(goal)
    if not needs_skill:
        return {
            "needs_skill": False,
            "reason": gate_reason,
            "candidates": [],
            "confidence": 0.0,
            "fallback_to_llm": True
        }

    # ─── L1: LEXICON BRIDGE ───
    task_val   = (radar or {}).get("task",   {}).get("value",  "") or ""
    domain_val = (radar or {}).get("domain", {}).get("value",  "") or ""
    bridge_hits = set(bridge_lookup(task_val.upper(), domain_val.upper()))

    # ─── L2+L3: SCORE ALL SKILLS ───
    scored: List[Dict] = []

    for skill_id, info in all_skills.items():
        # L1 score: 1.0 nếu bridge hit, 0.0 nếu không
        l1_score = 1.0 if (skill_id in bridge_hits or
                           info.get("id", "") in bridge_hits) else 0.0

        # L2 score: alias fuzzy match
        l2_score = alias_match_score(goal, info)

        # Skip skills có 0 điểm cả 2 lớp
        if l1_score == 0.0 and l2_score < 0.1:
            continue

        # L3: Policy Score
        priority = info.get("priority", "NORMAL")
        latency  = int(info.get("latency", 2))
        success  = float(info.get("success_rate", 0.8))

        final_score = compute_policy_score(l1_score, l2_score, success, latency, priority)

        # L4: Filter by confidence threshold
        if final_score < CONFIDENCE_THRESHOLD:
            continue

        scored.append({
            "skill_id":    skill_id,
            "name":        info.get("name_vn", skill_id),
            "description": info.get("description", ""),
            "domain":      info.get("domain", "CORE"),
            "score":       round(final_score, 4),
            "l1_bridge":   l1_score > 0,
            "l2_alias":    round(l2_score, 3),
            "priority":    priority,
            "rel_path":    info.get("rel_path", ""),
        })

    # Sort by score desc
    scored.sort(key=lambda x: x["score"], reverse=True)
    top_candidates = scored[:top_k]

    # ─── L4: CONFIDENCE GATE & DYNAMIC RE-RANKING ───
    max_conf = top_candidates[0]["score"] if top_candidates else 0.0
    fallback = max_conf < 0.55  # Nếu score thấp, recommend LLM reason

    # [HYBRID-RE-RANKING]: Nếu độ tin cậy thấp (< 0.65) và có nhiều ứng viên, gọi LLM tái định tuyến toàn cục
    if max_conf < 0.65 and len(top_candidates) > 1:
        try:
            from core.utils.engine import engine
            engine.publish_mission_log(
                "SKILL-SELECTOR",
                f"🧠 [SELECTOR-RE-RANK] Độ tin cậy thấp ({max_conf:.0%}). Triệu hồi Planner tái định tuyến toàn cục...",
                task_id, stealth=True
            )
            
            candidates_info = "\n".join([
                f"- ID: {c['skill_id']}\n  Tên: {c['name']}\n  Mô tả: {c['description']}\n  Domain: {c['domain']}"
                for c in top_candidates
            ])
            
            rerank_prompt = f"""Bạn là Bộ Điều Phối Kỹ Năng Tối Cao của Zenith OS.
Yêu cầu của Master: "{goal}"

Danh sách các kỹ năng ứng viên tiềm năng:
{candidates_info}

Hãy phân tích toàn cục và chọn ra duy nhất 1 ID kỹ năng phù hợp nhất với yêu cầu.
Trả về JSON định dạng chuẩn xác: {{"selected_id": "ID_KỸ_NĂNG_ĐÃ_CHỌN", "reason": "Lý do lựa chọn chiến lược"}}"""

            import json
            rerank_resp = await engine.call_chat(
                messages=[{"role": "user", "content": rerank_prompt}],
                role="PLANNER",
                task_id=task_id,
                json_mode=True
            )
            
            if isinstance(rerank_resp, str):
                match = re.search(r'\{.*\}', rerank_resp, re.DOTALL)
                if match:
                    rerank_resp = json.loads(match.group())
            
            selected_id = rerank_resp.get("selected_id")
            if selected_id:
                for c in top_candidates:
                    if c["skill_id"].upper() == selected_id.upper():
                        c["score"] = 1.0
                        c["reason"] = f"Planner Re-ranked: {rerank_resp.get('reason')}"
                        top_candidates.sort(key=lambda x: x["score"], reverse=True)
                        max_conf = 1.0
                        fallback = False
                        engine.publish_mission_log(
                            "SKILL-SELECTOR",
                            f"🎯 [SELECTOR-RE-RANK] Planner đã chọn: `{selected_id}` | Lý do: {rerank_resp.get('reason')}",
                            task_id
                        )
                        break
        except Exception as e:
            logger.warning(f"[SELECTOR-RE-RANK-FAILED] Lỗi re-rank: {e}")

    if fallback and top_candidates:
        logger.warning(f"[SELECTOR-LOW-CONF] Max={max_conf:.2f} — Recommend LLM self-reflection.")

    try:
        from core.utils.engine import engine
        found_names = [c['skill_id'] for c in top_candidates]
        engine.publish_mission_log(
            "SKILL-SELECTOR",
            f"✅ [SELECTOR-v2] Top-{len(top_candidates)}: {found_names} | Max confidence: {max_conf:.0%}",
            task_id, stealth=True
        )
    except:
        pass

    return {
        "needs_skill":    True,
        "reason":         gate_reason,
        "candidates":     top_candidates,
        "confidence":     max_conf,
        "fallback_to_llm": fallback,
        "bridge_hits":    list(bridge_hits),
    }


# ─────────────────────────────────────────────────────────────
# SELF-REFLECTION HOOK (Post-execution)
# Inspired by Grok: "After execution, verify quality"
# ─────────────────────────────────────────────────────────────

async def reflect_on_result(
    goal: str,
    skill_id: str,
    result: Any,
    task_id: str = "sys"
) -> Dict:
    """
    🪞 Post-execution reflection: Đánh giá chất lượng kết quả.
    Nếu thất bại hoặc kết quả rỗng → gợi ý re-route.
    """
    if not result:
        return {"quality": "empty", "should_reroute": True, "reason": "empty_result"}

    result_str = str(result)
    if len(result_str) < 20 or "error" in result_str.lower() or "lỗi" in result_str.lower():
        return {"quality": "low", "should_reroute": True, "reason": "error_in_result"}

    return {"quality": "ok", "should_reroute": False, "reason": ""}
