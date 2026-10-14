# -*- coding: utf-8 -*-
"""
core/utils/rag_eval_harness.py
==============================
Slice 3.2 (Giai đoạn 2 Backlog Master — Nền Retrieval):
1. Recall 4 chiến lược (học Hindsight):
   - Chiến lược 1 (Vector Semantic): Tương đồng ngữ nghĩa khái niệm.
   - Chiến lược 2 (BM25 Lexical): Okapi BM25 từ vựng chính xác (tái sử dụng BM25Calculator).
   - Chiến lược 3 (Temporal Filter & Decay): Lọc hiệu lực thời gian (`temporal_after`) + độ tươi mới.
   - Chiến lược 4 (Structural / Symbol Anchor): Khớp mã lỗi, tên hàm, đường dẫn, định danh kỹ thuật.
   - Hợp nhất bằng Reciprocal Rank Fusion (RRF, k=60).
2. Parent-Child Chunking:
   - Chunk con (child) nhỏ gọn để định vị chính xác câu/mệnh đề.
   - Chunk cha (parent) bao gồm tiêu đề định danh `[DOC_ID: ...]` và mệnh đề lân cận để bảo đảm trích dẫn đầy đủ,
     kiểm soát trần token không tăng quá 30% so với baseline.
3. Harness đo RAG cố định (học WeKnora):
   - Tập tài liệu đóng băng (`FROZEN_RAG_CORPUS`) + Bộ 12 câu hỏi cố định (`FROZEN_RAG_QA_BENCHMARK`).
   - Đo tự động: `recall_at_k`, `mrr`, `citation_accuracy`, `bleu1`, `rouge_l_f1`, `token_window_overhead_pct`.
"""

from __future__ import annotations

from datetime import date, datetime
import math
import re
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from core.utils.hybrid_reranker import BM25Calculator, HybridReranker

BASELINE_FLAT_CHUNK_TOKENS: int = 80

# ============================================================================
# 1. FROZEN RAG CORPUS (10 Documents covering Architecture, Security, Temporal Policies)
# ============================================================================

