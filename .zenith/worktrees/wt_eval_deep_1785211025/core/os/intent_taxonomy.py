"""
OS-level intent → capability tags → pipeline hints (domain-agnostic).
"""

from __future__ import annotations

import re
from enum import Enum
from typing import List, Set

_GIT_URL = re.compile(r"https?://(?:www\.)?(?:github|gitlab|bitbucket)\.com/", re.I)
_IMAGE_HINT = re.compile(r"\b(hình|hinh|ảnh|anh|image|vision|screenshot|ocr)\b", re.I)
_BUILD_RE = re.compile(
    r"\b(tạo|tao|build|implement|scaffold|viết api|viet api|deploy|docker compose)\b",
    re.I,
)
_CHAT_RE = re.compile(
    r"^(xin chào|chào|hello|hi\b|cảm ơn|cam on|thanks|thời tiết|thoi tiet)\b",
    re.I,
)


class OSIntent(str, Enum):
    COMMAND = "command"
    CAPABILITIES = "capabilities"
    SOCIAL = "social"
    MULTIMODAL = "multimodal"
    RESEARCH = "research"
    ANALYZE = "analyze"
    DEBUG = "debug"
    BUILD = "build"
    FIX = "fix"
    AUDIT = "audit"
    OPERATE = "operate"
    GENERAL = "general"


def capability_tags(goal: str, kwargs: dict) -> Set[str]:
    g = goal or ""
    tags: Set[str] = set()
    if kwargs.get("images"):
        tags.add("multimodal")
    if _GIT_URL.search(g):
        tags.add("remote_repo")
    if kwargs.get("jkai_workspace_target") or kwargs.get("jkai_cloned_repos"):
        tags.add("local_workspace")
    if kwargs.get("jkai_web_only_analysis"):
        tags.add("web_only")
    if kwargs.get("jkai_fast_fix"):
        tags.add("single_file_fix")
    if kwargs.get("resolved_skill_ids"):
        tags.add("skill_deck")
    if re.search(r"\b(docker|kubectl|systemctl|restart)\b", g, re.I):
        tags.add("ops")
    return tags


def classify_os_intent(goal: str, kwargs: dict | None = None) -> OSIntent:
    kw = kwargs or {}
    g = (goal or "").strip()
    if not g:
        return OSIntent.GENERAL
    if kw.get("images") or _IMAGE_HINT.search(g):
        return OSIntent.MULTIMODAL
    try:
        from core.utils.jkai_capabilities import goal_is_capabilities_inquiry

        if goal_is_capabilities_inquiry(g):
            return OSIntent.CAPABILITIES
    except Exception:
        pass
    if _CHAT_RE.search(g) and len(g) < 120:
        return OSIntent.SOCIAL
    try:
        from core.utils.deep_routing import goal_should_force_deep

        if goal_should_force_deep(g, kw.get("history")):
            if re.search(r"\b(lỗi|loi|traceback|fix|debug)\b", g, re.I):
                return OSIntent.DEBUG
    except Exception:
        pass
    try:
        from core.utils.deep_routing import goal_should_force_deep_for_analysis

        if goal_should_force_deep_for_analysis(g):
            return OSIntent.ANALYZE
    except Exception:
        pass
    try:
        from core.utils.project_workspace import _FIX_RE, _AUDIT_RE

        if _FIX_RE.search(g) and kw.get("jkai_fast_fix"):
            return OSIntent.FIX
        if _FIX_RE.search(g):
            return OSIntent.FIX
        if _AUDIT_RE.search(g):
            return OSIntent.AUDIT
    except Exception:
        pass
    if _BUILD_RE.search(g):
        return OSIntent.BUILD
    if _GIT_URL.search(g) or re.search(r"\b(tìm kiếm|tim kiem|search|research|tin tức)\b", g, re.I):
        return OSIntent.RESEARCH
    if re.search(r"\b(docker|deploy|chạy lệnh|chay lenh)\b", g, re.I):
        return OSIntent.OPERATE
    return OSIntent.GENERAL


def default_pipeline_for_intent(intent: OSIntent, tags: Set[str]) -> str:
    """Preferred pipeline id before mode overrides."""
    if "single_file_fix" in tags:
        return "fast_fix"
    if intent == OSIntent.CAPABILITIES:
        return "capabilities"
    if intent == OSIntent.SOCIAL:
        return "fast_chat"
    if intent == OSIntent.MULTIMODAL:
        return "deep"
    if intent == OSIntent.DEBUG:
        return "deep_full"
    if intent == OSIntent.ANALYZE:
        if "web_only" in tags:
            return "deep"
        if "local_workspace" in tags or "remote_repo" in tags:
            return "deep_full"
        return "deep_full"
    if intent in (OSIntent.FIX, OSIntent.BUILD, OSIntent.AUDIT):
        if "local_workspace" in tags:
            return "cursor_agent"
        return "deep"
    if intent == OSIntent.RESEARCH:
        return "fast"
    if intent == OSIntent.OPERATE:
        return "deep"
    return "auto"
