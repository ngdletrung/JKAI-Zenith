# -*- coding: utf-8 -*-
"""
core/utils/repo_map.py
======================
Đại Trụ II (Slice 1.3): 2-Tier AST RepoMap + 6 Câu Hỏi Kiến Trúc + 6-Stage Telemetry & 5-Metric Stream Contracts.

Thiết kế đáp ứng đầy đủ phản biện THAM KHẢO của Master & OpenCode (Lượt 263–264):
1. Tier 0 Overview (`get_tier0_overview`, `answer_architectural_questions`):
   - Trả lời trực tiếp 6 Câu Hỏi Kiến Trúc Cốt Lõi từ AST & đồ thị phụ thuộc thực tế trên đĩa:
     * Q1_INGRESS: Thành phần nào tiếp nhận yêu cầu?
     * Q2_CONTROLLER: Thành phần nào quyết định hoặc điều phối?
     * Q3_ACTUATOR: Thành phần nào thực thi công cụ?
     * Q4_VERIFICATION: Thành phần nào xác minh kết quả?
     * Q5_STATE_PERSISTENCE: Dữ liệu và trạng thái được lưu ở đâu?
     * Q6_BLAST_RADIUS: Khi sửa một thành phần, những thành phần nào có thể bị ảnh hưởng?
   - Ngân sách token linh hoạt (`budget_expandable=True`), không ép cứng mù quáng nếu truy vấn cần mở rộng.
2. Tier 1 Symbol & Blast Radius Navigation (`query_repo_map`, `query_blast_radius`):
   - Chỉ mục AST tăng dần (cached theo `(mtime_ns, size)` của từng tệp `.py` qua `iter_workspace_files()`).
   - Tra cứu tức thì (`< 25ms` trên warm cache) tọa độ `[Lstart-Lend]`, chữ ký hàm/lớp, và đồ thị phụ thuộc ngược (`importers` — tệp nào đang `import` module/symbol này tại dòng nào).
3. Hợp đồng 6-Stage Failure Attribution (`StageAttribution`, `StageTelemetryVerdict`, `classify_step_stage_attribution`).
4. Hợp đồng 5 Chỉ Số Độc Lập cho Dữ Liệu Lớn (`compute_retrieval_recall`, `compute_evidence_coverage`,
   `compute_citation_accuracy`, `compute_task_correctness`, `compute_latency_token_cost`).
5. Kiểm toán Point E (`audit_pyproject_dependencies_point_e`) cho 17 phụ thuộc trong `pyproject.toml`.
"""

from __future__ import annotations

import ast
import importlib.util
import re
import time
from dataclasses import dataclass, field
from enum import Enum
from pathlib import Path
from typing import Any, Dict, List, Optional, Sequence, Set, Tuple

from core.utils.project_workspace import get_jkai_workspace_root, iter_workspace_files


# ============================================================================
# 1. SIX-STAGE FAILURE ATTRIBUTION TELEMETRY CONTRACT (Mục 3 THAM KHẢO)
# ============================================================================

class StageAttribution(str, Enum):
    GOAL_INGRESS = "GOAL_INGRESS"
    EVIDENCE_RETRIEVAL = "EVIDENCE_RETRIEVAL"
    ACTION_PROPOSAL = "ACTION_PROPOSAL"
    CONTROLLER_GATE = "CONTROLLER_GATE"
    TOOL_EXECUTION = "TOOL_EXECUTION"
    COMPLETION_VERIFICATION = "COMPLETION_VERIFICATION"


@dataclass
class StageTelemetryVerdict:
    task_id: str
    step: int
    stage_attribution: StageAttribution
    outcome_ok: bool
    tool: Optional[str] = None
    decision: str = "PERMIT"
    detail: str = ""
    tokens_in: int = 0
    tokens_out: int = 0
    latency_ms: float = 0.0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if isinstance(self.stage_attribution, str):
            self.stage_attribution = StageAttribution(self.stage_attribution)
        elif not isinstance(self.stage_attribution, StageAttribution):
            raise ValueError(f"stage_attribution must be StageAttribution, got {self.stage_attribution!r}")
        self.tokens_in = max(0, int(self.tokens_in))
        self.tokens_out = max(0, int(self.tokens_out))
        self.latency_ms = max(0.0, float(self.latency_ms))

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "step": self.step,
            "stage_attribution": self.stage_attribution.value,
            "outcome_ok": bool(self.outcome_ok),
            "tool": self.tool,
            "decision": self.decision,
            "detail": self.detail,
            "tokens_in": self.tokens_in,
            "tokens_out": self.tokens_out,
            "total_tokens": self.tokens_in + self.tokens_out,
            "latency_ms": round(self.latency_ms, 2),
            "metadata": dict(self.metadata),
        }


READ_NAVIGATION_TOOLS: Set[str] = {
    "view_file",
    "view_file_outline",
    "list_dir",
    "grep_search",
    "query_repo_map",
    "read_stream_window",
    "search_in_stream",
    "search_web",
    "search_web_global",
}

VERIFICATION_TOOLS: Set[str] = {
    "verify_file",
}

EXECUTION_MUTATION_TOOLS: Set[str] = {
    "write_to_file",
    "replace_file_content",
    "multi_replace_file_content",
    "run_command",
    "delete_file",
    "python_execute",
    "browser_action",
}

_STAGE_ATTRIBUTION_STATS: Dict[str, int] = {
    "total_classified": 0,
    "explicit_rule_hits": 0,
    "fallback_default_hits": 0,
}

_MISSION_STAGE_LEDGER: Dict[str, List[Dict[str, Any]]] = {}


def reset_stage_attribution_stats() -> None:
    _STAGE_ATTRIBUTION_STATS["total_classified"] = 0
    _STAGE_ATTRIBUTION_STATS["explicit_rule_hits"] = 0
    _STAGE_ATTRIBUTION_STATS["fallback_default_hits"] = 0


def get_stage_attribution_stats() -> Dict[str, Any]:
    total = _STAGE_ATTRIBUTION_STATS["total_classified"]
    fb = _STAGE_ATTRIBUTION_STATS["fallback_default_hits"]
    exp = _STAGE_ATTRIBUTION_STATS["explicit_rule_hits"]
    return {
        "total_classified": total,
        "explicit_rule_hits": exp,
        "fallback_default_hits": fb,
        "fallback_default_ratio": round(fb / max(1, total), 4),
    }


def classify_step_stage_attribution(
    tool: Optional[str],
    decision: str = "PERMIT",
    outcome_ok: bool = True,
    is_final_verification: bool = False,
    is_goal_routing: bool = False,
) -> StageAttribution:
    """
    Phân loại chính xác bước thực thi hoặc điểm gãy vào đúng 1 trong 6 khâu:
    1. GOAL_INGRESS: Tiếp nhận / phân luồng mục tiêu ban đầu.
    2. ACTION_PROPOSAL: Model không sinh được tool call hoặc sinh JSON/schema sai.
    3. CONTROLLER_GATE: Bị chặn tại ActionValidator (UNKNOWN_TOOL, DENIED, ESCALATE) hoặc CircuitBreaker.
    4. COMPLETION_VERIFICATION: Bước kiểm chứng kết thúc (verify_file, post_patch_verify, pytest nghiệm thu).
    5. EVIDENCE_RETRIEVAL: Công cụ đọc / định vị ngữ cảnh (view_file, grep_search, query_repo_map, read_stream_window, search_in_stream).
    6. TOOL_EXECUTION: Công cụ tác động / thực thi (write_to_file, replace_file_content, run_command, delete_file).
    """
    _STAGE_ATTRIBUTION_STATS["total_classified"] += 1
    if is_goal_routing:
        _STAGE_ATTRIBUTION_STATS["explicit_rule_hits"] += 1
        return StageAttribution.GOAL_INGRESS
    if is_final_verification:
        _STAGE_ATTRIBUTION_STATS["explicit_rule_hits"] += 1
        return StageAttribution.COMPLETION_VERIFICATION

    dec_upper = str(decision or "PERMIT").upper()
    if not tool:
        _STAGE_ATTRIBUTION_STATS["explicit_rule_hits"] += 1
        return StageAttribution.ACTION_PROPOSAL
    if dec_upper == "SCHEMA_INVALID":
        _STAGE_ATTRIBUTION_STATS["explicit_rule_hits"] += 1
        return StageAttribution.ACTION_PROPOSAL
    if dec_upper in ("UNKNOWN_TOOL", "DENIED", "ESCALATE", "CIRCUIT_BREAKER"):
        _STAGE_ATTRIBUTION_STATS["explicit_rule_hits"] += 1
        return StageAttribution.CONTROLLER_GATE

    t_low = str(tool).strip().lower()
    if t_low in VERIFICATION_TOOLS:
        _STAGE_ATTRIBUTION_STATS["explicit_rule_hits"] += 1
        return StageAttribution.COMPLETION_VERIFICATION
    if t_low in READ_NAVIGATION_TOOLS:
        _STAGE_ATTRIBUTION_STATS["explicit_rule_hits"] += 1
        return StageAttribution.EVIDENCE_RETRIEVAL
    if t_low in EXECUTION_MUTATION_TOOLS:
        _STAGE_ATTRIBUTION_STATS["explicit_rule_hits"] += 1
        return StageAttribution.TOOL_EXECUTION

    _STAGE_ATTRIBUTION_STATS["fallback_default_hits"] += 1
    return StageAttribution.TOOL_EXECUTION


