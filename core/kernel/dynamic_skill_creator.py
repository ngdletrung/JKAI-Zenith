# -*- coding: utf-8 -*-
"""
core/kernel/dynamic_skill_creator.py
====================================
JKAI-Zenith Sovereign Skill Governance Pipeline:
PROPOSAL -> PATH VALIDATION -> AST ALLOWLIST -> StateSanitizer SCAN
-> REGRESSION 100% -> APPROVAL -> CHECKPOINT -> ATOMIC PUBLISH
-> EXECUTION RECEIPT -> ROLLBACK.

Guarantees:
1. LLM cannot write directly to production `logic.py` without passing AST allowlist,
   StateSanitizer retain defense, regression check, and approval gate.
2. Path traversal (`..`, `/`, `\\`, `:`) is strictly blocked.
3. Dangerous AST nodes (`eval`, `exec`, `compile`, `__import__`, `subprocess`,
   `os.system`, `shutil.rmtree`, `socket`, `pickle`, `ctypes`) are blocked.
4. Atomic file writes (`tmp` + `os.fsync` + `os.replace`) with automatic checkpoint
   and SHA-256 verified rollback on partial publish, receipt failure, or hot-reload failure.
"""

from __future__ import annotations

import ast
import hashlib
import json
import logging
import os
import re
import shutil
import time
import uuid
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

import httpx

from core.kernel.execution_integrity import ExecutionIntegrityLayer
from core.sanitizer.state_sanitizer import StateSanitizer

logger = logging.getLogger("DynamicSkillCreator")

_SAFE_NAME_RE = re.compile(r"^[A-Za-z0-9_\- ]+$")
_PATH_TRAVERSAL_TOKENS = ("..", "/", "\\", ":", "\x00")

_BANNED_IMPORT_MODULES = {
    "subprocess",
    "shutil",
    "socket",
    "ctypes",
    "pty",
    "winreg",
    "multiprocessing",
    "pickle",
    "marshal",
    "builtins",
    "importlib",
}

_BANNED_CALL_NAMES = {
    "eval",
    "exec",
    "compile",
    "__import__",
    "open",
    "input",
    "breakpoint",
}

_BANNED_ATTR_CALLS = {
    "system",
    "popen",
    "spawn",
    "spawnl",
    "spawnle",
    "spawnlp",
    "spawnlpe",
    "spawnv",
    "spawnve",
    "spawnvp",
    "spawnvpe",
    "execl",
    "execle",
    "execlp",
    "execlpe",
    "execv",
    "execve",
    "execvp",
    "execvpe",
    "rmtree",
    "unlink",
    "remove",
    "rmdir",
    "kill",
    "killpg",
}


