"""
Repo Surgeon — rà soát và sửa mã JKAI trong workspace (tích hợp /tusualoi, /tucaitien).

Chính sách:
- Đọc/ghi mọi path con trong gốc JKAI (workspace), trừ denylist (.env, sovereign…).
- Ghi production chỉ sau AST OK (và sandbox gate khi có code chạy được).
"""

from __future__ import annotations

import json
import os
import re
import shutil
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from core.utils.sandbox_deploy_gate import validate_python_ast

REPO_SCAN_TOP = ("services", "core", "scripts")
SKIP_DIR_NAMES = frozenset(
    {".git", "__pycache__", "node_modules", "vault", ".obsidian", ".venv", "dist", "build"}
)
BLOCKLIST_PATH_FRAGMENTS = (
    ".env",
    "sovereign",
    "credential",
    "secret",
    "api_key",
    "private_key",
    ".pem",
)


def _workspace_root() -> Path:
    from core.config import settings
    from core.utils import path_manager

    root = settings.WORKSPACE_ROOT or path_manager.get("WORKSPACE_ROOT") or path_manager.get_root()
    if root:
        p = Path(root)
        if p.is_dir():
            return p.resolve()
    for cand in (Path("/workspace"), Path("D:/Docker/JKAI")):
        if cand.is_dir():
            return cand.resolve()
    return Path(".").resolve()


def is_allowed_repo_path(rel_path: str) -> bool:
    """Mọi path con trong gốc JKAI, trừ denylist (secrets, .env…)."""
    from core.utils.project_workspace import is_allowed_workspace_rel, normalize_workspace_rel

    norm = normalize_workspace_rel(rel_path.replace("\\", "/").lstrip("/"))
    if not norm:
        return False
    low = norm.lower()
    if any(frag in low for frag in BLOCKLIST_PATH_FRAGMENTS):
        return False
    return is_allowed_workspace_rel(norm)


def resolve_repo_path(rel_or_abs: str, workspace: Optional[Path] = None) -> Optional[Path]:
    ws = workspace or _workspace_root()
    p = Path(rel_or_abs)
    if p.is_absolute():
        try:
            rel = p.resolve().relative_to(ws)
        except ValueError:
            return None
    else:
        rel = Path(rel_or_abs.replace("\\", "/"))
    norm = str(rel).replace("\\", "/")
    if not is_allowed_repo_path(norm):
        return None
    full = (ws / rel).resolve()
    if not str(full).startswith(str(ws.resolve())):
        return None
    return full


def candidate_path_for(rel_path: str, workspace: Optional[Path] = None) -> Path:
    ws = workspace or _workspace_root()
    safe = rel_path.replace("\\", "/").lstrip("/").replace("..", "_")
    return ws / "scratch" / "sandbox" / "repo_candidates" / safe


def _scan_top_dirs(ws: Path) -> tuple:
    tops = []
    try:
        for name in os.listdir(ws):
            if name in SKIP_DIR_NAMES or name.startswith("."):
                continue
            if (ws / name).is_dir():
                tops.append(name)
    except OSError:
        pass
    return tuple(tops) if tops else REPO_SCAN_TOP


def scan_python_syntax(
    workspace: Optional[Path] = None,
    max_files: int = 400,
    scope_rel: Optional[str] = None,
) -> List[Dict[str, str]]:
    ws = workspace or _workspace_root()
    errors: List[Dict[str, str]] = []
    count = 0
    if scope_rel:
        tops = (scope_rel.replace("\\", "/").strip("/"),)
    else:
        tops = _scan_top_dirs(ws)
    for top in tops:
        base = ws / top
        if not base.is_dir():
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]
            for name in files:
                if not name.endswith(".py"):
                    continue
                full = Path(root) / name
                try:
                    rel = full.relative_to(ws)
                except ValueError:
                    continue
                rel_s = str(rel).replace("\\", "/")
                if not is_allowed_repo_path(rel_s):
                    continue
                count += 1
                if count > max_files:
                    return errors
                try:
                    src = full.read_text(encoding="utf-8", errors="replace")
                    compile(src, rel_s, "exec")
                except SyntaxError as e:
                    errors.append(
                        {
                            "path": rel_s,
                            "line": str(e.lineno or "?"),
                            "msg": e.msg or str(e),
                        }
                    )
                except OSError as e:
                    errors.append({"path": rel_s, "line": "?", "msg": str(e)})
    return errors