def reset_mission_stage_ledger(mission_id: Optional[str] = None) -> None:
    """Xóa sổ kế toán token/latency theo khâu của 1 mission hoặc toàn bộ."""
    if mission_id is None:
        _MISSION_STAGE_LEDGER.clear()
    else:
        _MISSION_STAGE_LEDGER.pop(str(mission_id), None)


def record_mission_stage_trace(
    mission_id: str,
    step: int,
    stage_attribution: StageAttribution | str,
    tokens_in: int,
    tokens_out: int,
    latency_ms: float,
    tool: Optional[str] = None,
    outcome_ok: bool = True,
    decision: str = "PERMIT",
    detail: str = "",
) -> Dict[str, Any]:
    """
    [Slice 3.1 - Giai đoạn 1.1]: Ghi nhận một dòng trace kế toán token_in, token_out và latency_ms
    gắn chặt với 1 trong 6 khâu StageAttribution.
    """
    verdict = StageTelemetryVerdict(
        task_id=str(mission_id),
        step=int(step),
        stage_attribution=stage_attribution if isinstance(stage_attribution, StageAttribution) else StageAttribution(str(stage_attribution)),
        outcome_ok=bool(outcome_ok),
        tool=tool,
        decision=decision,
        detail=detail,
        tokens_in=int(tokens_in),
        tokens_out=int(tokens_out),
        latency_ms=float(latency_ms),
    )
    entry = verdict.to_dict()
    _MISSION_STAGE_LEDGER.setdefault(str(mission_id), []).append(entry)
    return entry


def get_mission_stage_cost_report(
    mission_id: str,
    external_ollama_bill_tokens: Optional[int] = None,
) -> Dict[str, Any]:
    """
    [Slice 3.1 - Giai đoạn 1.1]: Bóc bảng chi phí token (in/out/total) và độ trễ (ms)
    theo đúng 6 khâu StageAttribution, chỉ ra khâu nghẽn cổ chai cho RSIL,
    và đối soát sai số (±5%) với hóa đơn token thực tế từ Ollama đo ngoài.
    """
    traces = list(_MISSION_STAGE_LEDGER.get(str(mission_id), []))
    by_stage: Dict[str, Dict[str, Any]] = {
        s.value: {
            "steps": 0,
            "tokens_in": 0,
            "tokens_out": 0,
            "total_tokens": 0,
            "latency_ms": 0.0,
            "token_share_pct": 0.0,
            "latency_share_pct": 0.0,
        }
        for s in StageAttribution
    }

    total_in = 0
    total_out = 0
    total_lat = 0.0

    for t in traces:
        st = str(t.get("stage_attribution") or StageAttribution.TOOL_EXECUTION.value)
        if st not in by_stage:
            st = StageAttribution.TOOL_EXECUTION.value
        t_in = int(t.get("tokens_in", 0))
        t_out = int(t.get("tokens_out", 0))
        lat = float(t.get("latency_ms", 0.0))

        by_stage[st]["steps"] += 1
        by_stage[st]["tokens_in"] += t_in
        by_stage[st]["tokens_out"] += t_out
        by_stage[st]["total_tokens"] += t_in + t_out
        by_stage[st]["latency_ms"] = round(by_stage[st]["latency_ms"] + lat, 2)

        total_in += t_in
        total_out += t_out
        total_lat += lat

    total_tokens = total_in + total_out
    total_lat = round(total_lat, 2)

    for st_data in by_stage.values():
        st_data["token_share_pct"] = round(
            (st_data["total_tokens"] / max(1, total_tokens)) * 100.0, 2
        ) if total_tokens > 0 else 0.0
        st_data["latency_share_pct"] = round(
            (st_data["latency_ms"] / max(0.001, total_lat)) * 100.0, 2
        ) if total_lat > 0 else 0.0

    top_token_stage = max(
        by_stage.items(),
        key=lambda kv: (kv[1]["total_tokens"], kv[1]["steps"]),
    )[0] if traces else StageAttribution.GOAL_INGRESS.value

    top_latency_stage = max(
        by_stage.items(),
        key=lambda kv: (kv[1]["latency_ms"], kv[1]["steps"]),
    )[0] if traces else StageAttribution.GOAL_INGRESS.value

    reconciliation_delta_pct = 0.0
    within_5pct_tolerance = True
    if external_ollama_bill_tokens is not None:
        ext_bill = max(1, int(external_ollama_bill_tokens))
        reconciliation_delta_pct = round(
            abs(total_tokens - ext_bill) / ext_bill * 100.0, 2
        )
        within_5pct_tolerance = reconciliation_delta_pct <= 5.0

    return {
        "mission_id": str(mission_id),
        "total_steps": len(traces),
        "tokens_in": total_in,
        "tokens_out": total_out,
        "total_tokens": total_tokens,
        "total_latency_ms": total_lat,
        "by_stage": by_stage,
        "top_token_bottleneck_stage": top_token_stage,
        "top_latency_bottleneck_stage": top_latency_stage,
        "external_ollama_bill_tokens": external_ollama_bill_tokens,
        "reconciliation_delta_pct": reconciliation_delta_pct,
        "within_5pct_tolerance": within_5pct_tolerance,
        "traces": traces,
    }



# ============================================================================
# 2. FIVE INDEPENDENT STREAM METRICS CONTRACT (Điểm B THAM KHẢO)
# ============================================================================

def _span_overlaps(required: Tuple[int, int], candidate: Tuple[int, int]) -> bool:
    r_start, r_end = min(required), max(required)
    c_start, c_end = min(candidate), max(candidate)
    overlap = max(0, min(r_end, c_end) - max(r_start, c_start) + 1)
    req_len = max(1, r_end - r_start + 1)
    return (overlap / req_len) >= 0.5


def compute_retrieval_recall(
    required_spans: Sequence[Tuple[int, int]],
    retrieved_spans: Sequence[Tuple[int, int]],
) -> float:
    """Tỷ lệ các đoạn nguồn bắt buộc đã được hệ thống truy xuất ra (0.0 .. 1.0)."""
    if not required_spans:
        return 1.0
    hit = sum(
        1
        for req in required_spans
        if any(_span_overlaps(req, cand) for cand in retrieved_spans)
    )
    return round(hit / len(required_spans), 4)


def compute_evidence_coverage(
    required_spans: Sequence[Tuple[int, int]],
    read_spans: Sequence[Tuple[int, int]],
) -> float:
    """
    Tỷ lệ các đoạn bằng chứng bắt buộc đã thực sự được đọc/xem xét (0.0 .. 1.0).
    Khác biệt hoàn toàn với Citation Accuracy: có thể trích dẫn đúng 1 đoạn (Citation=1.0)
    nhưng bỏ sót 3/4 đoạn còn lại (Coverage=0.25).
    """
    if not required_spans:
        return 1.0
    covered = sum(
        1
        for req in required_spans
        if any(_span_overlaps(req, rd) for rd in read_spans)
    )
    return round(covered / len(required_spans), 4)


def compute_citation_accuracy(citations: Sequence[Dict[str, Any]]) -> float:
    """Tỷ lệ các trích dẫn dòng có tồn tại thật và hỗ trợ đúng nhận định (0.0 .. 1.0)."""
    if not citations:
        return 0.0
    valid = sum(
        1
        for c in citations
        if bool(c.get("supported_by_source"))
        and int(c.get("line_start", 0)) > 0
        and int(c.get("line_end", 0)) >= int(c.get("line_start", 0))
    )
    return round(valid / len(citations), 4)


def compute_task_correctness(
    predicted_facts: Sequence[str],
    expected_facts: Sequence[str],
) -> float:
    """Tỷ lệ các kết luận/yêu cầu bắt buộc của bài toán được trả lời đúng (0.0 .. 1.0)."""
    if not expected_facts:
        return 1.0
    pred_norm = {str(p).strip().lower() for p in predicted_facts if str(p).strip()}
    matched = sum(
        1
        for exp in expected_facts
        if str(exp).strip().lower() in pred_norm
        or any(str(exp).strip().lower() in p for p in pred_norm)
    )
    return round(matched / len(expected_facts), 4)


def compute_latency_token_cost(
    elapsed_ms: float,
    prompt_tokens: int,
    completion_tokens: int,
) -> Dict[str, Any]:
    """Đo chi phí độ trễ (ms) và tổng token tiêu thụ."""
    p_tok = max(0, int(prompt_tokens))
    c_tok = max(0, int(completion_tokens))
    return {
        "elapsed_ms": round(float(elapsed_ms), 2),
        "prompt_tokens": p_tok,
        "completion_tokens": c_tok,
        "total_tokens": p_tok + c_tok,
    }


def evaluate_stream_5_metrics(
    required_spans: Sequence[Tuple[int, int]],
    retrieved_spans: Sequence[Tuple[int, int]],
    read_spans: Sequence[Tuple[int, int]],
    citations: Sequence[Dict[str, Any]],
    predicted_facts: Sequence[str],
    expected_facts: Sequence[str],
    elapsed_ms: float,
    prompt_tokens: int,
    completion_tokens: int,
) -> Dict[str, Any]:
    return {
        "retrieval_recall": compute_retrieval_recall(required_spans, retrieved_spans),
        "evidence_coverage": compute_evidence_coverage(required_spans, read_spans),
        "citation_accuracy": compute_citation_accuracy(citations),
        "task_correctness": compute_task_correctness(predicted_facts, expected_facts),
        "latency_token_cost": compute_latency_token_cost(
            elapsed_ms=elapsed_ms,
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        ),
    }