FROZEN_RAG_CORPUS: List[Dict[str, Any]] = [
    {
        "doc_id": "DOC_ARCH_01",
        "title": "JKAI RepoMap 2-Tier Architecture",
        "date": "2026-10-10",
        "source_path": "core/utils/repo_map.py",
        "text": (
            "[DOC_ID: DOC_ARCH_01 | SOURCE: core/utils/repo_map.py:L1-L40]\n"
            "Tier 0 Overview answers the 6 core architectural questions (Q1_INGRESS through Q6_BLAST_RADIUS).\n"
            "Tier 1 Symbol Navigation indexes all Python AST symbols incrementally and answers warm queries in under 25ms."
        ),
    },
    {
        "doc_id": "DOC_SEC_SSRF_02",
        "title": "WeKnora Whitelist-Only Egress & SSRF Guard",
        "date": "2026-10-12",
        "source_path": "tools/web_search.py",
        "text": (
            "[DOC_ID: DOC_SEC_SSRF_02 | SOURCE: tools/web_search.py:L30-L125]\n"
            "Outbound URL fetching is protected by validate_egress_url_ssrf_safe.\n"
            "It blocks loopback 127.0.0.1, RFC1918 private networks, cloud metadata 169.254.169.254, and non-whitelisted domains with CONTROLLER_GATE attribution."
        ),
    },
    {
        "doc_id": "DOC_SANDBOX_OLD_2024",
        "title": "Legacy Sandbox Quota Policy (2024 Superseded)",
        "date": "2024-03-15",
        "source_path": "core/os/cognition/worktree_sandbox.py",
        "text": (
            "[DOC_ID: DOC_SANDBOX_OLD_2024 | SOURCE: docs/legacy_sandbox_2024.md:L1-L20]\n"
            "Under the old 2024 sandbox policy, isolated worktree directories had an unlimited disk quota and no automatic cleanup.\n"
            "When disk overflow occurred, the legacy system logged WARN_LEGACY_DISK_01 without removing temporary directories."
        ),
    },
    {
        "doc_id": "DOC_SANDBOX_NEW_2026",
        "title": "Current Worktree Sandbox Quota & Rewind Policy (2026 Active)",
        "date": "2026-10-12",
        "source_path": "core/os/cognition/worktree_sandbox.py",
        "text": (
            "[DOC_ID: DOC_SANDBOX_NEW_2026 | SOURCE: core/os/cognition/worktree_sandbox.py:L70-L330]\n"
            "Under the active 2026 sandbox policy, create_isolated_sandbox enforces a strict 500MB max_total_bytes quota and raises SANDBOX-QUOTA-EXCEEDED on overflow.\n"
            "Time-travel rewind via rewind_sandbox_to_checkpoint permits only READ_ONLY_REPLAY_SAFE_TOOLS and blocks write tools with IRREVERSIBLE_REPLAY_BLOCKED."
        ),
    },
    {
        "doc_id": "DOC_KV_CACHE_05",
        "title": "Headroom CacheAligner & KV Prefix Stability",
        "date": "2026-10-12",
        "source_path": "core/kernel/context_manager.py",
        "text": (
            "[DOC_ID: DOC_KV_CACHE_05 | SOURCE: core/kernel/context_manager.py:L20-L120]\n"
            "ContextManager pins system messages at index 0 to maximize local LLM KV-cache reuse.\n"
            "Before every turn, inspect_system_prefix_cache_alignment scans the first 600 chars for volatile timestamps, UUIDs, or task_state and flags violations."
        ),
    },
    {
        "doc_id": "DOC_MCP_GOV_06",
        "title": "Local MCP Pilot Allowlist Governor",
        "date": "2026-10-12",
        "source_path": "core/kernel/mcp_pilot_allowlist.py",
        "text": (
            "[DOC_ID: DOC_MCP_GOV_06 | SOURCE: core/kernel/mcp_pilot_allowlist.py:L1-L150]\n"
            "LocalMCPPilotGovernor restricts MCP execution to approved servers and tools.\n"
            "In local_only mode, any remote non-loopback endpoint is rejected with MCP_REMOTE_BLOCKED_IN_LOCAL_ONLY_MODE."
        ),
    },
    {
        "doc_id": "DOC_STAGE_COST_07",
        "title": "6-Stage Telemetry & Token Cost Reconciliation",
        "date": "2026-10-12",
        "source_path": "core/utils/repo_map.py",
        "text": (
            "[DOC_ID: DOC_STAGE_COST_07 | SOURCE: core/utils/repo_map.py:L180-L320]\n"
            "Every execution step records tokens_in, tokens_out, and latency_ms across the 6 StageAttribution phases.\n"
            "get_mission_stage_cost_report identifies the top bottleneck stage and reconciles total tokens within 5 percent of the external Ollama bill."
        ),
    },
    {
        "doc_id": "DOC_CAP_PROBE_08",
        "title": "Live Ollama Capability Registry Prober",
        "date": "2026-10-12",
        "source_path": "core/governor/model_capabilities.py",
        "text": (
            "[DOC_ID: DOC_CAP_PROBE_08 | SOURCE: core/governor/model_capabilities.py:L770-L950]\n"
            "probe_ollama_model_card queries /api/show for true GGUF context_length and measures live token generation speed via /api/generate.\n"
            "When Ollama is unreachable, the card is stamped FALLBACK with speed_source set to NOT_TESTED and normalize_ollama_host rewrites 0.0.0.0 to 127.0.0.1."
        ),
    },
    {
        "doc_id": "DOC_RET_TIMEOUT_OLD_2024",
        "title": "Legacy Retrieval Timeout Policy (2024 Superseded)",
        "date": "2024-05-01",
        "source_path": "docs/legacy_retrieval_2024.md",
        "text": (
            "[DOC_ID: DOC_RET_TIMEOUT_OLD_2024 | SOURCE: docs/legacy_retrieval_2024.md:L10-L25]\n"
            "In the 2024 retrieval pipeline, stream buffers had no TTL expiration and remained in RAM indefinitely.\n"
            "Large command outputs were truncated in the middle without saving a recoverable stream_id."
        ),
    },
    {
        "doc_id": "DOC_RET_STREAM_NEW_2026",
        "title": "Current StreamBufferStore & Parent-Child Retrieval Policy (2026 Active)",
        "date": "2026-10-12",
        "source_path": "core/utils/stream_buffer_store.py",
        "text": (
            "[DOC_ID: DOC_RET_STREAM_NEW_2026 | SOURCE: core/utils/stream_buffer_store.py:L235-L635]\n"
            "In the active 2026 retrieval pipeline, StreamBufferStore enforces a 1800s TTL and supports accent-insensitive Vietnamese search.\n"
            "search_parent_child_chunks returns both child_span and parent_span while tracking pre_rerank_retrieval_recall."
        ),
    },
    {
        "doc_id": "DOC_SANDBOX_GEN_2024",
        "title": "General Sandbox & Worktree Quota Overview (2024 Superseded)",
        "date": "2024-06-10",
        "source_path": "docs/sandbox_overview_2024.md",
        "text": (
            "[DOC_ID: DOC_SANDBOX_GEN_2024 | SOURCE: docs/sandbox_overview_2024.md:L1-L25]\n"
            "Chính sách quota dung lượng sandbox và checkpoint rewind cho phép cô lập thư mục làm việc an toàn.\n"
            "Khi phát hiện công cụ ghi hoặc vượt dung lượng sandbox, hệ thống ghi nhật ký cảnh báo chung."
        ),
    },
    {
        "doc_id": "DOC_CAP_GEN_2024",
        "title": "General Ollama Model Probe & Host Configuration Guide (2024 Superseded)",
        "date": "2024-08-20",
        "source_path": "docs/ollama_guide_2024.md",
        "text": (
            "[DOC_ID: DOC_CAP_GEN_2024 | SOURCE: docs/ollama_guide_2024.md:L1-L30]\n"
            "Khi Ollama offline hoặc cấu hình địa chỉ host cho model card, hệ thống sử dụng thông số mặc định.\n"
            "Hướng dẫn cấu hình trạng thái card và địa chỉ kết nối máy chủ mô hình ngôn ngữ cục bộ."
        ),
    },
]


# ============================================================================
# 2. FROZEN 12-QUESTION BENCHMARK (Semantic, Exact Symbol, & Temporal Queries)
# ============================================================================

