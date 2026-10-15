# -*- coding: utf-8 -*-
"""
tests/test_multi_query_retriever.py
====================================
Kiểm thử chuyên biệt cho Trọng điểm 2: Multi-Query Deep Retrieval (Học hỏi Perplexica & Khoj):
1. Phân loại Domain (Finance, Tech, News, General).
2. Phân tách câu hỏi thành 3 sub-queries chuyên biệt (Aspect-based decomposition).
3. Chuẩn hóa URL (canonicalization, xóa utm/tracking parameters).
4. Khử trùng lặp và xếp hạng trọng số xuất hiện chéo (Cross-query frequency ranking).
5. Tích hợp sâu StreamBufferStore khi kết quả tổng hợp lớn (stream_id).
6. Ghi nhận sự kiện cấu trúc vào CognitiveEventStore.
7. Minh bạch từ chối khi chạy local_only hoặc mất kết nối.
"""

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from core.os.cognition.event_model import event_store
from core.os.cognition.multi_query_retriever import (
    MultiQueryConfig,
    MultiQueryRetriever,
    QueryDomain,
    canonicalize_url,
    classify_query_domain,
    decompose_query,
    deduplicate_and_rank_results,
)


def test_classify_query_domain():
    assert classify_query_domain("phân tích thị trường chứng khoán vnindex tuần qua") == QueryDomain.FINANCE_STOCK
    assert classify_query_domain("tìm hiểu kiến trúc microkernel os docker linux") == QueryDomain.TECH_SOFTWARE
    assert classify_query_domain("tin tức thời sự hôm nay có bão lớn") == QueryDomain.NEWS_CURRENT
    assert classify_query_domain("cách làm bánh mì ngon") == QueryDomain.GENERAL


def test_decompose_query_generates_three_distinct_aspects():
    q = "hãy phân tích thị trường chứng khoán tuần qua nguồn tin cậy"
    subs = decompose_query(q)
    assert len(subs) == 3
    # Không còn chứa từ ngữ chỉ thị rườm rà
    assert not any("hãy phân tích" in s.lower() for s in subs)
    assert not any("nguồn tin cậy" in s.lower() for s in subs)
    # Bao phủ 3 góc nhìn
    assert any("vn-index" in s.lower() or "thanh khoản" in s.lower() for s in subs)
    assert any("khối ngoại" in s.lower() or "tự doanh" in s.lower() for s in subs)
    assert any("nhóm ngành" in s.lower() or "cổ phiếu" in s.lower() for s in subs)


def test_canonicalize_url():
    raw_1 = "https://vietstock.vn/2026/10/nhan-dinh-123.htm?utm_source=facebook&utm_medium=cpc&ref=123"
    canon_1 = canonicalize_url(raw_1)
    assert canon_1 == "https://vietstock.vn/2026/10/nhan-dinh-123.htm"

    raw_2 = "https://VnEconomy.vn/tin-tuc/index.html/?utm_campaign=winter#top"
    canon_2 = canonicalize_url(raw_2)
    assert canon_2 == "https://vneconomy.vn/tin-tuc/index.html"


def test_deduplicate_and_rank_results():
    sub_results = [
        (
            "subquery_1",
            [
                {"title": "Bài A", "url": "https://vietstock.vn/bai-a.htm?utm_source=news", "snippet": "Đoạn 1"},
                {"title": "Bài B", "url": "https://cafef.vn/bai-b.htm", "snippet": "Đoạn B1"},
            ],
        ),
        (
            "subquery_2",
            [
                # Bài A xuất hiện lần 2 với URL khác param tracking
                {"title": "Bài A chi tiết", "url": "https://vietstock.vn/bai-a.htm?ref=social", "snippet": "Đoạn 1 mở rộng rất dài"},
                {"title": "Bài C", "url": "https://vneconomy.vn/bai-c.htm", "snippet": "Đoạn C"},
            ],
        ),
    ]

    deduped = deduplicate_and_rank_results(sub_results)
    # Phải khử trùng lặp Bài A (chỉ còn 3 bài duy nhất A, B, C)
    assert len(deduped) == 3
    # Bài A xuất hiện ở cả 2 sub-queries nên có rank_score cao nhất
    assert deduped[0]["canonical_url"] == "https://vietstock.vn/bai-a.htm"
    assert len(deduped[0]["matched_subqueries"]) == 2
    assert "rất dài" in deduped[0]["snippet"]


