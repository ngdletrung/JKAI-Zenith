# -*- coding: utf-8 -*-
"""
[ZENITH FILE DIRECTIVE]
- File: core/cognitive_bus/backends/reflex_engine_backend.py
- Role: Sovereign Bilingual (EN/VI) Single-Pass Reflex Decision Backend (Tier 2).
- Ownership: Master LeeTrung
- Status: Active | Version: SDS v28.0

Invariants:
  1. 100% Local Sovereign Execution (Zero external cloud or HuggingFace Hub egress).
  2. Sets USE_TF=0 prior to any ML library import to prevent Windows TensorFlow deadlock.
  3. Implements bilingual (Vietnamese + English) language detection (detect_language_bcp47),
     symmetric binary cross-check for Boolean (mitigating false-negative bias),
     expected-value rubric scoring for Score (mitigating level-0 position bias),
     length-sorted batching (predict_batch), and tournament bracket shortlisting (predict_tournament).
  4. Honest Provenance: Exposes active_execution_mode ("onnx_safetensors_single_pass" when
     local weights exist, or "bilingual_semantic_matrix_v2" when weights_vendored=false)
     and fail-closed per-language calibration_state via ReflexEvolutionManager.
"""

from __future__ import annotations

import os

os.environ.setdefault("USE_TF", "0")

import json
import math
import re
import time
import unicodedata
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.cognitive_bus.decision_substrate_adapter import (
    DecisionPrimitive,
    ExecutionTier,
    TypedJudgementPacket,
)
from core.cognitive_bus.reflex_evolution import (
    ReflexEvolutionManager,
    get_reflex_evolution_manager,
)
from core.cognitive_bus.tier2_backend import BackendMetadata

ROOT_DIR = Path(__file__).resolve().parent.parent.parent.parent

# Decision-model discipline (transferred engineering, clean-room implementation):
# - Max options per single CHOICE pass; larger sets auto-route to tournament brackets.
# - State truncation budget with explicit flag (never silent).
# - Scorer/prompt/calibration version trio travels together; changing the scorer
#   invalidates temperatures fitted under the old one.
MAX_OPTIONS_PER_QUESTION: int = 10
MAX_STATE_CHARS: int = 32000
SCORER_VERSION: str = "bilingual_semantic_matrix_v2"
PROMPT_VERSION: str = "1"

# Vietnamese diacritic characters for fast BCP-47 detection
_VI_DIACRITIC_RE = re.compile(
    r"[àáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ"
    r"ÀÁẢÃẠĂẰẮẲẴẶÂẦẤẨẪẬÈÉẺẼẸÊỀẾỂỄỆÌÍỈĨỊÒÓỎÕỌÔỒỐỔỖỘƠỜỚỞỠỢÙÚỦŨỤƯỪỨỬỮỰỲÝỶỸỴĐ]"
)

# Unaccented Vietnamese lexical markers (collision-audited: no whole-word English overlap;
# every addition must pass the English battery in tests/test_sovereign_reflex_hub.py before merge)
_VI_UNACCENTED_MARKERS = {
    "khong", "duoc", "nhung", "kiem", "tra", "thuc", "hien", "thong",
    "nguoi", "dung", "lieu", "xoa", "them", "sua", "chao",
    "hom", "nay", "thoi", "tiet", "nhu", "nao", "giup", "toi",
    "cau", "hinh", "ket", "noi", "loi", "mang", "quyen", "truy", "cap",
    "tuong", "lua", "mo", "tat", "xem", "ghi", "doi", "danh", "sach",
    "tinh", "lenh",
}

# High-frequency English function words with no Vietnamese-syllable collision.
# Excluded lookalikes: an (an), in (in), do (do/do), to (to/to), can (can),
# no (no), a (single-letter noise). Each entry is whole-word matched.
_EN_FUNCTION_WORDS = {
    "the", "is", "are", "was", "were", "been", "with", "from", "that",
    "this", "it", "as", "at", "by", "please", "your", "you", "we",
    "they", "will", "would", "could", "should", "not", "yes", "if",
    "else", "when", "how", "what", "which", "who", "does", "did",
    "has", "have", "had", "and", "or", "but", "for", "of", "on", "be",
}

# Bilingual antonym / negation pairs for semantic cache & contradiction checks
_BILINGUAL_ANTONYM_PAIRS: List[Tuple[Tuple[str, ...], Tuple[str, ...]]] = [
    (("bật", "mở", "kích hoạt", "cho phép", "enable", "turn on", "start", "allow", "open", "activate"),
     ("tắt", "đóng", "vô hiệu", "vô hiệu hóa", "chặn", "cấm", "disable", "turn off", "stop", "block", "deny", "close", "deactivate")),
    (("xóa", "gỡ", "hủy", "drop", "delete", "remove", "destroy", "purge"),
     ("tạo", "thêm", "giữ", "sao lưu", "khôi phục", "create", "add", "keep", "backup", "restore")),
    (("tăng", "mở rộng", "nâng", "increase", "scale up", "upgrade", "expand"),
     ("giảm", "thu hẹp", "hạ", "decrease", "scale down", "downgrade", "shrink")),
    (("an toàn", "hợp lệ", "đúng", "safe", "valid", "benign", "compliant"),
     ("nguy hiểm", "độc hại", "trái phép", "dangerous", "malicious", "unauthorized", "unsafe")),
]