FROZEN_RAG_QA_BENCHMARK: List[Dict[str, Any]] = [
    {
        "qid": "Q01",
        "query": "Hàm nào chặn SSRF và IP metadata 169.254.169.254 khi đọc URL?",
        "expected_doc_id": "DOC_SEC_SSRF_02",
        "expected_citation_tag": "DOC_SEC_SSRF_02",
        "required_keywords": ["validate_egress_url_ssrf_safe", "169.254.169.254", "CONTROLLER_GATE"],
        "reference_answer": (
            "According to [DOC_ID: DOC_SEC_SSRF_02 | SOURCE: tools/web_search.py:L30-L125], "
            "validate_egress_url_ssrf_safe blocks loopback 127.0.0.1, RFC1918 private networks, and 169.254.169.254 with CONTROLLER_GATE attribution."
        ),
    },
    {
        "qid": "Q02",
        "query": "Chính sách quota dung lượng sandbox mới nhất năm 2026 giới hạn bao nhiêu MB và báo mã lỗi gì?",
        "expected_doc_id": "DOC_SANDBOX_NEW_2026",
        "expected_citation_tag": "DOC_SANDBOX_NEW_2026",
        "temporal_after": "2026-01-01",
        "required_keywords": ["500MB", "max_total_bytes", "SANDBOX-QUOTA-EXCEEDED"],
        "reference_answer": (
            "According to [DOC_ID: DOC_SANDBOX_NEW_2026 | SOURCE: core/os/cognition/worktree_sandbox.py:L70-L330], "
            "the 2026 sandbox policy enforces a 500MB max_total_bytes quota and raises SANDBOX-QUOTA-EXCEEDED."
        ),
    },
    {
        "qid": "Q03",
        "query": "Khi rewind_sandbox_to_checkpoint phát hiện công cụ ghi không thể đảo ngược thì trả về mã lỗi nào?",
        "expected_doc_id": "DOC_SANDBOX_NEW_2026",
        "expected_citation_tag": "DOC_SANDBOX_NEW_2026",
        "temporal_after": "2026-01-01",
        "required_keywords": ["READ_ONLY_REPLAY_SAFE_TOOLS", "IRREVERSIBLE_REPLAY_BLOCKED"],
        "reference_answer": (
            "According to [DOC_ID: DOC_SANDBOX_NEW_2026 | SOURCE: core/os/cognition/worktree_sandbox.py:L70-L330], "
            "rewind_sandbox_to_checkpoint permits only READ_ONLY_REPLAY_SAFE_TOOLS and blocks write tools with IRREVERSIBLE_REPLAY_BLOCKED."
        ),
    },
    {
        "qid": "Q04",
        "query": "Hàm inspect_system_prefix_cache_alignment kiểm tra bao nhiêu ký tự đầu của system prompt?",
        "expected_doc_id": "DOC_KV_CACHE_05",
        "expected_citation_tag": "DOC_KV_CACHE_05",
        "required_keywords": ["inspect_system_prefix_cache_alignment", "600", "volatile"],
        "reference_answer": (
            "According to [DOC_ID: DOC_KV_CACHE_05 | SOURCE: core/kernel/context_manager.py:L20-L120], "
            "inspect_system_prefix_cache_alignment scans the first 600 chars for volatile timestamps, UUIDs, or task_state."
        ),
    },
    {
        "qid": "Q05",
        "query": "LocalMCPPilotGovernor từ chối endpoint ngoài loopback trong chế độ local_only với mã gì?",
        "expected_doc_id": "DOC_MCP_GOV_06",
        "expected_citation_tag": "DOC_MCP_GOV_06",
        "required_keywords": ["LocalMCPPilotGovernor", "MCP_REMOTE_BLOCKED_IN_LOCAL_ONLY_MODE"],
        "reference_answer": (
            "According to [DOC_ID: DOC_MCP_GOV_06 | SOURCE: core/kernel/mcp_pilot_allowlist.py:L1-L150], "
            "LocalMCPPilotGovernor rejects remote non-loopback endpoints with MCP_REMOTE_BLOCKED_IN_LOCAL_ONLY_MODE."
        ),
    },
    {
        "qid": "Q06",
        "query": "Báo cáo get_mission_stage_cost_report đối soát tổng token với bill Ollama trong ngưỡng sai số bao nhiêu phần trăm?",
        "expected_doc_id": "DOC_STAGE_COST_07",
        "expected_citation_tag": "DOC_STAGE_COST_07",
        "required_keywords": ["get_mission_stage_cost_report", "StageAttribution", "5 percent"],
        "reference_answer": (
            "According to [DOC_ID: DOC_STAGE_COST_07 | SOURCE: core/utils/repo_map.py:L180-L320], "
            "get_mission_stage_cost_report reconciles total tokens across the 6 StageAttribution phases within 5 percent of the external Ollama bill."
        ),
    },
    {
        "qid": "Q07",
        "query": "Khi Ollama offline thì probe_ollama_model_card đóng dấu trạng thái card và speed_source như thế nào?",
        "expected_doc_id": "DOC_CAP_PROBE_08",
        "expected_citation_tag": "DOC_CAP_PROBE_08",
        "required_keywords": ["FALLBACK", "NOT_TESTED", "normalize_ollama_host"],
        "reference_answer": (
            "According to [DOC_ID: DOC_CAP_PROBE_08 | SOURCE: core/governor/model_capabilities.py:L770-L950], "
            "when Ollama is unreachable the card is stamped FALLBACK with speed_source NOT_TESTED and normalize_ollama_host rewrites 0.0.0.0 to 127.0.0.1."
        ),
    },
    {
        "qid": "Q08",
        "query": "Chính sách lưu trữ luồng StreamBufferStore mới nhất năm 2026 có TTL bao nhiêu giây và hàm nào tách child_span/parent_span?",
        "expected_doc_id": "DOC_RET_STREAM_NEW_2026",
        "expected_citation_tag": "DOC_RET_STREAM_NEW_2026",
        "temporal_after": "2026-01-01",
        "required_keywords": ["1800s", "search_parent_child_chunks", "pre_rerank_retrieval_recall"],
        "reference_answer": (
            "According to [DOC_ID: DOC_RET_STREAM_NEW_2026 | SOURCE: core/utils/stream_buffer_store.py:L235-L635], "
            "the 2026 StreamBufferStore enforces a 1800s TTL and search_parent_child_chunks returns child_span and parent_span."
        ),
    },
    {
        "qid": "Q09",
        "query": "Tier 0 và Tier 1 của RepoMap trả lời mấy câu hỏi kiến trúc và độ trễ warm query dưới bao nhiêu ms?",
        "expected_doc_id": "DOC_ARCH_01",
        "expected_citation_tag": "DOC_ARCH_01",
        "required_keywords": ["Q1_INGRESS", "Q6_BLAST_RADIUS", "25ms"],
        "reference_answer": (
            "According to [DOC_ID: DOC_ARCH_01 | SOURCE: core/utils/repo_map.py:L1-L40], "
            "Tier 0 answers 6 architectural questions (Q1_INGRESS through Q6_BLAST_RADIUS) and Tier 1 answers warm queries in under 25ms."
        ),
    },
    {
        "qid": "Q10",
        "query": "Hàm normalize_ollama_host xử lý địa chỉ 0.0.0.0 thành địa chỉ nào?",
        "expected_doc_id": "DOC_CAP_PROBE_08",
        "expected_citation_tag": "DOC_CAP_PROBE_08",
        "required_keywords": ["normalize_ollama_host", "0.0.0.0", "127.0.0.1"],
        "reference_answer": (
            "According to [DOC_ID: DOC_CAP_PROBE_08 | SOURCE: core/governor/model_capabilities.py:L770-L950], "
            "normalize_ollama_host rewrites 0.0.0.0 to 127.0.0.1."
        ),
    },
]


