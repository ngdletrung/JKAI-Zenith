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

_SENSITIVE_PATTERNS = (
    re.compile(r"(^|/)\.env(\..*)?$", re.IGNORECASE),
    re.compile(r"(^|/)credentials?\.(json|yaml|yml|ini)$", re.IGNORECASE),
    re.compile(r".*\.(pem|key|p12|pfx)$", re.IGNORECASE),
    re.compile(r"(^|/)id_rsa$", re.IGNORECASE),
    re.compile(r"(^|/)sovereign_secret.*", re.IGNORECASE),
)


def is_sensitive_path(path_str: str) -> bool:
    """Kiểm tra đường dẫn nhạy cảm bằng Regex chuẩn xác (tránh false positive như secret_santa.py)."""
    norm = str(path_str).replace("\\", "/").strip().lower()
    return any(p.search(norm) for p in _SENSITIVE_PATTERNS)


_ROOT_ONLY_BLOCK = frozenset(
    {
        ".git",
        ".zenith",
        "node_modules",
        "__pycache__",
        ".venv",
        "venv",
        "env",
        "dist",
        "build",
        ".pytest_cache",
        ".ruff_cache",
        ".mypy_cache",
        "sealed_C",
        "sealed_c",
    }
)

CANONICAL_IGNORED_DIRS = _ROOT_ONLY_BLOCK
EXCLUDED_WORKSPACE_DIRS = CANONICAL_IGNORED_DIRS

_AUDIT_RE = re.compile(
    r"\b(kiểm tra|kiem tra|check|audit|rà soát|ra soat|xem lỗi|xem loi|"
    r"tìm lỗi|tim loi|phân tích|phan tich|chạy thử|chay thu|đọc code|doc code)\b",
    re.IGNORECASE,
)
# Không dùng \bxem\b đơn lẻ — tránh nhầm «…tính năng… xem?»

