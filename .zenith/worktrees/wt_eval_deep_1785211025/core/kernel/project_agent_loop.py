"""
Cursor-style agent loop — phạm vi = bất kỳ thư mục con trong gốc JKAI (workspace).

Đọc → chạy lệnh → (sửa nếu fix mode) → lặp đến khi xong hoặc hết bước.
"""

from __future__ import annotations

import json
import logging
import os
import re
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.utils.engine import engine

logger = logging.getLogger("jkai.project_agent")

TOOLS_AUDIT = ("list_dir", "view_file", "grep_search", "run_command")
TOOLS_FIX = TOOLS_AUDIT + ("replace_file_content", "write_to_file")


def _env_enabled() -> bool:
    return os.getenv("JKAI_CURSOR_AGENT", "true").strip().lower() in ("1", "true", "yes", "on")


def _workspace_abs(scope_rel: str) -> str:
    """relative/to/root → /workspace/relative/to/root"""
    from core.utils.project_workspace import get_jkai_workspace_root

    pr = scope_rel.replace("\\", "/").strip("/")
    ws = get_jkai_workspace_root()
    # Trong container thường mount tại /workspace
    if str(ws).replace("\\", "/").endswith("/workspace") or Path("/workspace").is_dir():
        return f"/workspace/{pr}"
    return str((ws / pr).resolve()).replace("\\", "/")


def _guard_path(scope_rel: str, path: str) -> Optional[str]:
    from core.utils.project_workspace import is_allowed_workspace_rel, normalize_workspace_rel

    base = _workspace_abs(scope_rel)
    if not path or path in (".", "./"):
        return base
    p = path.replace("\\", "/")
    if not p.startswith("/"):
        if p.startswith(scope_rel):
            p = f"/workspace/{normalize_workspace_rel(p)}"
        else:
            p = f"{base}/{p.lstrip('/')}"
    if ".." in p.split("/"):
        return None
    low = p.lower()
    if any(x in low for x in (".env", "sovereign", "credential", "secret")):
        return None
    # Phải nằm trong scope (thư mục Master chọn)
    if not (p == base or p.startswith(base + "/")):
        return None
    rel_under = p[len("/workspace/") :] if p.startswith("/workspace/") else p
    if not is_allowed_workspace_rel(rel_under):
        return None
    return p