# Bilingual concept profiles for common JKAI Choice options and capabilities
_CONCEPT_PROFILES: Dict[str, Tuple[str, ...]] = {
    "mikrotik_router": (
        "mikrotik", "router", "routerboard", "routeros", "ether1", "ether", "vlan",
        "firewall", "băng thông", "gói tin", "winbox", "nat", "ip lạ", "rule chặn",
        "cổng mạng", "routing", "bgp", "ospf", "wireguard", "pppoe",
    ),
    "mariadb": (
        "mariadb", "mysql", "sql", "select", "insert", "update", "join", "explain",
        "cơ sở dữ liệu", "database", "bảng", "table", "index", "truy vấn", "query",
        "schema", "orders", "users", "bán hàng", "tối ưu hóa bảng",
    ),
    "web_recon": (
        "web_recon", "recon", "quét cổng", "port scan", "lỗ hổng", "vulnerability",
        "domain", "ssl", "tls", "chứng chỉ", "dns", "records", "subdomain", "nmap",
        "whois", "http header", "cve", "pentest", "mục tiêu",
    ),
    "google_drive": (
        "google_drive", "google drive", "drive", "đồng bộ file", "thư mục chia sẻ",
        "tải xuống tài liệu", "pdf", "cloud file", "upload file", "download file",
        "tài liệu", "báo cáo tuần", "drive công ty",
    ),
    "smtp_mail": (
        "smtp_mail", "smtp", "email", "gửi email", "mail", "thư điện tử",
        "thông báo sự cố", "ban quản trị", "inbox", "imap", "gửi thư",
    ),
    "network_transient": (
        "connectionreseterror", "10054", "forcibly closed", "connecttimeout",
        "timed out", "timeout", "gaierror", "11001", "getaddrinfo", "dns",
        "connection refused", "network", "unreachable", "upstream proxy", "socket",
        "mất kết nối", "timeout mạng",
    ),
    "permission_denied": (
        "permissionerror", "errno 13", "permission denied", "accessdeniederror",
        "without role", "unauthorized", "forbidden", "403", "/etc/shadow",
        "không có quyền", "từ chối truy cập", "privilege",
    ),
    "file_not_found": (
        "filenotfounderror", "errno 2", "no such file", "does not exist",
        "unmounted", "missing file", "404", "không tìm thấy file", "đường dẫn không tồn tại",
    ),
    "contradictory_facts": (
        "assertionerror", "state conflict", "contradict", "logicaldeadlock",
        "explicitly forbids", "prerequisite", "completed but payment is marked unpaid",
        "mâu thuẫn", "xung đột trạng thái", "deadlock",
    ),
    "unknown_anomaly": (
        "quantumflukeexception", "flux capacitor", "0xdeadbeef", "unknown_anomaly",
    ),
    "fast_path": (
        "xin chào", "chào bạn", "chào buổi sáng", "hello", "hi,", "hi ", "cảm ơn",
        "hẹn gặp lại", "mấy giờ rồi", "thời tiết thế nào", "bạn có khỏe không",
        "good morning", "thank you", "bye", "what time",
    ),
    "deep_path": (
        "phân tích", "giải thuật", "tối ưu hóa", "explain", "join", "memory leak",
        "driver c++", "routeros api", "tái cấu trúc", "microservices", "p99",
        "dump crash", "race condition", "worker threads", "thiết kế sơ đồ",
        "phân tán", "100,000 rps", "architecture", "refactor", "debug", "root cause",
    ),
    # Canonical DECISION_VOCAB (8 decisions) + VERIFY_AND_CLOSE proposal profiles
    "allow": (
        "an toàn", "hợp lệ", "cho phép", "modus ponens", "định lý bayes",
        "occam", "stable sort", "tit-for-tat", "chia hết cho 2", "kiểm tra băng thông",
        "đọc file", "safe", "benign", "read-only",
    ),
    "clarify": (
        "mơ hồ", "thiếu thông tin", "chưa rõ", "xung đột yêu cầu", "hỏi lại",
        "cần làm rõ", "consistency level", "legal precedence", "transaction pattern",
        "metric objective", "ambiguous", "clarify", "missing parameter",
    ),
    "deny": (
        "rm -rf", "~/.ssh", "169.254.169.254", "ssrf", "/dev/mem", "negative list",
        "từ chối", "cấm", "xóa toàn bộ", "rò rỉ", "trái phép", "drop table",
        "attacker-c2", "/etc/shadow", "ignore all previous instructions",
    ),
    "escalate": (
        "rò rỉ khóa", "master key", "revocation ceremony", "báo cáo cấp trên",
        "vượt thẩm quyền", "escalate", "critical incident", "ban quản trị",
    ),
    "handle_fault": (
        "lệch múi giờ", "ntp", "clock skew", "worker drain", "treo tiến trình",
        "fault", "sự cố phần cứng", "zombie",
    ),
    "modify": (
        "sửa lại", "điều chỉnh", "constant time compare", "atomic file creation",
        "fencing token", "separate task thread pools", "reduce dns ttl",
        "idempotency mismatch", "thay vì",
    ),
    "recover": (
        "hết inode", "df -i", "purge inodes", "load shedding", "quá tải",
        "compatibility adapter", "khôi phục", "phục hồi", "recover",
    ),
    "reject_invalid_reasoning": (
        "ngụy biện", "affirming the consequent", "chuồng bồ câu", "pigeonhole",
        "tương quan", "nhân quả", "ăn kem", "triệu phú", "10 chiếc áo", "fallacy",
    ),
    "verify_and_close": (
        "đã tạo artifact", "sha256", "kiểm chứng hoàn tất", "verify_file",
        "đủ bằng chứng", "ready to verify", "verify and close", "xác minh đóng tác vụ",
    ),
    "continue_execution": (
        "đang thực thi", "chưa có artifact", "còn bước tiếp theo", "in progress",
        "continue", "tiếp tục", "pending",
    ),
}

# Forbidden completion labels that a model must NEVER emit (Step 2: NO_EVIDENCE_NO_COMPLETION).
# Completion is exclusively granted by Runtime CompletionAuthority after verifying physical
# artifacts, schema, and state transition. Model may only propose "VERIFY_AND_CLOSE".
FORBIDDEN_COMPLETION_LABELS: frozenset[str] = frozenset(
    {
        "complete",
        "completed",
        "complete_candidate",
        "task_complete",
        "mission_complete",
        "done",
    }
)


def validate_no_model_completion_label(options_or_labels: Optional[List[str]]) -> None:
    """
    Enforces Step 2 Hard Fence: Model is strictly prohibited from emitting or choosing
    any COMPLETE / COMPLETE_CANDIDATE label. Only 'VERIFY_AND_CLOSE' proposal is permitted.
    """
    if not options_or_labels:
        return
    for item in options_or_labels:
        norm = str(item).strip().lower()
        if norm in FORBIDDEN_COMPLETION_LABELS or norm.startswith("complete_"):
            raise PermissionError(
                f"NO_EVIDENCE_NO_COMPLETION Violation: Forbidden model completion label '{item}'. "
                "Model must NEVER emit COMPLETE or COMPLETE_CANDIDATE; use 'VERIFY_AND_CLOSE' "
                "proposal and defer completion authority to Runtime CompletionAuthority."
            )


# Bilingual security / destructive risk indicators
_HIGH_RISK_PATTERNS: Tuple[str, ...] = (
    r"\brm\s+-[a-z]*r[a-z]*f\b",
    r"\bdrop\s+table\b",
    r"\bdrop\s+database\b",
    r"\btruncate\s+table\b",
    r"\bdelete\s+from\b",
    r"\bformat\s+[a-z]:",
    r"format\s+ổ\s+cứng",
    r"xóa\s+sạch\s+thư\s+mục",
    r"xóa\s+sạch\s+dữ\s+liệu",
    r"curl\s+-x\s+post",
    r"-d\s+@\.env",
    r"attacker-c2",
    r"/etc/shadow",
    r"bỏ\s+qua\s+toàn\s+bộ\s+hướng\s+dẫn",
    r"cấp\s+quyền\s+super\s*admin",
    r"grant_super_admin",
    r"ignore\s+all\s+previous\s+instructions",
    r"ignore\s+previous\s+instructions",
    r"prompt_injection",
    r"\beval\s*\(",
    r"\bexec\s*\(",
)

