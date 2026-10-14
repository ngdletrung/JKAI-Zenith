# -*- coding: utf-8 -*-
"""
core/utils/stream_buffer_store.py
=================================
Đại Trụ I (Slice 1.4): StreamBufferStore — Lưu Trữ Luồng Lớn, Phân Trang Cửa Sổ,
Tìm Kiếm Có Mục Tiêu & Kiểm Soát Độ Bao Phủ Bằng Chứng (Coverage Ledger).

Thiết kế đáp ứng đầy đủ Điểm B & Mục 3 trong tài liệu THAM KHẢO của Master & OpenCode:
1. Không cắt cụt đầu ra mù quáng (`[:16384]`, `[:12000]`, `[:300]...[-300:]`):
   Mọi đầu ra vượt ngưỡng đều được gán `stream_id` bất biến (băm SHA-256) và giữ nguyên 100% dòng gốc.
2. Truy xuất có mục tiêu (`search_in_stream`) & Phân trang cửa sổ (`read_stream_window`):
   Mỗi dòng trả về đều gắn nhãn tọa độ `[L{line_no}]` để bảo toàn 100% trích dẫn nguồn.
3. Kiểm soát độ bao phủ (`Coverage Ledger`):
   Theo dõi chính xác `retrieved_spans`, `read_spans`, `unread_spans` và `line_coverage_ratio`.
4. Kiểm tra kết quả trên 5 chỉ số độc lập (`get_stream_coverage_report`):
   Tách biệt rõ `Citation Accuracy` và `Evidence Coverage` qua `evaluate_stream_5_metrics()`.
"""

from __future__ import annotations

import hashlib
import re
import time
import unicodedata
from collections import OrderedDict
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from core.utils.repo_map import evaluate_stream_5_metrics


def fold_vietnamese_accents(text: str) -> str:
    """
    Chuẩn hóa chuỗi tiếng Việt có dấu thành không dấu (bao gồm Đ/đ -> D/d)
    để hỗ trợ tìm kiếm không dấu (accent-insensitive search) trong `search_in_stream`.
    """
    if not text:
        return ""
    s = str(text).replace("đ", "d").replace("Đ", "D")
    nfd = unicodedata.normalize("NFD", s)
    return "".join(ch for ch in nfd if unicodedata.category(ch) != "Mn")


def _merge_spans(spans: Sequence[Tuple[int, int]]) -> List[Tuple[int, int]]:
    valid = [
        (min(int(a), int(b)), max(int(a), int(b)))
        for a, b in spans
        if int(a) > 0 and int(b) > 0
    ]
    if not valid:
        return []
    valid.sort(key=lambda x: (x[0], x[1]))
    merged: List[Tuple[int, int]] = [valid[0]]
    for s, e in valid[1:]:
        prev_s, prev_e = merged[-1]
        if s <= prev_e + 1:
            merged[-1] = (prev_s, max(prev_e, e))
        else:
            merged.append((s, e))
    return merged


def _compute_unread_spans(total_lines: int, merged_read: Sequence[Tuple[int, int]]) -> List[Tuple[int, int]]:
    if total_lines <= 0:
        return []
    if not merged_read:
        return [(1, total_lines)]
    unread: List[Tuple[int, int]] = []
    cursor = 1
    for s, e in merged_read:
        if s > cursor:
            unread.append((cursor, min(total_lines, s - 1)))
        cursor = max(cursor, e + 1)
    if cursor <= total_lines:
        unread.append((cursor, total_lines))
    return unread


def _compute_line_coverage_ratio(total_lines: int, merged_read: Sequence[Tuple[int, int]]) -> float:
    if total_lines <= 0:
        return 1.0
    covered_lines = sum(max(0, min(total_lines, e) - max(1, s) + 1) for s, e in merged_read)
    return round(min(1.0, covered_lines / total_lines), 4)


