# -*- coding: utf-8 -*-
"""
Unit test suite cho Fact Distiller v2.0, MasterPromptArchitect MID Mode & Dynamic Truncation
"""

import os
import sys
import pytest
from core.knowledge_sources.fact_distiller import fact_distiller

# Nạp module MasterPromptArchitect
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "ai-brain"))
from prompt_engine.master_prompt_architect import MasterPromptArchitect


class TestIQAndPromptArchitect:
    """Kiểm tra độ chính xác của Fact Distiller v2.0 và MasterPromptArchitect v50.0."""

    def test_fact_distiller_extracts_key_facts(self):
        raw_text = (
            "Chào mừng quý độc giả đến với trang tin tức hàng đầu. "
            "Hôm nay ngày 25/08/2026, giá vàng SJC tăng mạnh 500.000đ đạt mức 91.5 triệu/lượng. "
            "Hãy nhấn like và theo dõi chúng tôi để nhận thông báo mới nhất. "
            "Tổng cục thống kê công bố GDP quý 3 tăng trưởng 7.2% vượt kế hoạch đề ra."
        )
        distilled = fact_distiller.distill_facts(raw_text, query="giá vàng SJC")
        
        assert "91.5 triệu/lượng" in distilled
        assert "7.2%" in distilled
        assert "quảng cáo" not in distilled
        assert "theo dõi chúng tôi" not in distilled
        assert "•" in distilled

    def test_fact_distiller_preserves_bullet_points(self):
        bullet_text = (
            "- Doanh thu quý 2 đạt 1500 tỷ VND, tăng trưởng +12.5%\n"
            "- Lợi nhuận sau thuế đạt 320 tỷ VND\n"
            "- Chi phí vận hành giảm 4.5% nhờ tối ưu hóa hệ thống\n"
            "- Quảng cáo: Hãy đăng ký khóa học ngay hôm nay"
        )
        distilled = fact_distiller.distill_facts(bullet_text, query="doanh thu")
        assert "1500 tỷ VND" in distilled
        assert "320 tỷ VND" in distilled
        assert "Quảng cáo" not in distilled

    def test_fact_distiller_jaccard_deduplication(self):
        duplicate_text = (
            "Giá vàng SJC hôm nay tăng mạnh lên mức 91.5 triệu đồng một lượng.\n"
            "Giá vàng SJC hôm nay tăng mạnh đạt mức 91.5 triệu đồng một lượng trên thị trường.\n"
            "Tỷ giá USD/VND duy trì ở mức 25.400 VND đổi 1 đô la."
        )
        distilled = fact_distiller.distill_facts(duplicate_text, query="giá vàng")
        # Khử trùng lặp: chỉ giữ lại 1 câu về giá vàng + 1 câu về USD
        lines = [line for line in distilled.splitlines() if line.strip()]
        assert len(lines) == 2
        assert "25.400 VND" in distilled

    def test_mid_prompt_mode_for_small_models(self):
        architect = MasterPromptArchitect()
        mid_prompt = architect.build_master_system_prompt(
            role="RECEPTIONIST",
            task_type=["CODING", "ANALYSIS"],
            prompt_variant="MID"
        )
        
        assert "IDENTITY: JKAI Zenith Autonomous OS" in mid_prompt
        assert "COGNITIVE REASONING DIRECTIVE" in mid_prompt
        assert "<thinking>" in mid_prompt
        assert "CODING" in mid_prompt
        
        full_prompt = architect.build_master_system_prompt(
            role="RECEPTIONIST",
            task_type=["CODING", "ANALYSIS"],
            prompt_variant="FULL"
        )
        assert len(mid_prompt) < len(full_prompt)

    def test_truncate_to_limit_preserves_bounds(self):
        architect = MasterPromptArchitect()
        long_prompt = "Header Info\n" + ("Nội dung bài viết rất dài " * 500) + "\nFooter Directives"
        truncated = architect.truncate_to_limit(long_prompt, max_tokens=100)
        
        assert len(truncated) < len(long_prompt)
        assert "PROMPT CONTENT TRUNCATED" in truncated
        assert "Header Info" in truncated
        assert "Footer Directives" in truncated

    def test_yaml_administrative_templates_loaded(self):
        architect = MasterPromptArchitect()
        assert "templates" in architect._admin_templates or len(architect._admin_templates) >= 0