def _extract_path_hints(text: str) -> List[str]:
    hints: List[str] = []
    for m in re.finditer(
        r"(?:services|core|intelligence|scripts)/[\w./\-]+\.py",
        text,
        re.IGNORECASE,
    ):
        hints.append(m.group(0).replace("\\", "/"))
    for m in re.finditer(r"`([^`]+\.py)`", text):
        hints.append(m.group(1).replace("\\", "/"))
    seen = set()
    out = []
    for h in hints:
        if h not in seen:
            seen.add(h)
            out.append(h)
    return out[:8]


def grep_repo(
    keywords: List[str],
    workspace: Optional[Path] = None,
    max_hits: int = 12,
) -> List[Dict[str, str]]:
    ws = workspace or _workspace_root()
    hits: List[Dict[str, str]] = []
    if not keywords:
        return hits
    for top in REPO_SCAN_TOP:
        base = ws / top
        if not base.is_dir():
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]
            for name in files:
                if not name.endswith((".py", ".md", ".json", ".yaml", ".yml")):
                    continue
                full = Path(root) / name
                try:
                    rel = str(full.relative_to(ws)).replace("\\", "/")
                except ValueError:
                    continue
                if not is_allowed_repo_path(rel):
                    continue
                try:
                    text = full.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                upper = text.upper()
                for kw in keywords:
                    if kw.upper() in upper or kw in text:
                        line_no = 0
                        for i, line in enumerate(text.splitlines(), 1):
                            if kw in line or kw.upper() in line.upper():
                                line_no = i
                                snippet = line.strip()[:120]
                                break
                        hits.append(
                            {
                                "path": rel,
                                "keyword": kw,
                                "line": str(line_no),
                                "snippet": snippet if line_no else "",
                            }
                        )
                        break
                if len(hits) >= max_hits:
                    return hits
    return hits


def scan_common_bugs(
    workspace: Optional[Path] = None,
    max_files: int = 400,
) -> List[Dict[str, Any]]:
    """Detect common bug patterns: bare except, mutable defaults, sync-in-async, print in prod."""
    ws = workspace or _workspace_root()
    findings: List[Dict[str, Any]] = []
    count = 0

    _BUG_PATTERNS = [
        ("bare-except", re.compile(r"^\s*except\s*:", re.MULTILINE)),
        ("mutable-default-list", re.compile(r"def \w+\([^)]*=\s*\[")),
        ("mutable-default-dict", re.compile(r"def \w+\([^)]*=\s*\{")),
        ("sync-sleep-in-async", re.compile(
            r"async\s+def\s+\w+.*?(?=\n\S|\Z)[\s\S]*?time\.sleep\("
        )),
        ("print-in-prod", re.compile(r"^\s*print\(", re.MULTILINE)),
    ]

    for top in _scan_top_dirs(ws):
        base = ws / top
        if not base.is_dir():
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]
            for name in files:
                if not name.endswith(".py"):
                    continue
                full = Path(root) / name
                try:
                    rel = str(full.relative_to(ws)).replace("\\", "/")
                except ValueError:
                    continue
                if not is_allowed_repo_path(rel):
                    continue
                count += 1
                if count > max_files:
                    return findings
                try:
                    src = full.read_text(encoding="utf-8", errors="replace")
                except OSError:
                    continue
                for bug_id, pattern in _BUG_PATTERNS:
                    for m in pattern.finditer(src):
                        line_num = src[:m.start()].count("\n") + 1
                        findings.append({
                            "path": rel,
                            "line": line_num,
                            "bug": bug_id,
                            "snippet": src.splitlines()[line_num - 1].strip()[:120],
                        })
    return findings