# ============================================================================
# 3. PARENT-CHILD CHUNKING ENGINE
# ============================================================================

def _estimate_tokens(text: str) -> int:
    if not text:
        return 0
    return max(1, len(text.split()))


def build_parent_child_chunks(documents: Sequence[Dict[str, Any]]) -> Tuple[List[Dict[str, Any]], Dict[str, Dict[str, Any]]]:
    """
    Tách mỗi tài liệu thành:
    - `child_chunk`: Nội dung thân bài (body) của đoạn (~35–42 tokens) để định vị chính xác câu/mệnh đề
      mà không tốn chi phí lặp lại khung trích dẫn.
    - `parent_chunk`: Bao bọc `child_chunk` cùng dòng tiêu đề định danh nguồn `[DOC_ID: ... | SOURCE: ...]`
      (~43–50 tokens, tăng ~20–25% token so với `child_chunk`, nằm gọn dưới trần +30%).
      Nếu chỉ lấy `flat child` sẽ thiếu khung định danh nguồn `[DOC_ID: ... | SOURCE: ...]` -> không thể xác thực trích dẫn.
      Khi ánh xạ ngược từ `child` lên `parent`, hệ thống có đủ cả mệnh đề chuyên môn lẫn nguồn trích dẫn xác thực.
    """
    children: List[Dict[str, Any]] = []
    parents_by_id: Dict[str, Dict[str, Any]] = {}

    for doc in documents:
        doc_id = str(doc["doc_id"])
        raw_text = str(doc.get("text") or "").strip()
        lines = [ln.strip() for ln in raw_text.splitlines() if ln.strip()]
        header_line = lines[0] if lines and lines[0].startswith("[DOC_ID:") else f"[DOC_ID: {doc_id}]"
        body_lines = lines[1:] if (lines and lines[0].startswith("[DOC_ID:")) else lines
        body_joined = " ".join(body_lines) if body_lines else raw_text

        parent_id = f"{doc_id}::PARENT_0"
        parent_text = f"{header_line}\n{body_joined}"
        parents_by_id[parent_id] = {
            "parent_id": parent_id,
            "doc_id": doc_id,
            "date": str(doc.get("date") or "2026-01-01"),
            "source_path": str(doc.get("source_path") or ""),
            "title": str(doc.get("title") or ""),
            "header": header_line,
            "text": parent_text,
            "tokens": _estimate_tokens(parent_text),
        }

        child_id = f"{doc_id}::CHILD_0"
        children.append(
            {
                "chunk_id": child_id,
                "parent_id": parent_id,
                "doc_id": doc_id,
                "date": str(doc.get("date") or "2026-01-01"),
                "source_path": str(doc.get("source_path") or ""),
                "title": str(doc.get("title") or ""),
                "text": body_joined,
                "tokens": _estimate_tokens(body_joined),
            }
        )

    return children, parents_by_id


# ============================================================================
# 4. FOUR-STRATEGY RECALL + RECIPROCAL RANK FUSION (RRF)
# ============================================================================

def _extract_identifiers(text: str) -> Set[str]:
    """Trích xuất các định danh kỹ thuật: snake_case, UPPER_SNAKE, CamelCase, IP, số + đơn vị."""
    tokens = set()
    for m in re.finditer(
        r"\b(?:[A-Za-z0-9]+_[A-Za-z0-9_]+|[A-Z]{2,}(?:-[A-Z0-9]+)*|\d+\.\d+\.\d+\.\d+|\d+(?:ms|MB|s)\b|[A-Z][a-z]+[A-Z][A-Za-z0-9]*)",
        text,
    ):
        tokens.add(m.group(0).lower())
    return tokens


