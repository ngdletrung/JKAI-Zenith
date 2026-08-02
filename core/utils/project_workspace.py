"""
Nhận diện thư mục làm việc bất kỳ TRONG GỐC JKAI (workspace) — không cố định scratch/projects.

Ví dụ:
- scratch/projects/app_loi_di
- services/ai-brain
- demo/my_tool
- D:\\Docker\\JKAI\\projects\\foo  → projects/foo
"""

from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Optional, Tuple

from core.utils.regex import URL as _URL_RE, GIT_URL as _GIT_HOST_RE, PY_FILE as _PY_FILE_RE

_BLOCK_FRAGMENTS = (
    ".env",
    "sovereign",
    "credential",
    "secret",
    "private_key",
    ".pem",
)

_ROOT_ONLY_BLOCK = frozenset({".git", "node_modules", "__pycache__", ".venv", "dist", "build"})

_AUDIT_RE = re.compile(
    r"\b(kiểm tra|kiem tra|check|audit|rà soát|ra soat|xem lỗi|xem loi|"
    r"tìm lỗi|tim loi|phân tích|phan tich|chạy thử|chay thu|đọc code|doc code)\b",
    re.IGNORECASE,
)
# Không dùng \bxem\b đơn lẻ — tránh nhầm «…tính năng… xem?»

_FIX_RE = re.compile(
    r"\b(sửa|sua|fix|repair|sửa lỗi|sua loi|khắc phục|khac phuc)\b",
    re.IGNORECASE,
)

_ERROR_RE = re.compile(
    r"\b(lỗi|loi|bug|crash|traceback|exception)\b",
    re.IGNORECASE,
)

_REL_PATH_RE = re.compile(
    r"\b((?:[\w\-]+)(?:/[\w\-]+)+)\b",
)

# Path giả từ hostname URL (com/org/repo, net/...)
_URL_PATH_ARTIFACT_RE = re.compile(r"^(?:com|org|net|io|dev)/", re.IGNORECASE)

_NO_FIX_RE = re.compile(
    r"\b(không sửa|khong sua|không fix|khong fix|no fix|don't fix|do not fix|"
    r"không sửa code|khong sua code|không ghi|khong ghi|read[- ]only|"
    r"không thay đổi|khong thay doi|without (?:editing|changing))\b",
    re.IGNORECASE,
)

# Phân tích repo GitHub trên web — không map path ảo (web/README, …)
_WEB_ANALYSIS_RE = re.compile(
    r"\b(phân tích|phan tich|so sánh|so sanh|đánh giá|danh gia|analyze|compare|review)\b",
    re.IGNORECASE,
)
_NO_LOCAL_AGENT_RE = re.compile(
    r"\b(không list_dir|khong list_dir|no list_dir|không list_dir workspace|"
    r"chỉ đọc web|chi doc web|đọc web/readme|doc web/readme|read web/readme|"
    r"chỉ đọc readme trên web|chi doc readme tren web)\b",
    re.IGNORECASE,
)

# Path mô tả README trên web, không phải thư mục JKAI
_FALSE_WORKSPACE_PATHS = frozenset(
    {
        "web/readme",
        "web/readme.md",
        "docs/readme",
        "readme",
        "readme.md",
    }
)

# Regex cho các path giả do tên model AI (Gemini/GPT-4o, Claude/3.5, ...)
_AI_MODEL_PATH_RE = re.compile(
    r"\b(Gemini|GPT|Claude|DeepSeek|Grok|Llama|Mistral|Qwen|"
    r"gemini|gpt|claude|deepseek|grok|llama|mistral|qwen)"
    r"/[\w\-]+",
    re.IGNORECASE,
)

# Regex cho các path giả do đơn vị đo lường / thông số kỹ thuật (request/phút, lần/giây, ...)
_METRIC_UNIT_PATH_RE = re.compile(
    r"\b[\w\-]+/(phút|giây|ngày|tháng|năm|giờ|phut|giay|ngay|thang|nam|gio|lần|lan|giây|giay)\b",
    re.IGNORECASE,
)

_READ_WEB_NOISE_RE = re.compile(
    r"\b(?:chỉ\s+)?(?:đọc|doc|read)\s+web/readme\b|"
    r"\bweb/readme\b|"
    r"\bkhông\s+list_dir(?:\s+workspace)?\b|"
    r"\bno\s+list_dir(?:\s+workspace)?\b",
    re.IGNORECASE,
)