@pytest.mark.asyncio
async def test_multi_query_retriever_full_flow():
    task_id = "test_mission_mq_full"
    trace_id = "trace_mq_full"
    query = "phân tích thị trường chứng khoán tuần qua"

    # Giả lập kết quả tìm kiếm cho các sub-queries
    fake_search_res = {
        "status": "success",
        "results": [
            {
                "title": "Báo cáo thị trường tuần 13/10",
                "url": "https://vietstock.vn/2026/10/bao-cao-tuan-1310.htm",
                "snippet": "VN-Index vượt cản 1300 điểm với thanh khoản lớn...",
                "source": "tavily",
            },
            {
                "title": "Dòng tiền ngoại gom mạnh cổ phiếu",
                "url": "https://vneconomy.vn/dong-tien-ngoai-gom-hang.htm",
                "snippet": "Khối ngoại mua ròng 1.500 tỷ đồng tập trung nhóm ngân hàng...",
                "source": "tavily",
            },
        ],
    }

    retriever = MultiQueryRetriever(
        MultiQueryConfig(
            max_subqueries=3,
            results_per_subquery=2,
            max_deep_reads=2,
        )
    )

    with patch("tools.web_search.execute_real_web_search_sync", return_value=fake_search_res):
        res = await retriever.retrieve_deep(
            query=query,
            task_id=task_id,
            trace_id=trace_id,
        )

    assert res["status"] == "success"
    assert res["is_simulated"] is False
    assert len(res["sub_queries"]) == 3
    assert res["total_sources_found"] >= 2
    assert "vietstock.vn" in str(res["results"])
    assert "Báo cáo Dữ liệu Đa Chiều" in res["output"]

    # Kiểm tra sự kiện lưu trữ
    events = event_store.get_events_for_aggregate(task_id)
    assert any(e.event_type == "MULTI_QUERY_RETRIEVAL_STARTED" for e in events)
    assert any(e.event_type == "MULTI_QUERY_RETRIEVAL_COMPLETED" for e in events)


@pytest.mark.asyncio
async def test_multi_query_retriever_refuses_honestly_when_no_data():
    task_id = "test_mission_mq_empty"
    retriever = MultiQueryRetriever()

    with patch("tools.web_search.execute_real_web_search_sync", return_value={"status": "unavailable", "results": []}):
        res = await retriever.retrieve_deep(
            query="câu hỏi không có mạng",
            task_id=task_id,
        )

    assert res["status"] == "unavailable"
    assert res["is_simulated"] is False
    assert res["reason"] == "SEARCH_PROVIDERS_UNREACHABLE"


@pytest.mark.asyncio
async def test_multi_query_retriever_ssrf_protection():
    task_id = "test_mission_mq_ssrf"
    retriever = MultiQueryRetriever()

    # Search returns loopback / metadata URL
    fake_ssrf_res = {
        "status": "success",
        "results": [
            {"title": "Metadata", "url": "http://169.254.169.254/latest/meta-data/", "snippet": "AWS keys"},
            {"title": "Localhost", "url": "http://127.0.0.1:8000/internal", "snippet": "Local"},
        ],
    }

    with patch("tools.web_search.execute_real_web_search_sync", return_value=fake_ssrf_res):
        res = await retriever.retrieve_deep(
            query="câu hỏi ssrf",
            task_id=task_id,
        )

    assert res["status"] == "success"
    # Cả 2 URL private đều phải bị chặn, không có deep read nào được thực hiện
    assert res["deep_reads_count"] == 0
