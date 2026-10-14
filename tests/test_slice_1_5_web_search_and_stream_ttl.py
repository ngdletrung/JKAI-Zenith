# -*- coding: utf-8 -*-
"""
tests/test_slice_1_5_web_search_and_stream_ttl.py
=================================================
Kiểm thử nghiệm thu độc lập cho Slice 1.5:
1. Xóa bỏ hoàn toàn `"Fake search result"` trong `tools/web_search.py` và kênh bịa URL
   `https://cloud-llm-search.internal` trong `OMNI_SEARCH_ENGINE/logic.py`.
2. Cơ chế từ chối minh bạch (`status="unavailable"`, `is_simulated=False`,
   `reason="LOCAL_ONLY_MODE" | "SEARCH_PROVIDERS_UNREACHABLE"`) khi chạy Local-Only hoặc mất kết nối.
3. Khi có dữ liệu Web Search / `read_url_content` lớn: bảo toàn trích dẫn nguồn
   (`url`, `title`, `snippet`, `retrieved_at`) và tự động lưu luồng lớn vào `StreamBufferStore`
   (thay thế cắt cụt `resp.text[:5000]` trong `read_url_content`).
4. Đóng 2 điều kiện mở rộng Lượt 268 của OpenCode:
   - `TTL` thực + `evict_mission(mission_id)` trong `StreamBufferStore`.
   - Tìm kiếm tiếng Việt không dấu (accent-insensitive matching) trong `search_in_stream`.
"""

from __future__ import annotations

import asyncio
from unittest.mock import AsyncMock, MagicMock, patch

from core.utils.stream_buffer_store import (
    StreamBufferStore,
    read_stream_window,
    search_in_stream,
    store_stream,
)
from intelligence.skills.DEVOPS.SYSTEM_CORE_EXECUTOR import logic as core_logic
import tools.web_search as legacy_web_search


def test_tools_web_search_never_returns_fake_search_result_and_refuses_transparently_in_local_only():
    """
    [Slice 1.5 - Điểm 1 & 2.A THAM KHẢO]:
    `tools/web_search.py` tuyệt đối không được trả `"Fake search result for: ..."`.
    Khi ở chế độ `local_only=True` (hoặc `JKAI_LOCAL_ONLY=1`), phải trả về từ chối minh bạch:
    `status="unavailable"`, `is_simulated=False`, `reason="LOCAL_ONLY_MODE"`, `error` rõ ràng.
    """
    res = legacy_web_search.run({"query": "CVE-2026-99999 kernel exploit", "local_only": True})
    assert "Fake search result" not in str(res)
    assert res.get("status") == "unavailable"
    assert res.get("is_simulated") is False
    assert res.get("reason") == "LOCAL_ONLY_MODE"
    assert res.get("output") is None
    assert res.get("error") is not None


def test_logic_search_web_and_read_url_content_transparent_local_only_and_stream_buffering():
    """
    [Slice 1.5 - Tích hợp SYSTEM_CORE_EXECUTOR & StreamBufferStore]:
    - `core_logic.search_web` ở chế độ `local_only=True` phải trả từ chối minh bạch (`status="unavailable"`).
    - `core_logic.read_url_content` không được cắt cụt mù quáng `resp.text[:5000]`;
      khi trang web dài > 5000 ký tự, phải lưu toàn văn vào `StreamBufferStore` kèm `stream_id`
      để đọc tiếp phần cuối bằng `read_stream_window`.
    """
    refusal = asyncio.run(
        core_logic.search_web(
            query="Python 3.14 release notes",
            task_id="test_s15_local",
            local_only=True,
        )
    )
    assert refusal.get("status") == "unavailable"
    assert refusal.get("is_simulated") is False
    assert refusal.get("reason") == "LOCAL_ONLY_MODE"

    # Kiểm tra read_url_content với nội dung 220 dòng (> 10.000 ký tự), dòng 215 chứa dữ liệu quan trọng
    long_lines = [
        f"Line {i:03d}: Documentation paragraph for section {i} with detailed technical specification."
        for i in range(1, 221)
    ]
    long_lines[214] = "Line 215: CRITICAL_URL_FACT=MAX_CONCURRENT_WORKERS_64"
    full_page_text = "\n".join(long_lines)
    assert len(full_page_text) > 10000

    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.text = full_page_text

    mock_client_instance = AsyncMock()
    mock_client_instance.get = AsyncMock(return_value=mock_resp)
    mock_client_ctx = AsyncMock()
    mock_client_ctx.__aenter__.return_value = mock_client_instance
    mock_client_ctx.__aexit__.return_value = False

    with patch("httpx.AsyncClient", return_value=mock_client_ctx):
        url_res = asyncio.run(
            core_logic.read_url_content(
                url="https://docs.example.com/spec",
                task_id="test_s15_url",
            )
        )

    assert url_res.get("status") == "success"
    assert url_res.get("stream_id") is not None
    sid = url_res["stream_id"]
    win = read_stream_window(stream_id=sid, start_line=210, end_line=220)
    assert win["status"] == "success"
    assert "[L215] Line 215: CRITICAL_URL_FACT=MAX_CONCURRENT_WORKERS_64" in win["content"]