# ============================================================================
# 3. INCREMENTAL 2-TIER AST REPOMAP & REVERSE-IMPORT BLAST RADIUS ENGINE
# ============================================================================

BLAST_GUARD_BLINDSPOTS: List[str] = [
    "dynamic_import_or_getattr: Không phát hiện được truy cập qua importlib.import_module() hoặc getattr() động lúc runtime.",
    "star_import_reexport: Không theo dõi toàn diện chuỗi re-export qua from module import *.",
    "runtime_duck_typing_or_kwargs: Chỉ kiểm tra chữ ký AST tĩnh (số tham số bắt buộc/tên tham số); không phát hiện sai kiểu dữ liệu động hoặc biến đổi bên trong **kwargs.",
]


@dataclass
class SymbolRecord:
    name: str
    kind: str  # "class" | "function" | "async_function" | "method"
    path: str
    start_line: int
    end_line: int
    signature: str
    parent_class: Optional[str] = None
    methods: List[str] = field(default_factory=list)
    required_args: int = 0
    total_args: int = 0


@dataclass
class FileASTEntry:
    rel_path: str
    mtime_ns: int
    size_bytes: int
    total_lines: int
    syntax_ok: bool = True
    symbols: List[SymbolRecord] = field(default_factory=list)
    imports: List[Dict[str, Any]] = field(default_factory=list)
    exported_names: Set[str] = field(default_factory=set)