@dataclass
class StreamEntry:
    stream_id: str
    task_id: str
    source_tool: str
    sha256: str
    total_bytes: int
    total_lines: int
    lines: List[str]
    mission_id: str = "sys"
    ttl_seconds: float = 1800.0
    created_at: float = field(default_factory=time.time)
    retrieved_spans: List[Tuple[int, int]] = field(default_factory=list)
    read_spans: List[Tuple[int, int]] = field(default_factory=list)
    search_queries: List[str] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def is_expired(self, now: Optional[float] = None) -> bool:
        if self.ttl_seconds <= 0:
            return False
        curr = time.time() if now is None else float(now)
        return (curr - self.created_at) >= self.ttl_seconds

    def record_retrieved(self, start_line: int, end_line: int) -> None:
        if self.total_lines <= 0:
            return
        s = max(1, min(self.total_lines, int(start_line)))
        e = max(s, min(self.total_lines, int(end_line)))
        self.retrieved_spans = _merge_spans([*self.retrieved_spans, (s, e)])

    def record_read(self, start_line: int, end_line: int) -> None:
        if self.total_lines <= 0:
            return
        s = max(1, min(self.total_lines, int(start_line)))
        e = max(s, min(self.total_lines, int(end_line)))
        self.read_spans = _merge_spans([*self.read_spans, (s, e)])
        self.record_retrieved(s, e)


class StreamBufferStore:
    """Kho lưu trữ luồng dữ liệu lớn có kiểm soát độ bao phủ (Bounded LRU 256 + TTL + Mission Eviction)."""

    def __init__(self, max_entries: int = 256, default_ttl_seconds: float = 1800.0) -> None:
        self.max_entries = max_entries
        self.default_ttl_seconds = float(default_ttl_seconds)
        self._store: OrderedDict[str, StreamEntry] = OrderedDict()

    def purge_expired(self, now: Optional[float] = None) -> int:
        """Dọn dẹp toàn bộ các `stream_id` đã hết hạn TTL và trả về số lượng luồng đã xóa."""
        curr = time.time() if now is None else float(now)
        expired_ids = [
            sid for sid, entry in self._store.items()
            if entry.is_expired(curr)
        ]
        for sid in expired_ids:
            self._store.pop(sid, None)
        return len(expired_ids)

    def evict_mission(self, mission_id: str) -> int:
        """Xóa chủ động toàn bộ các `stream_id` thuộc về một `mission_id` (hoặc `task_id`)."""
        target = str(mission_id or "").strip()
        if not target:
            return 0
        to_remove = [
            sid for sid, entry in self._store.items()
            if entry.mission_id == target or entry.task_id == target
        ]
        for sid in to_remove:
            self._store.pop(sid, None)
        return len(to_remove)

    def put(
        self,
        content: str,
        source_tool: str = "tool",
        task_id: str = "sys",
        preview_chars: int = 4000,
        metadata: Optional[Dict[str, Any]] = None,
        mission_id: Optional[str] = None,
        ttl_seconds: Optional[float] = None,
    ) -> Dict[str, Any]:
        self.purge_expired()
        raw = str(content or "")
        raw_bytes = raw.encode("utf-8", errors="ignore")
        sha256 = hashlib.sha256(raw_bytes).hexdigest()
        effective_task = str(task_id or mission_id or "sys")
        effective_mission = str(mission_id or task_id or "sys")
        effective_ttl = self.default_ttl_seconds if ttl_seconds is None else float(ttl_seconds)
        clean_task = re.sub(r"[^A-Za-z0-9_\-]", "_", effective_task)[:24]
        stream_id = f"stream_{clean_task}_{sha256[:10]}"

        lines = raw.splitlines()
        total_lines = len(lines)
        total_bytes = len(raw_bytes)

        entry = self._store.get(stream_id)
        if entry is None:
            entry = StreamEntry(
                stream_id=stream_id,
                task_id=effective_task,
                mission_id=effective_mission,
                ttl_seconds=effective_ttl,
                source_tool=str(source_tool or "tool"),
                sha256=sha256,
                total_bytes=total_bytes,
                total_lines=total_lines,
                lines=lines,
                metadata=dict(metadata or {}),
            )
            self._store[stream_id] = entry
            while len(self._store) > self.max_entries:
                self._store.popitem(last=False)
        else:
            entry.created_at = time.time()
            entry.ttl_seconds = effective_ttl
            entry.mission_id = effective_mission
            self._store.move_to_end(stream_id)

        # Compute initial preview lines within preview_chars budget
        preview_end_line = 0
        acc_chars = 0
        preview_buf: List[str] = []
        for idx, ln in enumerate(lines, 1):
            if acc_chars + len(ln) + 1 > preview_chars and preview_end_line > 0:
                break
            preview_buf.append(ln)
            acc_chars += len(ln) + 1
            preview_end_line = idx

        if preview_end_line > 0:
            entry.record_read(1, preview_end_line)

        cov = _compute_line_coverage_ratio(total_lines, entry.read_spans)
        unread = _compute_unread_spans(total_lines, entry.read_spans)
        has_more = preview_end_line < total_lines

        return {
            "stream_id": stream_id,
            "task_id": entry.task_id,
            "mission_id": entry.mission_id,
            "ttl_seconds": entry.ttl_seconds,
            "source_tool": entry.source_tool,
            "sha256": sha256,
            "total_bytes": total_bytes,
            "total_lines": total_lines,
            "preview_start_line": 1 if total_lines > 0 else 0,
            "preview_end_line": preview_end_line,
            "preview": "\n".join(preview_buf),
            "has_more": has_more,
            "next_start_line": (preview_end_line + 1) if has_more else None,
            "coverage_ratio": cov,
            "read_spans": list(entry.read_spans),
            "unread_spans": unread,
        }

    def get(self, stream_id: str) -> Optional[StreamEntry]:
        key = str(stream_id or "").strip()
        entry = self._store.get(key)
        if entry is None:
            return None
        if entry.is_expired():
            self._store.pop(key, None)
            return None
        return entry