def test_stream_buffer_store_ttl_expiration_and_mission_id_eviction():
    """
    [Slice 1.5 - Điều kiện mở rộng 1 của OpenCode Lượt 268]:
    - Hỗ trợ `ttl_seconds` thực tế: khi mục lưu trữ quá hạn TTL, `get()` tự động thu hồi
      và `purge_expired()` trả về số lượng luồng đã dọn.
    - Hỗ trợ `evict_mission(mission_id)`: xóa toàn bộ các `stream_id` thuộc một `mission_id` / `task_id`
      mà không ảnh hưởng tới các `mission_id` khác đang hoạt động.
    """
    store = StreamBufferStore(max_entries=32, default_ttl_seconds=60.0)

    m1_a = store.put("Mission 1 stream A\nLine 2", source_tool="search_web", task_id="mission_alpha", mission_id="mission_alpha")
    m1_b = store.put("Mission 1 stream B\nLine 2", source_tool="read_url_content", task_id="mission_alpha", mission_id="mission_alpha")
    m2_a = store.put("Mission 2 stream A\nLine 2", source_tool="run_command", task_id="mission_beta", mission_id="mission_beta")

    # Xóa theo mission_id='mission_alpha'
    evicted_count = store.evict_mission("mission_alpha")
    assert evicted_count == 2
    assert store.get(m1_a["stream_id"]) is None
    assert store.get(m1_b["stream_id"]) is None
    assert store.get(m2_a["stream_id"]) is not None

    # Kiểm tra TTL hết hạn
    short_ttl_env = store.put(
        "Ephemeral web search result",
        source_tool="search_web",
        task_id="mission_ttl",
        ttl_seconds=5.0,
    )
    sid_ttl = short_ttl_env["stream_id"]
    entry = store.get(sid_ttl)
    assert entry is not None

    # Giả lập thời gian trôi qua 10 giây (> ttl_seconds=5.0)
    entry.created_at -= 10.0
    purged = store.purge_expired()
    assert purged == 1
    assert store.get(sid_ttl) is None


def test_search_in_stream_vietnamese_accent_insensitive_matching():
    """
    [Slice 1.5 - Điều kiện mở rộng 2 của OpenCode Lượt 268]:
    `search_in_stream` phải hỗ trợ tìm kiếm tiếng Việt không dấu (accent-insensitive matching)
    khớp chính xác vào văn bản tiếng Việt có dấu (bao gồm chữ Đ/đ), đồng thời giữ nguyên
    tọa độ dòng `[L{line_no}]` và cập nhật `retrieved_spans` / `read_spans`.
    """
    vn_lines = [
        f"Dòng {i:03d}: Nhật ký hệ thống hoạt động bình thường."
        for i in range(1, 101)
    ]
    vn_lines[41] = "Dòng 042: CẢNH BÁO ĐẶC BIỆT - Kết nối cơ sở dữ liệu đồ thị bị ngắt đột ngột tại tầng điều phối!"
    vn_lines[87] = "Dòng 088: Khôi phục đường truyền đồng bộ thành công sau 150ms."

    env = store_stream(
        content="\n".join(vn_lines),
        source_tool="search_web",
        task_id="test_vn_accent",
        preview_chars=300,
    )
    sid = env["stream_id"]

    # Tìm bằng chuỗi tiếng Việt KHÔNG DẤU có chứa chữ d/đ
    hit_unaccented = search_in_stream(
        stream_id=sid,
        query="ket noi co so du lieu do thi bi ngat dot ngot tai tang dieu phoi",
        context_lines=1,
    )
    assert hit_unaccented["status"] == "success"
    assert hit_unaccented["total_matches"] == 1
    assert hit_unaccented["matches"][0]["line"] == 42
    assert "[L42] Dòng 042: CẢNH BÁO ĐẶC BIỆT" in hit_unaccented["content"]

    # Tìm tiếp câu có chữ "đường truyền đồng bộ" bằng truy vấn không dấu "duong truyen dong bo"
    hit_d_bar = search_in_stream(
        stream_id=sid,
        query="duong truyen dong bo thanh cong",
        context_lines=1,
    )
    assert hit_d_bar["status"] == "success"
    assert hit_d_bar["total_matches"] == 1
    assert hit_d_bar["matches"][0]["line"] == 88