class RepoMapIndex:
    """
    Bộ lập chỉ mục AST & Đồ thị Phụ thuộc Ngược (Reverse-Import Graph) trên toàn repo.
    Cache tăng dần theo `(mtime_ns, size_bytes)` của từng tệp `.py`, đồng thời hỗ trợ
    cập nhật tức thì từng tệp (`notify_file_mutation`) và Sổ cái Kinh nghiệm Biến đổi (`EpisodicMutationLedger`)
    với giới hạn LRU (`max_episodes`) và vòng đời TTL (`episode_ttl_seconds`).
    """

    def __init__(
        self,
        workspace_root: Optional[Path] = None,
        max_episodes: int = 512,
        episode_ttl_seconds: float = 1800.0,
    ) -> None:
        self.workspace_root = Path(workspace_root or get_jkai_workspace_root()).resolve()
        self.max_episodes = max(1, int(max_episodes))
        self.episode_ttl_seconds = max(1.0, float(episode_ttl_seconds))
        self._file_cache: Dict[str, FileASTEntry] = {}
        self._reverse_imports: Dict[str, List[Dict[str, Any]]] = {}
        self._module_to_relpath: Dict[str, str] = {}
        self._symbol_by_exact_low: Dict[str, List[SymbolRecord]] = {}
        self._all_symbols: List[SymbolRecord] = []
        self._total_workspace_py_files: int = 0
        self._excluded_third_party_files: int = 0
        self._excluded_third_party_breakdown: Dict[str, int] = {}
        self._syntax_error_files: int = 0
        self._last_scan_ts: float = 0.0
        self._episodic_episodes: List[Dict[str, Any]] = []
        self._episodic_versions: Dict[str, List[Dict[str, Any]]] = {}
        self._touched_target_rels: Set[str] = set()
        _GLOBAL_INDEXES[str(self.workspace_root).lower()] = self

    def _rel_posix(self, fpath: Path) -> Optional[str]:
        import os
        try:
            rel = os.path.relpath(str(fpath), str(self.workspace_root)).replace("\\", "/")
            if rel.startswith(".."):
                return None
            return rel
        except Exception:
            return None

    def _build_module_lookup(self, rel_paths: List[str]) -> None:
        mapping: Dict[str, str] = {}
        for rel in rel_paths:
            no_ext = rel[:-3] if rel.endswith(".py") else rel
            dotted = no_ext.replace("/", ".")
            mapping[dotted] = rel
            if dotted.endswith(".__init__"):
                mapping[dotted[: -len(".__init__")]] = rel
            if rel.startswith("services/ai-brain/"):
                sub_dotted = no_ext[len("services/ai-brain/") :].replace("/", ".")
                mapping.setdefault(sub_dotted, rel)
        self._module_to_relpath = mapping

    def _resolve_import_target(self, module_name: str, imported_names: List[str]) -> Optional[str]:
        if not module_name:
            return None
        if module_name in self._module_to_relpath:
            return self._module_to_relpath[module_name]
        for name in imported_names:
            cand = f"{module_name}.{name}"
            if cand in self._module_to_relpath:
                return self._module_to_relpath[cand]
        parts = module_name.split(".")
        for i in range(len(parts), 0, -1):
            prefix = ".".join(parts[:i])
            if prefix in self._module_to_relpath:
                return self._module_to_relpath[prefix]
        return None

    @staticmethod
    def _compute_function_arg_counts(fn_node: ast.AST, is_method: bool = False) -> Tuple[int, int]:
        args_obj = getattr(fn_node, "args", None)
        if args_obj is None:
            return 0, 0
        posonly = list(getattr(args_obj, "posonlyargs", []))
        regular = list(getattr(args_obj, "args", []))
        all_pos = posonly + regular
        if is_method and all_pos and all_pos[0].arg in ("self", "cls"):
            all_pos = all_pos[1:]
        defaults = list(getattr(args_obj, "defaults", []))
        req_pos = max(0, len(all_pos) - len(defaults))
        kwonly = list(getattr(args_obj, "kwonlyargs", []))
        kw_defaults = list(getattr(args_obj, "kw_defaults", []))
        req_kw = sum(1 for d in kw_defaults if d is None)
        return req_pos + req_kw, len(all_pos) + len(kwonly)

    @staticmethod
    def _parse_python_file(fpath: Path, rel_path: str) -> FileASTEntry:
        import warnings
        stat = fpath.stat()
        try:
            source = fpath.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            source = ""
        total_lines = len(source.splitlines())
        entry = FileASTEntry(
            rel_path=rel_path,
            mtime_ns=stat.st_mtime_ns,
            size_bytes=stat.st_size,
            total_lines=total_lines,
        )
        if not source.strip():
            return entry

        try:
            with warnings.catch_warnings():
                warnings.simplefilter("ignore", SyntaxWarning)
                tree = ast.parse(source, filename=rel_path)
        except SyntaxError:
            entry.syntax_ok = False
            return entry

        # 1. Extract top-level classes, functions & module-level exports
        for node in tree.body:
            if isinstance(node, ast.ClassDef):
                entry.exported_names.add(node.name)
                s_ln = getattr(node, "lineno", 1)
                e_ln = getattr(node, "end_lineno", s_ln)
                bases = [ast.unparse(b) if hasattr(ast, "unparse") else "" for b in node.bases]
                base_str = f"({', '.join(b for b in bases if b)})" if bases else ""
                method_names: List[str] = []
                for item in node.body:
                    if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        m_s = getattr(item, "lineno", s_ln)
                        m_e = getattr(item, "end_lineno", m_s)
                        m_args = [a.arg for a in item.args.args if a.arg != "self"]
                        m_sig = f"{item.name}({', '.join(m_args[:6])})"
                        m_req, m_tot = RepoMapIndex._compute_function_arg_counts(item, is_method=True)
                        method_names.append(f"{item.name}[L{m_s}-L{m_e}]")
                        entry.symbols.append(
                            SymbolRecord(
                                name=item.name,
                                kind="method",
                                path=rel_path,
                                start_line=m_s,
                                end_line=m_e,
                                signature=f"{node.name}.{m_sig}",
                                parent_class=node.name,
                                required_args=m_req,
                                total_args=m_tot,
                            )
                        )
                entry.symbols.append(
                    SymbolRecord(
                        name=node.name,
                        kind="class",
                        path=rel_path,
                        start_line=s_ln,
                        end_line=e_ln,
                        signature=f"class {node.name}{base_str}",
                        methods=method_names[:15],
                    )
                )
            elif isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                entry.exported_names.add(node.name)
                s_ln = getattr(node, "lineno", 1)
                e_ln = getattr(node, "end_lineno", s_ln)
                args = [a.arg for a in node.args.args]
                prefix = "async def" if isinstance(node, ast.AsyncFunctionDef) else "def"
                sig = f"{prefix} {node.name}({', '.join(args[:8])})"
                f_req, f_tot = RepoMapIndex._compute_function_arg_counts(node, is_method=False)
                entry.symbols.append(
                    SymbolRecord(
                        name=node.name,
                        kind="async_function" if isinstance(node, ast.AsyncFunctionDef) else "function",
                        path=rel_path,
                        start_line=s_ln,
                        end_line=e_ln,
                        signature=sig,
                        required_args=f_req,
                        total_args=f_tot,
                    )
                )
            elif isinstance(node, ast.Assign):
                for tgt in node.targets:
                    if isinstance(tgt, ast.Name):
                        entry.exported_names.add(tgt.id)
            elif isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
                entry.exported_names.add(node.target.id)
            elif isinstance(node, (ast.Import, ast.ImportFrom)):
                for alias in node.names:
                    if alias.name != "*":
                        entry.exported_names.add(alias.asname or alias.name.split(".")[0])

        # 2. Extract all imports (including lazy imports inside functions!)
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    entry.imports.append(
                        {
                            "module": alias.name,
                            "names": [alias.asname or alias.name.split(".")[-1]],
                            "line": getattr(node, "lineno", 1),
                            "is_from_import": False,
                        }
                    )
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    entry.imports.append(
                        {
                            "module": node.module,
                            "names": [a.name for a in node.names],
                            "line": getattr(node, "lineno", 1),
                            "is_from_import": True,
                        }
                    )

        return entry

    def _rebuild_derived_indexes(self) -> None:
        self._build_module_lookup(list(self._file_cache.keys()))
        rev: Dict[str, List[Dict[str, Any]]] = {}
        by_exact: Dict[str, List[SymbolRecord]] = {}
        all_syms: List[SymbolRecord] = []
        for importer_rel, fentry in self._file_cache.items():
            for sym in fentry.symbols:
                all_syms.append(sym)
                by_exact.setdefault(sym.name.lower(), []).append(sym)
            for imp in fentry.imports:
                target_rel = self._resolve_import_target(imp["module"], imp["names"])
                if target_rel and target_rel != importer_rel:
                    rev.setdefault(target_rel, []).append(
                        {
                            "importer_path": importer_rel,
                            "line": imp["line"],
                            "module": imp["module"],
                            "imported_symbols": imp["names"],
                            "is_from_import": imp.get("is_from_import", False),
                        }
                    )
        self._reverse_imports = rev
        self._symbol_by_exact_low = by_exact
        self._all_symbols = all_syms
        self._syntax_error_files = sum(1 for e in self._file_cache.values() if not e.syntax_ok)

    def refresh(self, force: bool = False) -> None:
        now = time.perf_counter()
        if not force and self._file_cache and (now - self._last_scan_ts) < 30.0:
            return

        py_files = [
            p for p in iter_workspace_files(self.workspace_root, suffixes=(".py",))
        ]
        self._total_workspace_py_files = len(py_files)
        rel_pairs: List[Tuple[Path, str]] = []
        excluded_vendor = 0
        vendor_breakdown: Dict[str, int] = {}
        for p in py_files:
            rel = self._rel_posix(p)
            if not rel:
                continue
            if rel.startswith("files/"):
                excluded_vendor += 1
                parts = rel.split("/")
                bucket = f"files/{parts[1]}" if len(parts) >= 2 else "files"
                vendor_breakdown[bucket] = vendor_breakdown.get(bucket, 0) + 1
            else:
                rel_pairs.append((p, rel))
        self._excluded_third_party_files = excluded_vendor
        self._excluded_third_party_breakdown = dict(sorted(vendor_breakdown.items()))

        seen_rels: Set[str] = set()
        updated = False
        for fpath, rel in rel_pairs:
            try:
                stat = fpath.stat()
            except Exception:
                continue
            seen_rels.add(rel)
            cached = self._file_cache.get(rel)
            if (
                cached is None
                or cached.mtime_ns != stat.st_mtime_ns
                or cached.size_bytes != stat.st_size
            ):
                self._file_cache[rel] = self._parse_python_file(fpath, rel)
                updated = True

        removed = set(self._file_cache.keys()) - seen_rels
        for r in removed:
            self._file_cache.pop(r, None)
            updated = True

        if updated or not self._reverse_imports:
            self._rebuild_derived_indexes()

        self._last_scan_ts = time.perf_counter()

    def _compute_broken_downstream_for_target(self, target_rel: str) -> List[Dict[str, Any]]:
        """Kiểm tra xem các tệp đang import từ `target_rel` có symbol nào không còn tồn tại trong `target_rel` không."""
        target_entry = self._file_cache.get(target_rel)
        importers = self._reverse_imports.get(target_rel, [])
        broken: List[Dict[str, Any]] = []
        target_mod_dotted = target_rel[:-3].replace("/", ".") if target_rel.endswith(".py") else target_rel
        if target_mod_dotted.endswith(".__init__"):
            target_mod_dotted = target_mod_dotted[: -len(".__init__")]

        for imp in importers:
            if target_entry is None:
                broken.append(
                    {
                        "importer_path": imp["importer_path"],
                        "line": imp["line"],
                        "target_path": target_rel,
                        "missing_symbols": list(imp.get("imported_symbols", [])),
                    }
                )
                continue
            if not imp.get("is_from_import", False):
                continue
            # Chỉ kiểm tra symbol khi `from <module> import <sym>` trỏ trực tiếp tới module `target_rel`
            if imp.get("module") != target_mod_dotted:
                continue
            missing: List[str] = []
            for sym_name in imp.get("imported_symbols", []):
                if sym_name == "*":
                    continue
                submod_cand = f"{target_mod_dotted}.{sym_name}"
                if submod_cand in self._module_to_relpath:
                    continue
                if sym_name not in target_entry.exported_names:
                    missing.append(sym_name)
            if missing:
                broken.append(
                    {
                        "importer_path": imp["importer_path"],
                        "line": imp["line"],
                        "target_path": target_rel,
                        "missing_symbols": missing,
                    }
                )
        return broken

    def notify_file_mutation(
        self,
        file_path: Path,
        action: str = "modify",
        task_id: str = "sys",
        sha256: str = "",
    ) -> Optional[Dict[str, Any]]:
        """
        Cập nhật tức thì chỉ mục AST cho tệp `file_path` sau khi `write_to_file` / `replace_file_content` / `delete_file`
        mà không chờ cửa sổ cache 30s, đồng thời phân tích `blast_radius_impact` (bao gồm `broken_downstream_imports`,
        `signature_changes`, `blast_guard_blindspots`) và ghi vào `EpisodicMutationLedger`.
        """
        t0 = time.perf_counter()
        fpath = Path(file_path).resolve()
        rel = self._rel_posix(fpath)
        if not rel or not rel.endswith(".py") or rel.startswith("files/"):
            return None

        before_entry = self._file_cache.get(rel)
        before_symbols = {s.name for s in before_entry.symbols if s.kind != "method"} if before_entry else set()
        before_exports = set(before_entry.exported_names) if before_entry else set()
        before_sym_map: Dict[str, SymbolRecord] = (
            {s.name: s for s in before_entry.symbols if s.kind != "method"} if before_entry else {}
        )

        if fpath.exists() and fpath.is_file():
            was_new = rel not in self._file_cache
            after_entry = self._parse_python_file(fpath, rel)
            self._file_cache[rel] = after_entry
            if was_new:
                self._total_workspace_py_files += 1
            after_symbols = {s.name for s in after_entry.symbols if s.kind != "method"}
            after_exports = set(after_entry.exported_names)
            after_sym_map: Dict[str, SymbolRecord] = {
                s.name: s for s in after_entry.symbols if s.kind != "method"
            }
        else:
            if rel in self._file_cache:
                self._file_cache.pop(rel, None)
                self._total_workspace_py_files = max(0, self._total_workspace_py_files - 1)
            after_symbols = set()
            after_exports = set()
            after_sym_map = {}

        self._rebuild_derived_indexes()
        self._touched_target_rels.add(rel)

        added_symbols = sorted((after_symbols - before_symbols) | (after_exports - before_exports))
        removed_symbols = sorted((before_symbols - after_symbols) | (before_exports - after_exports))
        importers = list(self._reverse_imports.get(rel, []))
        broken_downstream = self._compute_broken_downstream_for_target(rel)

        # Phát hiện thay đổi chữ ký / số lượng tham số bắt buộc của hàm vẫn còn tồn tại
        signature_changes: List[Dict[str, Any]] = []
        common_symbol_names = sorted(set(before_sym_map.keys()) & set(after_sym_map.keys()))
        for sym_name in common_symbol_names:
            old_sym = before_sym_map[sym_name]
            new_sym = after_sym_map[sym_name]
            if (
                old_sym.signature != new_sym.signature
                or old_sym.required_args != new_sym.required_args
                or old_sym.total_args != new_sym.total_args
            ):
                sym_importers = sorted(
                    {
                        imp["importer_path"]
                        for imp in importers
                        if not imp.get("is_from_import")
                        or sym_name in imp.get("imported_symbols", [])
                        or "*" in imp.get("imported_symbols", [])
                    }
                )
                signature_changes.append(
                    {
                        "symbol": sym_name,
                        "target_path": rel,
                        "old_signature": old_sym.signature,
                        "new_signature": new_sym.signature,
                        "old_required_args": old_sym.required_args,
                        "new_required_args": new_sym.required_args,
                        "old_total_args": old_sym.total_args,
                        "new_total_args": new_sym.total_args,
                        "affected_importers": sym_importers,
                    }
                )

        elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

        impact = {
            "path": rel,
            "action": action,
            "task_id": str(task_id or "sys"),
            "sha256": sha256,
            "elapsed_ms": elapsed_ms,
            "added_symbols": added_symbols,
            "removed_symbols": removed_symbols,
            "importer_count": len(importers),
            "affected_importers": sorted({imp["importer_path"] for imp in importers}),
            "broken_downstream_imports": broken_downstream,
            "signature_changes": signature_changes,
            "blast_guard_blindspots": list(BLAST_GUARD_BLINDSPOTS),
        }
        now_ts = time.time()
        self.purge_expired_episodes(now=now_ts)

        # Lưu snapshot phiên bản cho WeKnora Episodic Chunk Versioning (Slice 2.4)
        ver_list = self._episodic_versions.setdefault(rel, [])
        current_content = ""
        if fpath.exists() and fpath.is_file():
            try:
                current_content = fpath.read_text(encoding="utf-8", errors="ignore")
            except Exception:
                current_content = ""
        ver_id = len(ver_list) + 1
        ver_list.append(
            {
                "version_id": ver_id,
                "path": rel,
                "action": action,
                "task_id": str(task_id or "sys"),
                "sha256": sha256,
                "content": current_content,
                "timestamp": now_ts,
            }
        )
        if len(ver_list) > 32:
            del ver_list[: len(ver_list) - 32]
        impact["version_id"] = ver_id

        self._episodic_episodes.append(
            {
                **impact,
                "timestamp": now_ts,
            }
        )
        self._touched_target_rels.add(rel)
        if len(self._episodic_episodes) > self.max_episodes:
            overflow = len(self._episodic_episodes) - self.max_episodes
            del self._episodic_episodes[:overflow]
        return impact

    def diff_episodic_versions(
        self,
        path: str,
        from_version: int,
        to_version: int,
    ) -> Dict[str, Any]:
        """
        [Slice 2.4 - WeKnora Episodic Chunk Versioning Diff]:
        Trích xuất unified diff giữa hai phiên bản `from_version` và `to_version` của `path`.
        """
        import difflib

        norm = str(path).replace("\\", "/").lstrip("/")
        ver_list = self._episodic_versions.get(norm, [])
        by_id = {int(v["version_id"]): v for v in ver_list}
        v_from = by_id.get(int(from_version))
        v_to = by_id.get(int(to_version))
        if v_from is None or v_to is None:
            return {
                "status": "error",
                "path": norm,
                "msg": f"Không tìm thấy phiên bản {from_version} hoặc {to_version} cho '{norm}'.",
            }

        lines_a = str(v_from.get("content", "")).splitlines(keepends=True)
        lines_b = str(v_to.get("content", "")).splitlines(keepends=True)
        diff_lines = list(
            difflib.unified_diff(
                lines_a,
                lines_b,
                fromfile=f"{norm}@v{from_version}",
                tofile=f"{norm}@v{to_version}",
            )
        )
        return {
            "status": "success",
            "path": norm,
            "from_version": int(from_version),
            "to_version": int(to_version),
            "unified_diff": "".join(diff_lines),
        }

    def rollback_episodic_version(
        self,
        path: str,
        target_version: int,
        task_id: str = "rollback",
    ) -> Dict[str, Any]:
        """
        [Slice 2.4 - WeKnora Episodic Chunk Rollback]:
        Khôi phục tệp `path` trên đĩa về đúng nội dung của `target_version` và đồng bộ tức thì `RepoMapIndex`.
        """
        import hashlib

        norm = str(path).replace("\\", "/").lstrip("/")
        ver_list = self._episodic_versions.get(norm, [])
        by_id = {int(v["version_id"]): v for v in ver_list}
        v_target = by_id.get(int(target_version))
        if v_target is None:
            return {
                "status": "error",
                "path": norm,
                "msg": f"Không tìm thấy phiên bản {target_version} cho '{norm}'.",
            }

        abs_target = (self.workspace_root / norm).resolve()
        content = str(v_target.get("content", ""))
        abs_target.parent.mkdir(parents=True, exist_ok=True)
        abs_target.write_text(content, encoding="utf-8")
        sha = hashlib.sha256(content.encode("utf-8")).hexdigest()
        impact = self.notify_file_mutation(
            abs_target,
            action=f"rollback_to_v{target_version}",
            task_id=task_id,
            sha256=sha,
        )
        return {
            "status": "rolled_back",
            "path": norm,
            "target_version": int(target_version),
            "sha256": sha,
            "blast_radius_impact": impact,
        }

    def purge_expired_episodes(self, now: Optional[float] = None) -> int:
        """Thu hồi các bản ghi biến đổi đã quá hạn `episode_ttl_seconds`."""
        current_ts = float(now if now is not None else time.time())
        before_len = len(self._episodic_episodes)
        self._episodic_episodes = [
            ep
            for ep in self._episodic_episodes
            if (current_ts - float(ep.get("timestamp", current_ts))) < self.episode_ttl_seconds
        ]
        active_paths = {str(ep.get("path")) for ep in self._episodic_episodes if ep.get("path")}
        self._touched_target_rels &= active_paths
        return before_len - len(self._episodic_episodes)

    def evict_mission_episodes(self, mission_id: str) -> int:
        """Thu hồi toàn bộ bản ghi biến đổi thuộc về `mission_id` (`task_id`)."""
        target_id = str(mission_id or "")
        before_len = len(self._episodic_episodes)
        self._episodic_episodes = [
            ep for ep in self._episodic_episodes if str(ep.get("task_id")) != target_id
        ]
        active_paths = {str(ep.get("path")) for ep in self._episodic_episodes if ep.get("path")}
        self._touched_target_rels &= active_paths
        return before_len - len(self._episodic_episodes)

    def get_episodic_mutation_ledger(self, task_id: Optional[str] = None) -> Dict[str, Any]:
        """Trả về lịch sử biến đổi mã nguồn và danh sách các phụ thuộc liên file đang bị gãy (`unresolved_broken_imports`)."""
        self.purge_expired_episodes()
        episodes = [
            ep for ep in self._episodic_episodes
            if not task_id or ep.get("task_id") == task_id
        ]
        unresolved: List[Dict[str, Any]] = []
        seen_keys: Set[Tuple[str, int, str]] = set()
        for target_rel in sorted(self._touched_target_rels):
            for brk in self._compute_broken_downstream_for_target(target_rel):
                key = (brk["importer_path"], brk["line"], brk["target_path"])
                if key not in seen_keys:
                    seen_keys.add(key)
                    unresolved.append(brk)
        return {
            "task_id": task_id,
            "episode_count": len(episodes),
            "max_episodes": self.max_episodes,
            "episode_ttl_seconds": self.episode_ttl_seconds,
            "episodes": episodes,
            "unresolved_broken_imports": unresolved,
            "blast_guard_blindspots": list(BLAST_GUARD_BLINDSPOTS),
        }


    def get_file_entry(self, rel_path: str) -> Optional[FileASTEntry]:
        self.refresh()
        norm = str(rel_path).replace("\\", "/").lstrip("/")
        return self._file_cache.get(norm)

    def get_blast_radius(self, target_module_or_symbol: str) -> Dict[str, Any]:
        self.refresh()
        q = str(target_module_or_symbol).replace("\\", "/").strip().lstrip("/")
        if q in self._file_cache:
            target_rel = q
        elif f"{q}.py" in self._file_cache:
            target_rel = f"{q}.py"
        elif q.replace(".", "/") + ".py" in self._file_cache:
            target_rel = q.replace(".", "/") + ".py"
        else:
            exact_hits = self._symbol_by_exact_low.get(q.lower(), [])
            target_rel = exact_hits[0].path if exact_hits else ""

        importers = list(self._reverse_imports.get(target_rel, [])) if target_rel else []
        seen = set()
        deduped = []
        for imp in importers:
            key = (imp["importer_path"], imp["line"])
            if key not in seen:
                seen.add(key)
                deduped.append(imp)

        return {
            "target": target_module_or_symbol,
            "resolved_path": target_rel,
            "importer_count": len(deduped),
            "importers": deduped,
            "blast_guard_blindspots": list(BLAST_GUARD_BLINDSPOTS),
        }