_GLOBAL_STREAM_STORE = StreamBufferStore()


def get_stream_store() -> StreamBufferStore:
    return _GLOBAL_STREAM_STORE


def evict_mission_streams(mission_id: str) -> int:
    return _GLOBAL_STREAM_STORE.evict_mission(mission_id)


def purge_expired_streams(now: Optional[float] = None) -> int:
    return _GLOBAL_STREAM_STORE.purge_expired(now=now)


def store_stream(
    content: str,
    source_tool: str = "tool",
    task_id: str = "sys",
    preview_chars: int = 4000,
    metadata: Optional[Dict[str, Any]] = None,
    mission_id: Optional[str] = None,
    ttl_seconds: Optional[float] = None,
) -> Dict[str, Any]:
    return _GLOBAL_STREAM_STORE.put(
        content=content,
        source_tool=source_tool,
        task_id=task_id,
        preview_chars=preview_chars,
        metadata=metadata,
        mission_id=mission_id,
        ttl_seconds=ttl_seconds,
    )


def read_stream_window(
    stream_id: str,
    start_line: int = 1,
    end_line: int = 100,
) -> Dict[str, Any]:
    """
    Đọc phân trang cửa sổ dòng `[start_line..end_line]` (1-indexed) từ `stream_id`.
    Gắn nhãn `[L{line_no}]` vào đầu mỗi dòng và cập nhật sổ cái độ bao phủ (`read_spans`).
    """
    entry = _GLOBAL_STREAM_STORE.get(stream_id)
    if entry is None:
        return {
            "status": "error",
            "stream_id": stream_id,
            "msg": f"Không tìm thấy stream_id '{stream_id}' trong StreamBufferStore.",
        }

    total = entry.total_lines
    if total == 0:
        return {
            "status": "success",
            "stream_id": entry.stream_id,
            "start_line": 0,
            "end_line": 0,
            "total_lines": 0,
            "has_more": False,
            "next_start_line": None,
            "coverage_ratio": 1.0,
            "read_spans": [],
            "unread_spans": [],
            "content": "",
        }

    s_idx = max(1, min(total, int(start_line or 1)))
    e_idx = max(s_idx, min(total, int(end_line or (s_idx + 99))))
    entry.record_read(s_idx, e_idx)

    formatted_lines = [
        f"[L{line_no}] {entry.lines[line_no - 1]}"
        for line_no in range(s_idx, e_idx + 1)
    ]
    content = "\n".join(formatted_lines)
    cov = _compute_line_coverage_ratio(total, entry.read_spans)
    unread = _compute_unread_spans(total, entry.read_spans)
    has_more = e_idx < total

    return {
        "status": "success",
        "stream_id": entry.stream_id,
        "start_line": s_idx,
        "end_line": e_idx,
        "total_lines": total,
        "has_more": has_more,
        "next_start_line": (e_idx + 1) if has_more else None,
        "coverage_ratio": cov,
        "read_spans": list(entry.read_spans),
        "unread_spans": unread,
        "content": content,
    }