def get_jkai_workspace_root() -> Path:
    from core.config import settings
    from core.utils import path_manager

    root = settings.WORKSPACE_ROOT or path_manager.get("WORKSPACE_ROOT") or path_manager.get_root()
    p = Path(root)
    if p.is_dir():
        return p.resolve()
    for cand in (Path("/workspace"), Path("D:/Docker/JKAI")):
        if cand.is_dir():
            return cand.resolve()
    return Path(".").resolve()


def normalize_workspace_rel(rel: str) -> str:
    if not rel:
        return ""
    s = rel.replace("\\", "/").strip().strip("`\"'")
    while "//" in s:
        s = s.replace("//", "/")
    parts = [p for p in s.strip("/").split("/") if p and p != "."]
    if ".." in parts:
        return ""
    return "/".join(parts)


def is_allowed_workspace_rel(rel: str) -> bool:
    norm = normalize_workspace_rel(rel)
    if not norm:
        return False
    if _URL_PATH_ARTIFACT_RE.match(norm):
        return False
    if norm in _ROOT_ONLY_BLOCK:
        return False
    low = norm.lower()
    if low in _FALSE_WORKSPACE_PATHS:
        return False
    if low.endswith("/dossier") or low.endswith("/manifest") or low.endswith("/logic") or low.endswith("/skill"):
        return False
    if any(frag in low for frag in _BLOCK_FRAGMENTS):
        return False
    if _AI_MODEL_PATH_RE.search(rel):
        return False
    if _METRIC_UNIT_PATH_RE.search(rel):
        return False
    return True


def _text_without_urls(text: str) -> str:
    """Xóa URL khỏi chuỗi trước khi regex bắt path kiểu foo/bar."""
    return _URL_RE.sub(" ", text or "")


def goal_forces_web_analysis_pipeline(goal: str) -> bool:
    """
  Chỉ pipeline web (scrape README) — khi Master nói rõ không clone / không list_dir.
  Phân tích GitHub mặc định → repo_clone (scratch/projects/*-ref), không ép web-only.
    """
    if not goal or not _GIT_HOST_RE.search(goal):
        return False
    if _NO_LOCAL_AGENT_RE.search(goal):
        return True
    if re.search(
        r"\b(chỉ\s+(?:đọc|doc|read)\s+(?:web|readme)|web-only|web only|chỉ\s+scrape|chi\s+scrape)\b",
        goal,
        re.IGNORECASE,
    ):
        return True
    return False


def goal_is_external_repo_url_analysis(goal: str) -> bool:
    """
    Phân tích link GitHub/GitLab ngoài workspace — không chạy Cursor Agent local.
    """
    if goal_forces_web_analysis_pipeline(goal):
        return True
    if not goal or not _GIT_HOST_RE.search(goal):
        return False
    remainder = _text_without_urls(goal)
    remainder = _READ_WEB_NOISE_RE.sub(" ", remainder)
    return detect_workspace_target(remainder) is None


def detect_workspace_target(text: str) -> Optional[str]:
    """
    Trả về đường dẫn tương đối so với gốc JKAI (workspace), vd: scratch/projects/app_loi_di
    """
    if not text:
        return None

    ws = get_jkai_workspace_root()
    ws_posix = str(ws).replace("\\", "/")
    t = text.replace("\\", "/")
    path_scan = _text_without_urls(t)
    if _GIT_HOST_RE.search(t):
        path_scan = _READ_WEB_NOISE_RE.sub(" ", path_scan)

    # /workspace/relative/...
    m = re.search(r"/workspace/([^\s`\"']+)", t, re.IGNORECASE)
    if m:
        rel = normalize_workspace_rel(m.group(1).rstrip("/.,;"))
        if is_allowed_workspace_rel(rel):
            return rel

    low_t = t.lower()

    # Đường dẫn tuyệt đối trỏ vào gốc JKAI từ environment variable WORKSPACE_ROOT
    env_ws = os.getenv("WORKSPACE_ROOT")
    if env_ws:
        env_ws_posix = env_ws.replace("\\", "/").lower()
        if env_ws_posix in low_t:
            pos = low_t.find(env_ws_posix)
            tail = t[pos + len(env_ws_posix) :].lstrip("/")
            tail = re.split(r"[\s`\"',;]", tail)[0]
            rel = normalize_workspace_rel(tail)
            if rel == "":
                return "."
            if is_allowed_workspace_rel(rel):
                return rel

    # Đường dẫn tuyệt đối trỏ vào gốc JKAI
    low_ws = ws_posix.lower()
    if low_ws in low_t:
        pos = low_t.find(low_ws)
        tail = t[pos + len(ws_posix) :].lstrip("/")
        tail = re.split(r"[\s`\"',;]", tail)[0]
        rel = normalize_workspace_rel(tail)
        # === SỬA: Cho phép scope root ===
        if rel == "":
            return "."
        if is_allowed_workspace_rel(rel):
            return rel

    # File .py → thư mục chứa file (trong workspace)
    pm = _PY_FILE_RE.search(path_scan)
    if pm:
        rel = normalize_workspace_rel(str(Path(pm.group(1)).parent))
        if rel and is_allowed_workspace_rel(rel):
            return rel

    # thư mục foo/bar
    fm = re.search(
        r"(?:thư mục|thu muc|folder|trong|tại|tai)\s+[`\"']?([\w\-]+(?:/[\w\-]+)*)",
        path_scan,
        re.IGNORECASE,
    )
    if fm:
        rel = normalize_workspace_rel(fm.group(1))
        if is_allowed_workspace_rel(rel):
            if "/" not in rel:
                if workspace_scope_exists(rel):
                    return rel
            else:
                return rel

    # Đoạn path có dấu / (ưu tiên dài nhất hợp lệ) — không lấy từ URL đã strip
    candidates = []
    for m in _REL_PATH_RE.finditer(path_scan):
        rel = normalize_workspace_rel(m.group(1))
        if is_allowed_workspace_rel(rel) and "://" not in rel:
            candidates.append(rel)
    if candidates:
        return max(candidates, key=len)

    return None


