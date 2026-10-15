# -*- coding: utf-8 -*-
"""
core/os/cognition/in_flight_chain.py
====================================
[Trọng điểm 1 - Hiện đại hóa Kiến trúc T4: Học hỏi OpenManus]
In-Flight Dynamic Tool Chain:
- Trao quyền cho Worker trong T4 thực hiện chuỗi phản xạ vi mô cục bộ (Micro-loops):
  `search_web` -> tự động phân tích URL uy tín -> gọi `read_url_content` -> hợp nhất dữ liệu sâu.
- Nếu truy vấn tìm kiếm ban đầu bị rỗng/thất bại do query quá dài hoặc chứa từ ngữ nhiễu,
  chuỗi vi mô tự động đơn giản hóa câu lệnh truy vấn (Query Simplification) và thử lại 1 lần.
- Đảm bảo ngân sách thời gian độc lập (Step Timeout Budget, mặc định tối đa 2 vòng lặp).
- Nếu không có URL đọc thêm hoặc sau 2 vòng lặp, trả về kết quả tốt nhất có được
  (kể cả PARTIAL) chứ không làm đứt gãy cả bước DAG.
- Ghi nhận đầy đủ sự kiện vào `CognitiveEventStore` để phục vụ quan sát (Observability).
"""

from __future__ import annotations

import asyncio
import json
import logging
import os
import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlparse

logger = logging.getLogger("JKAI.InFlightChain")


@dataclass
class InFlightChainConfig:
    max_micro_turns: int = 2
    timeout_budget: float = 30.0
    auto_read_top_urls: bool = True
    max_urls_to_read: int = 2
    auto_simplify_empty_query: bool = True
    enabled: bool = True

    @classmethod
    def from_env(cls) -> "InFlightChainConfig":
        enabled = os.getenv("JKAI_IN_FLIGHT_CHAIN_ENABLED", "1") != "0"
        max_turns = int(os.getenv("JKAI_IN_FLIGHT_MAX_TURNS", "2"))
        max_urls = int(os.getenv("JKAI_IN_FLIGHT_MAX_URLS", "2"))
        budget = float(os.getenv("JKAI_IN_FLIGHT_TIMEOUT_BUDGET", "30.0"))
        return cls(
            max_micro_turns=max_turns,
            timeout_budget=budget,
            auto_read_top_urls=True,
            max_urls_to_read=max_urls,
            auto_simplify_empty_query=True,
            enabled=enabled,
        )


DISALLOWED_DOMAINS_FOR_DEEP_READ = {
    "youtube.com",
    "youtu.be",
    "facebook.com",
    "fb.watch",
    "tiktok.com",
    "twitter.com",
    "x.com",
    "instagram.com",
    "pinterest.com",
    "reddit.com",
}


def filter_candidate_urls(
    results: Sequence[Dict[str, Any]],
    max_urls: int = 2,
) -> List[str]:
    """Lọc ra các URL bài viết chất lượng cao từ kết quả tìm kiếm, loại bỏ video/mạng xã hội."""
    candidates: List[str] = []
    seen_domains: set[str] = set()

    for item in results:
        if not isinstance(item, dict):
            continue
        raw_url = str(item.get("url") or item.get("link") or "").strip()
        if not raw_url.startswith(("http://", "https://")):
            continue

        parsed = urlparse(raw_url)
        domain = (parsed.hostname or "").lower()
        if not domain:
            continue

        # Bỏ qua mạng xã hội, video
        if any(d in domain for d in DISALLOWED_DOMAINS_FOR_DEEP_READ):
            continue

        # Bỏ qua domain gốc không có đường dẫn bài viết
        path = parsed.path.strip("/")
        if not path or len(path) < 3:
            continue

        if domain not in seen_domains:
            candidates.append(raw_url)
            seen_domains.add(domain)
            if len(candidates) >= max_urls:
                break

    return candidates


def simplify_verbose_query(query: str) -> str:
    """Loại bỏ từ ngữ chỉ thị / nhiễu để phục vụ tìm kiếm từ khóa chuẩn xác."""
    q = str(query or "").strip()
    noise_prefixes = [
        r"^hãy\s+phân\s+tích\s+",
        r"^phân\s+tích\s+",
        r"^tìm\s+kiếm\s+",
        r"^cho\s+tôi\s+biết\s+",
        r"^hãy\s+cho\s+biết\s+",
        r"^tổng\s+hợp\s+",
        r"^báo\s+cáo\s+",
    ]
    for pattern in noise_prefixes:
        q = re.sub(pattern, "", q, flags=re.IGNORECASE).strip()

    noise_suffixes = [
        r"\s+nguồn\s+tin\s+cậy.*$",
        r"\s+chi\s+tiết\s+nhất.*$",
        r"\s+mới\s+nhất\s+hôm\s+nay.*$",
    ]
    for pattern in noise_suffixes:
        q = re.sub(pattern, "", q, flags=re.IGNORECASE).strip()

    words = q.split()
    if len(words) > 16:
        q = " ".join(words[:16])
    return q.strip()


