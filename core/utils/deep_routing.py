"""
Tự chọn DEEP pipeline khi Master báo lỗi / debug trong chat thường (không cần /deep).
"""

from __future__ import annotations

import os
import re
from typing import Any, List, Optional

_ERROR_TRACE_RE = re.compile(
    r"traceback|error:|exception:|stack\s*trace|syntaxerror|importerror|"
    r"attributeerror|typeerror|valueerror|keyerror|modulenotfounderror|"
    r"errno\s*\d+|failed|failure|critical",
    re.IGNORECASE,
)

_ERROR_VI_RE = re.compile(
    r"\b(lỗi|loi|bug|crash|hỏng|hong|đứt|dut|sập|sap|"
    r"không chạy|khong chay|không hoạt động|khong hoat dong|"
    r"sửa lỗi|sua loi|tìm lỗi|tim loi|tìm nguyên nhân|tim nguyen nhan|"
    r"fix\s+bug|broken|no output|connection refused)\b",
    re.IGNORECASE,
)

_CODE_CONTEXT_RE = re.compile(
    r"(services/|core/|intelligence/|\.py\b|planner|executor|docker|"
    r"import\s+\w+|file\s+[\"'])",
    re.IGNORECASE,
)

_HTTP_ERROR_RE = re.compile(r"\b(500|502|503|504)\b")

_AUDIT_VI_RE = re.compile(
    r"\b(rà soát|ra soat|điểm nghẽn|diem nghen|audit|bottleneck|tối ưu hệ thống|toi uu he thong)\b",
    re.IGNORECASE,
)


def _env_auto_deep() -> bool:
    raw = os.getenv("JKAI_AUTO_DEEP_ON_ERROR", "true").strip().lower()
    return raw in ("1", "true", "yes", "on")


def _env_auto_deep_analysis() -> bool:
    raw = os.getenv("JKAI_AUTO_DEEP_ON_ANALYSIS", "true").strip().lower()
    return raw in ("1", "true", "yes", "on")


_SEARCH_NEWS_RE = re.compile(
    r"\b(tin tức|tin tuc|tìm kiếm|tim kiem|tra cứu|tra cuu|search|news|thời sự|thoi su|"
    r"hôm nay|hom nay|mới nhất|moi nhat)\b",
    re.IGNORECASE,
)

def goal_should_force_deep_for_analysis(goal: str) -> bool:
    """Phân tích / so sánh / báo cáo → DEEP + T5 CRITIC (Harness producer-reviewer).
    Loại trừ các truy vấn tìm kiếm tin tức để không ép DEEP."""
    if not _env_auto_deep_analysis():
        return False
    g = (goal or "").strip()
    if not g or g.startswith("/"):
        return False
    if _SEARCH_NEWS_RE.search(g):
        return False
    try:
        from core.utils.team_patterns import infer_team_pattern, PATTERN_PRODUCER_REVIEWER

        pat = infer_team_pattern(g)
        return pat.requires_deep_pipeline or pat.id == PATTERN_PRODUCER_REVIEWER
    except Exception:
        return False


def _last_user_text(history: Optional[List[Any]], max_turns: int = 3) -> str:
    if not history:
        return ""
    chunks: List[str] = []
    for item in reversed(history[-max_turns * 2 :]):
        if isinstance(item, dict):
            role = (item.get("role") or "").lower()
            if role in ("user", "human", "master"):
                chunks.append(str(item.get("content") or item.get("text") or ""))
        elif isinstance(item, (list, tuple)) and len(item) >= 2:
            if str(item[0]).lower() in ("user", "human"):
                chunks.append(str(item[1]))
    return "\n".join(chunks)


_KNOWLEDGE_QUERY_RE = re.compile(
    r"\b(là gì|la gi|là ai|la ai|định nghĩa|dinh nghia|khái niệm|khai niem|"
    r"giải thích|giai thich|explain|what is|who is|what are|"
    r"tìm hiểu|tim hieu|có nghĩa là|co nghia la|"
    r"khác nhau|khac nhau|so sánh|so sanh|"
    r"tại sao|tai sao|vì sao|vi sao|nguyên nhân|nguyen nhan|"
    r"làm thế nào|lam the nao|làm sao|lam sao|"
    r"cách nào|cach nao|cách.*(làm|học|dùng|sử dụng)|"
    r"cach.*(lam|hoc|dung|su dung)|"
    r"hướng dẫn|huong dan|tutorial|guide|"
    r"học\s+\w+|hoc\s+\w+|"
    r"\w+\s+gì\b|\w+\s+gi\b|\w+\s+nhỉ\b)\b",
    re.IGNORECASE,
)

