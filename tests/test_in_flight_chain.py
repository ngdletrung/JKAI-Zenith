# -*- coding: utf-8 -*-
"""
tests/test_in_flight_chain.py
==============================
Kiểm thử đơn vị cho T4 In-Flight Dynamic Tool Chain (Học hỏi OpenManus):
1. Lọc và chuẩn hóa candidate URLs (loại bỏ video/mạng xã hội).
2. Tối ưu hóa truy vấn rườm rà (Query Simplification).
3. Chuỗi phản xạ vi mô: tự động kích hoạt `read_url_content` khi tìm thấy URL giá trị.
4. Tự động thử lại khi truy vấn ban đầu rỗng/thất bại với câu hỏi dài.
5. Kiểm soát trần micro-turn (không vượt quá 2 vòng lặp cục bộ).
6. Ghi nhận sự kiện cấu trúc vào CognitiveEventStore.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock

import pytest

from core.os.cognition.event_model import event_store
from core.os.cognition.in_flight_chain import (
    InFlightChainConfig,
    InFlightChainExecutor,
    filter_candidate_urls,
    simplify_verbose_query,
)


def test_filter_candidate_urls_removes_social_and_keeps_articles():
    results = [
        {"title": "Video Youtube", "url": "https://www.youtube.com/watch?v=neYWiV7Q4ZM"},
        {"title": "Facebook Post", "url": "https://facebook.com/groups/chungkhoan"},
        {"title": "Vietstock News", "url": "https://vietstock.vn/2026/10/nhan-dinh-thi-truong-12345.htm"},
        {"title": "VnEconomy Report", "url": "https://vneconomy.vn/chung-khoan-tuan-qua-but-pha.htm"},
        {"title": "TikTok", "url": "https://tiktok.com/@investor/video/1"},
    ]
    candidates = filter_candidate_urls(results, max_urls=2)
    assert len(candidates) == 2
    assert "vietstock.vn" in candidates[0]
    assert "vneconomy.vn" in candidates[1]
    assert not any("youtube" in u for u in candidates)
    assert not any("facebook" in u for u in candidates)


def test_simplify_verbose_query():
    raw_query = "hãy phân tích thị trường chứng khoán việt nam tuần qua chỉ số vn-index nguồn tin cậy"
    simplified = simplify_verbose_query(raw_query)
    assert "hãy phân tích" not in simplified.lower()
    assert "nguồn tin cậy" not in simplified.lower()
    assert "thị trường chứng khoán" in simplified
    assert "vn-index" in simplified


@pytest.mark.asyncio
async def test_in_flight_chain_triggers_deep_read_on_search_urls():
    # Giả lập Gateway
    gateway = MagicMock()
    task_id = "test_mission_inflight_01"
    trace_id = "trace_inflight_01"

    # Turn 0: Search Web trả về 1 URL Vietstock
    search_resp = MagicMock()
    search_resp.tool_executed = True
    search_resp.outcome = "ALLOW"
    search_resp.result = {
        "status": "success",
        "results": [
            {
                "title": "Báo cáo thị trường tuần qua",
                "url": "https://vietstock.vn/2026/10/tong-ket-tuan-1310.htm",
                "snippet": "VN-Index tăng 12 điểm...",
            }
        ],
    }

    # Turn 1: read_url_content trả về bài viết chi tiết
    read_resp = MagicMock()
    read_resp.tool_executed = True
    read_resp.outcome = "ALLOW"
    read_resp.result = "Toàn văn bài phân tích: Thanh khoản toàn thị trường đạt 50.5 nghìn tỷ, nhóm ngân hàng dẫn dắt."

    async def mock_execute_tool(req, tid):
        if req.tool_name == "SEARCH_WEB_GLOBAL":
            return search_resp
        elif req.tool_name == "read_url_content":
            return read_resp
        return MagicMock()

    gateway.execute_tool = AsyncMock(side_effect=mock_execute_tool)

    req = MagicMock()
    req.tool_name = "SEARCH_WEB_GLOBAL"
    req.tool_args = {"query": "thị trường chứng khoán tuần qua"}

    executor = InFlightChainExecutor(InFlightChainConfig(max_micro_turns=2, auto_read_top_urls=True))
    is_success, final_out, history = await executor.execute_step_with_chain(
        gateway=gateway,
        primary_request=req,
        task_id=task_id,
        trace_id=trace_id,
    )

    assert is_success is True
    assert len(history) == 2  # Turn 0 (search) + Turn 1 (read_url_content)
    assert history[0]["action"] == "SEARCH_WEB_GLOBAL"
    assert history[1]["action"] == "read_url_content"
    assert "DỮ LIỆU ĐỌC SÂU TOÀN VĂN" in str(final_out)
    assert "Thanh khoản toàn thị trường đạt 50.5 nghìn tỷ" in str(final_out)

    # Thẩm tra sự kiện đã được ghi vào event_store
    events = event_store.get_events_for_aggregate(task_id)
    assert any(e.event_type == "IN_FLIGHT_CHAIN_STARTED" for e in events)
    assert any(e.event_type == "IN_FLIGHT_CHAIN_COMPLETED" for e in events)


@pytest.mark.asyncio
async def test_in_flight_chain_simplifies_and_retries_on_empty_search():
    gateway = MagicMock()
    task_id = "test_mission_inflight_retry"
    trace_id = "trace_inflight_retry"

    # Turn 0: Câu hỏi quá dài -> trả về unavailable
    resp_empty = MagicMock()
    resp_empty.tool_executed = False
    resp_empty.outcome = "ALLOW"
    resp_empty.result = {"status": "unavailable", "results": []}

    # Turn 1: Thử lại câu hỏi rút gọn -> trả về thành công
    resp_success = MagicMock()
    resp_success.tool_executed = True
    resp_success.outcome = "ALLOW"
    resp_success.result = {
        "status": "success",
        "results": [{"title": "Thị trường khởi sắc", "url": "https://vneconomy.vn/tt-khoi-sac.htm"}],
    }

    call_count = 0

    async def mock_execute(req, tid):
        nonlocal call_count
        call_count += 1
        if call_count == 1:
            return resp_empty
        return resp_success

    gateway.execute_tool = AsyncMock(side_effect=mock_execute)

    req = MagicMock()
    req.tool_name = "SEARCH_WEB_GLOBAL"
    req.tool_args = {"query": "hãy phân tích thị trường chứng khoán việt nam tuần qua nguồn tin cậy"}

    executor = InFlightChainExecutor(InFlightChainConfig(max_micro_turns=2, auto_simplify_empty_query=True))
    is_success, final_out, history = await executor.execute_step_with_chain(
        gateway=gateway,
        primary_request=req,
        task_id=task_id,
        trace_id=trace_id,
    )

    assert is_success is True
    assert len(history) >= 2
    assert call_count >= 2
    assert "Thị trường khởi sắc" in str(final_out)
