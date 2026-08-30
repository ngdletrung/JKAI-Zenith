# -*- coding: utf-8 -*-
"""
core/os/cognition/goal_contract.py
JKAI DEMS v1.0 — Deterministic Goal Contract Compiler.

Extracts objective acceptance criteria, required topics, time bounds,
and explicitly excluded scopes from Master's request without calling any LLM.
"""

from __future__ import annotations
import re
import time
from dataclasses import dataclass, field
from datetime import datetime
from typing import List, Optional, Set


@dataclass(frozen=True)
class GoalContract:
    raw_goal: str
    required_topics: List[str]
    required_time: Optional[str]
    excluded_scopes: List[str]
    success_criteria: List[str]
    is_realtime_news: bool
    min_length: int = 80
    min_paragraphs: int = 2
    suggested_tool: Optional[str] = None
    suggested_action_prompt: Optional[str] = None
    created_at: float = field(default_factory=time.time)

    def to_dict(self) -> dict:
        return {
            "raw_goal": self.raw_goal,
            "required_topics": self.required_topics,
            "required_time": self.required_time,
            "excluded_scopes": self.excluded_scopes,
            "success_criteria": self.success_criteria,
            "is_realtime_news": self.is_realtime_news,
            "min_length": self.min_length,
            "min_paragraphs": self.min_paragraphs,
            "suggested_tool": self.suggested_tool,
            "suggested_action_prompt": self.suggested_action_prompt,
            "created_at": self.created_at
        }


class GoalContractCompiler:
    """Deterministic Goal Contract Compiler (< 1ms execution)."""

    def compile(self, goal_text: str) -> GoalContract:
        text_lower = goal_text.strip().lower()
        now = datetime.now()
        today_str = now.strftime("%d/%m/%Y")

        required_topics: List[str] = []
        excluded_scopes: List[str] = []
        success_criteria: List[str] = []
        is_realtime_news = False
        required_time: Optional[str] = None

        # 1. Detect Time Anchors
        if any(kw in text_lower for kw in ["hôm nay", "today", "mới nhất", "hiện tại", "vừa xong"]):
            required_time = today_str
            is_realtime_news = True
            success_criteria.append("CURRENT_DATE_ANCHOR")

        # 2. Detect World News / Geopolitics Scope
        if any(kw in text_lower for kw in ["thế giới", "quốc tế", "world", "quân sự", "chiến sự", "ngoại giao"]):
            required_topics.extend(["POLITICS", "GEOPOLITICS", "INTERNATIONAL"])
            excluded_scopes.extend(["HOROSCOPE", "ENTERTAINMENT", "ASTROLOGY"])
            success_criteria.append("WORLD_EVENT_COVERAGE")
            success_criteria.append("EXCLUDE_NOISE_SCOPES")

        # 3. Detect Economy & Financial Scope
        if any(kw in text_lower for kw in ["kinh tế", "tài chính", "giá vàng", "chứng khoán", "usd", "tỷ giá", "lãi suất", "fed"]):
            required_topics.append("ECONOMY")
            success_criteria.append("FINANCIAL_METRIC_COVERAGE")

        # 4. Detect Coding / Technical Scope
        if any(kw in text_lower for kw in ["code", "fix", "sửa lỗi", "refactor", "viết hàm", "class", "module"]):
            required_topics.append("TECHNICAL")
            success_criteria.append("CODE_INTEGRITY")

        # 5. Tool Suggestion Substrate (Scope-Aware & False-Positive Protected)
        suggested_tool = None
        suggested_action_prompt = None
        
        # Chặn gợi ý thừa cho các câu hỏi đơn giản, ngắn gọn (<15 ký tự hoặc chỉ hỏi giá/thời tiết tức thì)
        is_simple_query = any(kw in text_lower for kw in ["mấy giờ", "thời tiết", "là gì", "ở đâu"]) or (len(text_lower.split()) <= 4 and "giá vàng" in text_lower)
        
        if not is_simple_query:
            if any(kw in text_lower for kw in ["báo cáo", "thống kê", "doanh thu", "danh sách", "bảng biểu", "tổng hợp số liệu", "so sánh"]):
                if "POLITICS" in required_topics or "GENERAL" in required_topics:
                    suggested_tool = "OFFICE_SUITE_MASTER"
                    suggested_action_prompt = "Master có muốn tôi xuất bản tin tóm lược này thành định dạng Word (.docx) chuyên nghiệp không?"
                else:
                    suggested_tool = "OFFICE_SUITE_MASTER"
                    suggested_action_prompt = "Master có muốn tôi xuất dữ liệu phân tích này thành một tệp Excel (.xlsx) chuyên nghiệp kèm biểu đồ trực quan không?"
            elif any(kw in text_lower for kw in ["hợp đồng", "tờ trình", "văn bản", "thông báo", "công văn"]):
                suggested_tool = "OFFICE_SUITE_MASTER"
                suggested_action_prompt = "Master có muốn tôi xuất văn bản này thành định dạng Word (.docx) chuẩn quy thức không?"
            elif any(kw in text_lower for kw in ["tự động hóa", "script", "viết bot", "tool", "cào dữ liệu"]):
                suggested_tool = "CODE_ACTUATOR"
                suggested_action_prompt = "Master có muốn tôi viết và chạy thử nghiệm đoạn script Python này trong Sandbox không?"

        # 6. Dynamic Minimum Length & Depth Thresholds
        min_len = 80
        min_paras = 2
        if any(kw in text_lower for kw in ["phân tích", "đánh giá", "chi tiết", "toàn diện", "so sánh"]):
            min_len = 150
            min_paras = 3
        elif any(kw in text_lower for kw in ["thời tiết", "mấy giờ", "ngày nào", "ai là", "định nghĩa"]):
            min_len = 30
            min_paras = 1

        return GoalContract(
            raw_goal=goal_text,
            required_topics=sorted(list(set(required_topics))),
            required_time=required_time,
            excluded_scopes=sorted(list(set(excluded_scopes))),
            success_criteria=success_criteria,
            is_realtime_news=is_realtime_news,
            min_length=min_len,
            min_paragraphs=min_paras,
            suggested_tool=suggested_tool,
            suggested_action_prompt=suggested_action_prompt
        )


goal_contract_compiler = GoalContractCompiler()
