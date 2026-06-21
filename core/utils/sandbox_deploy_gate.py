"""
Sandbox deploy gate — no production write until AST + isolated sandbox pass.

Used by /tucaitien (code) and /tusualoi (JSON/config validation).
"""

from __future__ import annotations

import json
import logging
import os
import re
import shutil
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Tuple

logger = logging.getLogger("jkai.sandbox_gate")


def validate_python_ast(code: str, filename: str = "<sandbox>") -> Tuple[bool, str]:
    try:
        compile(code, filename, "exec")
        return True, "AST OK"
    except SyntaxError as e:
        return False, f"SyntaxError: {e.msg} (line {e.lineno})"


def validate_json_file(path: str | Path) -> Tuple[bool, str]:
    try:
        p = Path(path)
        json.loads(p.read_text(encoding="utf-8"))
        return True, "JSON OK"
    except Exception as e:
        return False, str(e)


async def run_code_deploy_gate(
    code: str,
    script_name: str,
    filesystem_scope: str,
    timeout_sec: float = 10.0,
    task_id: str = "sys",
) -> Dict[str, Any]:
    """
    Full gate: AST compile → policy prover → sandbox subprocess.
    Returns dict with passed=True only if safe to deploy code to production.
    """
    from core.kernel.capability_broker import CapabilityType, capability_broker, sandbox_executor
    from core.utils.engine import engine

    result: Dict[str, Any] = {
        "passed": False,
        "ast_ok": False,
        "sandbox_ok": False,
        "exit_code": -1,
        "stdout": "",
        "stderr": "",
        "summary": "",
    }

    ast_ok, ast_msg = validate_python_ast(code, script_name)
    result["ast_ok"] = ast_ok
    if not ast_ok:
        result["summary"] = f"❌ SANDBOX GATE: AST failed — {ast_msg}"
        return result

    fs_token = capability_broker.issue_token(
        task_id=task_id,
        cap_type=CapabilityType.FILESYSTEM,
        scope=filesystem_scope,
    )
    exec_token = capability_broker.issue_token(
        task_id=task_id,
        cap_type=CapabilityType.EXECUTION,
        scope=filesystem_scope,
    )
    if not capability_broker.verify_privilege(fs_token.token_id, CapabilityType.FILESYSTEM, filesystem_scope):
        result["summary"] = "❌ SANDBOX GATE: filesystem privilege denied"
        return result

    engine.publish_mission_log(
        "SANDBOX",
        f"📦 [DEPLOY-GATE] Chạy thử `{script_name}` trong hộp cát trước khi triển khai thật...",
        task_id,
        task_id,
        stealth=True,
    )

    sb_ok, exit_code, stdout, stderr = await sandbox_executor.execute_isolated_code(
        token_id=exec_token.token_id,
        code_content=code,
        script_name=script_name,
        timeout_sec=timeout_sec,
    )
    result["sandbox_ok"] = bool(sb_ok) and exit_code == 0
    result["exit_code"] = exit_code
    result["stdout"] = (stdout or "")[:1500]
    result["stderr"] = (stderr or "")[:1500]

    if result["sandbox_ok"]:
        result["passed"] = True
        result["summary"] = (
            "✅ **SANDBOX GATE: PASSED** — AST + hộp cát OK. "
            "Đủ điều kiện triển khai thực tế (production write)."
        )
    else:
        result["summary"] = (
            f"❌ **SANDBOX GATE: FAILED** (exit={exit_code}). "
            f"Không được ghi file production.\nStderr: {(stderr or '')[:500]}"
        )
    return result


def format_gate_footer(passed: bool) -> str:
    if passed:
        return (
            "\n---\n🔒 **Chính sách Zenith:** File thử sandbox PASS → mới được copy sang `logic.py` production."
        )
    return (
        "\n---\n🔒 **Chính sách Zenith:** `logic.py` production **không đổi** — sửa file thử và chạy lại sandbox."
    )


from core.utils.skill_selector import normalize_skill_name


def _safe_skill_dir(skill_id: str) -> str:
    normalized = normalize_skill_name(skill_id) or "UNKNOWN"
    return re.sub(r"[^\w\-]", "_", normalized)