# Aliases (tương thích code cũ)
def detect_project_path(text: str) -> Optional[str]:
    return detect_workspace_target(text)


def goal_targets_scratch_project(goal: str) -> bool:
    return detect_workspace_target(goal) is not None


def goal_targets_workspace_folder(goal: str) -> bool:
    return detect_workspace_target(goal) is not None


def workspace_task_mode(goal: str) -> str:
    g = goal or ""
    if _NO_FIX_RE.search(g):
        return "audit"
    if _FIX_RE.search(g):
        return "fix"
    if _AUDIT_RE.search(g) or _ERROR_RE.search(g):
        return "audit"
    return "audit"


def project_task_mode(goal: str) -> str:
    return workspace_task_mode(goal)


def enrich_goal_for_workspace_target(
    goal: str, target: Optional[str] = None
) -> Tuple[str, Optional[str], str]:
    if not target:
        target = detect_workspace_target(goal)
    if not target:
        return goal, None, ""

    mode = workspace_task_mode(goal)
    container_path = "/workspace" if target == "." else f"/workspace/{target}"

    if mode == "fix":
        directive = (
            f"\n\n[JKAI WORKSPACE — {target}]\n"
            f"- Phạm vi DUY NHẤT: `{container_path}` (trong gốc JKAI).\n"
            "- Thực thi như Cursor: list_dir → đọc → chạy test/lệnh → sửa CHỈ trong phạm vi này "
            "→ chạy lại đến khi hết lỗi.\n"
            "- Bắt buộc dùng tool (list_dir, view_file, replace_file_content, run_command).\n"
        )
    else:
        directive = (
            f"\n\n[JKAI WORKSPACE — {target}]\n"
            f"- Phạm vi: `{container_path}`.\n"
            "- list_dir → đọc → chạy lệnh/test → báo lỗi (file, dòng, traceback).\n"
            "- Không ghi file trừ khi Master yêu cầu sửa.\n"
            "- Bắt buộc dùng tool, không đoán.\n"
        )

    return (goal or "").strip() + directive, target, mode


def enrich_goal_for_project_workspace(goal: str) -> Tuple[str, Optional[str], str]:
    return enrich_goal_for_workspace_target(goal)


def workspace_scope_exists(scope_rel: str) -> bool:
    """Thư mục scope có thật trên đĩa (tránh agent ảo web/README, com/org/repo)."""
    # Cho phép scope "." là root workspace
    if scope_rel == ".":
        return get_jkai_workspace_root().is_dir()
    rel = normalize_workspace_rel(scope_rel or "")
    if not rel:
        return False
    try:
        return (get_jkai_workspace_root() / rel).is_dir()
    except OSError:
        return False


def goal_should_use_workspace_agent(goal: str) -> bool:
    """Có thư mục/file trong workspace → Cursor agent + DEEP."""
    if goal_forces_web_analysis_pipeline(goal):
        return False
    scope = detect_workspace_target(goal)
    if not scope:
        return False
    return workspace_scope_exists(scope)


def goal_should_use_project_pipeline(goal: str) -> bool:
    return goal_should_use_workspace_agent(goal)