def test_omni_search_no_fake_cloud_llm_and_web_search_cited_stream_buffering(monkeypatch):
    """
    [Slice 1.5 - Kiểm chứng xóa tận gốc _search_cloud_llm / cloud-llm-search.internal & luồng trích dẫn tìm kiếm lớn]:
    1. Khẳng định mã nguồn `OMNI_SEARCH_ENGINE/logic.py` và `tools/web_search.py` đã xóa vĩnh viễn
       phương thức `_search_cloud_llm`, chuỗi `cloud-llm-search.internal` và `"Fake search result for:"`.
    2. Khi các kênh tìm kiếm thật (Tavily/DDG/Browser) đều rỗng/lỗi, `OmniSearchEngine.omni_search`
       phải trả `status="unavailable"`, `is_simulated=False`, `reason="SEARCH_PROVIDERS_UNREACHABLE"`.
    3. Khi `tools.web_search.run` nhận kết quả thật vượt ngưỡng `preview_chars`,
       phải bảo toàn trích dẫn nguồn (`URL:`, `Thời điểm truy xuất (UTC):`) và lưu toàn văn vào `StreamBufferStore`.
    """
    from pathlib import Path
    from intelligence.skills.CORE.OMNI_SEARCH_ENGINE import logic as omni_mod
    from intelligence.skills.CORE.OMNI_SEARCH_ENGINE.logic import OmniSearchEngine

    omni_src = Path(omni_mod.__file__).read_text(encoding="utf-8")
    web_search_src = Path(legacy_web_search.__file__).read_text(encoding="utf-8")
    assert not hasattr(OmniSearchEngine, "_search_cloud_llm")
    assert "_search_cloud_llm" not in omni_src
    assert "cloud-llm-search.internal" not in omni_src
    assert "Fake search result for:" not in web_search_src

    engine_inst = OmniSearchEngine()
    engine_inst.tavily_api_key = ""
    monkeypatch.setattr(engine_inst, "_search_ddg", AsyncMock(return_value=[]))
    monkeypatch.setattr(engine_inst, "_search_browse", AsyncMock(side_effect=RuntimeError("browser offline")))

    omni_res = asyncio.run(
        engine_inst.omni_search(
            query="Zero-day exploit 2026-XYZ-nonexistent",
            mode="fast",
            bypass_cache=True,
        )
    )
    assert omni_res.get("status") == "unavailable"
    assert omni_res.get("is_simulated") is False
    assert omni_res.get("reason") == "SEARCH_PROVIDERS_UNREACHABLE"
    assert "cloud-llm-search.internal" not in str(omni_res)

    # Kiểm tra tools.web_search.run với kết quả thực tế có trích dẫn vượt ngưỡng preview_chars
    monkeypatch.setenv("TAVILY_API_KEY", "tvly-test-key")
    fake_tavily_results = [
        {
            "title": f"Báo cáo kỹ thuật phân hệ số {idx}",
            "url": f"https://research.example.org/paper-{idx}",
            "content": (
                f"Tài liệu kỹ thuật chi tiết chương {idx}. "
                + ("Kiến trúc đồng bộ hóa trạng thái phân tán tốc độ cao. " * 15)
                + ("Mật mã kiểm chứng cuối trang: ZETA_OMEGA_991." if idx == 5 else "")
            ),
        }
        for idx in range(1, 6)
    ]
    mock_http_resp = MagicMock()
    mock_http_resp.status_code = 200
    mock_http_resp.json.return_value = {"results": fake_tavily_results}

    mock_http_client = MagicMock()
    mock_http_client.__enter__.return_value.post.return_value = mock_http_resp
    mock_http_client.__exit__.return_value = False

    with patch("httpx.Client", return_value=mock_http_client):
        ws_res = legacy_web_search.run(
            {
                "query": "Kiến trúc đồng bộ hóa trạng thái phân tán",
                "task_id": "mission_ws_stream",
                "mission_id": "mission_ws_stream",
                "preview_chars": 600,
                "local_only": False,
            }
        )

    assert ws_res["status"] == "success"
    assert ws_res["is_simulated"] is False
    assert len(ws_res["results"]) == 5
    assert ws_res.get("stream_id") is not None
    assert "STREAM_BUFFERED" in ws_res["output"]

    # Dùng search_in_stream không dấu tiếng Việt để tìm đoạn cuối của kết quả thứ 5
    stream_hit = search_in_stream(
        stream_id=ws_res["stream_id"],
        query="mat ma kiem chung cuoi trang: ZETA_OMEGA_991",
        context_lines=2,
    )
    assert stream_hit["status"] == "success"
    assert stream_hit["total_matches"] == 1
    assert "https://research.example.org/paper-5" in stream_hit["content"]