def scan_import_anomalies(
    workspace: Optional[Path] = None,
    max_files: int = 400,
) -> List[Dict[str, Any]]:
    """Detect likely-broken imports by checking local module existence."""
    ws = workspace or _workspace_root()
    findings: List[Dict[str, Any]] = []
    count = 0

    py_files: List[Path] = []
    for top in _scan_top_dirs(ws):
        base = ws / top
        if not base.is_dir():
            continue
        for root, dirs, files in os.walk(base):
            dirs[:] = [d for d in dirs if d not in SKIP_DIR_NAMES]
            for name in files:
                if not name.endswith(".py"):
                    continue
                py_files.append(Path(root) / name)

    for full in py_files:
        try:
            rel = str(full.relative_to(ws)).replace("\\", "/")
        except ValueError:
            continue
        if not is_allowed_repo_path(rel):
            continue
        count += 1
        if count > max_files:
            break
        try:
            src = full.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        from_imports = re.findall(r"^\s*from\s+(\S+)\s+import", src, re.MULTILINE)
        for mod in from_imports:
            if mod.startswith("core.") or mod.startswith("services.") or mod.startswith("intelligence."):
                mod_path = mod.replace(".", "/") + ".py"
                candidate = ws / mod_path
                pkg_candidate = ws / mod.replace(".", "/") / "__init__.py"
                if not candidate.exists() and not pkg_candidate.exists():
                    findings.append({
                        "path": rel,
                        "import": mod,
                        "note": "module not found locally",
                    })

    return findings


def audit_repo(instruction: str = "", workspace: Optional[Path] = None) -> Dict[str, Any]:
    ws = workspace or _workspace_root()
    syntax_errors = scan_python_syntax(ws)
    common_bugs = scan_common_bugs(ws)
    import_issues = scan_import_anomalies(ws)
    hints = _extract_path_hints(instruction or "")
    keywords = []
    if instruction:
        for w in re.findall(r"[\w]{4,}", instruction):
            wl = w.lower()
            if wl not in ("master", "zenith", "jkai", "system", "khong", "khắc", "phục"):
                keywords.append(w)
        keywords = keywords[:6]
    grep_hits = grep_repo(keywords, ws) if keywords else []

    snippets = []
    for rel in hints:
        full = resolve_repo_path(rel, ws)
        if full and full.is_file():
            try:
                lines = full.read_text(encoding="utf-8", errors="replace").splitlines()
                head = "\n".join(lines[:35])
                snippets.append({"path": rel, "preview": head[:2000]})
            except OSError:
                pass

    return {
        "workspace": str(ws),
        "syntax_errors": syntax_errors,
        "common_bugs": common_bugs,
        "import_issues": import_issues,
        "grep_hits": grep_hits,
        "path_hints": hints,
        "snippets": snippets,
    }