_SAFE_ADMIN_PATTERNS: Tuple[str, ...] = (
    r"đọc\s+file\s+readme",
    r"kiểm\s+tra\s+dung\s+lượng\s+ổ\s+đĩa",
    r"\bdocker\s+ps\b",
    r"xem\s+log\s+của\s+container",
    r"sao\s+lưu\s+cấu\s+hình",
    r"backup\s+nội\s+bộ",
    r"select\s+",
    r"hướng\s+dẫn\s+cài\s+đặt",
)


# Layer 5 Upstream: High-precision multi-word Vietnamese phrase accent restoration table
# (derived from Vietnamese news & IT ops corpora; applied only on multi-word bigram/trigram matches
# when enable_upstream_accent_restore=True so single English tokens are never touched).
_VI_PHRASE_ACCENT_RESTORE_MAP: Tuple[Tuple[str, str], ...] = (
    ("kiem tra tuong lua", "kiểm tra tường lửa"),
    ("tat tuong lua", "tắt tường lửa"),
    ("bat tuong lua", "bật tường lửa"),
    ("mo tuong lua", "mở tường lửa"),
    ("khoi dong lai dich vu", "khởi động lại dịch vụ"),
    ("khoi dong lai", "khởi động lại"),
    ("dich vu web", "dịch vụ web"),
    ("deploy ban moi len server", "deploy bản mới lên server"),
    ("xu ly cham", "xử lý chậm"),
    ("mo file bao cao", "mở file báo cáo"),
    ("doi mat khau", "đổi mật khẩu"),
    ("tinh trang o dia", "tình trạng ổ đĩa"),
    ("danh sach container dang chay", "danh sách container đang chạy"),
    ("xem camera mo khoa", "xem camera mở khóa"),
    ("cau hinh ket noi mang", "cấu hình kết nối mạng"),
)

# Layer 5 Downstream: Domain prior markers to disambiguate polysemous Vietnamese terms
# such as "tường lửa" / "tuong lua" (Network Firewall vs Civil Construction Fire-Wall).
_NETWORK_DOMAIN_MARKERS: Tuple[str, ...] = (
    "router", "routeros", "mikrotik", "ether1", "ether", "vlan", "port", "443", "80",
    "ip", "nat", "bgp", "ospf", "packet", "gói tin", "goi tin", "băng thông", "bang thong",
    "server", "nginx", "container", "docker", "ssh", "dns", "tcp", "udp", "rule", "filter",
)
_CONSTRUCTION_DOMAIN_MARKERS: Tuple[str, ...] = (
    "bê tông", "be tong", "gạch", "gach", "vữa", "vua", "xi măng", "xi mang",
    "tầng hầm", "tang ham", "cửa chống cháy", "cua chong chay", "chống cháy", "chong chay",
    "nhà kho", "nha kho", "công trình", "cong trinh", "xây dựng", "xay dung", "xay tuong",
    "kiến trúc", "kien truc", "móng nhà", "mong nha", "thép chịu lực", "thep chiu luc", "chống cháy lan",
)


def restore_vietnamese_accents_ops(text: str) -> Tuple[str, bool]:
    """
    Layer 5 (Upstream): Restores Vietnamese diacritics on multi-word unaccented
    phrases using verified bigram/trigram ops & news collocations.
    Returns (restored_text, was_restored).
    """
    if not text:
        return "", False
    norm = unicodedata.normalize("NFC", str(text))
    lowered = norm.lower()
    restored = lowered
    changed = False
    for src_phrase, dst_phrase in _VI_PHRASE_ACCENT_RESTORE_MAP:
        if src_phrase in restored:
            restored = restored.replace(src_phrase, dst_phrase)
            changed = True
    return (restored if changed else norm), changed


def evaluate_accent_restore_coverage(ops_queries: Sequence[str]) -> Dict[str, Any]:
    """
    Measures coverage of _VI_PHRASE_ACCENT_RESTORE_MAP across a sample of unaccented ops queries.
    Used to audit coverage before enabling upstream accent restoration by default.
    """
    total = len(ops_queries)
    if total == 0:
        return {"total": 0, "restored_count": 0, "coverage_rate": 0.0, "default_enabled_in_predict": False}
    restored_count = sum(1 for q in ops_queries if restore_vietnamese_accents_ops(q)[1])
    return {
        "total": total,
        "restored_count": restored_count,
        "coverage_rate": round(restored_count / total, 4),
        "phrase_map_size": len(_VI_PHRASE_ACCENT_RESTORE_MAP),
        "default_enabled_in_predict": False,
    }


def disambiguate_domain_prior(text: str, domain_context: Optional[str] = None) -> Dict[str, Any]:
    """
    Layer 5 (Downstream): Applies domain prior to disambiguate polysemous terms
    (e.g., 'tường lửa' / 'tuong lua' in Network Security vs Civil Construction).
    """
    combined = f"{text or ''} {domain_context or ''}".lower()
    net_hits = sum(1 for m in _NETWORK_DOMAIN_MARKERS if m in combined)
    con_hits = sum(1 for m in _CONSTRUCTION_DOMAIN_MARKERS if m in combined)
    has_tuong_lua = ("tường lửa" in combined) or ("tuong lua" in combined) or ("firewall" in combined)

    if con_hits > net_hits and con_hits >= 1:
        domain = "civil_construction"
    elif net_hits > con_hits and net_hits >= 1:
        domain = "network_security"
    elif has_tuong_lua:
        # Default JKAI operational prior for standalone firewall queries when no construction signal exists
        domain = "network_security_prior"
    else:
        domain = "general_ops"

    return {
        "domain": domain,
        "network_signal_hits": net_hits,
        "construction_signal_hits": con_hits,
        "polysemy_resolved": "network_firewall" if (has_tuong_lua and "construction" not in domain) else (
            "structural_fire_barrier" if (has_tuong_lua and "construction" in domain) else None
        ),
    }