_FIX_RE = re.compile(
    r"\b(sửa|sua|fix|repair|sửa lỗi|sua loi|khắc phục|khac phuc|tạo|tao|create|viết|viet|write|sinh|generate|make|thêm|them|add|build)\b",
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


def strip_worktree_nesting(path_value: Path | str) -> Path:
    """
    If path_value points inside a .zenith/worktrees/... subdirectory, returns the canonical
    parent repository root above .zenith so worktrees can never nest recursively.
    """
    resolved = Path(path_value).resolve()
    parts = list(resolved.parts)
    for i, part in enumerate(parts):
        if part.lower() == ".zenith" and i > 0:
            return Path(*parts[:i])
    return resolved


def get_jkai_workspace_root() -> Path:
    try:
        from core.config import settings
        cfg_root = getattr(settings, "WORKSPACE_ROOT", None)
    except Exception:
        cfg_root = None
    from core.utils import path_manager

    root = cfg_root or os.getenv("WORKSPACE_ROOT") or path_manager.get("WORKSPACE_ROOT") or path_manager.get_root()
    if root:
        p = Path(root)
        if p.is_dir():
            return strip_worktree_nesting(p)
    repo_from_file = Path(__file__).resolve().parents[2]
    if repo_from_file.is_dir():
        return strip_worktree_nesting(repo_from_file)
    for cand in (Path("/workspace"), Path(".")):
        if cand.is_dir():
            return strip_worktree_nesting(cand)
    return Path(".").resolve()


_CONTAINER_MOUNT_MAP: Tuple[Tuple[str, str], ...] = (
    ("core", "/shared/core"),
    ("intelligence", "/intelligence"),
    ("services/tools", "/shared/tools"),
    ("tools", "/shared/tools"),
    ("services/ai-brain", "/app"),
    ("data", "/data"),
    ("workspace", "/workspace"),
)


def to_workspace_rel_path(target_path: str) -> str:
    """Chuyển đổi đường dẫn container (/workspace/..., /shared/core/..., v.v.) hoặc tuyệt đối về tương đối so với gốc JKAI."""
    if not target_path:
        return ""
    p = str(target_path).replace("\\", "/").strip()
    if p in (".", "./", "/workspace", "/workspace/"):
        return "."
    if p.startswith("/workspace/"):
        return normalize_workspace_rel(p[len("/workspace/") :])
    # [F4 FIX]: Chuẩn hóa prefix shared/ và /shared/ về đúng thư mục gốc (core, tools)
    clean_p = p.lstrip("/")
    if clean_p.startswith("shared/core"):
        sub = clean_p[len("shared/core") :].lstrip("/")
        return normalize_workspace_rel(f"core/{sub}" if sub else "core")
    if clean_p.startswith("shared/tools"):
        sub = clean_p[len("shared/tools") :].lstrip("/")
        return normalize_workspace_rel(f"tools/{sub}" if sub else "tools")

    for rel_prefix, mount_root in _CONTAINER_MOUNT_MAP:
        if p == mount_root or p == mount_root + "/":
            return rel_prefix
        if p.startswith(mount_root + "/"):
            sub = p[len(mount_root) + 1 :]
            return normalize_workspace_rel(f"{rel_prefix}/{sub}")
    try:
        ws_root = str(get_jkai_workspace_root()).replace("\\", "/").rstrip("/")
        if ws_root and p.lower() == ws_root.lower():
            return "."
        if ws_root and p.lower().startswith(ws_root.lower() + "/"):
            return normalize_workspace_rel(p[len(ws_root) + 1 :])
    except Exception:
        pass
    if not p.startswith("/") and not (len(p) >= 2 and p[1] == ":" and p[0].isalpha()):
        return normalize_workspace_rel(p)
    return ""


def resolve_container_or_workspace_path(target_path: str) -> str:
    """
    [RC-1 FIX]: Phân giải đường dẫn thống nhất cho cả Host và Container đa mount:
    - Nếu đường dẫn bắt đầu bằng /workspace/<rel> hoặc tương đối <rel>, tự động kiểm tra:
      1. Đường dẫn trực tiếp trên <ws_root>/<rel> (Host hoặc /workspace/<rel> nếu có thật)
      2. Bảng ánh xạ mount trong container (/shared/core, /intelligence, /shared/tools, /app, /data)
    """
    if not target_path:
        return ""
    p = str(target_path).replace("\\", "/").strip()
    ws_root = get_jkai_workspace_root()
    ws_root_str = str(ws_root).replace("\\", "/").rstrip("/")

    if p in (".", "./"):
        return os.path.normpath(ws_root_str)

    # Nếu không phải /workspace/... mà đã tồn tại trực tiếp trên đĩa (ví dụ /shared/core/... hoặc D:/Docker/JKAI/...)
    if not p.startswith("/workspace") and (p.startswith("/") or (len(p) >= 2 and p[1] == ":" and p[0].isalpha())):
        if os.path.exists(p):
            return os.path.normpath(p)

    rel = to_workspace_rel_path(p)
    if rel == ".":
        if os.path.isdir("/workspace"):
            return os.path.normpath("/workspace")
        return os.path.normpath(ws_root_str)

    if rel:
        # 1. Kiểm tra trên ws_root/<rel> trước (ưu tiên Host hoặc file nằm thật trong /workspace)
        cand_ws = f"{ws_root_str}/{rel}"
        if os.path.exists(cand_ws):
            return os.path.normpath(cand_ws)

        # 2. Kiểm tra ánh xạ volume mount trong container (/shared/core, /intelligence, ...)
        for rel_prefix, mount_root in _CONTAINER_MOUNT_MAP:
            if rel == rel_prefix or rel.startswith(rel_prefix + "/"):
                sub = rel[len(rel_prefix) :].lstrip("/")
                cand_mount = f"{mount_root}/{sub}" if sub else mount_root
                if os.path.exists(cand_mount) or os.path.isdir(mount_root):
                    return os.path.normpath(cand_mount)

        # 3. Fallback về ws_root/<rel>
        return os.path.normpath(cand_ws)

    return os.path.normpath(p)



def iter_workspace_files(
    root: Path | str | None = None,
    suffixes: Optional[Tuple[str, ...]] = None,
    extra_ignored_dirs: Optional[frozenset[str]] = None,
):
    """
    Canonical workspace file iterator that prunes .zenith, .git, __pycache__, node_modules,
    .venv, dist, build in-place during os.walk so no tool/RAG/RepoMap ever traverses worktree
    or cache bloat.
    """
    base = Path(root).resolve() if root is not None else get_jkai_workspace_root()
    ignored = CANONICAL_IGNORED_DIRS if not extra_ignored_dirs else (CANONICAL_IGNORED_DIRS | set(extra_ignored_dirs))
    norm_suffixes = tuple(s.lower() for s in suffixes) if suffixes else None

    for dirpath, dirnames, filenames in os.walk(base, topdown=True):
        dirnames[:] = sorted(
            d
            for d in dirnames
            if d not in ignored
            and not d.startswith(".zenith")
            and not d.endswith(".worktrees")
            and not d.lower().startswith("sealed_")
            and d.lower() != "sealed_c"
        )
        for fname in sorted(filenames):
            if is_sensitive_path(fname):
                continue
            if "sealed_c" in dirpath.replace("\\", "/").lower():
                continue
            if norm_suffixes and not fname.lower().endswith(norm_suffixes):
                continue
            yield Path(dirpath) / fname


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
    # Chặn chuỗi thuần số hoặc phân số / ngày tháng (VD: 2/9, 30/4, 2024/2025, 1, 2)
    if re.match(r"^\d+(?:/\d+)*$", norm):
        return False
    if len(norm) <= 2:
        return False
    if _URL_PATH_ARTIFACT_RE.match(norm):
        return False
    if norm in _ROOT_ONLY_BLOCK:
        return False
    low = norm.lower()
    if "sealed_c" in low or "sealed_exam" in low:
        return False
    if low in _FALSE_WORKSPACE_PATHS:
        return False
    if low.endswith("/dossier") or low.endswith("/manifest") or low.endswith("/logic") or low.endswith("/skill"):
        return False
    if is_sensitive_path(norm):
        return False
    if _AI_MODEL_PATH_RE.search(rel):
        return False
    if _METRIC_UNIT_PATH_RE.search(rel):
        return False
    # Chặn các cặp từ nối bằng dấu gạch chéo thông dụng trong văn bản/prompt (VD: tool/plan, and/or, input/output, frontend/backend, client/server)
    _COMMON_SLASH_PAIRS = frozenset({
        "tool/plan", "plan/tool", "and/or", "input/output", "frontend/backend",
        "client/server", "read/write", "import/export", "true/false", "yes/no",
        "on/off", "pass/fail", "success/error", "req/res", "request/response"
    })
    if low in _COMMON_SLASH_PAIRS:
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

    # thư mục foo/bar (ưu tiên các cụm có 'thư mục', 'folder' trước các giới từ 'trong', 'tại')
    fm = re.search(
        r"(?:(?:trong|tại|tai)\s+)?(?:thư\s+mục|thu\s+muc|folder|thư mục con|thu muc con|directory|dir)\s+[`\"']?([\w\-]+(?:/[\w\-]+)*)"
        r"|(?:trong|tại|tai)\s+[`\"']?([\w\-]+(?:/[\w\-]+)*)",
        path_scan,
        re.IGNORECASE,
    )
    if fm:
        matched_path = fm.group(1) or fm.group(2)
        if matched_path:
            rel = normalize_workspace_rel(matched_path)
            if is_allowed_workspace_rel(rel):
                if "/" not in rel:
                    if workspace_scope_exists(rel):
                        return rel
                else:
                    return rel

    # Đoạn path có dấu / (chỉ chấp nhận nếu THỰC SỰ TỒN TẠI trên đĩa cứng Workspace)
    candidates = []
    for m in _REL_PATH_RE.finditer(path_scan):
        rel = normalize_workspace_rel(m.group(1))
        if is_allowed_workspace_rel(rel) and "://" not in rel:
            # Kiểm tra xem đường dẫn có thực sự tồn tại trên đĩa không trước khi coi là workspace
            if workspace_scope_exists(rel):
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
    low = g.lower()
    if _NO_FIX_RE.search(g):
        return "audit"
    if any(k in low for k in ["kiểm toán", "audit", "rà soát", "so sánh", "đối chiếu"]):
        if any(k in low for k in ["hãy sửa", "hãy fix", "sửa lỗi này", "tiến hành sửa", "sửa mã", "refactor", "áp dụng bản vá"]):
            return "fix"
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
            "- Dùng view_file / verify_file đọc đầy đủ từng tệp mục tiêu trong yêu cầu (lấy số liệu từ [FILE_METADATA]) → phân tích chính xác theo yêu cầu của Master.\n"
            "- Không ghi file trừ khi Master yêu cầu sửa.\n"
            "- Bắt buộc dùng tool thực chứng, tuyệt đối không suy đoán hoặc bịa đặt.\n"
        )

    return (goal or "").strip() + directive, target, mode


def enrich_goal_for_project_workspace(goal: str) -> Tuple[str, Optional[str], str]:
    return enrich_goal_for_workspace_target(goal)


def workspace_scope_exists(scope_rel: str) -> bool:
    """Thư mục scope có thật trên đĩa hoặc mount container (tránh agent ảo web/README, com/org/repo)."""
    if scope_rel == ".":
        return get_jkai_workspace_root().is_dir() or os.path.isdir("/workspace")
    rel = normalize_workspace_rel(scope_rel or "")
    if not rel:
        return False
    try:
        resolved = resolve_container_or_workspace_path(rel)
        return os.path.isdir(resolved)
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
