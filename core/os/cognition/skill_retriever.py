# -*- coding: utf-8 -*-
"""
🧠 DYNAMIC SEMANTIC SKILL RETRIEVER & ARGUMENT VALIDATOR
Cơ chế truy xuất công cụ động theo ngữ cảnh (Dynamic Tool Retrieval) và Pre-flight Argument Gate.

Tối ưu hoá cho AI Agents:
- Chỉ nạp Top 2-4 công cụ phù hợp nhất vào Prompt của LLM.
- Kiểm tra tính hợp lệ của tham số trước khi chuyển cho Executor.
- Hỗ trợ Self-Healing (Retry-with-repair) khi LLM truyền thiếu hoặc sai tham số.
"""

from __future__ import annotations

import re
import logging
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Tuple

from core.kernel.semantic_skill_registry import semantic_skill_registry, SemanticSkillManifest, SkillDomain

logger = logging.getLogger("JKAI.SkillRetriever")


@dataclass
class ToolRetrievalVerdict:
    query: str
    selected_manifests: List[SemanticSkillManifest]
    mcp_tools: List[Dict[str, Any]]
    confidence_scores: Dict[str, float]
    excluded_manifests: List[str]


class DynamicSkillRetriever:
    """Bộ truy xuất công cụ động & xác thực ngữ nghĩa."""

    def __init__(self):
        self.registry = semantic_skill_registry

    def retrieve_active_tools(
        self,
        query: str,
        top_k: int = 3,
        forced_skills: Optional[List[str]] = None,
        min_score: float = 0.25
    ) -> ToolRetrievalVerdict:
        """
        Truy xuất động các công cụ phù hợp nhất với câu hỏi / mục tiêu.
        """
        all_manifests = self.registry.list_all_manifests()
        q_lower = query.lower()
        
        scores: Dict[str, float] = {}
        excluded: List[str] = []

        # Tách từ khóa trong query
        q_tokens = set(re.findall(r'\w+', q_lower))

        for m in all_manifests:
            # 1. Nếu có trong danh sách ép buộc (forced_skills), cho điểm tối đa
            if forced_skills and (m.skill_id in forced_skills or any(a in forced_skills for a in m.aliases)):
                scores[m.skill_id] = 10.0
                continue

            score = 0.0

            # 2. Đánh giá tính phù hợp với `when_to_use` (+ điểm mạnh)
            for trigger in m.when_to_use:
                tr_lower = trigger.lower()
                matched_words = [w for w in q_tokens if len(w) > 2 and w in tr_lower]
                if matched_words:
                    score += len(matched_words) * 0.45

            # 3. Đánh giá tính phù hợp với `tags` và `display_name`
            for tag in m.tags:
                if tag.lower() in q_tokens or tag.lower() in q_lower:
                    score += 0.6

            if m.display_name.lower() in q_lower:
                score += 0.8

            # 4. Kiểm tra điều kiện loại trừ `when_not_to_use` (- phạt điểm nặng)
            is_anti_triggered = False
            for anti in m.when_not_to_use:
                anti_lower = anti.lower()
                # Kiểm tra xem có từ khóa anti-trigger rõ ràng không
                if any(k in q_lower for k in ["chào", "hello", "hi jkai", "bạn là ai"]) and m.domain != SkillDomain.GENERAL:
                    score -= 2.0
                    is_anti_triggered = True
                    break

            if is_anti_triggered or score < min_score:
                excluded.append(m.skill_id)
            else:
                scores[m.skill_id] = round(score, 3)

        # Sắp xếp và chọn Top-K
        sorted_skills = sorted(scores.items(), key=lambda x: x[1], reverse=True)
        selected_manifests: List[SemanticSkillManifest] = []

        for skill_id, score in sorted_skills[:top_k]:
            if score >= min_score:
                m = self.registry.get_manifest(skill_id)
                if m:
                    selected_manifests.append(m)

        # Chuyển đổi sang định dạng MCP tools
        mcp_tools = [m.to_mcp_tool_def() for m in selected_manifests]

        logger.info(
            "[DYNAMIC-TOOL-RETRIEVER] Query='%s' -> Selected %d tools: %s",
            query[:60],
            len(selected_manifests),
            [m.skill_id for m in selected_manifests]
        )

        return ToolRetrievalVerdict(
            query=query,
            selected_manifests=selected_manifests,
            mcp_tools=mcp_tools,
            confidence_scores=scores,
            excluded_manifests=excluded
        )

    def validate_tool_call(self, tool_name: str, arguments: Dict[str, Any]) -> Tuple[bool, Optional[str]]:
        """
        Kiểm tra tính hợp lệ của lệnh gọi công cụ trước khi chuyển sang Executor.
        Trả về (True, None) nếu hợp lệ, hoặc (False, error_message) để ReAct loop tự sửa.
        """
        manifest = self.registry.get_manifest(tool_name)
        if not manifest:
            # Nếu công cụ không nằm trong registry, cho phép chạy qua fallback router
            return True, None

        is_valid, err_msg = manifest.validate_arguments(arguments)
        if not is_valid:
            logger.warning("[PREFLIGHT-VALIDATION-FAIL] Tool '%s' call invalid: %s", tool_name, err_msg)
            return False, err_msg

        return True, None


skill_retriever = DynamicSkillRetriever()