def search_in_stream(
    stream_id: str,
    query: str,
    context_lines: int = 2,
    offset: int = 0,
    limit: int = 20,
) -> Dict[str, Any]:
    """
    Truy xuất có mục tiêu (`Targeted Retrieval`) bên trong một `stream_id`.
    Ghi nhận mọi cửa sổ khớp vào `retrieved_spans` và các cửa sổ trong trang hiện tại vào `read_spans`.
    """
    entry = _GLOBAL_STREAM_STORE.get(stream_id)
    if entry is None:
        return {
            "status": "error",
            "stream_id": stream_id,
            "msg": f"Không tìm thấy stream_id '{stream_id}' trong StreamBufferStore.",
        }

    q_str = str(query or "").strip()
    if not q_str:
        return {
            "status": "error",
            "stream_id": entry.stream_id,
            "msg": "Tham số query không được rỗng khi gọi search_in_stream.",
        }

    entry.search_queries.append(q_str)
    try:
        pattern = re.compile(q_str, re.IGNORECASE)
    except re.error:
        pattern = re.compile(re.escape(q_str), re.IGNORECASE)

    q_folded = fold_vietnamese_accents(q_str)
    try:
        folded_pattern = re.compile(q_folded, re.IGNORECASE)
    except re.error:
        folded_pattern = re.compile(re.escape(q_folded), re.IGNORECASE)

    ctx = max(0, min(10, int(context_lines or 2)))
    page_offset = max(0, int(offset or 0))
    page_limit = max(1, min(100, int(limit or 20)))

    all_matches: List[Dict[str, Any]] = []
    total_lines = entry.total_lines

    for idx, ln in enumerate(entry.lines, 1):
        is_match = bool(pattern.search(ln))
        if not is_match and q_folded:
            is_match = bool(folded_pattern.search(fold_vietnamese_accents(ln)))
        if is_match:
            w_start = max(1, idx - ctx)
            w_end = min(total_lines, idx + ctx)
            entry.record_retrieved(w_start, w_end)
            snippet_lines = [
                f"[L{lno}] {entry.lines[lno - 1]}"
                for lno in range(w_start, w_end + 1)
            ]
            all_matches.append(
                {
                    "line": idx,
                    "window_start": w_start,
                    "window_end": w_end,
                    "line_content": ln,
                    "snippet": "\n".join(snippet_lines),
                }
            )

    total_matches = len(all_matches)
    paged = all_matches[page_offset : page_offset + page_limit]
    for m in paged:
        entry.record_read(m["window_start"], m["window_end"])

    cov = _compute_line_coverage_ratio(total_lines, entry.read_spans)
    unread = _compute_unread_spans(total_lines, entry.read_spans)
    has_more = (page_offset + page_limit) < total_matches

    rendered_snippets = "\n---\n".join(m["snippet"] for m in paged)
    return {
        "status": "success",
        "stream_id": entry.stream_id,
        "query": q_str,
        "total_matches": total_matches,
        "offset": page_offset,
        "limit": page_limit,
        "has_more": has_more,
        "next_offset": (page_offset + page_limit) if has_more else None,
        "coverage_ratio": cov,
        "read_spans": list(entry.read_spans),
        "unread_spans": unread,
        "matches": paged,
        "content": rendered_snippets,
    }