def format_audit_report(data: Dict[str, Any], instruction: str = "") -> str:
    lines = [
        "\n📂 **RÀ SOÁT REPO (CURSOR-STYLE):**",
        f"- Workspace: `{data.get('workspace', '?')}`",
    ]
    if instruction:
        lines.append(f"- Chỉ thị: {instruction[:200]}{'…' if len(instruction) > 200 else ''}")

    errs = data.get("syntax_errors") or []
    if errs:
        lines.append(f"- **SyntaxError:** {len(errs)} file `.py`:")
        for e in errs[:10]:
            lines.append(f"  • `{e['path']}` L{e['line']}: {e['msg']}")
        if len(errs) > 10:
            lines.append(f"  • … và {len(errs) - 10} file khác.")
    else:
        lines.append("- Syntax scan (`services/`, `core/`, `scripts/`): ✅ không lỗi cú pháp.")

    bugs = data.get("common_bugs") or []
    if bugs:
        bug_counts: Dict[str, int] = {}
        for b in bugs:
            bug_counts[b["bug"]] = bug_counts.get(b["bug"], 0) + 1
        summary = ", ".join(f"{k}: {v}" for k, v in sorted(bug_counts.items()))
        lines.append(f"- **Bug patterns:** {summary}")
        _BUG_LABELS = {
            "bare-except": "Bare `except:`",
            "mutable-default-list": "Mutable list default arg",
            "mutable-default-dict": "Mutable dict default arg",
            "sync-sleep-in-async": "`time.sleep()` in async function",
            "print-in-prod": "`print()` in production code",
        }
        for b in bugs[:15]:
            label = _BUG_LABELS.get(b["bug"], b["bug"])
            lines.append(f"  • `{b['path']}` L{b['line']}: {label} — `{b['snippet']}`")
        if len(bugs) > 15:
            lines.append(f"  • … và {len(bugs) - 15} lỗi khác.")
    else:
        lines.append("- Bug patterns: ✅ không phát hiện.")

    imp = data.get("import_issues") or []
    if imp:
        lines.append(f"- **Import anomalies:** {len(imp)} vấn đề:")
        for ix in imp[:8]:
            lines.append(f"  • `{ix['path']}`: `{ix['import']}` — {ix['note']}")
        if len(imp) > 8:
            lines.append(f"  • … và {len(imp) - 8} vấn đề khác.")
    else:
        lines.append("- Import scan: ✅ không phát hiện.")

    gh = data.get("grep_hits") or []
    if gh:
        lines.append(f"- **Grep theo chỉ thị:** {len(gh)} điểm chạm:")
        for h in gh[:8]:
            snip = f" — `{h.get('snippet', '')[:60]}`" if h.get("snippet") else ""
            lines.append(f"  • `{h['path']}`:{h['line']} ({h['keyword']}){snip}")

    for sn in data.get("snippets") or []:
        lines.append(f"- **Đọc nhanh** `{sn['path']}` (35 dòng đầu trong báo cáo nội bộ).")

    return "\n".join(lines)


def write_repo_candidate(rel_path: str, content: str, workspace: Optional[Path] = None) -> Tuple[Path, str]:
    if not is_allowed_repo_path(rel_path.replace("\\", "/")):
        return Path(), "path not allowed"
    ws = workspace or _workspace_root()
    dest = candidate_path_for(rel_path, ws)
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_text(content, encoding="utf-8")
    return dest, "OK"


def promote_repo_candidate(candidate: Path, production: Path) -> Tuple[bool, str]:
    if not candidate.is_file() or not production.parent.exists():
        return False, "missing candidate or production parent"
    bak = production.with_suffix(production.suffix + ".repo_bak")
    try:
        if production.is_file():
            shutil.copy2(production, bak)
        production.write_text(candidate.read_text(encoding="utf-8"), encoding="utf-8")
        return True, f"Đã promote → `{production}` (backup: `{bak.name}`)"
    except Exception as e:
        return False, str(e)


async def propose_repo_patches(
    instruction: str,
    audit_data: Dict[str, Any],
    task_id: str = "sys",
    max_files: int = 2,
) -> List[Dict[str, str]]:
    """LLM đề xuất sửa tối đa max_files (full file content)."""
    from core.utils.engine import engine

    ws = _workspace_root()
    context_parts = []
    for e in (audit_data.get("syntax_errors") or [])[:5]:
        full = resolve_repo_path(e["path"], ws)
        if full and full.is_file():
            context_parts.append(
                f"### SYNTAX ERROR: {e['path']} L{e['line']}\n"
                f"{full.read_text(encoding='utf-8', errors='replace')[:8000]}"
            )
    for sn in (audit_data.get("snippets") or [])[:2]:
        context_parts.append(f"### FILE: {sn['path']}\n{sn.get('preview', '')[:4000]}")

    if not context_parts and not instruction:
        return []

    prompt = f"""[JKAI REPO SURGEON]
Master instruction: {instruction}

Audit summary:
- syntax errors: {len(audit_data.get('syntax_errors') or [])}
- grep hits: {len(audit_data.get('grep_hits') or [])}

Files context:
{chr(10).join(context_parts) if context_parts else "(no file bodies — use grep hints only)"}

Return ONLY a JSON array (max {max_files} items). Each item:
{{"path": "services/.../file.py", "content": "<full new file content>"}}

Rules:
- path must be under services/, core/, intelligence/skills/, or scripts/
- no .env, no sovereign keys
- fix root cause minimally; valid Python only
- if unsure return []
"""
    try:
        raw = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="EXECUTOR",
            lock_timeout=90,
            timeout=90,
        )
    except Exception as e:
        return [{"error": str(e)}]

    if not raw or not isinstance(raw, str):
        return []

    m = re.search(r"\[[\s\S]*\]", raw)
    if not m:
        return []
    try:
        arr = json.loads(m.group(0))
        if not isinstance(arr, list):
            return []
        out = []
        for item in arr[:max_files]:
            if isinstance(item, dict) and item.get("path") and item.get("content"):
                rel = item["path"].replace("\\", "/").lstrip("/")
                if is_allowed_repo_path(rel):
                    out.append({"path": rel, "content": item["content"]})
        return out
    except json.JSONDecodeError:
        return []