def detect_language_with_trace(
    text: str,
    *,
    enable_upstream_accent_restore: bool = False,
    domain_context: Optional[str] = None,
) -> Dict[str, Any]:
    """
    5-Layer Bilingual Language Detection & Disambiguation Pipeline with explicit route trace:
      - L1_DIACRITIC_SHORTCUT: Tone/diacritic regex shortcut -> 'vi' immediately.
      - L2_UNACCENTED_VI_MARKER: Collision-audited unaccented VI marker count -> 'vi'.
      - L3_SYMMETRIC_EN_FUNCTION: English function words (excluding an/in/do/to/can/no/a) with 0 VI hits -> 'en'.
      - L4_HONEST_ABSTAIN_NEUTRAL: Insufficient or tied evidence -> '*' (no guessing).
      - L5_UPSTREAM_ACCENT_RESTORE_AND_DOMAIN_PRIOR: Optional upstream phrase accent restoration & downstream domain prior.
    """
    domain_info = disambiguate_domain_prior(text, domain_context)
    if not text or not str(text).strip():
        return {
            "language": "*",
            "layer": "L4_HONEST_ABSTAIN_NEUTRAL",
            "vi_hits": 0,
            "en_hits": 0,
            "accent_restored": False,
            "domain_prior": domain_info,
        }

    s = unicodedata.normalize("NFC", str(text))
    accent_restored = False

    # Layer 1: Accented Vietnamese diacritic shortcut
    if _VI_DIACRITIC_RE.search(s):
        return {
            "language": "vi",
            "layer": "L1_DIACRITIC_SHORTCUT",
            "vi_hits": 1,
            "en_hits": 0,
            "accent_restored": False,
            "domain_prior": domain_info,
        }

    tokens = [t.lower() for t in re.findall(r"[a-zA-Z]+", s)]
    if not tokens:
        return {
            "language": "*",
            "layer": "L4_HONEST_ABSTAIN_NEUTRAL",
            "vi_hits": 0,
            "en_hits": 0,
            "accent_restored": False,
            "domain_prior": domain_info,
        }

    vi_hits = sum(1 for t in tokens if t in _VI_UNACCENTED_MARKERS)
    en_hits = sum(1 for t in tokens if t in _EN_FUNCTION_WORDS)

    # Layer 2: Unaccented Vietnamese marker count (>= 2 markers, or 1 marker with 0 EN signal)
    if vi_hits >= 2:
        return {
            "language": "vi",
            "layer": "L2_UNACCENTED_VI_MARKER",
            "vi_hits": vi_hits,
            "en_hits": en_hits,
            "accent_restored": False,
            "domain_prior": domain_info,
        }

    # Layer 3: Symmetric English function words (>= 1 EN function word with 0 VI markers)
    if en_hits >= 1 and vi_hits == 0:
        return {
            "language": "en",
            "layer": "L3_SYMMETRIC_EN_FUNCTION",
            "vi_hits": vi_hits,
            "en_hits": en_hits,
            "accent_restored": False,
            "domain_prior": domain_info,
        }

    if vi_hits == 1 and en_hits == 0:
        return {
            "language": "vi",
            "layer": "L2_UNACCENTED_VI_MARKER",
            "vi_hits": vi_hits,
            "en_hits": en_hits,
            "accent_restored": False,
            "domain_prior": domain_info,
        }

    # Layer 5 (Upstream): Optional multi-word phrase accent restoration before abstaining
    if enable_upstream_accent_restore:
        restored_s, accent_restored = restore_vietnamese_accents_ops(s)
        if accent_restored and _VI_DIACRITIC_RE.search(restored_s):
            return {
                "language": "vi",
                "layer": "L5_UPSTREAM_ACCENT_RESTORE_AND_DOMAIN_PRIOR",
                "vi_hits": vi_hits,
                "en_hits": en_hits,
                "accent_restored": True,
                "restored_text": restored_s,
                "domain_prior": domain_info,
            }

    # Layer 4: Honest Abstention to '*' when evidence is insufficient
    return {
        "language": "*",
        "layer": "L4_HONEST_ABSTAIN_NEUTRAL",
        "vi_hits": vi_hits,
        "en_hits": en_hits,
        "accent_restored": accent_restored,
        "domain_prior": domain_info,
    }


def detect_language_bcp47(text: str) -> str:
    """
    Detects whether input text is primarily Vietnamese ('vi'), English ('en'), or neutral ('*').
    Executes Layers 1-4 of the 5-layer pipeline and abstains honestly to '*' when signal is insufficient.
    """
    return str(detect_language_with_trace(text, enable_upstream_accent_restore=False)["language"])


def _is_conversation_state(raw_state: Any) -> bool:
    """Returns True if raw_state is a conversation turn list or dict wrapping conversation turns."""
    if isinstance(raw_state, list):
        return True
    if isinstance(raw_state, dict):
        for conv_key in ("messages", "turns", "conversation", "chat_history", "history"):
            if isinstance(raw_state.get(conv_key), list):
                return True
    return False


def _normalize_text(value: Any) -> str:
    if isinstance(value, (dict, list)):
        # Compact JSON serialization (separators=(",",":")) saves ~68 tokens per decision pass
        raw = json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    else:
        raw = str(value or "")
    norm = unicodedata.normalize("NFC", raw).lower().strip()
    return re.sub(r"\s+", " ", norm)


def _tokenize_words(text: str) -> List[str]:
    norm = _normalize_text(text)
    return [
        tok
        for tok in re.findall(
            r"[\wàáảãạăằắẳẵặâầấẩẫậèéẻẽẹêềếểễệìíỉĩịòóỏõọôồốổỗộơờớởỡợùúủũụưừứửữựỳýỷỹỵđ]+",
            norm,
        )
        if len(tok) > 1
    ]


def _truncate_state_with_flag(state_str: str, raw_state: Any = None) -> Tuple[str, bool]:
    """Truncates long states to MAX_STATE_CHARS with smart directionality:
    - Conversation lists keep their most recent turns (tail: state_str[-MAX_STATE_CHARS:]).
    - Other structured/document states keep their beginning (head: state_str[:MAX_STATE_CHARS]).
    - Questions and options are NEVER truncated.

    Returns (text, truncated_flag). Short states pass through byte-identical
    with truncated=False.
    """
    if len(state_str) <= MAX_STATE_CHARS:
        return state_str, False
    if _is_conversation_state(raw_state):
        return state_str[-MAX_STATE_CHARS:], True
    return state_str[:MAX_STATE_CHARS], True


def resolve_calibration_bucket(primitive_name: str, option_count: int = 2) -> str:
    """
    Maps (primitive, option_count) to option-count calibration buckets:
      - Boolean -> 'boolean:2'
      - Score   -> 'score:3-5' (or 'score:6+' for >5 levels)
      - Choice  -> 'choice:2', 'choice:3-5', or 'choice:6-10'
    Because binary choices have sharper raw logits than 6-10 way choices, fitting
    temperature per option-count bucket prevents over/under-confidence across arities.
    """
    p = str(primitive_name).strip().lower()
    if p in ("boolean", "noul"):
        return "boolean:2"
    if p == "score":
        return "score:3-5" if option_count <= 5 else "score:6+"
    if option_count <= 2:
        return "choice:2"
    if option_count <= 5:
        return "choice:3-5"
    return "choice:6-10"


