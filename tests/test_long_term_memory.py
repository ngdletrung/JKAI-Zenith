# -*- coding: utf-8 -*-
"""
Unit test suite cho Persistent Long-Term Memory (Trụ cột 3)
"""

import time
import pytest
from core.memory.long_term_memory import PersistentLongTermMemory, ConversationEngram


class TestLongTermMemory:
    """Kiểm tra chức năng lưu trữ engram, Temporal Recall và Memory Consolidation."""

    def test_store_and_recall_engram(self):
        ltm = PersistentLongTermMemory()
        # Lưu 1 ký ức về cấu hình hệ thống
        ltm.store_engram(
            session_id="session_may_1",
            user_goal="Cấu hình card đồ họa AMD Radeon RX 6600 cho JKAI",
            topic="Cấu hình phần cứng",
            key_facts=["RX 6600 có 8GB VRAM", "Chạy Vulkan Native", "Keep alive = -1"],
            summary="Đã tối ưu hóa VRAM cho RX 6600",
            importance=2.0
        )

        # Truy xuất ký ức với câu hỏi mới
        results = ltm.recall_relevant_engrams("Tôi đang dùng card RX 6600 bao nhiêu VRAM?")
        assert len(results) >= 1
        assert results[0]["topic"] == "Cấu hình phần cứng"
        assert results[0]["score"] > 0
        assert "RX 6600 có 8GB VRAM" in results[0]["key_facts"]

    def test_temporal_factor_gives_higher_score_to_recent(self):
        ltm = PersistentLongTermMemory()
        now = time.time()
        
        # Ký ức 1: Hôm nay
        e_recent = ltm.store_engram(
            session_id="s_recent",
            user_goal="Kế hoạch phát triển dự án tuần này",
            topic="Kế hoạch dự án",
            summary="Ưu tiên làm Observability"
        )
        e_recent.created_at = now

        # Ký ức 2: 30 ngày trước
        e_old = ltm.store_engram(
            session_id="s_old",
            user_goal="Kế hoạch phát triển dự án tháng trước",
            topic="Kế hoạch dự án",
            summary="Ưu tiên làm Fast Pipeline"
        )
        e_old.created_at = now - (30 * 86400)

        results = ltm.recall_relevant_engrams("Kế hoạch phát triển dự án", top_k=2, current_time=now)
        assert len(results) == 2
        # Ký ức mới phải có điểm cao hơn ký ức 30 ngày trước
        assert results[0]["session_id"] == "s_recent"
        assert results[0]["score"] > results[1]["score"]

    def test_consolidate_memory(self):
        ltm = PersistentLongTermMemory()
        ltm.local_engrams.clear()
        ltm.entity_index.clear()

        # Tạo 2 engram trùng lặp nội dung
        ltm.store_engram(
            session_id="s1",
            user_goal="Báo cáo tài chính doanh nghiệp quý 3 năm 2026",
            topic="Tài chính",
            key_facts=["Doanh thu đạt 50 tỷ", "Lợi nhuận 12 tỷ"],
            summary="Báo cáo tài chính Q3 hoàn tất"
        )
        ltm.store_engram(
            session_id="s2",
            user_goal="Báo cáo tài chính doanh nghiệp quý 3 năm 2026",
            topic="Tài chính",
            key_facts=["Doanh thu đạt 50 tỷ", "Chi phí 38 tỷ"],
            summary="Báo cáo tài chính Q3 hoàn tất"
        )

        assert len(ltm.local_engrams) == 2
        cons = ltm.consolidate_memory()
        assert cons["status"] == "CONSOLIDATED"
        assert cons["merged_count"] == 1
        assert cons["total_engrams"] == 1