def get_evolution_candidate_path(skill_id: str, workspace_root: str) -> Path:
    """Đường dẫn file thử (candidate) — không phải production logic.py."""
    root = Path(workspace_root)
    return (
        root
        / "scratch"
        / "sandbox"
        / "evolution_candidates"
        / _safe_skill_dir(skill_id)
        / "logic_candidate.py"
    )


def write_evolution_candidate(
    skill_id: str,
    workspace_root: str,
    new_code: str,
    production_path: Path,
) -> Path:
    """
    Bước 1: Ghi bản cải tiến vào file thử trong sandbox (production chưa đụng).
    """
    candidate_path = get_evolution_candidate_path(skill_id, workspace_root)
    candidate_path.parent.mkdir(parents=True, exist_ok=True)
    candidate_path.write_text(new_code, encoding="utf-8")
    manifest = {
        "skill_id": skill_id,
        "candidate_file": str(candidate_path),
        "production_file": str(production_path),
        "written_at": datetime.now(timezone.utc).isoformat(),
        "status": "awaiting_sandbox_test",
    }
    (candidate_path.parent / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False),
        encoding="utf-8",
    )
    return candidate_path


async def test_candidate_file(
    candidate_path: Path,
    filesystem_scope: str,
    skills_root: str,
    task_id: str = "sys",
    timeout_sec: float = 10.0,
) -> Dict[str, Any]:
    """
    Bước 2: Chạy sandbox trên **nội dung file thử** (logic_candidate.py).
    """
    if not candidate_path.is_file():
        return {
            "passed": False,
            "summary": f"❌ Không tìm thấy file thử: `{candidate_path}`",
        }
    body = candidate_path.read_text(encoding="utf-8", errors="replace")
    wrapper = (
        f"import sys\n"
        f"sys.path.insert(0, r'{skills_root}')\n"
        f"# --- candidate under test: {candidate_path.name} ---\n"
        f"{body}\n"
    )
    return await run_code_deploy_gate(
        code=wrapper,
        script_name=f"run_{candidate_path.parent.name}_candidate.py",
        filesystem_scope=filesystem_scope,
        timeout_sec=timeout_sec,
        task_id=task_id,
    )


def promote_candidate_to_production(
    candidate_path: Path,
    production_path: Path,
    invalidate_cache: bool = True,
) -> Tuple[bool, str]:
    """
    Bước 3: Chỉ sau sandbox PASS — copy file thử → logic.py production.
    """
    if not candidate_path.is_file():
        return False, f"Thiếu file thử: {candidate_path}"
    production_path = Path(production_path)
    production_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(candidate_path, production_path)
    manifest_path = candidate_path.parent / "manifest.json"
    if manifest_path.is_file():
        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
            data["status"] = "promoted_to_production"
            data["promoted_at"] = datetime.now(timezone.utc).isoformat()
            manifest_path.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding="utf-8",
            )
        except Exception:
            pass
    msg = f"Đã copy `{candidate_path}` → `{production_path}`"
    if invalidate_cache:
        try:
            from core.utils.executor_cache import invalidate_all_executors_sync

            _ok, inv_msg = invalidate_all_executors_sync()
            msg += f"\n🔄 {inv_msg}"
        except Exception as e:
            msg += f"\n⚠️ invalidate_cache: {e}"
    try:
        rel = None
        from core.utils import path_manager

        ws = Path(path_manager.get("WORKSPACE_ROOT") or path_manager.get_root())
        try:
            rel = str(production_path.resolve().relative_to(ws.resolve())).replace("\\", "/")
        except ValueError:
            pass
        if rel and production_path.suffix == ".py":
            from core.utils.post_patch_verify import verify_after_repair

            _v_ok, v_msg = verify_after_repair(
                touched_rel_paths=[rel],
                run_compileall=False,
                run_tests=True,
            )
            msg += f"\n{v_msg}"
    except Exception as ve:
        msg += f"\n⚠️ post-patch verify: {ve}"
    return True, msg