def get_stream_coverage_report(
    stream_id: str,
    required_spans: Optional[Sequence[Tuple[int, int]]] = None,
    citations: Optional[Sequence[Dict[str, Any]]] = None,
    predicted_facts: Optional[Sequence[str]] = None,
    expected_facts: Optional[Sequence[str]] = None,
    elapsed_ms: float = 0.0,
    prompt_tokens: int = 0,
    completion_tokens: int = 0,
) -> Dict[str, Any]:
    """
    Đối chiếu trạng thái đọc của `stream_id` với nguồn gốc và tính toán 5 chỉ số `StreamMetrics`.
    Xác minh từng trích dẫn (`citations`) xem dòng trích dẫn có tồn tại thật trong `stream_id`,
    có chứa nội dung dẫn chiếu (`expected_substring`), và đã nằm trong `read_spans` hay chưa.
    """
    entry = _GLOBAL_STREAM_STORE.get(stream_id)
    if entry is None:
        return {
            "status": "error",
            "stream_id": stream_id,
            "msg": f"Không tìm thấy stream_id '{stream_id}'.",
        }

    verified_citations: List[Dict[str, Any]] = []
    for c in citations or []:
        l_start = int(c.get("line_start", 0))
        l_end = int(c.get("line_end", l_start))
        exp_sub = str(c.get("expected_substring", "")).strip()
        in_bounds = 1 <= l_start <= l_end <= entry.total_lines
        was_read = any(rs <= l_start and l_end <= re_ for rs, re_ in entry.read_spans)
        text_ok = True
        if in_bounds and exp_sub:
            span_text = "\n".join(entry.lines[l_start - 1 : l_end])
            text_ok = exp_sub in span_text
        supported = bool(c.get("supported_by_source", in_bounds and was_read and text_ok))
        verified_citations.append(
            {
                "line_start": l_start,
                "line_end": l_end,
                "supported_by_source": supported,
                "was_read": was_read,
            }
        )

    req_list = list(required_spans or [])
    metrics = evaluate_stream_5_metrics(
        required_spans=req_list,
        retrieved_spans=entry.retrieved_spans,
        read_spans=entry.read_spans,
        citations=verified_citations,
        predicted_facts=list(predicted_facts or []),
        expected_facts=list(expected_facts or []),
        elapsed_ms=elapsed_ms,
        prompt_tokens=prompt_tokens,
        completion_tokens=completion_tokens,
    )
    line_cov = _compute_line_coverage_ratio(entry.total_lines, entry.read_spans)
    unread = _compute_unread_spans(entry.total_lines, entry.read_spans)

    return {
        "status": "success",
        "stream_id": entry.stream_id,
        "total_lines": entry.total_lines,
        "total_bytes": entry.total_bytes,
        "line_coverage_ratio": line_cov,
        "retrieved_spans": list(entry.retrieved_spans),
        "read_spans": list(entry.read_spans),
        "unread_spans": unread,
        "verified_citations": verified_citations,
        "metrics": metrics,
    }


def buffer_text_if_large(
    text: str,
    source_tool: str = "tool",
    task_id: str = "sys",
    max_inline_chars: int = 12000,
) -> Tuple[str, Optional[Dict[str, Any]]]:
    """
    Nếu `text` vượt quá `max_inline_chars`, lưu toàn văn vào `StreamBufferStore`
    và trả về bản xem trước kèm chỉ dẫn `stream_id` rõ ràng thay vì cắt cụt mù quáng.
    """
    raw = str(text or "")
    if len(raw) <= max_inline_chars:
        return raw, None

    env = store_stream(
        content=raw,
        source_tool=source_tool,
        task_id=task_id,
        preview_chars=max_inline_chars,
    )
    sid = env["stream_id"]
    banner = (
        f"\n... [STREAM_BUFFERED: stream_id={sid} | "
        f"lines_shown=1..{env['preview_end_line']}/{env['total_lines']} | "
        f"coverage={env['coverage_ratio']} | "
        f"Dùng read_stream_window(stream_id='{sid}', start_line={env['next_start_line']}, end_line=...) "
        f"hoặc search_in_stream(stream_id='{sid}', query='...') để đọc tiếp phần bị cắt]"
    )
    return env["preview"] + banner, env