def goal_should_force_deep(goal: str, history: Optional[List[Any]] = None) -> bool:
    """
    True → receptionist/ingress nên dùng DEEP (plan + tool) thay vì FAST chat.
    Siêu lệnh /... do CommandRouter xử lý — không ép DEEP ở đây.
    """
    if not _env_auto_deep():
        return False
    g = (goal or "").strip()
    if not g or g.startswith("/"):
        return False

    try:
        from core.utils.project_workspace import goal_should_use_workspace_agent

        if goal_should_use_workspace_agent(g):
            return True
    except Exception:
        pass

    if _ERROR_TRACE_RE.search(g) or _HTTP_ERROR_RE.search(g):
        return True
    if _ERROR_VI_RE.search(g):
        return True
    if _AUDIT_VI_RE.search(g):
        return True
    if _ERROR_VI_RE.search(g) and _CODE_CONTEXT_RE.search(g):
        return True

    _FILE_BUILD_RE = re.compile(
        r"\b(tạo|tao|xuất|xuat|viết|viet|export|build|generate)\b.*?\b(file|tệp|tep|bảng|bang|excel|\.xlsx|\.csv|\.pdf|\.docx|báo cáo|bao cao)\b",
        re.IGNORECASE,
    )
    if _FILE_BUILD_RE.search(g):
        return True

    # Knowledge queries (definition, explanation, comparison) → DEEP for search
    if _KNOWLEDGE_QUERY_RE.search(g):
        return True

    prior = _last_user_text(history)
    if prior and _ERROR_TRACE_RE.search(prior):
        return True
    if prior and _ERROR_VI_RE.search(prior) and _CODE_CONTEXT_RE.search(g + " " + prior):
        return True

    if goal_should_force_deep_for_analysis(g):
        return True

    return False


def should_use_deep_pipeline_full(goal: str, kwargs: Optional[dict] = None) -> bool:
    """
    T2→T6 full DeepPipeline when env on and goal matches analysis / error / workspace.
    Override: JKAI_DEEP_PIPELINE_FULL=true|false forces on/off.
    """
    kw = kwargs or {}
    force = os.getenv("JKAI_DEEP_PIPELINE_FULL", "").strip().lower()
    if force in ("1", "true", "yes", "on"):
        return True
    if force in ("0", "false", "no", "off"):
        return False
    if kw.get("jkai_force_deep_full"):
        return True
    if kw.get("jkai_workspace_target") or kw.get("jkai_project_root"):
        return True
    if kw.get("jkai_cloned_repos"):
        return True
    if goal_should_force_deep_for_analysis(goal):
        return True
    if goal_should_force_deep(goal, kw.get("history")):
        return True
    return False


# Danh sách các skill chạy ở chế độ DEEP bắt buộc
_DEEP_SKILLS = {
    "skill_self_healing",
    "skill_dongbotrithuc",
    "skill_strategic_recon",
    "skill_host_control",
    "skill_quantrihethong",
    "skill_autonomous_researcher",
    "skill_code_audit_elite",
}


def effective_ingress_mode(goal: str, requested_mode: str, history=None) -> str:
    """Nâng fast/auto → deep khi phát hiện báo lỗi (Ngoại trừ tác vụ LOOKUP)."""
    mode = (requested_mode or "fast").strip().lower()
    
    # 🧠 [ZAP-v4-ROUTING-GATE]: Kiểm tra nếu kích hoạt các skill bắt buộc chạy DEEP
    try:
        # 1. Check deck references (ví dụ: #1002)
        from core.utils.skill_deck_index import SkillDeckIndex
        deck = SkillDeckIndex.get()
        deck.ensure_loaded()
        deck_entries = deck.resolve_all_in_text(goal)
        if any(e.registry_id in _DEEP_SKILLS for e in deck_entries if e.registry_id):
            return "deep"
            
        # 2. Check semantic matches (ví dụ: "hội đồng chuyên gia")
        from core.utils.semantic_skill_matcher import SemanticSkillMatcher
        matcher = SemanticSkillMatcher.get()
        matches = matcher.match(goal, top_k=2, min_score=0.40)
        if matches and matches[0].skill_id in _DEEP_SKILLS:
            return "deep"
    except Exception:
        pass

    # 🧠 [ZAP-v3-ROUTING-GATE]: Tuyệt đối không ép DEEP đối với tác vụ LOOKUP
    try:
        from prompt_assembler import ZenithPromptAssembler
        if ZenithPromptAssembler.classify_task(goal) == "LOOKUP":
            return "fast"
    except Exception:
        pass

    if mode in ("deep", "deliberative"):
        return "deep"
    if mode == "fast":
        return "fast"
    if mode == "auto":
        if goal_should_force_deep(goal, history) or goal_should_force_deep_for_analysis(goal):
            return "deep"
    return mode


def get_deep_routing_label(goal: str, history: Optional[List[Any]] = None) -> str:
    """Trả về mô tả định tuyến chi tiết, tránh log nhầm 'lỗi/debug' cho câu hỏi tri thức."""
    g = (goal or "").strip()
    if _ERROR_TRACE_RE.search(g) or _HTTP_ERROR_RE.search(g):
        return "DEEP — xử lý sự cố / stack trace."
    if _ERROR_VI_RE.search(g):
        return "DEEP — khắc phục lỗi hệ thống."
    if _AUDIT_VI_RE.search(g):
        return "DEEP — rà soát và tối ưu."
    if _KNOWLEDGE_QUERY_RE.search(g):
        return "DEEP — tra cứu tri thức chuyên sâu."
    prior = _last_user_text(history)
    if prior and (_ERROR_TRACE_RE.search(prior) or _ERROR_VI_RE.search(prior)):
        return "DEEP — theo dõi sửa lỗi tiếp diễn."
    return "DEEP — tự động định tuyến."