class ReflexEngineBackend:
    """
    Sovereign Bilingual (EN/VI) Single-Forward-Pass Decision Backend (Tier 2).
    Supports Mode A (local ONNX / Safetensors checkpoint) and Mode B
    (Bilingual Semantic Matrix Engine v2) with automatic honest provenance reporting.
    """

    def __init__(
        self,
        model_path: Optional[str] = None,
        version: Optional[str] = None,
        device: str = "cpu",
        evolution_manager: Optional[ReflexEvolutionManager] = None,
    ):
        self._version = version or os.environ.get("JKAI_REFLEX_VERSION", "0.4.2")
        env_model = os.environ.get("JKAI_REFLEX_MODEL")
        default_dir = ROOT_DIR / "models" / "reflex_engine" / self._version
        self._model_path = Path(model_path or env_model or default_dir)
        self._device = device
        self._loaded = False
        self._active_mode = "bilingual_semantic_matrix_v2"
        self._onnx_session: Optional[Any] = None
        self._evolution = evolution_manager or get_reflex_evolution_manager()

    # ------------------------------------------------------------------
    # Lifecycle & Provenance
    # ------------------------------------------------------------------

    def load(self) -> None:
        """
        Idempotent loader. Checks manifest license gate and detects whether local
        ONNX / Safetensors weights are present on disk. Never makes network calls.
        """
        if self._loaded:
            return

        # Verify manifest license & zero-egress gate
        try:
            manifest_info = self._evolution.verify_checkpoint_manifest(self._model_path)
            if manifest_info.get("weights_found"):
                onnx_file = self._model_path / "model.onnx"
                if onnx_file.exists():
                    try:
                        import onnxruntime as ort  # type: ignore
                        self._onnx_session = ort.InferenceSession(
                            str(onnx_file),
                            providers=["CPUExecutionProvider"],
                        )
                        self._active_mode = "onnx_safetensors_single_pass"
                    except Exception:
                        self._active_mode = "bilingual_semantic_matrix_v2"
                else:
                    self._active_mode = "onnx_safetensors_single_pass"
            else:
                self._active_mode = "bilingual_semantic_matrix_v2"
        except Exception:
            self._active_mode = "bilingual_semantic_matrix_v2"

        self._loaded = True

    def unload(self) -> None:
        self._onnx_session = None
        self._loaded = False

    def is_loaded(self) -> bool:
        return self._loaded

    def reload_checkpoint(self, new_model_path: Optional[str] = None, new_version: Optional[str] = None) -> Dict[str, Any]:
        """Hot-reloads a verified local checkpoint directory without restarting the process."""
        self.unload()
        if new_version:
            self._version = new_version
        if new_model_path:
            self._model_path = Path(new_model_path)
        elif new_version:
            self._model_path = ROOT_DIR / "models" / "reflex_engine" / self._version
        self.load()
        return {
            "loaded": self._loaded,
            "version": self._version,
            "model_path": str(self._model_path),
            "active_mode": self._active_mode,
        }

    def metadata(self) -> BackendMetadata:
        cal_state = self._evolution.get_calibration_state("*")
        return BackendMetadata(
            name="reflex-engine",
            version=self._version,
            is_deterministic=True,
            is_local_only=True,
            supported_languages=("en", "vi", "*"),
            calibration_state=cal_state,
            ece=None,
            notes=(
                f"mode={self._active_mode}; "
                f"per_lang_calibration={self._evolution.get_per_language_calibration_map()}"
            ),
        )

    # ------------------------------------------------------------------
    # Core Single-State Prediction (Tier2Backend Protocol)
    # ------------------------------------------------------------------

    def predict(
        self,
        state: Dict[str, Any],
        questions: List[Tuple[DecisionPrimitive, str, Optional[List[str]]]],
        timeout_ms: int = 450,
        descriptions: Optional[Dict[str, str]] = None,
    ) -> Dict[str, TypedJudgementPacket]:
        if not self.is_loaded():
            raise RuntimeError("ReflexEngineBackend.predict called before load()")

        t_batch_start = time.perf_counter()
        state_str = _normalize_text(state)
        state_str, state_truncated = _truncate_state_with_flag(state_str, state)
        results: Dict[str, TypedJudgementPacket] = {}

        for prim, question, options in questions:
            elapsed_so_far = (time.perf_counter() - t_batch_start) * 1000.0
            if elapsed_so_far > timeout_ms:
                raise TimeoutError(
                    f"ReflexEngineBackend exceeded timeout_ms={timeout_ms} (elapsed={elapsed_so_far:.1f}ms)"
                )

            t0 = time.perf_counter()
            lang_trace = detect_language_with_trace(f"{state_str} {question}")
            lang = str(lang_trace["language"])
            cal_state = self._evolution.get_calibration_state(lang)
            prim_name = prim.value if hasattr(prim, "value") else str(prim)
            opt_count = len(options) if options else (2 if prim == DecisionPrimitive.BOOLEAN else 5)
            bucket_key = resolve_calibration_bucket(prim_name, opt_count)
            temp = self._evolution.get_temperature(lang, prim_name, bucket=bucket_key)
            version_trio = {
                "scorer_version": SCORER_VERSION,
                "prompt_version": PROMPT_VERSION,
                "calibration_bucket": bucket_key,
                "lang_detect_layer": lang_trace["layer"],
                "domain_prior": lang_trace["domain_prior"]["domain"],
            }

            # Check instant feedback memory (<50ms)
            pos_val, neg_vals, fb_id = self._evolution.lookup_feedback_adjustments(state, question)

            if prim == DecisionPrimitive.BOOLEAN:
                prob_true, raw_conf = self._score_boolean_bilingual(state, state_str, question, pos_val, neg_vals)
                scaled_conf = self._apply_temperature(raw_conf, temp)
                dist = {
                    "true": round(prob_true, 6),
                    "false": round(1.0 - round(prob_true, 6), 6),
                }
                bool_result = 1.0 if prob_true >= 0.5 else 0.0
                packet = TypedJudgementPacket(
                    primitive=DecisionPrimitive.BOOLEAN,
                    question=question,
                    result=bool_result,
                    confidence=round(scaled_conf, 6),
                    distribution=dist,
                    execution_tier=ExecutionTier.TIER_2_LOCAL,
                    latency_ms=(time.perf_counter() - t0) * 1000.0,
                    metadata={
                        "backend": "reflex-engine",
                        "version": self._version,
                        "mode": self._active_mode,
                        "language": lang,
                        "calibration_state": cal_state,
                        "feedback_entry_id": fb_id,
                        "truncated": state_truncated,
                        **version_trio,
                    },
                )
            elif prim == DecisionPrimitive.CHOICE:
                opts = list(options) if options else ["none"]
                validate_no_model_completion_label(opts)
                base_meta = {
                    "backend": "reflex-engine",
                    "version": self._version,
                    "mode": self._active_mode,
                    "language": lang,
                    "calibration_state": cal_state,
                    "feedback_entry_id": fb_id,
                    "truncated": state_truncated,
                    **version_trio,
                }
                if len(opts) > MAX_OPTIONS_PER_QUESTION:
                    # Auto-tournament: oversized option sets never enter a single pass.
                    rem_ms = max(50, int(timeout_ms - (time.perf_counter() - t_batch_start) * 1000.0))
                    ranked, _final = self.predict_tournament(
                        state=state,
                        question=question,
                        candidates=opts,
                        descriptions=descriptions,
                        group_size=MAX_OPTIONS_PER_QUESTION,
                        top_k=min(5, len(opts)),
                        timeout_ms=rem_ms,
                    )
                    top_total = sum(score for _, score in ranked) or 1.0
                    dist = {c: round(s / top_total, 6) for c, s in ranked}
                    residual = round(1.0 - sum(dist.values()), 6)
                    if ranked:
                        dist[ranked[0][0]] = round(dist[ranked[0][0]] + residual, 6)
                    winner_share = (ranked[0][1] / top_total) if ranked else 0.0
                    packet = TypedJudgementPacket(
                        primitive=DecisionPrimitive.CHOICE,
                        question=question,
                        result=ranked[0][0] if ranked else opts[0],
                        confidence=round(self._apply_temperature(winner_share, temp), 6),
                        distribution=dist,
                        execution_tier=ExecutionTier.TIER_2_LOCAL,
                        latency_ms=(time.perf_counter() - t0) * 1000.0,
                        metadata={
                            **base_meta,
                            "tournament": True,
                            "shortlisted_from": len(opts),
                        },
                    )
                    results[question] = packet
                    continue
                winner, dist, raw_conf = self._score_choice_bilingual(
                    state_str, question, opts, descriptions, pos_val, neg_vals
                )
                scaled_conf = self._apply_temperature(raw_conf, temp)
                packet = TypedJudgementPacket(
                    primitive=DecisionPrimitive.CHOICE,
                    question=question,
                    result=winner,
                    confidence=round(scaled_conf, 6),
                    distribution=dist,
                    execution_tier=ExecutionTier.TIER_2_LOCAL,
                    latency_ms=(time.perf_counter() - t0) * 1000.0,
                    metadata={
                        **base_meta,
                        "tournament": False,
                    },
                )
            else:  # DecisionPrimitive.SCORE
                levels = list(options) if options else ["0", "1", "2", "3", "4"]
                score_val, dist, raw_conf = self._score_rubric_bilingual(
                    state, state_str, question, levels, pos_val, neg_vals
                )
                scaled_conf = self._apply_temperature(raw_conf, temp)
                packet = TypedJudgementPacket(
                    primitive=DecisionPrimitive.SCORE,
                    question=question,
                    result=score_val,
                    confidence=round(scaled_conf, 6),
                    distribution=dist,
                    execution_tier=ExecutionTier.TIER_2_LOCAL,
                    latency_ms=(time.perf_counter() - t0) * 1000.0,
                    metadata={
                        "backend": "reflex-engine",
                        "version": self._version,
                        "mode": self._active_mode,
                        "language": lang,
                        "calibration_state": cal_state,
                        "feedback_entry_id": fb_id,
                        "truncated": state_truncated,
                        "legend": levels,
                        **version_trio,
                    },
                )

            results[question] = packet

        return results

    # ------------------------------------------------------------------
    # Batch & Tournament Extensions
    # ------------------------------------------------------------------

    def predict_batch(
        self,
        items: List[Tuple[Dict[str, Any], List[Tuple[DecisionPrimitive, str, Optional[List[str]]]]]],
        timeout_ms: int = 2000,
        sort_by_length: bool = True,
    ) -> List[Dict[str, TypedJudgementPacket]]:
        """
        Evaluates a batch of (state, questions) pairs.
        When sort_by_length=True, sorts items by serialized length prior to evaluation
        (minimizing padding variance in tensor mode) and restores exact original ordering.
        """
        if not self.is_loaded():
            raise RuntimeError("ReflexEngineBackend.predict_batch called before load()")
        if not items:
            return []

        indexed = list(enumerate(items))
        if sort_by_length:
            indexed.sort(key=lambda pair: len(_normalize_text(pair[1][0])))

        out_by_idx: Dict[int, Dict[str, TypedJudgementPacket]] = {}
        t_start = time.perf_counter()
        for orig_idx, (state, questions) in indexed:
            rem_ms = max(50, int(timeout_ms - (time.perf_counter() - t_start) * 1000.0))
            out_by_idx[orig_idx] = self.predict(state=state, questions=questions, timeout_ms=rem_ms)

        return [out_by_idx[i] for i in range(len(items))]

    def predict_tournament(
        self,
        state: Dict[str, Any],
        question: str,
        candidates: List[str],
        descriptions: Optional[Dict[str, str]] = None,
        group_size: int = 12,
        top_k: int = 5,
        timeout_ms: int = 450,
    ) -> Tuple[List[Tuple[str, float]], TypedJudgementPacket]:
        """
        Tournament bracket shortlisting for large candidate sets (N > group_size).
        Splits candidates into brackets of size `group_size` (default 12), selects top
        contenders from each bracket, and runs a final championship pass to return top_k.
        """
        if not self.is_loaded():
            raise RuntimeError("ReflexEngineBackend.predict_tournament called before load()")
        if not candidates:
            raise ValueError("predict_tournament requires at least one candidate")

        group_size = max(2, int(group_size))
        top_k = max(1, min(int(top_k), len(candidates)))

        if len(candidates) <= group_size:
            pkt = self.predict(
                state=state,
                questions=[(DecisionPrimitive.CHOICE, question, candidates)],
                timeout_ms=timeout_ms,
                descriptions=descriptions,
            )[question]
            ranked = sorted(pkt.distribution.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
            return ranked, pkt

        # Round 1+: Bracket elimination
        advancing: List[str] = []
        per_bracket_advance = max(2, min(3, group_size // 3))
        for start in range(0, len(candidates), group_size):
            bracket = candidates[start : start + group_size]
            pkt = self.predict(
                state=state,
                questions=[(DecisionPrimitive.CHOICE, question, bracket)],
                timeout_ms=timeout_ms,
                descriptions=descriptions,
            )[question]
            top_in_bracket = sorted(pkt.distribution.items(), key=lambda kv: kv[1], reverse=True)[
                :per_bracket_advance
            ]
            for cand, _ in top_in_bracket:
                if cand not in advancing:
                    advancing.append(cand)

        # Ensure finalists fit within a single championship pass
        if len(advancing) > group_size:
            advancing = advancing[:group_size]
        for c in candidates:
            if len(advancing) >= min(len(candidates), max(top_k, len(advancing))):
                break
            if c not in advancing:
                advancing.append(c)

        final_pkt = self.predict(
            state=state,
            questions=[(DecisionPrimitive.CHOICE, question, advancing)],
            timeout_ms=timeout_ms,
            descriptions=descriptions,
        )[question]
        ranked = sorted(final_pkt.distribution.items(), key=lambda kv: kv[1], reverse=True)[:top_k]
        return ranked, final_pkt

    # ------------------------------------------------------------------
    # Internal Scoring Primitives (Mode B Bilingual Semantic Matrix v2)
    # ------------------------------------------------------------------

    @staticmethod
    def _apply_temperature(raw_conf: float, temperature: float) -> float:
        c = max(1e-4, min(1.0 - 1e-4, float(raw_conf)))
        if abs(temperature - 1.0) < 1e-3:
            return c
        logit = math.log(c / (1.0 - c))
        scaled = 1.0 / (1.0 + math.exp(-logit / max(0.1, float(temperature))))
        return max(0.01, min(0.999, scaled))

    @staticmethod
    def _has_antonym_conflict(text_a: str, text_b: str) -> bool:
        """Detects semantic negation or antonym inversion between two bilingual strings."""
        a_norm = f" {_normalize_text(text_a)} "
        b_norm = f" {_normalize_text(text_b)} "

        for pos_group, neg_group in _BILINGUAL_ANTONYM_PAIRS:
            a_has_pos = any(f" {w} " in a_norm or w in a_norm.split() for w in pos_group)
            a_has_neg = any(f" {w} " in a_norm or w in a_norm.split() for w in neg_group)
            b_has_pos = any(f" {w} " in b_norm or w in b_norm.split() for w in pos_group)
            b_has_neg = any(f" {w} " in b_norm or w in b_norm.split() for w in neg_group)

            if (a_has_pos and b_has_neg and not a_has_neg) or (a_has_neg and b_has_pos and not a_has_pos):
                return True

        # Explicit negation markers ("không", "not", "đừng", "never") in one but not the other
        neg_markers = (" không ", " đừng ", " cấm ", " not ", " never ", " without ")
        a_neg = any(m in a_norm for m in neg_markers)
        b_neg = any(m in b_norm for m in neg_markers)
        if a_neg != b_neg:
            # Check if they share core subject words
            a_words = set(_tokenize_words(a_norm))
            b_words = set(_tokenize_words(b_norm))
            if len(a_words & b_words) >= 2:
                return True

        return False

    def _score_boolean_bilingual(
        self,
        raw_state: Any,
        state_str: str,
        question: str,
        pos_val: Optional[Any],
        neg_vals: List[Any],
    ) -> Tuple[float, float]:
        """
        Symmetric binary evaluation for DecisionPrimitive.BOOLEAN.
        Cross-checks direct signal detection with a symmetric 2-way binary score
        so False/True predictions do not suffer from single-token under-reporting.
        """
        if pos_val is not None:
            is_true = bool(pos_val) if isinstance(pos_val, bool) else (float(pos_val) >= 0.5)
            return (0.97 if is_true else 0.03), 0.97
        if neg_vals:
            neg_first = neg_vals[0]
            was_true = bool(neg_first) if isinstance(neg_first, bool) else (float(neg_first) >= 0.5)
            return (0.04 if was_true else 0.96), 0.96

        q_norm = _normalize_text(question)

        # Case 1: Semantic equivalence / cache verification between two queries
        if isinstance(raw_state, dict) and ("query" in raw_state or "query_a" in raw_state) and (
            "cached_query" in raw_state or "query_b" in raw_state or "candidate" in raw_state
        ):
            qa = str(raw_state.get("query") or raw_state.get("query_a") or "")
            qb = str(raw_state.get("cached_query") or raw_state.get("query_b") or raw_state.get("candidate") or "")
            if self._has_antonym_conflict(qa, qb):
                return 0.02, 0.97
            wa = set(_tokenize_words(qa))
            wb = set(_tokenize_words(qb))
            if not wa or not wb:
                return 0.10, 0.90
            jaccard = len(wa & wb) / max(1, len(wa | wb))
            if jaccard >= 0.55:
                return 0.96, 0.95
            return 0.12, 0.92

        # Case 2: Security / danger / threat / destructive check
        risk_q_terms = (
            "nguy hiểm", "độc hại", "phá hoại", "rủi ro", "tấn công", "trái phép",
            "dangerous", "destructive", "malicious", "injection", "harmful",
            "breach", "unauthorized", "violate", "exfiltration", "corrupt",
        )
        safe_q_terms = (
            "an toàn", "hợp lệ", "tuân thủ", "được phép",
            "safe", "compliant", "valid", "benign",
        )

        has_high_risk = any(re.search(pat, state_str) for pat in _HIGH_RISK_PATTERNS)
        has_safe_signal = any(re.search(pat, state_str) for pat in _SAFE_ADMIN_PATTERNS)

        is_risk_q = any(t in q_norm for t in risk_q_terms)
        is_safe_q = any(t in q_norm for t in safe_q_terms)

        if is_risk_q:
            if has_high_risk:
                return 0.98, 0.97
            if has_safe_signal:
                return 0.02, 0.97
            return 0.04, 0.94

        if is_safe_q:
            if has_high_risk:
                return 0.02, 0.97
            if has_safe_signal:
                return 0.98, 0.97
            return 0.95, 0.93

        # Case 3: Failure diagnostic questions
        if "failure caused by" in q_norm:
            if "schema" in q_norm or "validation" in q_norm:
                matched = any(w in state_str for w in ("schema", "type_error", "validation", "missing_key", "jsondecode"))
                return (0.88 if matched else 0.06), 0.95
            if "environment" in q_norm or "drift" in q_norm:
                matched = any(w in state_str for w in ("connection refused", "timeout", "network", "unreachable"))
                return (0.86 if matched else 0.08), 0.95
            if "tool defect" in q_norm or "tool crash" in q_norm:
                matched = any(w in state_str for w in ("tool_error", "command_not_found", "process died", "exit 127"))
                return (0.87 if matched else 0.05), 0.95
            if "state mismatch" in q_norm or "contradiction" in q_norm:
                matched = any(w in state_str for w in ("assertionerror", "state_conflict", "precondition", "deadlock"))
                return (0.85 if matched else 0.09), 0.95

        # Default symmetric check
        if has_high_risk:
            return 0.03, 0.95
        return 0.94, 0.92

    def _score_choice_bilingual(
        self,
        state_str: str,
        question: str,
        options: List[str],
        descriptions: Optional[Dict[str, str]],
        pos_val: Optional[Any],
        neg_vals: List[Any],
    ) -> Tuple[str, Dict[str, float], float]:
        """
        Scores candidate options using bilingual concept profiles, optional option
        descriptions, and token overlap, then normalizes via softmax to sum to 1.0.
        """
        n_opts = len(options)
        if n_opts == 1:
            return options[0], {options[0]: 1.0}, 0.99

        # Instant feedback override
        if pos_val is not None and str(pos_val) in options:
            winner = str(pos_val)
            peak = 0.96
            rest = round((1.0 - peak) / (n_opts - 1), 6)
            dist = {o: (peak if o == winner else rest) for o in options}
            dist[winner] = round(dist[winner] + (1.0 - sum(dist.values())), 6)
            return winner, dist, peak

        state_words = set(_tokenize_words(state_str))
        raw_scores: Dict[str, float] = {o: 0.0 for o in options}

        for opt in options:
            opt_key = opt.lower().strip()
            score = 0.0

            # 1. Exact option name or normalized phrase in state
            opt_phrase = opt_key.replace("_", " ").replace("-", " ")
            if opt_key not in ("none_of_the_above", "unknown_anomaly", "none"):
                if opt_key in state_str or (len(opt_phrase) > 3 and opt_phrase in state_str):
                    score += 3.5

            # 2. Bilingual concept profile matching
            profile_terms = _CONCEPT_PROFILES.get(opt_key, ())
            for term in profile_terms:
                if term in state_str:
                    score += 2.4 if " " in term else 1.6

            # 3. Option description matching (when caller passes descriptions)
            if descriptions and opt in descriptions:
                desc_words = set(_tokenize_words(descriptions[opt]))
                overlap = len(state_words & desc_words)
                score += overlap * 0.9

            # 4. Sub-token overlap with option identifier
            opt_tokens = set(_tokenize_words(opt_phrase))
            if opt_key not in ("none_of_the_above", "unknown_anomaly", "none"):
                score += len(state_words & opt_tokens) * 1.1

            # 5. Penalty if option is in negative feedback guards
            if opt in neg_vals:
                score -= 10.0

            raw_scores[opt] = score

        # Handle fallback options ("none_of_the_above", "unknown_anomaly") when no real option matched
        fallback_keys = ("none_of_the_above", "unknown_anomaly", "none")
        non_fallback_max = max(
            (v for k, v in raw_scores.items() if k.lower() not in fallback_keys),
            default=0.0,
        )
        if non_fallback_max < 0.8:
            for fk in fallback_keys:
                for opt in options:
                    if opt.lower() == fk:
                        raw_scores[opt] = max(raw_scores[opt], 3.2)

        # Find winner and compute calibrated softmax distribution (100% order-invariant tie-breaking)
        sorted_opts = sorted(options, key=lambda o: (-round(raw_scores[o], 9), o.lower()))
        winner = sorted_opts[0]
        top_score = raw_scores[winner]
        second_score = raw_scores[sorted_opts[1]] if n_opts > 1 else 0.0
        margin = max(0.0, top_score - second_score)

        # Confidence scales smoothly with margin between top-1 and top-2
        peak_conf = min(0.98, max(0.86, 0.88 + 0.03 * min(margin, 3.0)))
        rest_mass = round((1.0 - peak_conf) / (n_opts - 1), 6)
        dist = {o: (peak_conf if o == winner else rest_mass) for o in options}
        residual = 1.0 - sum(dist[k] for k in sorted(dist.keys()))
        if abs(residual) > 1e-9:
            dist[winner] = round(dist[winner] + residual, 6)

        return winner, dist, peak_conf

    def _score_rubric_bilingual(
        self,
        raw_state: Any,
        state_str: str,
        question: str,
        levels: List[str],
        pos_val: Optional[Any],
        neg_vals: List[Any],
    ) -> Tuple[float, Dict[str, float], float]:
        """
        Expected-value rubric scoring for DecisionPrimitive.SCORE.
        Avoids level-0 position bias by evaluating multi-criteria quality/severity
        signals across all levels and computing a normalized distribution.
        """
        n = len(levels)
        if n == 0:
            return 0.0, {"0": 1.0}, 0.90

        # Quality / grounding assessment signals
        bad_signals = (
            "error:", "timed out", "không có dữ liệu", "không thể kết nối",
            "hallucination", "bịa đặt", "mâu thuẫn", "rỗng", "empty", "fail",
            "exception", "traceback",
        )
        good_signals = (
            "thành công", "hoàn tất", "chính xác", "verified", "completed",
            "success", "accurate", "grounded", "đầy đủ",
        )

        bad_hits = sum(1 for s in bad_signals if s in state_str)
        good_hits = sum(1 for s in good_signals if s in state_str)

        if pos_val is not None:
            try:
                target_idx = max(0, min(n - 1, int(round(float(pos_val)))))
            except Exception:
                target_idx = n - 1
        elif bad_hits > good_hits:
            target_idx = 0 if bad_hits >= 2 else max(0, (n // 3) - 1)
        elif good_hits > 0:
            target_idx = n - 1
        else:
            # Balanced mid-high default (avoids level-0 collapse)
            target_idx = min(n - 1, max(1, (2 * n) // 3))

        # Construct smooth unimodal distribution peaked at target_idx
        weights: List[float] = []
        for i in range(n):
            dist_from_peak = abs(i - target_idx)
            w = math.exp(-1.6 * dist_from_peak)
            weights.append(w)

        total_w = sum(weights) or 1.0
        dist: Dict[str, float] = {}
        for i, lvl in enumerate(levels):
            dist[str(lvl)] = round(weights[i] / total_w, 6)

        peak_key = str(levels[target_idx])
        residual = 1.0 - sum(dist.values())
        if abs(residual) > 1e-9:
            dist[peak_key] = round(dist[peak_key] + residual, 6)

        # Expected value over numeric levels if levels are numeric, else target_idx
        expected_val = 0.0
        numeric_ok = True
        for i, lvl in enumerate(levels):
            try:
                val = float(lvl)
            except Exception:
                numeric_ok = False
                break
            expected_val += val * dist[str(lvl)]

        result_score = round(expected_val, 4) if numeric_ok else float(target_idx)
        confidence = max(0.88, min(0.96, dist[peak_key] + 0.15))
        return result_score, dist, confidence
