# -*- coding: utf-8 -*-
"""
Unit test suite cho Entity & Topic Shift Resolver v3.0
"""

import os
import sys
import pytest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "services", "ai-brain"))
from context.entity_resolver import EntityResolver


class TestEntityResolverV3:
    """Kiểm tra chức năng duy trì Topic Stack và khôi phục chủ đề sau khi chuyển hướng."""

    def test_topic_stack_push_and_limit(self):
        resolver = EntityResolver()
        resolver.push_topic("Bảng lương tháng 8")
        resolver.push_topic("Thời tiết Hà Nội")
        resolver.push_topic("Giá vàng hôm nay")
        resolver.push_topic("Báo cáo doanh thu")
        resolver.push_topic("File Excel tiến độ")
        resolver.push_topic("Chủ đề thứ 6")

        assert len(resolver.topic_stack) == 5
        assert "Bảng lương tháng 8" not in resolver.topic_stack
        assert "Chủ đề thứ 6" in resolver.topic_stack

    def test_topic_resumption_recovery(self):
        resolver = EntityResolver()
        resolver.push_topic("bảng lương tháng 8")
        resolver.push_topic("thời tiết hà nội")

        # Master nói "quay lại cái bảng lương lúc nãy"
        resumed = resolver.detect_topic_resumption("quay lại cái bảng lương lúc nãy thêm cột phụ cấp")
        assert resumed == "bảng lương tháng 8"

        resolved_query = resolver.resolve("quay lại cái bảng lương lúc nãy thêm cột phụ cấp")
        assert "[bảng lương tháng 8]" in resolved_query

    def test_anaphora_resolution_with_stack(self):
        resolver = EntityResolver()
        resolver.push_topic("giá vàng hôm nay")

        resolved = resolver.resolve("nó có tăng không bạn")
        assert "giá vàng hôm nay" in resolved