class ProjectAgentLoop:
    def __init__(
        self,
        executor_gateway,
        project_root: str,
        mode: str = "audit",
        max_steps: Optional[int] = None,
    ):
        self.gateway = executor_gateway
        self.scope_rel = project_root.replace("\\", "/").strip("/")
        self.project_root = self.scope_rel  # alias
        self.mode = "fix" if mode == "fix" else "audit"
        self.max_steps = max_steps or (18 if self.mode == "fix" else 10)
        self.base = _workspace_abs(self.scope_rel)
        self.touched_files: List[str] = []

    def _log(self, msg: str, task_id: str) -> None:
        engine.publish_mission_log("CURSOR-AGENT", msg, task_id)

    async def _tool(self, name: str, params: dict, task_id: str, trace_id: str) -> str:
        from receptionist.executor_gateway import ExecutionRequest

        if name not in (TOOLS_FIX if self.mode == "fix" else TOOLS_AUDIT):
            return f"Tool `{name}` không được phép ở chế độ {self.mode}."

        params = dict(params or {})
        safe_path: Optional[str] = None
        old_text = ""
        if "path" in params:
            safe_path = _guard_path(self.scope_rel, str(params["path"]))
            if not safe_path:
                return f"⛔ Path ngoài project: {params['path']}"
            params["path"] = safe_path
            if name in ("replace_file_content", "write_to_file"):
                from core.utils.file_diff_bridge import read_text_if_exists

                old_text = read_text_if_exists(safe_path)
        if name == "run_command":
            cmd = str(params.get("command", ""))
            if self.base not in cmd:
                params["command"] = f"cd {self.base} && {cmd}"
        elif name in ("replace_file_content", "write_to_file") and params.get("path"):
            rel = params["path"].replace(self.base, "").lstrip("/")
            rel_key = f"{self.scope_rel}/{rel}".replace("//", "/")
            if rel_key not in self.touched_files:
                self.touched_files.append(rel_key)

        req = ExecutionRequest(
            trace_id=trace_id,
            capability_token={},
            tool_name=name,
            tool_args={**params, "task_id": task_id},
        )
        out = await self.gateway.execute_tool(req, task_id)
        out_str = str(out)[:12000]
        if safe_path and name in ("replace_file_content", "write_to_file"):
            low = out_str.lower()
            if "success" in low or "thành công" in low or "phẫu thuật thành công" in low:
                from core.utils.file_diff_bridge import emit_file_edit, read_text_if_exists

                new_text = read_text_if_exists(safe_path)
                rel = safe_path.replace("\\", "/")
                if rel.startswith("/workspace/"):
                    rel = rel[len("/workspace/") :]
                emit_file_edit(rel, old_text, new_text, task_id=task_id, open_tab=True)
        return out_str

    def _system_prompt(self, goal: str) -> str:
        tools = ", ".join(TOOLS_FIX if self.mode == "fix" else TOOLS_AUDIT)
        fix_line = (
            "Được SỬA file (replace_file_content / write_to_file) trong project đến khi chạy OK."
            if self.mode == "fix"
            else "KHÔNG sửa file — chỉ báo lỗi. Nếu cần sửa Master sẽ nói 'sửa'."
        )
        return (
            f"# JKAI CURSOR AGENT — workspace `{self.scope_rel}`\n"
            f"Thư mục gốc tác vụ: `{self.base}`\n"
            f"Mục tiêu Master: {goal}\n\n"
            f"## Quy tắc\n"
            f"1. {fix_line}\n"
            f"2. Mỗi bước trả về ĐÚNG một JSON (không markdown):\n"
            '{{"thought":"...","tool":"tên_tool hoặc null","params":{{}},"final_answer":null}}\n'
            f"3. Tools: {tools}\n"
            f"4. Luồng: list_dir → view_file / grep_search → run_command (python, pytest…) → "
            f"{'sửa → chạy lại' if self.mode == 'fix' else 'báo lỗi chi tiết'}.\n"
            f"5. Khi xong, đặt final_answer (tiếng Việt, có file/dòng/lệnh đã chạy); tool=null.\n"
            f"6. Chỉ thao tác TRONG `{self.base}` — không ra ngoài gốc JKAI.\n"
        )

    @staticmethod
    def _parse_step(raw: Any) -> Dict[str, Any]:
        if isinstance(raw, dict):
            return raw
        text = str(raw or "")
        m = re.search(r"\{[\s\S]*\}", text)
        if m:
            try:
                return json.loads(m.group())
            except json.JSONDecodeError:
                pass
        return {"thought": text, "tool": None, "final_answer": text if "FINAL" in text.upper() else None}

    async def run(self, goal: str, task_id: str, trace_id: str = "sys") -> str:
        if not _env_enabled():
            return "JKAI_CURSOR_AGENT=tắt — dùng pipeline DEEP thường."

        try:
            from core.utils.project_workspace import goal_forces_web_analysis_pipeline

            if goal_forces_web_analysis_pipeline(goal):
                return (
                    "Yêu cầu phân tích URL GitHub/GitLab — dùng pipeline web "
                    "(SEARCH_WEB_GLOBAL), không Cursor Agent workspace."
                )
        except Exception:
            pass

        self._log(f"🎯 Cursor Agent — `{self.scope_rel}` ({self.mode})", task_id)
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self._system_prompt(goal)},
            {"role": "user", "content": "Bắt đầu: list_dir thư mục project rồi tiếp tục."},
        ]

        last_obs = ""
        for step in range(1, self.max_steps + 1):
            self._log(f"Bước {step}/{self.max_steps}", task_id)
            try:
                raw = await engine.call_chat(
                    messages=messages,
                    role="EXECUTOR",
                    task_id=task_id,
                    json_mode=True,
                    lock_timeout=120,
                    timeout=120,
                )
            except Exception as e:
                return f"❌ Agent loop LLM: {e}\nQuan sát cuối: {last_obs[:1500]}"

            data = self._parse_step(raw)
            thought = data.get("thought") or ""
            final = data.get("final_answer")
            tool = data.get("tool")
            params = data.get("params") or {}

            if final:
                self._log("✅ Hoàn tất", task_id)
                return self._finalize(str(final), task_id)

            if not tool:
                if thought and len(thought) > 80:
                    return self._finalize(thought, task_id)
                messages.append(
                    {"role": "user", "content": "Chọn tool hoặc trả final_answer JSON."}
                )
                continue

            messages.append({"role": "assistant", "content": json.dumps(data, ensure_ascii=False)})
            obs = await self._tool(str(tool), params, task_id, trace_id)
            last_obs = obs
            if "Neural Circuit Breaker" in obs or "repeating excessively" in obs:
                return self._finalize(
                    "Agent dừng vì lặp tool `list_dir` (thư mục workspace không hợp lệ hoặc trống).\n"
                    "Nếu Master phân tích link GitHub: gửi lại mission sau `docker restart ai-brain` "
                    "(pipeline WEB, không Cursor Agent).\n\n"
                    + obs,
                    task_id,
                )
            messages.append({"role": "user", "content": f"[OBSERVATION]\n{obs}"})

            if self.mode == "fix" and tool == "run_command":
                low = obs.lower()
                if "exit 0" in low or "passed" in low or "ok" in low[:200]:
                    if "error" not in low[:300] and "fail" not in low[:300]:
                        messages.append(
                            {
                                "role": "user",
                                "content": "Lệnh có vẻ PASS — trả final_answer tóm tắt.",
                            }
                        )

        return self._finalize(
            f"Đạt giới hạn {self.max_steps} bước. Xem log mission.\n{last_obs[:2000]}",
            task_id,
        )

    def _finalize(self, answer: str, task_id: str) -> str:
        try:
            summary = (answer or "").strip()
            if summary:
                engine.publish_mission_log("JKAI", summary[:12000], task_id)
                engine.publish_mission_log(
                    "MISSION_RESULT",
                    summary[:400] if len(summary) > 400 else summary,
                    task_id,
                )
        except Exception as pub_err:
            logger.warning("[CURSOR-AGENT] publish result: %s", pub_err)

        if self.mode == "fix" and self.touched_files:
            try:
                from core.utils.post_patch_verify import verify_after_repair
                from core.utils.executor_cache import invalidate_all_executors_sync

                _ok, vmsg = verify_after_repair(
                    touched_rel_paths=self.touched_files,
                    run_compileall=False,
                    run_tests=True,
                )
                invalidate_all_executors_sync()
                answer += f"\n\n{vmsg}"
            except Exception as e:
                answer += f"\n\n⚠️ Verify: {e}"
        return answer