def _create_execution_request(trace_id: str, tool_name: str, tool_args: dict, timeout: int = 60) -> Any:
    try:
        from receptionist.executor_gateway import ExecutionRequest
        return ExecutionRequest(
            trace_id=trace_id,
            capability_token={},
            tool_name=tool_name,
            tool_args=tool_args,
            timeout=timeout,
        )
    except ModuleNotFoundError:
        try:
            import importlib
            mod = importlib.import_module("services.ai-brain.receptionist.executor_gateway")
            return mod.ExecutionRequest(
                trace_id=trace_id,
                capability_token={},
                tool_name=tool_name,
                tool_args=tool_args,
                timeout=timeout,
            )
        except Exception:
            pass

    from dataclasses import dataclass, field
    @dataclass
    class _FallbackExecutionRequest:
        trace_id: str
        capability_token: dict = field(default_factory=dict)
        tool_name: str = ""
        tool_args: dict = field(default_factory=dict)
        timeout: int = 60

    return _FallbackExecutionRequest(
        trace_id=trace_id,
        capability_token={},
        tool_name=tool_name,
        tool_args=tool_args,
        timeout=timeout,
    )


def extract_urls_from_text(text: str) -> List[str]:
    """Trích xuất danh sách HTTP/HTTPS URL từ văn bản trần hoặc markdown."""
    pattern = r'https?://[^\s<>"\')]+'
    found = re.findall(pattern, text or "")
    clean_urls = []
    for u in found:
        u = u.rstrip(".,;)]}")
        if u and u not in clean_urls:
            clean_urls.append(u)
    return clean_urls