def search_parent_child_chunks(
    stream_id: str,
    query: str,
    child_window_lines: int = 4,
    parent_window_lines: int = 20,
    max_results: int = 5,
    required_spans: Optional[Sequence[Tuple[int, int]]] = None,
) -> Dict[str, Any]:
    """
    [Slice 2.4 - WeKnora Parent-Child Chunking & Pre-Rerank Recall Harness]:
    - Tìm kiếm trên cửa sổ con hẹp (`child_span` có độ rộng `child_window_lines`) để định vị chính xác dòng khớp.
    - Tự động mở rộng mỗi đoạn khớp ra cửa sổ cha (`parent_span` có độ rộng `parent_window_lines`) để giữ ngữ cảnh.
    - Đo `pre_rerank_retrieval_recall` trên toàn bộ tập ứng viên trước khi cắt `max_results`, và
      `post_rerank_retrieval_recall` sau khi cắt top-K rerank.
    """
    from core.utils.repo_map import compute_retrieval_recall

    entry = _GLOBAL_STREAM_STORE.get(stream_id)
    if entry is None:
        return {
            "status": "error",
            "stream_id": stream_id,
            "msg": f"Không tìm thấy stream_id '{stream_id}'.",
        }

    q_clean = str(query or "").strip()
    q_low = q_clean.lower()
    q_fold = fold_vietnamese_accents(q_low)
    terms = [t for t in q_fold.split() if t]

    total = entry.total_lines
    c_half = max(1, int(child_window_lines) // 2)
    p_half = max(c_half + 1, int(parent_window_lines) // 2)

    candidates: List[Dict[str, Any]] = []
    for idx, raw_line in enumerate(entry.lines):
        line_no = idx + 1
        line_low = raw_line.lower()
        line_fold = fold_vietnamese_accents(line_low)
        exact_hit = (q_low in line_low) or (q_fold and q_fold in line_fold)
        term_hits = sum(1 for t in terms if t in line_fold)
        if not exact_hit and term_hits == 0:
            continue

        score = (10.0 if exact_hit else 0.0) + float(term_hits)
        c_start = max(1, line_no - c_half)
        c_end = min(total, line_no + c_half)
        p_start = max(1, line_no - p_half)
        p_end = min(total, line_no + p_half)
        entry.record_retrieved(p_start, p_end)

        candidates.append(
            {
                "anchor_line": line_no,
                "score": score,
                "child_span": (c_start, c_end),
                "parent_span": (p_start, p_end),
                "child_content": "\n".join(
                    f"[L{ln}] {entry.lines[ln - 1]}" for ln in range(c_start, c_end + 1)
                ),
                "parent_content": "\n".join(
                    f"[L{ln}] {entry.lines[ln - 1]}" for ln in range(p_start, p_end + 1)
                ),
            }
        )

    # Sắp xếp giảm dần theo điểm khớp, ưu tiên dòng xuất hiện sớm nếu bằng điểm
    candidates.sort(key=lambda item: (-item["score"], item["anchor_line"]))
    all_candidate_spans = [c["parent_span"] for c in candidates]
    top_k = candidates[: max(1, int(max_results))]
    top_k_spans = [c["parent_span"] for c in top_k]

    for c in top_k:
        ps, pe = c["parent_span"]
        entry.record_read(ps, pe)

    req_list = list(required_spans or [])
    pre_recall = compute_retrieval_recall(req_list, all_candidate_spans)
    post_recall = compute_retrieval_recall(req_list, top_k_spans)
    cov = _compute_line_coverage_ratio(total, entry.read_spans)

    return {
        "status": "success",
        "stream_id": entry.stream_id,
        "query": q_clean,
        "total_candidates_before_rerank": len(candidates),
        "returned_chunks": len(top_k),
        "pre_rerank_retrieval_recall": pre_recall,
        "post_rerank_retrieval_recall": post_recall,
        "coverage_ratio": cov,
        "chunks": top_k,
    }