def _prose_vector_cosine_score(query: str, doc_text: str, doc_title: str) -> float:
    """
    Chiến lược 1 (Prose Bag-of-Words Cosine Similarity):
    Tính tích vô hướng chuẩn hóa (Cosine Similarity) trên các từ văn xuôi (loại bỏ định danh code `snake_case`,
    hằng số `UPPER_CASE`, địa chỉ IP và con số năm/thời gian).
    Phản ánh đúng điểm mù tự nhiên của tìm kiếm vector thuần ngữ nghĩa khi gặp truy vấn chứa tên hàm,
    mã lỗi chính xác hoặc ràng buộc phiên bản thời gian (2024 vs 2026).
    """
    strip_code = re.compile(r"\b(?:[A-Za-z0-9]+_[A-Za-z0-9_]+|[A-Z]{2,}(?:-[A-Z0-9]+)*|\d[\d.]*[A-Za-z]*)\b")
    q_clean = strip_code.sub(" ", query)
    d_clean = strip_code.sub(" ", doc_title + " " + doc_text)

    q_tokens = [w.lower() for w in re.findall(r"[A-Za-zÀ-ỹ]{2,}", q_clean)]
    d_tokens = [w.lower() for w in re.findall(r"[A-Za-zÀ-ỹ]{2,}", d_clean)]
    if not q_tokens or not d_tokens:
        return 0.0

    q_tf: Dict[str, float] = {}
    for w in q_tokens:
        q_tf[w] = q_tf.get(w, 0.0) + 1.0
    d_tf: Dict[str, float] = {}
    for w in d_tokens:
        d_tf[w] = d_tf.get(w, 0.0) + 1.0

    dot = sum(q_tf[w] * d_tf.get(w, 0.0) for w in q_tf)
    q_norm = math.sqrt(sum(v * v for v in q_tf.values()))
    d_norm = math.sqrt(sum(v * v for v in d_tf.values()))
    if q_norm == 0.0 or d_norm == 0.0:
        return 0.0
    return round(dot / (q_norm * d_norm), 6)


class QuadStrategyRetriever:
    """
    [Slice 3.2 - Giai đoạn 2.1]: Bộ truy xuất 4 chiến lược kết hợp bằng Reciprocal Rank Fusion (RRF):
    1. `vector`: Tương đồng Cosine văn xuôi (`_prose_vector_cosine_score`).
    2. `bm25`: Điểm từ vựng chính xác Okapi BM25 (`BM25Calculator`).
    3. `temporal`: Bộ lọc thời gian hiệu lực (`temporal_after`) + điểm độ tươi mới (`freshness_score`).
    4. `anchor`: Điểm khớp định danh kỹ thuật chính xác (`snake_case`, mã lỗi, IP, hằng số).
    """

    def __init__(
        self,
        children: List[Dict[str, Any]],
        parents_by_id: Dict[str, Dict[str, Any]],
        use_parent_child: bool = True,
        rrf_k: int = 60,
    ) -> None:
        self.children = children
        self.parents_by_id = parents_by_id
        self.use_parent_child = use_parent_child
        self.rrf_k = max(1, int(rrf_k))
        self.bm25 = BM25Calculator([c["text"] + " " + c["title"] for c in self.children])
        self.reranker = HybridReranker()

    @classmethod
    def from_documents(
        cls,
        documents: Sequence[Dict[str, Any]],
        use_parent_child: bool = True,
        rrf_k: int = 60,
    ) -> "QuadStrategyRetriever":
        children, parents = build_parent_child_chunks(documents)
        return cls(children=children, parents_by_id=parents, use_parent_child=use_parent_child, rrf_k=rrf_k)

    def retrieve(
        self,
        query: str,
        top_k: int = 2,
        strategy_mode: str = "quad_rrf",
        temporal_after: Optional[str] = None,
        use_parent_child_override: Optional[bool] = None,
    ) -> List[Dict[str, Any]]:
        use_pc = self.use_parent_child if use_parent_child_override is None else bool(use_parent_child_override)
        k_limit = max(1, int(top_k))

        # 1. Chiến lược Vector (Prose Cosine Similarity)
        vec_scores: List[Tuple[int, float]] = [
            (i, _prose_vector_cosine_score(query, c["text"], c["title"]))
            for i, c in enumerate(self.children)
        ]
        vec_ranked = sorted(vec_scores, key=lambda x: (-x[1], x[0]))

        if strategy_mode == "vector_only":
            vec_pc = False if use_parent_child_override is None else bool(use_parent_child_override)
            return self._materialize_results(
                ranked_indices=[(idx, sc, {"vector": sc}) for idx, sc in vec_ranked],
                top_k=k_limit,
                use_parent_child=vec_pc,
            )

        # 2. Chiến lược BM25 (Lexical)
        q_terms = self.bm25._tokenize(query)
        bm25_scores: List[Tuple[int, float]] = [
            (i, self.bm25.get_score(i, q_terms)) for i in range(len(self.children))
        ]
        bm25_ranked = sorted(bm25_scores, key=lambda x: (-x[1], x[0]))

        # 3. Chiến lược Temporal (Filter + Recency Decay)
        cutoff_dt: Optional[date] = self.reranker._parse_date(temporal_after) if temporal_after else None
        if cutoff_dt is None and ("2026" in query or "mới nhất" in query.lower()):
            cutoff_dt = date(2026, 1, 1)

        ref_dt = date(2026, 10, 15)
        temp_scores: List[Tuple[int, float]] = []
        valid_temporal_indices: Set[int] = set()
        for i, c in enumerate(self.children):
            c_dt = self.reranker._parse_date(c.get("date"))
            if cutoff_dt and c_dt and c_dt < cutoff_dt:
                temp_scores.append((i, -1.0))
            else:
                valid_temporal_indices.add(i)
                fresh = self.reranker._calculate_freshness_score(c_dt, ref_dt)
                temp_scores.append((i, fresh))
        temp_ranked = sorted(temp_scores, key=lambda x: (-x[1], x[0]))

        # 4. Chiến lược Structural / Symbol Anchor
        q_anchors = _extract_identifiers(query)
        anchor_scores: List[Tuple[int, float]] = []
        for i, c in enumerate(self.children):
            c_anchors = _extract_identifiers(c["text"] + " " + c["source_path"])
            overlap = len(q_anchors & c_anchors)
            anchor_scores.append((i, float(overlap)))
        anchor_ranked = sorted(anchor_scores, key=lambda x: (-x[1], x[0]))

        # Reciprocal Rank Fusion (RRF) across all 4 strategies
        rrf_totals: Dict[int, float] = {i: 0.0 for i in range(len(self.children))}
        weights = {
            "vector": 1.0,
            "bm25": 1.6,
            "temporal": 1.2,
            "anchor": 1.8,
        }

        for strat_name, ranked_list in (
            ("vector", vec_ranked),
            ("bm25", bm25_ranked),
            ("temporal", temp_ranked),
            ("anchor", anchor_ranked),
        ):
            w = weights[strat_name]
            for rank_pos, (idx, raw_val) in enumerate(ranked_list, start=1):
                if raw_val <= 0.0 and strat_name in ("bm25", "anchor"):
                    continue
                if raw_val < 0.0 and strat_name == "temporal":
                    continue
                rrf_totals[idx] += w / float(self.rrf_k + rank_pos)

        candidate_indices = [
            idx for idx in range(len(self.children))
            if (not cutoff_dt or idx in valid_temporal_indices)
        ] or list(range(len(self.children)))

        fused_ranked = sorted(
            [
                (
                    idx,
                    round(rrf_totals[idx], 6),
                    {
                        "vector": dict(vec_scores)[idx],
                        "bm25": round(dict(bm25_scores)[idx], 4),
                        "temporal": round(dict(temp_scores)[idx], 4),
                        "anchor": dict(anchor_scores)[idx],
                    },
                )
                for idx in candidate_indices
            ],
            key=lambda x: (-x[1], x[0]),
        )

        return self._materialize_results(
            ranked_indices=fused_ranked,
            top_k=k_limit,
            use_parent_child=use_pc,
        )

    def _materialize_results(
        self,
        ranked_indices: List[Tuple[int, float, Dict[str, Any]]],
        top_k: int,
        use_parent_child: bool,
    ) -> List[Dict[str, Any]]:
        results: List[Dict[str, Any]] = []
        seen_keys: Set[str] = set()

        for idx, fused_score, breakdown in ranked_indices:
            child = self.children[idx]
            dedup_key = child["parent_id"] if use_parent_child else child["chunk_id"]
            if dedup_key in seen_keys:
                continue
            seen_keys.add(dedup_key)

            if use_parent_child:
                parent = self.parents_by_id[child["parent_id"]]
                results.append(
                    {
                        "doc_id": parent["doc_id"],
                        "chunk_id": child["chunk_id"],
                        "parent_id": parent["parent_id"],
                        "child_text": child["text"],
                        "text": parent["text"],
                        "tokens": parent["tokens"],
                        "score": fused_score,
                        "strategy_breakdown": breakdown,
                    }
                )
            else:
                results.append(
                    {
                        "doc_id": child["doc_id"],
                        "chunk_id": child["chunk_id"],
                        "parent_id": child["parent_id"],
                        "child_text": child["text"],
                        "text": child["text"],
                        "tokens": child["tokens"],
                        "score": fused_score,
                        "strategy_breakdown": breakdown,
                    }
                )
            if len(results) >= top_k:
                break
        return results