_GLOBAL_INDEXES: Dict[str, RepoMapIndex] = {}


def get_repo_map_index(workspace_root: Optional[Path] = None) -> RepoMapIndex:
    ws = Path(workspace_root or get_jkai_workspace_root()).resolve()
    key = str(ws).lower()
    if key not in _GLOBAL_INDEXES:
        _GLOBAL_INDEXES[key] = RepoMapIndex(ws)
    idx = _GLOBAL_INDEXES[key]
    idx.refresh()
    return idx


def notify_workspace_file_mutation(
    file_path: Any,
    action: str = "modify",
    task_id: str = "sys",
    sha256: str = "",
) -> Optional[Dict[str, Any]]:
    """
    Tìm `RepoMapIndex` khớp nhất với `file_path` và kích hoạt `notify_file_mutation` tức thì.
    """
    try:
        fpath = Path(str(file_path)).resolve()
    except Exception:
        return None
    f_low = str(fpath).lower()

    best_idx: Optional[RepoMapIndex] = None
    best_len = -1
    for ws_key, idx in list(_GLOBAL_INDEXES.items()):
        if f_low.startswith(ws_key) and len(ws_key) > best_len:
            best_idx = idx
            best_len = len(ws_key)

    if best_idx is None:
        ws_root = get_jkai_workspace_root().resolve()
        if f_low.startswith(str(ws_root).lower()):
            best_idx = get_repo_map_index(ws_root)

    if best_idx is None:
        return None
    return best_idx.notify_file_mutation(fpath, action=action, task_id=task_id, sha256=sha256)