async def apply_repo_patches(
    patches: List[Dict[str, str]],
    dry_run: bool = True,
    task_id: str = "sys",
) -> Tuple[str, List[str]]:
    from core.utils.engine import engine

    promoted: List[str] = []
    if not patches:
        return "- Repo patch: không có đề xuất sửa (hoặc LLM trả về rỗng).", promoted

    lines = ["\n🔬 **SỬA REPO (sandbox trước production):**"]
    ws = _workspace_root()

    for item in patches:
        if item.get("error"):
            lines.append(f"- ⚠️ LLM: {item['error']}")
            continue
        rel = item["path"]
        content = item["content"]
        prod = resolve_repo_path(rel, ws)
        if not prod:
            lines.append(f"- ⛔ `{rel}` ngoài allowlist — bỏ qua.")
            continue

        ast_ok, ast_msg = validate_python_ast(content, rel)
        if not ast_ok:
            lines.append(f"- ❌ `{rel}` AST fail: {ast_msg}")
            continue

        cand, _ = write_repo_candidate(rel, content, ws)
        lines.append(f"- 📄 File thử: `{cand}` (AST OK)")

        if dry_run:
            lines.append(f"  • Production `{rel}` **chưa đổi** — dùng `/tucaitien --apply` hoặc `/tusualoi` (tự sửa bật).")
            continue

        ok, msg = promote_repo_candidate(cand, prod)
        lines.append(f"  • {'✅' if ok else '❌'} {msg}")
        if ok:
            promoted.append(rel)
            try:
                from core.utils.executor_cache import invalidate_all_executors

                _inv_ok, inv_msg = await invalidate_all_executors()
                lines.append(f"  • 🔄 {inv_msg}")
            except Exception as e:
                lines.append(f"  • ⚠️ invalidate_cache: {e}")

    if not dry_run and promoted:
        from core.utils.post_patch_verify import verify_after_repair

        v_ok, v_msg = verify_after_repair(
            touched_rel_paths=promoted,
            run_compileall=True,
            run_tests=True,
        )
        lines.append(v_msg)
        if not v_ok:
            lines.append("- ⚠️ Xác minh chưa pass — kiểm tra lại hoặc chạy `/tusualoi` lần nữa.")

    if not dry_run:
        engine.publish_mission_log(
            "REPO-SURGEON",
            "Đã promote repo — executor cache đã được yêu cầu xóa.",
            task_id,
        )
    return "\n".join(lines), promoted


async def run_repo_workflow(
    instruction: str,
    dry_run: bool = True,
    allow_llm_fix: bool = True,
    task_id: str = "sys",
) -> str:
    data = audit_repo(instruction)
    report = format_audit_report(data, instruction)
    if not allow_llm_fix:
        return report
    if dry_run and not (data.get("syntax_errors") or _extract_path_hints(instruction)):
        return report + "\n- 💡 Không có lỗi cú pháp / path trong chỉ thị — bỏ qua LLM patch."

    patches = await propose_repo_patches(instruction, data, task_id=task_id)
    fix_block, _promoted = await apply_repo_patches(patches, dry_run=dry_run, task_id=task_id)
    return report + "\n" + fix_block
