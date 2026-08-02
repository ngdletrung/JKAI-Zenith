"""
Xác minh sau khi /tusualoi hoặc promote repo/skill — py_compile + compileall + test nhỏ.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path
from typing import List, Optional, Tuple

from core.utils.repo_surgeon import _workspace_root, resolve_repo_path, scan_python_syntax


def _py_compile_file(path: Path) -> Tuple[bool, str]:
    try:
        subprocess.run(
            [sys.executable, "-m", "py_compile", str(path)],
            capture_output=True,
            text=True,
            timeout=30,
            check=True,
        )
        return True, "OK"
    except subprocess.CalledProcessError as e:
        err = (e.stderr or e.stdout or str(e))[:300]
        return False, err
    except Exception as e:
        return False, str(e)[:300]


def _compileall_dirs(workspace: Path, dirs: Tuple[str, ...] = ("services", "core")) -> Tuple[bool, str]:
    parts: List[str] = []
    ok_all = True
    for d in dirs:
        base = workspace / d
        if not base.is_dir():
            parts.append(f"- `{d}/`: không có")
            continue
        try:
            proc = subprocess.run(
                [sys.executable, "-m", "compileall", "-q", str(base)],
                capture_output=True,
                text=True,
                timeout=int(os.getenv("JKAI_COMPILEALL_TIMEOUT", "90")),
            )
            if proc.returncode == 0:
                parts.append(f"- `compileall {d}/`: ✅")
            else:
                ok_all = False
                err = (proc.stderr or proc.stdout or f"exit {proc.returncode}")[:400]
                parts.append(f"- `compileall {d}/`: ❌ {err}")
        except subprocess.TimeoutExpired:
            ok_all = False
            parts.append(f"- `compileall {d}/`: ⏱️ timeout")
        except Exception as e:
            ok_all = False
            parts.append(f"- `compileall {d}/`: ❌ {e}")
    return ok_all, "\n".join(parts)


def _run_quick_pytests(workspace: Path) -> Tuple[bool, str]:
    tests = os.getenv(
        "JKAI_POST_PATCH_TESTS",
        "core/utils/test_repo_surgeon.py,core/utils/test_skill_deck_index.py,core/utils/test_planner_agents.py",
    )
    paths = []
    for part in tests.split(","):
        p = workspace / part.strip().replace("/", os.sep)
        if p.is_file():
            paths.append(str(p))
    if not paths:
        return True, "- pytest: không có file test cấu hình."

    try:
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "-q", "--tb=no", *paths],
            capture_output=True,
            text=True,
            cwd=str(workspace),
            timeout=int(os.getenv("JKAI_POST_PATCH_PYTEST_TIMEOUT", "120")),
        )
        out = (proc.stdout or "")[-500:]
        if proc.returncode == 0:
            return True, f"- pytest ({len(paths)} file): ✅\n  `{out.strip()[:200]}`"
        return False, f"- pytest: ❌ exit {proc.returncode}\n  `{(proc.stderr or out)[:400]}`"
    except FileNotFoundError:
        ok = True
        lines = ["- pytest không cài — chạy file test trực tiếp:"]
        for t in paths:
            try:
                subprocess.run(
                    [sys.executable, t],
                    cwd=str(workspace),
                    timeout=30,
                    check=True,
                    capture_output=True,
                )
                lines.append(f"  • ✅ {os.path.basename(t)}")
            except Exception as e:
                ok = False
                lines.append(f"  • ❌ {os.path.basename(t)}: {e}")
        return ok, "\n".join(lines)
    except subprocess.TimeoutExpired:
        return False, "- pytest: ⏱️ timeout"
    except Exception as e:
        return False, f"- pytest: ❌ {e}"


def verify_after_repair(
    touched_rel_paths: Optional[List[str]] = None,
    run_compileall: bool = True,
    run_tests: bool = True,
    workspace: Optional[Path] = None,
) -> Tuple[bool, str]:
    ws = workspace or _workspace_root()
    lines = ["\n🧪 **XÁC MINH SAU SỬA (POST-REPAIR):**"]
    ok_all = True

    touched = touched_rel_paths or []
    for rel in touched:
        full = resolve_repo_path(rel, ws)
        if full and full.suffix == ".py":
            ok, msg = _py_compile_file(full)
            if not ok:
                ok_all = False
            lines.append(f"- `py_compile {rel}`: {'✅' if ok else '❌'} {msg}")

    scan = scan_python_syntax(ws, max_files=400)
    if scan:
        ok_all = False
        lines.append(f"- Syntax scan: ❌ còn **{len(scan)}** file lỗi (vd `{scan[0]['path']}` L{scan[0]['line']})")
    else:
        lines.append("- Syntax scan (`services/`, `core/`, `scripts/`): ✅")

    if run_compileall:
        c_ok, c_msg = _compileall_dirs(ws)
        if not c_ok:
            ok_all = False
        lines.append(c_msg)

    if run_tests and os.getenv("JKAI_POST_PATCH_TESTS", "").strip() != "off":
        t_ok, t_msg = _run_quick_pytests(ws)
        if not t_ok:
            ok_all = False
        lines.append(t_msg)

    status = "✅ PASS" if ok_all else "⚠️ CÒN LỖI — xem chi tiết trên"
    lines.insert(1, f"- Tổng kết: **{status}**")
    return ok_all, "\n".join(lines)


def format_post_repair_verification(**kwargs) -> str:
    _, text = verify_after_repair(**kwargs)
    return text