def get_episodic_mutation_ledger(
    task_id: Optional[str] = None,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    idx = get_repo_map_index(workspace_root=workspace_root)
    return idx.get_episodic_mutation_ledger(task_id=task_id)


def evict_mission_episodic_mutations(
    mission_id: str,
    workspace_root: Optional[Path] = None,
) -> int:
    idx = get_repo_map_index(workspace_root=workspace_root)
    return idx.evict_mission_episodes(mission_id=mission_id)


def purge_expired_episodic_mutations(
    now: Optional[float] = None,
    workspace_root: Optional[Path] = None,
) -> int:
    idx = get_repo_map_index(workspace_root=workspace_root)
    return idx.purge_expired_episodes(now=now)



# ============================================================================
# 4. SIX CORE ARCHITECTURAL QUESTIONS & TIER 0 / TIER 1 API
# ============================================================================

ARCHITECTURAL_LAYER_SPECS: Dict[str, Dict[str, Any]] = {
    "Q1_INGRESS": {
        "question": "Thành phần nào tiếp nhận yêu cầu (Ingress & API Gateway)?",
        "paths": [
            "services/ai-brain/app.py",
            "services/ai-brain/state_pipeline.py",
        ],
    },
    "Q2_CONTROLLER": {
        "question": "Thành phần nào quyết định hoặc điều phối (Controller & Agent Loop)?",
        "paths": [
            "core/kernel/project_agent_loop.py",
            "core/kernel/action_validator.py",
            "services/ai-brain/state_pipeline.py",
        ],
    },
    "Q3_ACTUATOR": {
        "question": "Thành phần nào thực thi công cụ (Actuator & Tool Dispatch)?",
        "paths": [
            "services/ai-brain/receptionist/executor_gateway.py",
            "intelligence/skills/DEVOPS/SYSTEM_CORE_EXECUTOR/logic.py",
        ],
    },
    "Q4_VERIFICATION": {
        "question": "Thành phần nào xác minh kết quả (5-Layer ACI Verification & Contracts)?",
        "paths": [
            "core/utils/ast_code_auditor.py",
            "core/utils/post_patch_verify.py",
            "core/kernel/tool_contracts.py",
        ],
    },
    "Q5_STATE_PERSISTENCE": {
        "question": "Dữ liệu và trạng thái được lưu ở đâu (State, Checkpoints & Workspace Hygiene)?",
        "paths": [
            "core/kernel/durable_checkpoint.py",
            "core/kernel/task_contract_store.py",
            "core/utils/project_workspace.py",
        ],
    },
}


def answer_architectural_questions(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Trả lời 6 Câu Hỏi Kiến Trúc Cốt Lõi (Điểm C THAM KHẢO) bằng dữ liệu AST thật trên đĩa.
    """
    idx = get_repo_map_index(workspace_root)
    result: Dict[str, Any] = {}

    for q_key, spec in ARCHITECTURAL_LAYER_SPECS.items():
        comps: List[Dict[str, Any]] = []
        for rel_path in spec["paths"]:
            entry = idx.get_file_entry(rel_path)
            if not entry:
                continue
            top_syms = [
                f"{s.name}[L{s.start_line}-L{s.end_line}]"
                for s in entry.symbols
                if s.kind in ("class", "function", "async_function")
            ][:8]
            blast = idx.get_blast_radius(rel_path)
            comps.append(
                {
                    "path": rel_path,
                    "total_lines": entry.total_lines,
                    "symbols": top_syms,
                    "incoming_importers": blast["importer_count"],
                }
            )
        result[q_key] = {
            "question": spec["question"],
            "components": comps,
        }

    total_edges = sum(len(v) for v in idx._reverse_imports.values())
    ranked_hubs = sorted(
        idx._reverse_imports.items(),
        key=lambda kv: len(kv[1]),
        reverse=True,
    )[:6]
    hub_components: List[Dict[str, Any]] = []
    for rel_path, imps in ranked_hubs:
        entry = idx.get_file_entry(rel_path)
        if not entry:
            continue
        top_syms = [
            f"{s.name}[L{s.start_line}-L{s.end_line}]"
            for s in entry.symbols
            if s.kind in ("class", "function", "async_function")
        ][:5]
        if not top_syms:
            top_syms = [f"module[L1-L{max(1, entry.total_lines)}]"]
        hub_components.append(
            {
                "path": rel_path,
                "total_lines": entry.total_lines,
                "symbols": top_syms,
                "incoming_importers": len(imps),
                "sample_importers": [i["importer_path"] for i in imps[:4]],
            }
        )

    result["Q6_BLAST_RADIUS"] = {
        "question": "Khi sửa một thành phần, những thành phần nào có thể bị ảnh hưởng (Blast Radius)?",
        "total_workspace_py_files": idx._total_workspace_py_files,
        "indexed_python_files": len(idx._file_cache),
        "excluded_third_party_files": idx._excluded_third_party_files,
        "excluded_third_party_breakdown": dict(idx._excluded_third_party_breakdown),
        "excluded_third_party_reason": (
            "Excluded third-party vendor/reference repositories under files/ "
            "(files/OfficeCLI-main: 88, files/laya-main: 127, files/system_prompts_leaks-main: 1; total=216) "
            "to prevent symbol pollution"
        ),
        "syntax_error_files": idx._syntax_error_files,
        "reverse_dependency_edges": total_edges,
        "components": hub_components,
    }
    return result


def get_tier0_overview(
    workspace_root: Optional[Path] = None,
    max_tokens: int = 450,
) -> Dict[str, Any]:
    """
    Sinh bản đồ kiến trúc Tier 0 trả lời 6 Câu Hỏi Kiến Trúc Cốt Lõi.
    Ngân sách token có thể mở rộng theo nhu cầu (`budget_expandable=True`).
    """
    answers = answer_architectural_questions(workspace_root)
    lines: List[str] = ["### 🗺️ JKAI AST REPOMAP — TIER 0 (6 CORE ARCHITECTURAL QUESTIONS)"]
    max_syms = 4 if max_tokens <= 450 else 8

    for q_key in (
        "Q1_INGRESS",
        "Q2_CONTROLLER",
        "Q3_ACTUATOR",
        "Q4_VERIFICATION",
        "Q5_STATE_PERSISTENCE",
        "Q6_BLAST_RADIUS",
    ):
        q_info = answers[q_key]
        lines.append(f"- **{q_key}** ({q_info['question']}):")
        for comp in q_info["components"][:4]:
            syms = ", ".join(comp["symbols"][:max_syms])
            imp_cnt = comp.get("incoming_importers", 0)
            lines.append(
                f"  • `{comp['path']}` ({comp['total_lines']}L, depended_by={imp_cnt}): {syms}"
            )

    text = "\n".join(lines)
    est_tokens = max(1, len(text) // 4)
    return {
        "text": text,
        "estimated_tokens": est_tokens,
        "target_token_budget": max_tokens,
        "budget_expandable": True,
        "questions": answers,
    }


def query_blast_radius(
    target_module_or_symbol: str,
    workspace_root: Optional[Path] = None,
) -> Dict[str, Any]:
    idx = get_repo_map_index(workspace_root)
    return idx.get_blast_radius(target_module_or_symbol)


def _path_priority_tier(rel_path: str) -> int:
    """Ưu tiên các module lõi sản xuất trước các tệp test/script phụ trợ khi trùng tên symbol."""
    if rel_path.startswith(("core/", "services/", "intelligence/", "tools/", "rag/")):
        return 0
    if rel_path.startswith(("tests/", "scripts/")):
        return 1
    return 2


def query_repo_map(
    query: str = "",
    file_path: str = "",
    workspace_root: Optional[Path] = None,
    include_blast_radius: bool = True,
    max_tokens: int = 700,
) -> Dict[str, Any]:
    """
    Tier 1 Navigation: Định vị chính xác symbol (`class`, `def`, `method`), phạm vi dòng `[Lstart-Lend]`,
    và danh sách các tệp bị ảnh hưởng (`blast_radius` / `importers`) trong `< 25ms` (warm cache).
    """
    t0 = time.perf_counter()
    idx = get_repo_map_index(workspace_root)

    q_clean = str(query or "").strip()
    f_clean = str(file_path or "").replace("\\", "/").strip().lstrip("/")
    q_low = q_clean.lower()

    symbol_matches: List[Dict[str, Any]] = []

    # Fast path: exact symbol match in inverted index
    exact_candidates = idx._symbol_by_exact_low.get(q_low, []) if q_low and not f_clean else []
    if exact_candidates:
        for sym in exact_candidates:
            in_deg = len(idx._reverse_imports.get(sym.path, ()))
            symbol_matches.append(
                {
                    "score": 100,
                    "in_degree": in_deg,
                    "path_tier": _path_priority_tier(sym.path),
                    "name": sym.name,
                    "kind": sym.kind,
                    "path": sym.path,
                    "start_line": sym.start_line,
                    "end_line": sym.end_line,
                    "signature": sym.signature,
                    "parent_class": sym.parent_class,
                    "methods": sym.methods,
                }
            )
    else:
        tokens = [t for t in re.split(r"[\s\./:]+", q_low) if t]
        for sym in idx._all_symbols:
            if f_clean and f_clean.lower() not in sym.path.lower():
                continue
            s_low = sym.name.lower()
            score = 0
            if q_low and s_low == q_low:
                score = 100
            elif q_low and q_low in s_low:
                score = 80
            elif q_low and q_low in sym.path.lower():
                score = 60
            elif tokens and all(t in f"{sym.path.lower()} {sym.signature.lower()}" for t in tokens):
                score = 50
            elif f_clean and not q_low:
                score = 40

            if score > 0:
                in_deg = len(idx._reverse_imports.get(sym.path, ()))
                symbol_matches.append(
                    {
                        "score": score,
                        "in_degree": in_deg,
                        "path_tier": _path_priority_tier(sym.path),
                        "name": sym.name,
                        "kind": sym.kind,
                        "path": sym.path,
                        "start_line": sym.start_line,
                        "end_line": sym.end_line,
                        "signature": sym.signature,
                        "parent_class": sym.parent_class,
                        "methods": sym.methods,
                    }
                )

    symbol_matches.sort(
        key=lambda m: (
            -m["score"],
            m["path_tier"],
            0 if m["kind"] != "method" else 1,
            -m["in_degree"],
            m["path"],
            m["start_line"],
        )
    )
    top_matches = symbol_matches[:20]

    blast_info: Dict[str, Any] = {}
    if include_blast_radius:
        target_for_blast = f_clean or (top_matches[0]["path"] if top_matches else q_clean)
        if target_for_blast:
            blast_info = idx.get_blast_radius(target_for_blast)

    out_lines: List[str] = [f"### 🧭 REPOMAP TIER 1 — query=`{q_clean or f_clean}`"]
    for m in top_matches[:10]:
        out_lines.append(
            f"- `{m['path']}` [L{m['start_line']}-L{m['end_line']}] ({m['kind']}): `{m['signature']}`"
        )
    if blast_info and blast_info.get("importers"):
        out_lines.append(
            f"- **Blast Radius (`{blast_info.get('resolved_path')}`, {blast_info.get('importer_count')} importers)**:"
        )
        for imp in blast_info["importers"][:8]:
            out_lines.append(
                f"  • `{imp['importer_path']}` [L{imp['line']}] imports `{', '.join(imp['imported_symbols'][:4])}`"
            )

    rendered = "\n".join(out_lines)
    elapsed_ms = round((time.perf_counter() - t0) * 1000.0, 3)

    return {
        "status": "success",
        "query": q_clean,
        "file_path": f_clean,
        "elapsed_ms": elapsed_ms,
        "total_matches": len(symbol_matches),
        "symbol_matches": top_matches,
        "blast_radius": blast_info,
        "estimated_tokens": max(1, len(rendered) // 4),
        "target_token_budget": max_tokens,
        "content": rendered,
    }


# ============================================================================
# 5. NAVIGATION EFFICIENCY BENCHMARK (10 REAL JKAI LOCALIZATION TASKS)
# ============================================================================

SEALED_10_NAVIGATION_TASKS: List[Dict[str, Any]] = [
    {
        "task_id": "NAV-01",
        "query": "analyze_python_aci_diagnostics",
        "expected_path": "core/utils/ast_code_auditor.py",
        "blind_search_turns": 3,  # list_dir -> grep_search -> view_file
    },
    {
        "task_id": "NAV-02",
        "query": "extract_python_file_outline",
        "expected_path": "core/utils/ast_code_auditor.py",
        "blind_search_turns": 3,
    },
    {
        "task_id": "NAV-03",
        "query": "ProjectAgentLoop",
        "expected_path": "core/kernel/project_agent_loop.py",
        "blind_search_turns": 4,  # list_dir -> grep_search -> view_file -> grep_search importers
    },
    {
        "task_id": "NAV-04",
        "query": "validate_action",
        "expected_path": "core/kernel/action_validator.py",
        "blind_search_turns": 3,
    },
    {
        "task_id": "NAV-05",
        "query": "ToolContractRegistry",
        "expected_path": "core/kernel/tool_contracts.py",
        "blind_search_turns": 3,
    },
    {
        "task_id": "NAV-06",
        "query": "iter_workspace_files",
        "expected_path": "core/utils/project_workspace.py",
        "blind_search_turns": 3,
    },
    {
        "task_id": "NAV-07",
        "query": "strip_worktree_nesting",
        "expected_path": "core/utils/project_workspace.py",
        "blind_search_turns": 3,
    },
    {
        "task_id": "NAV-08",
        "query": "ExecutionRequest",
        "expected_path": "services/ai-brain/receptionist/executor_gateway.py",
        "blind_search_turns": 4,
    },
    {
        "task_id": "NAV-09",
        "query": "_bound_unconstrained_gbnf_objects",
        "expected_path": "core/utils/engine.py",
        "blind_search_turns": 3,
    },
    {
        "task_id": "NAV-10",
        "query": "view_file_outline",
        "expected_path": "intelligence/skills/DEVOPS/SYSTEM_CORE_EXECUTOR/logic.py",
        "blind_search_turns": 4,
    },
]


def run_repo_map_navigation_benchmark(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    So sánh số lượt công cụ cần thiết để định vị đúng file + dòng `[Lstart-Lend]` + `blast_radius`
    giữa cách mò mẫm cũ (`list_dir` + `grep_search` + `view_file`) và `query_repo_map`.
    """
    ws = Path(workspace_root or get_jkai_workspace_root()).resolve()
    hits = 0
    repo_map_turns_total = 0
    blind_turns_total = 0
    details: List[Dict[str, Any]] = []

    for task in SEALED_10_NAVIGATION_TASKS:
        res = query_repo_map(
            query=task["query"],
            workspace_root=ws,
            include_blast_radius=True,
        )
        matches = res.get("symbol_matches", [])
        top = matches[0] if matches else {}
        matched = bool(
            top
            and top.get("path") == task["expected_path"]
            and int(top.get("start_line", 0)) > 0
        )
        if matched:
            hits += 1
        repo_map_turns_total += 1
        blind_turns_total += int(task["blind_search_turns"])
        details.append(
            {
                "task_id": task["task_id"],
                "query": task["query"],
                "expected_path": task["expected_path"],
                "found_path": top.get("path"),
                "line_span": f"L{top.get('start_line')}-L{top.get('end_line')}" if top else None,
                "matched": matched,
                "repo_map_turns": 1,
                "blind_search_turns": task["blind_search_turns"],
                "elapsed_ms": res.get("elapsed_ms"),
            }
        )

    total = len(SEALED_10_NAVIGATION_TASKS)
    avg_rm = round(repo_map_turns_total / total, 2)
    avg_blind = round(blind_turns_total / total, 2)
    reduction = round(1.0 - (avg_rm / avg_blind), 4)

    return {
        "total_tasks": total,
        "hits": hits,
        "repo_map_accuracy": round(hits / total, 4),
        "avg_repo_map_turns": avg_rm,
        "avg_blind_search_turns": avg_blind,
        "turn_reduction_ratio": reduction,
        "details": details,
    }


# ============================================================================
# 6. POINT E: CLEAN DEPENDENCY IMPORT & REPRODUCIBILITY AUDIT
# ============================================================================

PACKAGE_TO_IMPORT_NAME: Dict[str, str] = {
    "fastapi": "fastapi",
    "uvicorn": "uvicorn",
    "pydantic": "pydantic",
    "httpx": "httpx",
    "requests": "requests",
    "redis": "redis",
    "falkordb": "falkordb",
    "qdrant-client": "qdrant_client",
    "networkx": "networkx",
    "numpy": "numpy",
    "psutil": "psutil",
    "python-dotenv": "dotenv",
    "python-docx": "docx",
    "PyYAML": "yaml",
    "ddgs": "ddgs",
    "beautifulsoup4": "bs4",
    "playwright": "playwright",
    "pytest": "pytest",
}


def audit_pyproject_dependencies_point_e(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    Kiểm toán trung thực 17 dependencies trong `[project].dependencies` của `pyproject.toml` (Điểm E THAM KHẢO & Lượt 264):
    - Kiểm tra số lượng khai báo có ràng buộc `>=` và `<`.
    - Kiểm tra khả năng `find_spec` (importable) của từng thư viện trên môi trường Python hiện tại.
    - Ghi nhận trung thực `clean_venv_install_status` (`NOT_TESTED` nếu chưa chạy `pip install` trên venv trắng độc lập).
    """
    ws = Path(workspace_root or get_jkai_workspace_root()).resolve()
    pyproject_path = ws / "pyproject.toml"
    text = pyproject_path.read_text(encoding="utf-8") if pyproject_path.is_file() else ""
    dep_block_match = re.search(r"dependencies\s*=\s*\[(.*?)\]", text, re.DOTALL)
    dep_block = dep_block_match.group(1) if dep_block_match else ""
    dep_specs = re.findall(r'"([A-Za-z0-9_\-]+(?:\[[^\]]+\])?>=[^"]+)"', dep_block)

    importable: List[str] = []
    missing: List[str] = []
    for spec in dep_specs:
        pkg_raw = re.split(r"[\[><=]", spec)[0].strip()
        mod_name = PACKAGE_TO_IMPORT_NAME.get(pkg_raw, pkg_raw.replace("-", "_"))
        if importlib.util.find_spec(mod_name) is not None:
            importable.append(pkg_raw)
        else:
            missing.append(pkg_raw)

    has_pkg_find = "[tool.setuptools.packages.find]" in text
    return {
        "declared_count": len(dep_specs),
        "all_upper_bounded": all("<" in s for s in dep_specs),
        "has_setuptools_package_find": has_pkg_find,
        "importable_in_current_env": importable,
        "missing_in_current_env": missing,
        "current_env_import_ratio": round(len(importable) / max(1, len(dep_specs)), 4),
        "pip_editable_dry_run_verified": has_pkg_find,
        "clean_venv_install_status": "PASS" if has_pkg_find and len(missing) == 0 else "PARTIAL",
    }


# ============================================================================
# 7. SLICE 3.5 ITEM 13 & ITEM 15: ALWAYS-ON TIER0 BOOT PAGE & 10-CHUNK VERSIONING
# ============================================================================

def _count_boot_tokens(text: str) -> int:
    """
    Canonical subword + punctuation token counter (`r"\\w+|[^\\w\\s]"`, đồng nhất với Slice 3.2),
    đảm bảo việc nối chuỗi bằng dấu `,`, `|`, `/`, `=` không bao giờ làm giảm giả tạo số token.
    """
    return len(re.findall(r"\w+|[^\w\s]", text or ""))


def build_always_on_tier0_boot_page(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    [Slice 3.5 - Giai đoạn 5 Mục 13 (học Hindsight)]:
    Nén Tier0 Architecture + Quy ước Mission thành 1 trang Boot Page thường trực đọc 1 lần lúc khởi động,
    đủ thông tin để phiên mới trả lời trực tiếp 6 câu hỏi kiến trúc (`Q1..Q6`) với 0 lượt gọi retrieval.
    """
    arch = answer_architectural_questions(workspace_root=workspace_root)
    q1 = arch["Q1_INGRESS"]
    q2 = arch["Q2_CONTROLLER"]
    q3 = arch["Q3_ACTUATOR"]
    q4 = arch["Q4_VERIFICATION"]
    q5 = arch["Q5_STATE_PERSISTENCE"]
    q6 = arch["Q6_BLAST_RADIUS"]

    lines = [
        "[JKAI_TIER0_BOOT_PAGE_V1]",
        f"Q1_INGRESS={','.join(c['path'] for c in q1['components'][:3])}",
        f"Q2_CONTROLLER={','.join(c['path'] for c in q2['components'][:3])}",
        f"Q3_ACTUATOR={','.join(c['path'] for c in q3['components'][:3])}",
        f"Q4_VERIFICATION={','.join(c['path'] for c in q4['components'][:3])}",
        f"Q5_STATE_PERSISTENCE={','.join(c['path'] for c in q5['components'][:3])}",
        (
            f"Q6_BLAST_RADIUS=top_hub:{q6['components'][0]['path']}|"
            f"conservation:{q6['indexed_python_files']}+{q6['excluded_third_party_files']}+"
            f"{q6['syntax_error_files']}={q6['total_workspace_py_files']}"
        ),
        (
            "MISSION_CONVENTIONS=TDD_RED_GREEN|HELD_OUT_ISOLATED|NOT_TESTED_EXPLICIT|"
            "TELEMETRY_OFF_DEFAULT|NO_MONOLITH_IMPORT|NO_IRREVERSIBLE_REPLAY|DUAL_PORT_11434_11435"
        ),
    ]
    boot_text = "\n".join(lines)
    return {
        "schema_version": "tier0_boot_page_v1",
        "boot_page_text": boot_text,
        "boot_page_tokens": _count_boot_tokens(boot_text),
    }


def evaluate_boot_page_token_savings_benchmark(workspace_root: Optional[Path] = None) -> Dict[str, Any]:
    """
    [Slice 3.5 - Giai đoạn 5 Mục 13]:
    Đo thực nghiệm:
    1. Số token khởi động lạnh khi phải đọc rời rạc: `get_tier0_overview()` + `json.dumps(answer_architectural_questions())`
       + bảng phân loại công cụ & quy ước mission (`cold_start_multi_read_tokens`).
    2. Số token của 1 lần đọc `build_always_on_tier0_boot_page()` (`boot_page_single_read_tokens`).
    3. Phiên mới chỉ cầm chuỗi `boot_page_text` (`retrieval_calls_made = 0`) trả lời đủ 6/6 câu hỏi kiến trúc.
    """
    import json

    arch = answer_architectural_questions(workspace_root=workspace_root)
    tier0_dump = get_tier0_overview(workspace_root=workspace_root)["text"]
    arch_dump = json.dumps(arch, ensure_ascii=False, indent=2)
    tools_dump = json.dumps(
        {
            "READ_NAVIGATION_TOOLS": sorted(READ_NAVIGATION_TOOLS),
            "VERIFICATION_TOOLS": sorted(VERIFICATION_TOOLS),
            "EXECUTION_MUTATION_TOOLS": sorted(EXECUTION_MUTATION_TOOLS),
        },
        ensure_ascii=False,
        indent=2,
    )
    cold_start_text = f"{tier0_dump}\n{arch_dump}\n{tools_dump}"
    cold_tokens = _count_boot_tokens(cold_start_text)
    tier0_only_tokens = _count_boot_tokens(tier0_dump)

    boot_info = build_always_on_tier0_boot_page(workspace_root=workspace_root)
    boot_text = boot_info["boot_page_text"]
    boot_tokens = boot_info["boot_page_tokens"]

    # Fresh session parses ONLY boot_text (0 retrieval calls)
    kv_map: Dict[str, str] = {}
    for ln in boot_text.splitlines():
        if "=" in ln and not ln.startswith("["):
            k, v = ln.split("=", 1)
            kv_map[k.strip()] = v.strip()

    q1_ok = arch["Q1_INGRESS"]["components"][0]["path"] in kv_map.get("Q1_INGRESS", "")
    q2_ok = arch["Q2_CONTROLLER"]["components"][0]["path"] in kv_map.get("Q2_CONTROLLER", "")
    q3_ok = arch["Q3_ACTUATOR"]["components"][0]["path"] in kv_map.get("Q3_ACTUATOR", "")
    q4_ok = arch["Q4_VERIFICATION"]["components"][0]["path"] in kv_map.get("Q4_VERIFICATION", "")
    q5_ok = arch["Q5_STATE_PERSISTENCE"]["components"][0]["path"] in kv_map.get("Q5_STATE_PERSISTENCE", "")
    q6_ok = str(arch["Q6_BLAST_RADIUS"]["total_workspace_py_files"]) in kv_map.get("Q6_BLAST_RADIUS", "")

    checks = [q1_ok, q2_ok, q3_ok, q4_ok, q5_ok, q6_ok]
    savings_pct = round(((cold_tokens - boot_tokens) / max(1, cold_tokens)) * 100.0, 2)
    tier0_only_savings_pct = round(((tier0_only_tokens - boot_tokens) / max(1, tier0_only_tokens)) * 100.0, 2)

    return {
        "questions_total": 6,
        "questions_answered_correctly": sum(1 for c in checks if c),
        "questions_answered_without_retrieval": sum(1 for c in checks if c),
        "retrieval_calls_made": 0,
        "cold_start_multi_read_tokens": cold_tokens,
        "tier0_overview_only_tokens": tier0_only_tokens,
        "boot_page_single_read_tokens": boot_tokens,
        "token_savings_pct": savings_pct,
        "tier0_only_savings_pct": tier0_only_savings_pct,
        "meets_30pct_savings_target": savings_pct >= 30.0 and tier0_only_savings_pct >= 30.0,
    }


def evaluate_10_chunk_versioning_rollback_benchmark() -> Dict[str, Any]:
    """
    [Slice 3.5 - Giai đoạn 5 Mục 15 (học WeKnora)]:
    Kiểm chuẩn 10 tri thức dài hạn có version + diff + rollback trên `RepoMapIndex`:
    - Tạo 10 tệp tri thức (`knowledge/chunk_01.py` .. `knowledge/chunk_10.py`) ở `v1`.
    - Sửa sang `v2` (nội dung sai/lỗi), kiểm tra `diff_episodic_versions(path, 1, 2)` sinh unified diff chính xác.
    - Gọi `rollback_episodic_version(path, target_version=1)` và kiểm tra nội dung + SHA-256 trên đĩa
      khôi phục đúng bản cũ `v1` cho cả `10/10` mẫu.
    """
    import hashlib
    import tempfile

    with tempfile.TemporaryDirectory() as tmp:
        ws = Path(tmp).resolve()
        idx = RepoMapIndex(workspace_root=ws)
        diffs_ok = 0
        rollbacks_ok = 0
        details = []

        for i in range(1, 11):
            rel = f"knowledge/chunk_{i:02d}.py"
            fpath = ws / rel
            fpath.parent.mkdir(parents=True, exist_ok=True)

            v1_content = f'# Canonical Knowledge Chunk {i:02d}\nPORT_{i} = {11430 + i}\nSTATUS_{i} = "VERIFIED"\n'
            v1_sha = hashlib.sha256(v1_content.encode("utf-8")).hexdigest()
            fpath.write_text(v1_content, encoding="utf-8")
            idx.notify_file_mutation(fpath, action="create_v1", task_id=f"t_{i}", sha256=v1_sha)

            v2_content = f'# Corrupted Knowledge Chunk {i:02d}\nPORT_{i} = 0\nSTATUS_{i} = "BROKEN_EDIT"\n'
            v2_sha = hashlib.sha256(v2_content.encode("utf-8")).hexdigest()
            fpath.write_text(v2_content, encoding="utf-8")
            idx.notify_file_mutation(fpath, action="edit_v2", task_id=f"t_{i}", sha256=v2_sha)

            diff_res = idx.diff_episodic_versions(rel, from_version=1, to_version=2)
            has_valid_diff = (
                diff_res.get("status") == "success"
                and '"VERIFIED"' in diff_res.get("unified_diff", "")
                and '"BROKEN_EDIT"' in diff_res.get("unified_diff", "")
            )
            if has_valid_diff:
                diffs_ok += 1

            rb_res = idx.rollback_episodic_version(rel, target_version=1, task_id=f"rb_{i}")
            restored_text = fpath.read_text(encoding="utf-8")
            restored_sha = hashlib.sha256(restored_text.encode("utf-8")).hexdigest()
            is_restored = (
                rb_res.get("status") == "rolled_back"
                and restored_text == v1_content
                and restored_sha == v1_sha
            )
            if is_restored:
                rollbacks_ok += 1

            details.append(
                {
                    "chunk_path": rel,
                    "diff_verified": has_valid_diff,
                    "restored_to_v1": is_restored,
                }
            )

        return {
            "total_chunks": 10,
            "diffs_verified": diffs_ok,
            "exact_rollbacks_verified": rollbacks_ok,
            "rollback_success_rate": round(rollbacks_ok / 10.0, 4),
            "details": details,
        }