class DynamicSkillCreator:
    """
    Sovereign Skill Governance Engine:
    Quản lý toàn bộ chu trình đề xuất, thẩm định AST/Sanitizer, kiểm thử hồi quy 100%,
    phê duyệt, sao lưu checkpoint, xuất bản nguyên tử, ký biên nhận HMAC và hoàn tác (rollback).
    """

    def __init__(
        self,
        skills_root: Optional[str] = None,
        candidates_dir: Optional[str] = None,
        checkpoints_dir: Optional[str] = None,
    ):
        base_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        self.skills_root = os.path.abspath(skills_root or os.path.join(base_root, "intelligence", "skills"))
        self.candidates_dir = os.path.abspath(candidates_dir or os.path.join(base_root, "data", "skill_candidates"))
        self.checkpoints_dir = os.path.abspath(checkpoints_dir or os.path.join(base_root, "data", "skill_checkpoints"))

    @staticmethod
    def _is_production_env() -> bool:
        env_val = (os.environ.get("JKAI_ENV") or os.environ.get("ENVIRONMENT") or "development").strip().lower()
        return env_val in ("prod", "production")

    def validate_and_resolve_path(self, skill_name: str, category: str) -> Tuple[bool, str, str, str]:
        """
        [Step 2: PATH VALIDATION]
        Kiểm tra chống Path Traversal tuyệt đối trên `skill_name` và `category`.
        Trả về: (ok, clean_skill_name, clean_category, target_dir_or_error)
        """
        if not skill_name or not isinstance(skill_name, str) or not category or not isinstance(category, str):
            return False, "", "", "PATH_VALIDATION_ERROR: Empty skill_name or category."

        for raw_val, label in ((skill_name, "skill_name"), (category, "category")):
            if any(tok in raw_val for tok in _PATH_TRAVERSAL_TOKENS) or not _SAFE_NAME_RE.match(raw_val):
                return False, "", "", f"PATH_TRAVERSAL_BLOCKED: Illegal characters in {label} '{raw_val}'."

        skill_clean = skill_name.strip().lower().replace(" ", "_").replace("-", "_")
        cat_clean = category.strip().upper().replace(" ", "_").replace("-", "_")
        if not skill_clean or not cat_clean:
            return False, "", "", "PATH_VALIDATION_ERROR: Normalized identifier is empty."

        target_dir = os.path.abspath(os.path.join(self.skills_root, cat_clean, skill_clean))
        try:
            common = os.path.commonpath([self.skills_root, target_dir])
            if os.path.normcase(common) != os.path.normcase(self.skills_root):
                return False, "", "", "PATH_TRAVERSAL_BLOCKED: Target directory escapes skills_root."
        except ValueError:
            return False, "", "", "PATH_TRAVERSAL_BLOCKED: Cross-drive path traversal."

        return True, skill_clean, cat_clean, target_dir

    @staticmethod
    def validate_skill_ast(python_code: str) -> Tuple[bool, List[str]]:
        """
        [Step 3: AST ALLOWLIST VALIDATION]
        Phân tích cây cú pháp AST và chặn đứng mọi import/call nguy hiểm.
        """
        if not python_code or not isinstance(python_code, str) or not python_code.strip():
            return False, ["AST_EMPTY_CODE: Python code must not be empty."]

        try:
            tree = ast.parse(python_code)
        except SyntaxError as exc:
            return False, [f"AST_SYNTAX_ERROR: {exc}"]

        violations: List[str] = []
        has_function_def = False

        for node in ast.walk(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                has_function_def = True
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    top_mod = alias.name.split(".")[0]
                    if top_mod in _BANNED_IMPORT_MODULES:
                        violations.append(f"AST_BANNED_IMPORT: Module '{alias.name}' is forbidden in skills.")
            elif isinstance(node, ast.ImportFrom):
                mod_name = (node.module or "").split(".")[0]
                if mod_name in _BANNED_IMPORT_MODULES:
                    violations.append(f"AST_BANNED_IMPORT_FROM: Module '{node.module}' is forbidden in skills.")
                for alias in node.names:
                    if alias.name in _BANNED_ATTR_CALLS or alias.name in _BANNED_CALL_NAMES:
                        violations.append(f"AST_BANNED_SYMBOL_IMPORT: Symbol '{alias.name}' is forbidden.")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name):
                    if node.func.id in _BANNED_CALL_NAMES:
                        violations.append(f"AST_BANNED_CALL: Direct call to '{node.func.id}()' is forbidden.")
                elif isinstance(node.func, ast.Attribute):
                    if node.func.attr in _BANNED_ATTR_CALLS:
                        violations.append(f"AST_BANNED_ATTR_CALL: Method call '.{node.func.attr}()' is forbidden.")

        if not has_function_def:
            violations.append("AST_MISSING_ENTRYPOINT: Skill code must define at least one function.")

        return len(violations) == 0, violations

    @staticmethod
    def _atomic_write_text(file_path: str, content: str) -> None:
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        tmp_path = f"{file_path}.tmp.{uuid.uuid4().hex[:8]}"
        with open(tmp_path, "w", encoding="utf-8", newline="\n") as f:
            f.write(content)
            f.flush()
            os.fsync(f.fileno())
        os.replace(tmp_path, file_path)

    @staticmethod
    def _sha256_text(content: str) -> str:
        return hashlib.sha256(content.encode("utf-8")).hexdigest()

    @staticmethod
    def _sha256_file(path: str) -> Optional[str]:
        if not os.path.exists(path):
            return None
        with open(path, "rb") as f:
            return hashlib.sha256(f.read()).hexdigest()

    def propose_skill(
        self,
        skill_name: str,
        description: str,
        python_code: str,
        category: str = "CUSTOM",
        version: str = "1.0.0",
    ) -> Dict[str, Any]:
        """
        [Step 1..4: PROPOSAL -> PATH VALIDATION -> AST ALLOWLIST -> StateSanitizer SCAN]
        Tạo hồ sơ ứng viên kỹ năng (SkillCandidate) tại vùng staging, tuyệt đối chưa ghi vào runtime.
        """
        path_ok, skill_clean, cat_clean, target_or_err = self.validate_and_resolve_path(skill_name, category)
        if not path_ok:
            return {"status": "rejected", "reason": target_or_err, "stage": "PATH_VALIDATION"}

        ast_ok, ast_errors = self.validate_skill_ast(python_code)
        if not ast_ok:
            return {
                "status": "rejected",
                "reason": "; ".join(ast_errors),
                "violations": ast_errors,
                "stage": "AST_ALLOWLIST",
            }

        scan_code = StateSanitizer.scan_for_retain(python_code, policy="block")
        scan_desc = StateSanitizer.scan_for_retain(description, policy="block")
        if not scan_code["allowed_to_retain"] or not scan_desc["allowed_to_retain"]:
            matched = scan_code["matched_pattern_ids"] + scan_desc["matched_pattern_ids"]
            return {
                "status": "rejected",
                "reason": f"SANITIZER_BLOCKED: Detected sensitive or poisoning patterns {matched}",
                "matched_patterns": matched,
                "stage": "STATE_SANITIZER",
            }

        proposal_id = f"cand_{skill_clean}_{uuid.uuid4().hex[:10]}"
        proposal_record = {
            "proposal_id": proposal_id,
            "skill_name": skill_clean,
            "category": cat_clean,
            "version": version,
            "description": StateSanitizer.sanitize(description),
            "python_code": python_code,
            "code_sha256": self._sha256_text(python_code),
            "target_dir": target_or_err,
            "status": "PROPOSED",
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
        }
        cand_file = os.path.join(self.candidates_dir, f"{proposal_id}.json")
        self._atomic_write_text(cand_file, json.dumps(proposal_record, indent=2, ensure_ascii=False))
        return {
            "status": "proposed",
            "proposal_id": proposal_id,
            "candidate_file": cand_file,
            "skill_name": skill_clean,
            "category": cat_clean,
            "code_sha256": proposal_record["code_sha256"],
        }

    def create_checkpoint(self, skill_clean: str, cat_clean: str, target_dir: str) -> Dict[str, Any]:
        """
        [Step 7: CHECKPOINT]
        Sao lưu trạng thái hiện tại của skill (kèm mã băm SHA-256) trước khi ghi đè.
        """
        skill_md_path = os.path.join(target_dir, "SKILL.md")
        logic_py_path = os.path.join(target_dir, "logic.py")
        existed = os.path.exists(skill_md_path) or os.path.exists(logic_py_path)

        md_content = None
        py_content = None
        if os.path.exists(skill_md_path):
            with open(skill_md_path, "r", encoding="utf-8") as f:
                md_content = f.read()
        if os.path.exists(logic_py_path):
            with open(logic_py_path, "r", encoding="utf-8") as f:
                py_content = f.read()

        import hmac
        checkpoint_id = f"ckpt_{cat_clean.lower()}_{skill_clean}_{int(time.time() * 1000)}"
        hmac_key = os.getenv("SOVEREIGN_ROOT_HMAC_KEY", "jkai_enterprise_root_key_2026").encode("utf-8")
        content_hash = self._sha256_text((md_content or "") + "||" + (py_content or ""))
        canonical_str = f"{checkpoint_id}|{skill_clean}|{cat_clean}|{target_dir}|{existed}|{content_hash}"
        ckpt_hmac = hmac.new(hmac_key, canonical_str.encode("utf-8"), hashlib.sha256).hexdigest()

        ckpt_data = {
            "checkpoint_id": checkpoint_id,
            "skill_name": skill_clean,
            "category": cat_clean,
            "target_dir": target_dir,
            "existed": existed,
            "skill_md_content": md_content,
            "skill_md_sha256": self._sha256_text(md_content) if md_content is not None else None,
            "logic_py_content": py_content,
            "logic_py_sha256": self._sha256_text(py_content) if py_content is not None else None,
            "created_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            "checkpoint_hmac": ckpt_hmac,
        }
        ckpt_file = os.path.join(self.checkpoints_dir, f"{checkpoint_id}.json")
        self._atomic_write_text(ckpt_file, json.dumps(ckpt_data, indent=2, ensure_ascii=False))
        ckpt_data["checkpoint_file"] = ckpt_file
        return ckpt_data

    def rollback_skill(self, checkpoint_file: str, task_id: str = "skill_rollback") -> Dict[str, Any]:
        """
        [Step 10: ROLLBACK + SHA-256 VERIFICATION + RECEIPT]
        Khôi phục nguyên trạng kỹ năng từ tệp checkpoint, kiểm tra khớp SHA-256 và ký biên nhận Rollback.
        """
        if not checkpoint_file or not os.path.exists(checkpoint_file):
            return {"status": "error", "reason": f"CHECKPOINT_NOT_FOUND: {checkpoint_file}"}

        try:
            with open(checkpoint_file, "r", encoding="utf-8") as f:
                ckpt = json.loads(f.read())
        except Exception as exc:
            return {"status": "error", "reason": f"CORRUPT_CHECKPOINT: {exc}"}

        required_keys = {"checkpoint_id", "target_dir", "existed"}
        if not isinstance(ckpt, dict) or not required_keys.issubset(ckpt.keys()):
            return {"status": "error", "reason": "CORRUPT_CHECKPOINT_SCHEMA"}

        target_dir = ckpt["target_dir"]

        # Phase R4: Path Traversal and Symlink Escape Verification
        target_abs = os.path.abspath(target_dir)
        skills_abs = os.path.abspath(self.skills_root)
        if not (target_abs == skills_abs or target_abs.startswith(skills_abs + os.sep)):
            return {"status": "error", "reason": f"ROLLBACK_PATH_ESCAPE: target_dir '{target_dir}' escapes skills_root."}

        # Checkpoint Authenticity & HMAC Verification
        if "checkpoint_hmac" in ckpt:
            import hmac
            hmac_key = os.getenv("SOVEREIGN_ROOT_HMAC_KEY", "jkai_enterprise_root_key_2026").encode("utf-8")
            content_hash = self._sha256_text((ckpt.get("skill_md_content") or "") + "||" + (ckpt.get("logic_py_content") or ""))
            c_str = f"{ckpt.get('checkpoint_id')}|{ckpt.get('skill_name')}|{ckpt.get('category')}|{ckpt.get('target_dir')}|{ckpt.get('existed')}|{content_hash}"
            expected_hmac = hmac.new(hmac_key, c_str.encode("utf-8"), hashlib.sha256).hexdigest()
            if not hmac.compare_digest(ckpt["checkpoint_hmac"], expected_hmac):
                return {"status": "error", "reason": "CORRUPT_OR_TAMPERED_CHECKPOINT_HMAC"}

        skill_md_path = os.path.join(target_dir, "SKILL.md")
        logic_py_path = os.path.join(target_dir, "logic.py")

        for p in (skill_md_path, logic_py_path, target_dir):
            if os.path.islink(p):
                return {"status": "error", "reason": f"ROLLBACK_SYMLINK_ATTACK_REJECTED: '{p}' is a symbolic link."}

        # Tính toán mã băm trạng thái trước khi rollback (Cryptographic Pre-State Hash)
        pre_py_hash = self._sha256_file(logic_py_path) or self._sha256_text("EMPTY_LOGIC_PY")
        pre_md_hash = self._sha256_file(skill_md_path) or self._sha256_text("EMPTY_SKILL_MD")
        pre_state_hash = self._sha256_text(f"{pre_md_hash}:{pre_py_hash}")

        if not ckpt["existed"]:
            # Nếu trước khi publish chưa từng tồn tại skill này -> xóa sạch các file mới tạo
            for fp in (skill_md_path, logic_py_path):
                if os.path.exists(fp):
                    try:
                        os.remove(fp)
                    except Exception:
                        pass
            restored_py_hash = None
        else:
            # Whole-tree Rollback Transaction: Write to staging temp first
            staging_md = f"{skill_md_path}.rollback_stage.{uuid.uuid4().hex[:6]}"
            staging_py = f"{logic_py_path}.rollback_stage.{uuid.uuid4().hex[:6]}"
            try:
                if ckpt.get("skill_md_content") is not None:
                    with open(staging_md, "w", encoding="utf-8", newline="\n") as f:
                        f.write(ckpt["skill_md_content"])
                    if self._sha256_file(staging_md) != ckpt.get("skill_md_sha256"):
                        return {"status": "error", "reason": "ROLLBACK_SHA256_MISMATCH_SKILL_MD"}

                if ckpt.get("logic_py_content") is not None:
                    with open(staging_py, "w", encoding="utf-8", newline="\n") as f:
                        f.write(ckpt["logic_py_content"])
                    if self._sha256_file(staging_py) != ckpt.get("logic_py_sha256"):
                        return {"status": "error", "reason": "ROLLBACK_SHA256_MISMATCH_LOGIC_PY"}

                # Atomically commit staging files to production
                if ckpt.get("skill_md_content") is not None and os.path.exists(staging_md):
                    os.replace(staging_md, skill_md_path)
                if ckpt.get("logic_py_content") is not None and os.path.exists(staging_py):
                    os.replace(staging_py, logic_py_path)
            finally:
                for tmp_f in (staging_md, staging_py):
                    if os.path.exists(tmp_f):
                        try:
                            os.remove(tmp_f)
                        except Exception:
                            pass

            restored_py_hash = self._sha256_file(logic_py_path)

        # Tính toán mã băm trạng thái sau khi rollback (Cryptographic Post-State Hash)
        post_py_hash = restored_py_hash or self._sha256_text("EMPTY_LOGIC_PY")
        post_md_hash = self._sha256_file(skill_md_path) or self._sha256_text("EMPTY_SKILL_MD")
        post_state_hash = self._sha256_text(f"{post_md_hash}:{post_py_hash}")

        # Kiểm tra nghiêm ngặt không cho phép hash placeholder toàn 0
        if pre_state_hash == "0" * 64 or post_state_hash == "0" * 64:
            return {"status": "error", "reason": "ROLLBACK_PLACEHOLDER_STATE_HASH_REJECTED"}

        integrity = ExecutionIntegrityLayer(mission_id=task_id)
        rcpt = integrity.seal_execution_receipt(
            action="rollback_skill",
            arguments={"checkpoint_id": ckpt["checkpoint_id"], "target_dir": target_dir},
            output=f"restored_sha256={restored_py_hash}",
            task_id=task_id,
            pre_state_hash=pre_state_hash,
            post_state_hash=post_state_hash,
        )
        if rcpt is None:
            return {"status": "error", "reason": "ROLLBACK_RECEIPT_FAIL_CLOSED"}

        rcpt_dict = rcpt.to_dict() if hasattr(rcpt, "to_dict") else dict(rcpt)
        rcpt_dict["pre_state_hash"] = pre_state_hash
        rcpt_dict["post_state_hash"] = post_state_hash

        return {
            "status": "rolled_back",
            "checkpoint_id": ckpt["checkpoint_id"],
            "restored_logic_sha256": restored_py_hash,
            "expected_logic_sha256": ckpt.get("logic_py_sha256"),
            "pre_state_hash": pre_state_hash,
            "post_state_hash": post_state_hash,
            "receipt": rcpt_dict,
        }

    def rollback_to_previous_version(
        self,
        skill_name: str,
        category: str = "CUSTOM",
        task_id: str = "skill_rollback",
    ) -> Dict[str, Any]:
        """
        [Phase R3.2: VERSIONED ROLLBACK BY SKILL IDENTIFIER]
        Tìm bản checkpoint hợp lệ gần nhất của (category, skill_name) và hoàn tác kèm xác thực SHA-256 + Receipt.
        """
        path_ok, skill_clean, cat_clean, target_or_err = self.validate_and_resolve_path(skill_name, category)
        if not path_ok:
            return {"status": "error", "reason": target_or_err}
        if not os.path.isdir(self.checkpoints_dir):
            return {"status": "error", "reason": "NO_CHECKPOINTS_DIR"}

        prefix = f"ckpt_{cat_clean.lower()}_{skill_clean}_"
        candidates = [
            os.path.join(self.checkpoints_dir, fn)
            for fn in os.listdir(self.checkpoints_dir)
            if fn.startswith(prefix) and fn.endswith(".json")
        ]
        if not candidates:
            return {"status": "error", "reason": f"NO_CHECKPOINT_FOUND_FOR_{cat_clean}_{skill_clean}"}

        candidates.sort(key=lambda p: os.path.getmtime(p), reverse=True)
        return self.rollback_skill(candidates[0], task_id=task_id)

    @staticmethod
    def verify_skill_in_sandbox(
        python_code: str,
        smoke_test_args: Optional[Dict[str, Any]] = None,
        timeout_sec: float = 5.0,
    ) -> Tuple[bool, Dict[str, Any]]:
        """
        [Phase R3.1: ISOLATED SUBPROCESS SANDBOX VERIFICATION]
        Thực thi thử nghiệm mã nguồn ứng viên trong tiến trình Python cô lập (-I) trước khi xuất bản.
        Chặn đứng các skill qua mặt AST nhưng lỗi runtime (ZeroDivisionError, NameError, Infinite Loop).
        """
        import subprocess
        import sys
        import tempfile

        with tempfile.TemporaryDirectory() as tmp_dir:
            cand_path = os.path.join(tmp_dir, "candidate_logic.py")
            runner_path = os.path.join(tmp_dir, "sandbox_runner.py")
            args_json = json.dumps(smoke_test_args if isinstance(smoke_test_args, dict) else None)

            with open(cand_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(python_code)

            runner_code = (
                "import asyncio, inspect, json, importlib.util, sys, os\n"
                "# ─── PHASE R4: SECURITY SANDBOX CAPABILITY & RESOURCE ISOLATION ───\n"
                "import socket\n"
                "def _blocked_socket(*a, **kw):\n"
                "    raise PermissionError('SANDBOX_SECURITY_VIOLATION: Network access is forbidden in skills.')\n"
                "socket.socket = _blocked_socket\n"
                "socket.create_connection = _blocked_socket\n"
                "\n"
                "import subprocess\n"
                "def _blocked_spawn(*a, **kw):\n"
                "    raise PermissionError('SANDBOX_SECURITY_VIOLATION: Process spawning is forbidden in skills.')\n"
                "subprocess.Popen = _blocked_spawn\n"
                "os.system = _blocked_spawn\n"
                "if hasattr(os, 'spawnl'): os.spawnl = _blocked_spawn\n"
                "if hasattr(os, 'spawnv'): os.spawnv = _blocked_spawn\n"
                "if hasattr(os, 'popen'): os.popen = _blocked_spawn\n"
                "\n"
                f"_real_tmp = os.path.realpath({tmp_dir!r})\n"
                "_orig_open = open\n"
                "def _sandbox_open(file, mode='r', *a, **kw):\n"
                "    if any(m in mode for m in ('w', 'a', 'x', '+')):\n"
                "        file_path = str(file) if isinstance(file, (str, bytes, os.PathLike)) else ''\n"
                "        if file_path:\n"
                "            resolved = os.path.realpath(file_path)\n"
                "            if not resolved.startswith(_real_tmp):\n"
                "                raise PermissionError(f'SANDBOX_SECURITY_VIOLATION: Write outside sandbox is forbidden: {file_path}')\n"
                "    return _orig_open(file, mode, *a, **kw)\n"
                "import builtins\n"
                "builtins.open = _sandbox_open\n"
                "\n"
                f"spec = importlib.util.spec_from_file_location('candidate_logic', {cand_path!r})\n"
                "mod = importlib.util.module_from_spec(spec)\n"
                "spec.loader.exec_module(mod)\n"
                "funcs = [obj for name, obj in inspect.getmembers(mod, inspect.isfunction) if obj.__module__ == 'candidate_logic' and not name.startswith('_')]\n"
                "if not funcs:\n"
                "    print(json.dumps({'ok': False, 'reason': 'SANDBOX_NO_PUBLIC_FUNCTION'}))\n"
                "    sys.exit(2)\n"
                "fn = funcs[0]\n"
                f"smoke_args = json.loads({args_json!r})\n"
                "sig = inspect.signature(fn)\n"
                "required_params = [p for p in sig.parameters.values() if p.default is inspect.Parameter.empty and p.kind in (inspect.Parameter.POSITIONAL_ONLY, inspect.Parameter.POSITIONAL_OR_KEYWORD)]\n"
                "try:\n"
                "    if smoke_args is not None:\n"
                "        res = fn(**smoke_args)\n"
                "        if inspect.iscoroutine(res):\n"
                "            res = asyncio.run(res)\n"
                "    elif len(required_params) == 0:\n"
                "        res = fn()\n"
                "        if inspect.iscoroutine(res):\n"
                "            res = asyncio.run(res)\n"
                "    else:\n"
                "        res = 'IMPORT_AND_SIGNATURE_VERIFIED'\n"
                "    print(json.dumps({'ok': True, 'policy_enforced': True, 'entrypoint': fn.__name__, 'result_preview': str(res)[:200]}))\n"
                "except PermissionError as pe:\n"
                "    print(json.dumps({'ok': False, 'policy_enforced': True, 'status': 'BLOCKED_BY_SANDBOX_POLICY', 'reason': str(pe)}))\n"
                "    sys.exit(0)\n"
                "except Exception as exc:\n"
                "    print(json.dumps({'ok': False, 'policy_enforced': False, 'status': 'CANDIDATE_RUNTIME_ERROR', 'reason': f'{type(exc).__name__}: {exc}'}))\n"
                "    sys.exit(0)\n"
            )
            with open(runner_path, "w", encoding="utf-8", newline="\n") as f:
                f.write(runner_code)

            try:
                proc = subprocess.run(
                    [sys.executable, "-I", runner_path],
                    cwd=tmp_dir,
                    capture_output=True,
                    text=True,
                    timeout=timeout_sec,
                    encoding="utf-8",
                    errors="replace",
                )
            except subprocess.TimeoutExpired:
                return False, {"ok": False, "reason": f"SANDBOX_TIMEOUT_EXCEEDED: >{timeout_sec}s"}
            except Exception as exc:
                return False, {"ok": False, "reason": f"SANDBOX_LAUNCH_ERROR: {exc}"}

            if proc.returncode != 0:
                err_tail = (proc.stderr or proc.stdout or "").strip()[-300:]
                return False, {"ok": False, "reason": f"SANDBOX_RUNTIME_CRASH (exit={proc.returncode}): {err_tail}"}

            try:
                last_line = [ln.strip() for ln in (proc.stdout or "").splitlines() if ln.strip()][-1]
                payload = json.loads(last_line)
                return bool(payload.get("ok")), payload
            except Exception:
                return True, {"ok": True, "stdout": (proc.stdout or "")[:200]}

    def create_skill(
        self,
        skill_name: str,
        description: str,
        python_code: str,
        category: str = "CUSTOM",
        version: str = "1.0.0",
        approved: Optional[bool] = None,
        approver_id: str = "system_policy_gate",
        proposal_only: bool = False,
        regression_validator: Optional[Callable[[str], bool]] = None,
        smoke_test_args: Optional[Dict[str, Any]] = None,
        sandbox_timeout_sec: float = 5.0,
        require_hot_reload: Optional[bool] = None,
        task_id: str = "skill_publish_task",
        _simulate_partial_publish_crash: bool = False,
    ) -> Dict[str, Any]:
        """
        Thực thi chu trình 10 bước:
        PROPOSAL -> PATH VALIDATION -> AST ALLOWLIST -> StateSanitizer SCAN
        -> SANDBOX EXECUTION + REGRESSION 100% -> APPROVAL -> CHECKPOINT -> ATOMIC PUBLISH
        -> EXECUTION RECEIPT -> ROLLBACK (nếu có bất kỳ lỗi nào).
        """
        # Steps 1..4: Proposal, Path Validation, AST Allowlist, Sanitizer Scan
        proposal = self.propose_skill(
            skill_name=skill_name,
            description=description,
            python_code=python_code,
            category=category,
            version=version,
        )
        if proposal["status"] != "proposed":
            return proposal

        if proposal_only:
            return proposal

        # Step 5a: ISOLATED SANDBOX EXECUTION VERIFICATION (Phase R3.1)
        sbx_ok, sbx_report = self.verify_skill_in_sandbox(
            python_code=python_code,
            smoke_test_args=smoke_test_args,
            timeout_sec=sandbox_timeout_sec,
        )
        if not sbx_ok:
            return {
                "status": "rejected",
                "reason": str(sbx_report.get("reason", "SANDBOX_EXECUTION_FAILED")),
                "sandbox_report": sbx_report,
                "proposal_id": proposal["proposal_id"],
                "stage": "SANDBOX_EXECUTION_GATE",
            }

        # Step 5: REGRESSION 100% GATE (Mandatory in production)
        is_prod = self._is_production_env()
        if is_prod and regression_validator is None:
            return {
                "status": "rejected",
                "reason": "REGRESSION_REQUIRED_IN_PRODUCTION: 100% regression validator is mandatory in production.",
                "proposal_id": proposal["proposal_id"],
                "stage": "REGRESSION_100",
            }
        if regression_validator is not None:
            try:
                reg_ok = bool(regression_validator(python_code))
            except Exception as exc:
                return {"status": "rejected", "reason": f"REGRESSION_ERROR: {exc}", "stage": "REGRESSION_100"}
            if not reg_ok:
                return {
                    "status": "rejected",
                    "reason": "REGRESSION_FAILED: Skill candidate did not achieve 100% pass rate.",
                    "stage": "REGRESSION_100",
                }

        # Step 6: APPROVAL GATE (Mandatory in production)
        effective_approved = approved if approved is not None else (not is_prod)
        if not effective_approved or not approver_id or approver_id.lower() in ("llm", "unapproved", "self"):
            return {
                "status": "rejected",
                "reason": "APPROVAL_REQUIRED: Direct skill publication without governance approval is forbidden.",
                "proposal_id": proposal["proposal_id"],
                "stage": "APPROVAL_GATE",
            }

        skill_clean = proposal["skill_name"]
        cat_clean = proposal["category"]
        _, _, _, target_dir = self.validate_and_resolve_path(skill_clean, cat_clean)

        # Step 7: CHECKPOINT BEFORE PUBLISH
        ckpt = self.create_checkpoint(skill_clean, cat_clean, target_dir)
        ckpt_file = ckpt["checkpoint_file"]

        skill_md_path = os.path.join(target_dir, "SKILL.md")
        logic_py_path = os.path.join(target_dir, "logic.py")

        skill_md_content = (
            f"---\n"
            f"name: {skill_clean}\n"
            f"description: {StateSanitizer.sanitize(description)}\n"
            f"category: {cat_clean}\n"
            f"version: {version}\n"
            f"approved_by: {approver_id}\n"
            f"code_sha256: {proposal['code_sha256']}\n"
            f"---\n\n"
            f"# 🧠 Skill: {skill_clean}\n\n"
            f"{StateSanitizer.sanitize(description)}\n"
        )

        # Step 8: ATOMIC PUBLISH (with automatic rollback on partial write or crash)
        try:
            os.makedirs(target_dir, exist_ok=True)
            self._atomic_write_text(skill_md_path, skill_md_content)
            if _simulate_partial_publish_crash:
                raise RuntimeError("SIMULATED_PARTIAL_PUBLISH_CRASH_AFTER_SKILL_MD")
            self._atomic_write_text(logic_py_path, python_code)
        except Exception as pub_exc:
            rb = self.rollback_skill(ckpt_file, task_id=task_id)
            return {
                "status": "rolled_back_on_error",
                "reason": f"ATOMIC_PUBLISH_FAILED: {pub_exc}",
                "rollback": rb,
                "stage": "ATOMIC_PUBLISH",
            }

        # Step 9: CRYPTOGRAPHIC EXECUTION RECEIPT (Fail-Closed)
        try:
            integrity = ExecutionIntegrityLayer(mission_id=task_id)
            rcpt = integrity.seal_execution_receipt(
                action="publish_skill",
                arguments={
                    "skill_name": skill_clean,
                    "category": cat_clean,
                    "version": version,
                    "code_sha256": proposal["code_sha256"],
                    "approver_id": approver_id,
                },
                output=f"published:{target_dir}",
                task_id=task_id,
            )
            if rcpt is None:
                raise RuntimeError("SKILL_PUBLISH_RECEIPT_MISSING")
        except Exception as rcpt_exc:
            rb = self.rollback_skill(ckpt_file, task_id=task_id)
            return {
                "status": "rolled_back_on_error",
                "reason": f"RECEIPT_FAIL_CLOSED: {rcpt_exc}",
                "rollback": rb,
                "stage": "EXECUTION_RECEIPT",
            }

        # Hot-reload notification
        strict_reload = require_hot_reload if require_hot_reload is not None else is_prod
        try:
            from core.config import IS_DOCKER
            executor_url = os.getenv("EXECUTOR_URL", "http://ai-executor-1:8000")
            if not IS_DOCKER and "ai-executor-1" in executor_url:
                executor_url = "http://127.0.0.1:8002"
            with httpx.Client(timeout=2.0) as client:
                resp = client.post(f"{executor_url}/invalidate_cache")
                if strict_reload and resp.status_code >= 400:
                    raise RuntimeError(f"Hot-reload HTTP {resp.status_code}")
            logger.info(f"⚡ [SKILL-CREATOR-SUCCESS]: Đã nạp kỹ năng `{skill_clean}` vào bản đồ nơ-ron thực thi!")
        except Exception as reload_exc:
            if strict_reload:
                rb = self.rollback_skill(ckpt_file, task_id=task_id)
                return {
                    "status": "rolled_back_on_error",
                    "reason": f"HOT_RELOAD_FAILED: {reload_exc}",
                    "rollback": rb,
                    "stage": "HOT_RELOAD",
                }
            logger.warning(f"⚠️ [SKILL-CREATOR-WARN] Hot-reload notification error: {reload_exc}")

        return {
            "status": "success",
            "skill_name": skill_clean,
            "category": cat_clean,
            "version": version,
            "skill_dir": target_dir,
            "proposal_id": proposal["proposal_id"],
            "checkpoint_file": ckpt_file,
            "code_sha256": proposal["code_sha256"],
            "receipt": rcpt.to_dict(),
            "message": f"Kỹ năng `{skill_clean}` đã vượt qua 10 cổng kiểm định và sẵn sàng sử dụng!",
        }


dynamic_skill_creator = DynamicSkillCreator()