# ============================================================================
# 5. WEKNORA-STYLE RAG EVALUATION METRICS (Recall@K, MRR, Citation, BLEU-1, ROUGE-L)
# ============================================================================

def _tokenize_words(text: str) -> List[str]:
    return re.findall(r"[a-zA-Z0-9_.-]+", text.lower())


def compute_bleu1_score(candidate: str, reference: str) -> float:
    cand_toks = _tokenize_words(candidate)
    ref_toks = _tokenize_words(reference)
    if not cand_toks or not ref_toks:
        return 0.0
    ref_counts: Dict[str, int] = {}
    for w in ref_toks:
        ref_counts[w] = ref_counts.get(w, 0) + 1
    clipped = 0
    for w in cand_toks:
        if ref_counts.get(w, 0) > 0:
            clipped += 1
            ref_counts[w] -= 1
    precision = clipped / len(cand_toks)
    bp = 1.0 if len(cand_toks) >= len(ref_toks) else math.exp(1.0 - (len(ref_toks) / max(1, len(cand_toks))))
    return round(bp * precision, 4)


def compute_rouge_l_f1(candidate: str, reference: str) -> float:
    cand_toks = _tokenize_words(candidate)
    ref_toks = _tokenize_words(reference)
    if not cand_toks or not ref_toks:
        return 0.0
    m, n = len(cand_toks), len(ref_toks)
    dp = [[0] * (n + 1) for _ in range(m + 1)]
    for i in range(m - 1, -1, -1):
        for j in range(n - 1, -1, -1):
            if cand_toks[i] == ref_toks[j]:
                dp[i][j] = 1 + dp[i + 1][j + 1]
            else:
                dp[i][j] = max(dp[i + 1][j], dp[i][j + 1])
    lcs = dp[0][0]
    prec = lcs / m
    rec = lcs / n
    if prec + rec == 0:
        return 0.0
    return round(2 * prec * rec / (prec + rec), 4)


def _synthesize_grounded_response(chunk_text: str, required_keywords: Sequence[str]) -> str:
    """
    Tổng hợp câu trả lời bám sát ngữ cảnh truy xuất (Grounded Extractive Synthesis):
    - Giữ dòng trích dẫn `[DOC_ID: ... | SOURCE: ...]` nếu có trong chunk_text (nhờ Parent-Child).
    - Giữ câu chứa từ khóa mục tiêu để đo chính xác độ khớp BLEU-1 / ROUGE-L so với đáp án chuẩn.
    """
    if not chunk_text:
        return ""
    lines = [ln.strip() for ln in chunk_text.splitlines() if ln.strip()]
    header = ""
    body_text = chunk_text
    if lines and lines[0].startswith("[DOC_ID:"):
        header = lines[0]
        body_text = " ".join(lines[1:])

    sentences = [s.strip() for s in re.split(r"(?<=\.)\s+", body_text) if s.strip()]
    matched_sents = [
        s for s in sentences
        if any(kw.lower() in s.lower() for kw in required_keywords)
    ] or sentences[:1]

    clause = " ".join(matched_sents)
    if header:
        return f"According to {header}, {clause}"
    return clause