class InFlightChainExecutor:
    """
    Điều phối chuỗi phản xạ vi mô cục bộ trong T4:
    - Nhận diện khi nào cần kích hoạt micro-turn đọc sâu hoặc thử lại truy vấn.
    - Duy trì an toàn bước: không vượt ngân sách timeout, không đệ quy vô hạn.
    """

    def __init__(self, config: Optional[InFlightChainConfig] = None):
        self.config = config or InFlightChainConfig.from_env()

    async def execute_step_with_chain(
        self,
        gateway: Any,
        primary_request: Any,
        task_id: str,
        trace_id: str,
        step_id: str = "step",
        step_timeout: int = 120,
        logger_emitter: Optional[Any] = None,
    ) -> Tuple[bool, Any, List[Dict[str, Any]]]:
        """
        Thực thi bước DAG qua Gateway với chuỗi vi mô In-Flight.
        Trả về: (is_success, final_output, micro_turns_history)
        """
        history: List[Dict[str, Any]] = []

        def _emit_log(msg: str, stealth: bool = False):
            if logger_emitter and callable(logger_emitter):
                try:
                    logger_emitter("EXECUTOR", msg, task_id, stealth=stealth)
                except Exception:
                    pass

        # 1. Thực thi công cụ chính (Turn 0)
        t0_res = await gateway.execute_tool(primary_request, task_id)
        is_success = getattr(t0_res, "tool_executed", True) if hasattr(t0_res, "tool_executed") else True
        raw_out = getattr(t0_res, "result", str(t0_res)) if hasattr(t0_res, "result") else str(t0_res)
        outcome_str = getattr(t0_res, "outcome", "ALLOW")
        if str(outcome_str).upper() in ["DENY", "DECISIONOUTCOME.DENY"]:
            is_success = False

        history.append({
            "turn": 0,
            "action": primary_request.tool_name,
            "args": primary_request.tool_args,
            "success": is_success,
        })

        if not self.config.enabled:
            return is_success, raw_out, history

        tool_norm = str(primary_request.tool_name or "").upper()
        is_search_tool = any(s in tool_norm for s in ("SEARCH", "WEB_SEARCH", "OMNI_SEARCH"))

        # Ghi nhận sự kiện vào CognitiveEventStore nếu có
        try:
            from core.os.cognition.event_model import event_store
            event_store.append(
                aggregate_id=task_id,
                event_type="IN_FLIGHT_CHAIN_STARTED",
                payload={"step_id": step_id, "primary_tool": primary_request.tool_name},
                correlation_id=trace_id,
            )
        except Exception:
            pass

        final_output = raw_out
        turns_used = 1

        # 2. Xử lý trường hợp Tìm kiếm Web
        if is_search_tool:
            # Phân tích kết quả đầu ra
            parsed_results: List[Dict[str, Any]] = []
            if isinstance(raw_out, dict):
                parsed_results = raw_out.get("results") or []
            elif isinstance(raw_out, str):
                # Thử bóc tách JSON hoặc trích xuất URLs từ text
                try:
                    loaded = json.loads(raw_out)
                    if isinstance(loaded, dict):
                        parsed_results = loaded.get("results") or []
                except Exception:
                    pass

            # A. KỊCH BẢN 1: Tìm kiếm thành công nhưng chỉ có trích đoạn ngắn -> Tự động Đọc sâu URLs
            if is_success and self.config.auto_read_top_urls and turns_used <= self.config.max_micro_turns:
                candidate_urls = filter_candidate_urls(parsed_results, max_urls=self.config.max_urls_to_read)
                if not candidate_urls and isinstance(raw_out, str):
                    extracted = extract_urls_from_text(raw_out)
                    candidate_urls = filter_candidate_urls([{"url": u} for u in extracted], max_urls=self.config.max_urls_to_read)

                if candidate_urls:
                    deep_read_texts = []
                    _emit_log(f"⚡ [IN-FLIGHT-CHAIN] Đã phát hiện {len(candidate_urls)} nguồn uy tín. Đang tự động đọc sâu nội dung toàn văn...")
                    
                    for target_url in candidate_urls:
                        if turns_used > self.config.max_micro_turns:
                            break
                        read_req = _create_execution_request(
                            trace_id=trace_id,
                            tool_name="read_url_content",
                            tool_args={"url": target_url},
                            timeout=min(15, step_timeout),
                        )
                        try:
                            read_res = await gateway.execute_tool(read_req, task_id)
                            r_out = getattr(read_res, "result", str(read_res)) if hasattr(read_res, "result") else str(read_res)
                            r_succ = getattr(read_res, "tool_executed", True) if hasattr(read_res, "tool_executed") else True

                            history.append({
                                "turn": turns_used,
                                "action": "read_url_content",
                                "args": {"url": target_url},
                                "success": r_succ,
                            })
                            turns_used += 1

                            if r_succ and r_out:
                                deep_read_texts.append(f"### [DỮ LIỆU ĐỌC SÂU TOÀN VĂN] Nguồn: {target_url}\n{str(r_out).strip()}")
                        except Exception as read_err:
                            logger.warning("[IN-FLIGHT-CHAIN] Lỗi đọc sâu URL %s: %s", target_url, read_err)

                    if deep_read_texts:
                        final_output = f"{final_output}\n\n" + "\n\n".join(deep_read_texts)
                        _emit_log(f"✅ [IN-FLIGHT-CHAIN] Hoàn tất trích xuất dữ liệu sâu từ {len(deep_read_texts)} bài viết.")

            # B. KỊCH BẢN 2: Tìm kiếm thất bại / rỗng do câu hỏi rườm rà -> Tự động Tối ưu hóa truy vấn (Query Simplification)
            elif (not is_success or "no_results" in str(raw_out).lower() or "unavailable" in str(raw_out).lower()) and self.config.auto_simplify_empty_query and turns_used <= self.config.max_micro_turns:
                orig_query = primary_request.tool_args.get("query") or primary_request.tool_args.get("q") or ""
                simplified = simplify_verbose_query(orig_query)
                if simplified and simplified.lower() != str(orig_query).lower():
                    _emit_log(f"🔄 [IN-FLIGHT-CHAIN] Truy vấn ban đầu không có kết quả. Đang thử lại với từ khóa tinh gọn: '{simplified}'...")
                    new_args = dict(primary_request.tool_args)
                    new_args["query"] = simplified
                    retry_req = _create_execution_request(
                        trace_id=trace_id,
                        tool_name=primary_request.tool_name,
                        tool_args=new_args,
                        timeout=step_timeout,
                    )
                    try:
                        retry_res = await gateway.execute_tool(retry_req, task_id)
                        r_succ = getattr(retry_res, "tool_executed", True) if hasattr(retry_res, "tool_executed") else True
                        r_out = getattr(retry_res, "result", str(retry_res)) if hasattr(retry_res, "result") else str(retry_res)

                        history.append({
                            "turn": turns_used,
                            "action": primary_request.tool_name,
                            "args": new_args,
                            "success": r_succ,
                        })
                        turns_used += 1

                        if r_succ:
                            is_success = True
                            final_output = r_out
                            _emit_log("✅ [IN-FLIGHT-CHAIN] Thử lại thành công, đã thu thập được dữ liệu.")
                    except Exception as retry_err:
                        logger.warning("[IN-FLIGHT-CHAIN] Lỗi thử lại truy vấn tinh gọn: %s", retry_err)

        # Ghi nhận hoàn tất vào CognitiveEventStore
        try:
            from core.os.cognition.event_model import event_store
            event_store.append(
                aggregate_id=task_id,
                event_type="IN_FLIGHT_CHAIN_COMPLETED",
                payload={
                    "step_id": step_id,
                    "micro_turns_count": len(history),
                    "is_success": is_success,
                },
                correlation_id=trace_id,
            )
        except Exception:
            pass

        return is_success, final_output, history


# Singleton instance
in_flight_chain_executor = InFlightChainExecutor()