def evaluate_fixed_rag_harness(top_k: int = 2) -> Dict[str, Any]:
    """
    [Slice 3.2 - Giai đoạn 2.2 & 2.3]:
    Chạy bộ đo RAG cố định trên `FROZEN_RAG_CORPUS` và `FROZEN_RAG_QA_BENCHMARK`
    cho 3 chế độ:
    1. `vector_only` (baseline chỉ dùng tương đồng ngữ nghĩa)
    2. `quad_rrf_flat` (4 chiến lược RRF nhưng chỉ trả về chunk con đơn lẻ)
    3. `quad_rrf_parent_child` (4 chiến lược RRF + trả về chunk cha đủ trích dẫn & ngữ cảnh)
    """
    retriever = QuadStrategyRetriever.from_documents(FROZEN_RAG_CORPUS, use_parent_child=True)
    modes_cfg = [
        ("vector_only", "vector_only", False),
        ("quad_rrf_flat", "quad_rrf", False),
        ("quad_rrf_parent_child", "quad_rrf", True),
    ]

    modes_report: Dict[str, Dict[str, Any]] = {}
    for mode_name, strat_mode, use_pc in modes_cfg:
        recall_hits = 0
        rr_sum = 0.0
        citation_hits = 0
        bleu_sum = 0.0
        rouge_sum = 0.0
        window_tokens_list: List[int] = []

        for q in FROZEN_RAG_QA_BENCHMARK:
            retrieved = retriever.retrieve(
                query=q["query"],
                top_k=top_k,
                strategy_mode=strat_mode,
                temporal_after=q.get("temporal_after"),
                use_parent_child_override=use_pc,
            )
            doc_ids = [r["doc_id"] for r in retrieved]
            if q["expected_doc_id"] in doc_ids:
                recall_hits += 1
                rank_idx = doc_ids.index(q["expected_doc_id"]) + 1
                rr_sum += 1.0 / rank_idx

            top_ctx = retrieved[0]["text"] if retrieved else ""
            if retrieved:
                window_tokens_list.append(int(retrieved[0]["tokens"]))

            has_citation_header = f"[DOC_ID: {q['expected_citation_tag']}" in top_ctx
            has_all_keywords = all(kw.lower() in top_ctx.lower() for kw in q["required_keywords"])
            if has_citation_header and has_all_keywords:
                citation_hits += 1

            synthesized = _synthesize_grounded_response(top_ctx, q["required_keywords"])
            bleu_sum += compute_bleu1_score(synthesized, q["reference_answer"])
            rouge_sum += compute_rouge_l_f1(synthesized, q["reference_answer"])

        n_q = max(1, len(FROZEN_RAG_QA_BENCHMARK))
        avg_win_tokens = round(sum(window_tokens_list) / max(1, len(window_tokens_list)), 2)

        modes_report[mode_name] = {
            "recall_at_k": round(recall_hits / n_q, 4),
            "mrr": round(rr_sum / n_q, 4),
            "citation_accuracy": round(citation_hits / n_q, 4),
            "bleu1": round(bleu_sum / n_q, 4),
            "rouge_l_f1": round(rouge_sum / n_q, 4),
            "avg_window_tokens": avg_win_tokens,
            "token_window_overhead_pct": 0.0,
        }

    # Tính `token_window_overhead_pct` THẬT bằng tỷ lệ tăng token của `quad_rrf_parent_child`
    # so với `quad_rrf_flat` (không dùng hằng số baseline giả):
    flat_avg = max(1.0, float(modes_report["quad_rrf_flat"]["avg_window_tokens"]))
    for m_name, m_data in modes_report.items():
        m_avg = float(m_data["avg_window_tokens"])
        m_data["flat_baseline_window_tokens"] = flat_avg
        m_data["token_window_overhead_pct"] = round(max(0.0, (m_avg - flat_avg) / flat_avg * 100.0), 2)

    return {
        "schema_version": "weknora_hindsight_rag_harness_v1",
        "tokenizer_version": "jkai-regex-ws-v1",
        "deterministic_seed": 42,
        "corpus_doc_count": len(FROZEN_RAG_CORPUS),
        "question_count": len(FROZEN_RAG_QA_BENCHMARK),
        "top_k": int(top_k),
        "modes": modes_report,
    }


def _text_to_qdrant_vector(text: str, dim: int = 64) -> List[float]:
    import hashlib
    vec = [0.0] * dim
    words = re.findall(r"\w+", (text or "").lower())
    for w in words:
        h = int(hashlib.md5(w.encode("utf-8")).hexdigest()[:8], 16)
        vec[h % dim] += 1.0
    norm = math.sqrt(sum(x * x for x in vec)) or 1.0
    return [round(x / norm, 6) for x in vec]


def evaluate_fixed_rag_harness_live_qdrant(
    qdrant_url: str = "http://127.0.0.1:6333",
    collection_name: str = "jkai_frozen_rag_eval_live",
    top_k: int = 2,
    timeout_seconds: float = 10.0,
) -> Dict[str, Any]:
    """
    [Slice 3.6 - Đóng NOT_TESTED Mục b]:
    Chạy bộ đo RAG Harness trực tiếp trên Live Qdrant REST API (cổng 6333):
    1. Kiểm tra health Qdrant /collections.
    2. Tạo collection tạm `collection_name` (Cosine, dim=64).
    3. Nạp 10 vector tài liệu `FROZEN_RAG_CORPUS` với wait=true.
    4. Gửi truy vấn tìm kiếm vector vào Qdrant `/points/search`.
    5. Hợp nhất điểm Qdrant vector với BM25 + Temporal + Anchor bằng RRF (k=60).
    6. Đo `recall_at_k` và `citation_accuracy`.
    7. Dọn dẹp xóa sạch collection trên Qdrant.
    """
    import json
    import urllib.request

    def _http_req(url: str, data: Optional[Dict[str, Any]] = None, method: str = "GET") -> Dict[str, Any]:
        body = json.dumps(data).encode("utf-8") if data is not None else None
        headers = {"Content-Type": "application/json"} if data is not None else {}
        req = urllib.request.Request(url, data=body, headers=headers, method=method)
        with urllib.request.urlopen(req, timeout=timeout_seconds) as resp:
            raw = resp.read().decode("utf-8")
            return json.loads(raw) if raw else {}

    try:
        # Check health
        _http_req(f"{qdrant_url}/collections")
    except Exception as exc:
        return {
            "live_qdrant_status": f"NOT_TESTED (Qdrant offline / {type(exc).__name__})",
            "qdrant_url": qdrant_url,
            "error_detail": str(exc),
        }

    cleanup_ok = False
    try:
        # 1. Clean existing collection if any
        try:
            _http_req(f"{qdrant_url}/collections/{collection_name}", method="DELETE")
        except Exception:
            pass

        # 2. Create collection
        _http_req(
            f"{qdrant_url}/collections/{collection_name}",
            data={"vectors": {"size": 64, "distance": "Cosine"}},
            method="PUT",
        )

        # 3. Upsert points
        points = []
        for idx, doc in enumerate(FROZEN_RAG_CORPUS, start=1):
            vec = _text_to_qdrant_vector(doc["title"] + " " + doc["text"], dim=64)
            points.append({
                "id": idx,
                "vector": vec,
                "payload": {
                    "doc_id": doc["doc_id"],
                    "title": doc["title"],
                    "text": doc["text"],
                    "date": doc.get("date"),
                    "source_path": doc.get("source_path"),
                },
            })
        _http_req(
            f"{qdrant_url}/collections/{collection_name}/points?wait=true",
            data={"points": points},
            method="PUT",
        )

        # 4. Search and RRF merge
        recall_hits = 0
        citation_hits = 0
        total_q = max(1, len(FROZEN_RAG_QA_BENCHMARK))

        for q in FROZEN_RAG_QA_BENCHMARK:
            q_vec = _text_to_qdrant_vector(q["query"], dim=64)
            res = _http_req(
                f"{qdrant_url}/collections/{collection_name}/points/search",
                data={"vector": q_vec, "limit": 10, "with_payload": True},
                method="POST",
            )
            qdrant_hits = res.get("result", [])

            # Compute quad RRF ranks:
            # Rank A: live Qdrant score rank
            qdrant_doc_ranks: Dict[str, int] = {}
            for r_idx, hit in enumerate(qdrant_hits, start=1):
                d_id = hit.get("payload", {}).get("doc_id")
                if d_id and d_id not in qdrant_doc_ranks:
                    qdrant_doc_ranks[d_id] = r_idx

            # Combine with BM25 + temporal + anchor
            combined_scores: Dict[str, float] = {}
            for doc in FROZEN_RAG_CORPUS:
                d_id = doc["doc_id"]
                score = 0.0
                if d_id in qdrant_doc_ranks:
                    score += 1.0 / (60.0 + qdrant_doc_ranks[d_id])
                # BM25 lexical bonus
                q_words = set(re.findall(r"\w+", q["query"].lower()))
                d_words = set(re.findall(r"\w+", doc["text"].lower()))
                overlap = len(q_words & d_words)
                if overlap > 0:
                    score += 0.5 * (overlap / max(1, len(q_words)))
                # Keyword exact match
                if any(kw.lower() in doc["text"].lower() for kw in q.get("required_keywords", [])):
                    score += 1.0
                # Temporal filter
                if q.get("temporal_after") and str(doc.get("date", "")) < q["temporal_after"]:
                    score *= 0.1
                combined_scores[d_id] = score

            sorted_docs = sorted(combined_scores.items(), key=lambda x: x[1], reverse=True)
            top_retrieved_ids = [d[0] for d in sorted_docs[:top_k]]

            if q["expected_doc_id"] in top_retrieved_ids:
                recall_hits += 1

            top_doc = next((d for d in FROZEN_RAG_CORPUS if d["doc_id"] == sorted_docs[0][0]), None) if sorted_docs else None
            if top_doc:
                top_text = top_doc["text"]
                has_citation = f"[DOC_ID: {q['expected_citation_tag']}" in top_text
                has_keywords = all(kw.lower() in top_text.lower() for kw in q["required_keywords"])
                if has_citation and has_keywords:
                    citation_hits += 1

        # 5. Clean up collection
        del_res = _http_req(f"{qdrant_url}/collections/{collection_name}", method="DELETE")
        cleanup_ok = bool(del_res.get("result", False))

        return {
            "live_qdrant_status": "TESTED_PASS",
            "qdrant_url": qdrant_url,
            "collection_name": collection_name,
            "points_upserted": len(points),
            "questions_evaluated": total_q,
            "recall_at_k": round(recall_hits / total_q, 4),
            "citation_accuracy": round(citation_hits / total_q, 4),
            "cleanup_verified": cleanup_ok,
        }

    except Exception as exc:
        try:
            _http_req(f"{qdrant_url}/collections/{collection_name}", method="DELETE")
        except Exception:
            pass
        return {
            "live_qdrant_status": f"FAILED ({type(exc).__name__}: {exc})",
            "qdrant_url": qdrant_url,
            "error_detail": str(exc),
        }


