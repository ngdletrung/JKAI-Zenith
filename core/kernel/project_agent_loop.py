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
from core.kernel.action_validator import validate_action, ActionDecision
from core.kernel.model_output_parser import ModelOutputParser
from core.kernel.context_manager import context_manager
from core.kernel.durable_checkpoint import get_checkpoint_engine, StateEnvelope

logger = logging.getLogger("jkai.project_agent")

TOOLS_AUDIT = ("list_dir", "view_file", "grep_search", "run_command", "verify_file", "browser_action")
TOOLS_FIX = TOOLS_AUDIT + ("replace_file_content", "write_to_file", "delete_file")


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
    from core.utils.project_workspace import is_allowed_workspace_rel, normalize_workspace_rel, get_jkai_workspace_root

    base = _workspace_abs(scope_rel)
    if not path or path in (".", "./"):
        return base
    p = str(path).replace("\\", "/").strip()

    ws_root = str(get_jkai_workspace_root()).replace("\\", "/").rstrip("/")
    if p.startswith("/workspace"):
        if not Path("/workspace").is_dir():
            rel = p[len("/workspace"):].lstrip("/")
            p = f"{ws_root}/{rel}" if rel else ws_root

    is_abs = p.startswith("/") or (len(p) >= 2 and p[1] == ":" and p[0].isalpha())
    if not is_abs:
        if p.startswith(scope_rel.strip("/")):
            p = f"{ws_root}/{normalize_workspace_rel(p)}"
        else:
            p = f"{base}/" + p.lstrip("/")
    
    norm_p = os.path.normpath(p).replace("\\", "/")
    norm_base = os.path.normpath(base).replace("\\", "/")

    if ".." in norm_p.split("/"):
        return None
    low = norm_p.lower()
    if any(x in low for x in (".env", "sovereign", "credential", "secret")):
        return None
    # Phải nằm trong scope (thư mục Master chọn)
    if not (norm_p.lower() == norm_base.lower() or norm_p.lower().startswith(norm_base.lower() + "/")):
        return None
    
    ws_root_norm = os.path.normpath(str(get_jkai_workspace_root())).replace("\\", "/").lower()
    rel_under = norm_p[len(ws_root_norm) :].lstrip("/") if norm_p.lower().startswith(ws_root_norm) else norm_p
    if not is_allowed_workspace_rel(rel_under):
        return None
    return norm_p


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
        try:
            from receptionist.executor_gateway import ExecutionRequest
        except ImportError:
            import sys
            ai_brain_dir = str(Path(__file__).resolve().parent.parent.parent / "services" / "ai-brain")
            if ai_brain_dir not in sys.path:
                sys.path.insert(0, ai_brain_dir)
            from receptionist.executor_gateway import ExecutionRequest

        if name not in (TOOLS_FIX if self.mode == "fix" else TOOLS_AUDIT):
            return f"Tool `{name}` không được phép ở chế độ {self.mode}."

        params = dict(params or {})
        safe_path: Optional[str] = None
        old_text = ""

        # Normalize target path across all tool variants
        path_val = (
            params.get("path")
            or params.get("AbsolutePath")
            or params.get("TargetFile")
            or params.get("target_path")
            or params.get("file_path")
        )

        if name in ("view_file", "write_to_file", "replace_file_content", "verify_file", "delete_file"):
            if not path_val:
                return f"Tool `{name}` yêu cầu tham số đường dẫn tệp (path/TargetFile)."
            safe_path = _guard_path(self.scope_rel, str(path_val))
            if not safe_path:
                return f"⛔ Path ngoài project: {path_val}"
            params["path"] = safe_path
            params["AbsolutePath"] = safe_path
            params["TargetFile"] = safe_path
            params["target_path"] = safe_path
            params["file_path"] = safe_path

            if name == "view_file":
                self._last_viewed_path = safe_path
            if name in ("replace_file_content", "write_to_file"):
                from core.utils.file_diff_bridge import read_text_if_exists

                old_text = read_text_if_exists(safe_path)

        elif name == "list_dir":
            dir_val = params.get("path") or params.get("DirectoryPath") or params.get("dir") or "."
            if dir_val in (".", "./", ""):
                safe_dir = self.base
            else:
                safe_dir = _guard_path(self.scope_rel, str(dir_val))
                if not safe_dir:
                    return f"⛔ Path ngoài project: {dir_val}"
            params["path"] = safe_dir
            params["DirectoryPath"] = safe_dir

        elif name == "grep_search":
            q = params.get("query") or params.get("Query") or params.get("pattern") or ""
            search_path = params.get("path") or params.get("SearchPath") or "."
            if search_path in (".", "./", ""):
                safe_search = self.base
            else:
                safe_search = _guard_path(self.scope_rel, str(search_path)) or self.base
            params["query"] = q
            params["Query"] = q
            params["path"] = safe_search
            params["SearchPath"] = safe_search

        elif name == "run_command":
            cmd = str(params.get("command") or params.get("CommandLine") or params.get("cmd") or "").strip()
            # If model generated cd <dir> && <cmd>, peel it off and set cwd
            m_cd = re.match(r"^cd\s+(?:/d\s+)?([^\&]+)\s*&&\s*(.+)$", cmd, re.IGNORECASE)
            if m_cd:
                cd_target = m_cd.group(1).strip().strip("'\"")
                cmd_rest = m_cd.group(2).strip()
                safe_cd = _guard_path(self.scope_rel, cd_target) or self.base
                params["cwd"] = safe_cd
                params["Cwd"] = safe_cd
                params["command"] = cmd_rest
                params["CommandLine"] = cmd_rest
            else:
                params.setdefault("cwd", self.base)
                params.setdefault("Cwd", self.base)
                params["command"] = cmd
                params["CommandLine"] = cmd

        if name == "replace_file_content":
            tgt = (
                params.get("TargetContent")
                or params.get("target")
                or params.get("old_str")
                or params.get("old_code")
                or params.get("find")
                or ""
            )
            repl = (
                params.get("ReplacementContent")
                or params.get("replacement")
                or params.get("new_str")
                or params.get("new_code")
                or params.get("replace")
                or ""
            )
            params["TargetContent"] = tgt
            params["target"] = tgt
            params["ReplacementContent"] = repl
            params["replacement"] = repl

        elif name == "write_to_file":
            cnt = (
                params.get("CodeContent")
                or params.get("content")
                or params.get("code")
                or params.get("text")
                or ""
            )
            params["CodeContent"] = cnt
            params["content"] = cnt
            params["target_content"] = cnt
            params.setdefault("overwrite", True)
            params.setdefault("Overwrite", True)

        elif name == "delete_file":
            params.setdefault("confirm", True)

        if name in ("replace_file_content", "write_to_file") and safe_path:
            rel = safe_path.replace(self.base, "").lstrip("/")
            rel_key = f"{self.scope_rel}/{rel}".replace("//", "/")
            if rel_key not in self.touched_files:
                self.touched_files.append(rel_key)

        from core.kernel.task_contract_store import get_or_create_default_contract, get_or_create_policy_snapshot
        get_or_create_default_contract(task_id)
        get_or_create_policy_snapshot(task_id)

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

                # Tự động kiểm chứng cú pháp Python nếu file bị sửa đổi kết thúc bằng .py
                if safe_path.endswith(".py"):
                    import subprocess
                    import sys
                    try:
                        res = subprocess.run(
                            [sys.executable, "-m", "py_compile", safe_path],
                            capture_output=True,
                            text=True,
                            timeout=5
                        )
                        if res.returncode != 0:
                            compile_err = res.stderr.strip() or res.stdout.strip()
                            out_str += (
                                f"\n\n🚨 [COMPILE-WARNING]: Tệp tin python vừa lưu bị lỗi cú pháp và không thể biên dịch thành công!\n"
                                f"Chi tiết lỗi:\n{compile_err}\n"
                                f"Vui lòng sử dụng lại tool để sửa lỗi cú pháp này trước khi thực hiện bước tiếp theo."
                            )
                    except Exception as compile_ex:
                        logger.warning("Failed to auto compile-check: %s", compile_ex)
        return out_str

    def _system_prompt(self, goal: str) -> str:
        tools = ", ".join(TOOLS_FIX if self.mode == "fix" else TOOLS_AUDIT)
        fix_line = (
            "Được SỬA file (replace_file_content / write_to_file) trong project đến khi chạy OK."
            if self.mode == "fix"
            else "KHÔNG sửa file — chỉ báo lỗi. Nếu cần sửa Master sẽ nói 'sửa'."
        )
        flow_line = (
            "Luồng chuẩn: list_dir/view_file → write_to_file/replace_file_content → view_file (kiểm tra lại) → final_answer."
            if self.mode == "fix"
            else "Luồng chuẩn chế độ audit: list_dir/view_file/grep_search/run_command → phân tích kỹ lưỡng nội dung → final_answer (tuyệt đối KHÔNG sửa file)."
        )
        return (
            f"# JKAI CURSOR AGENT — workspace `{self.scope_rel}`\n"
            f"Thư mục gốc tác vụ: `{self.base}`\n"
            f"Mục tiêu Master: {goal}\n\n"
            f"## Quy tắc\n"
            f"1. {fix_line}\n"
            f"2. Mỗi bước trả về ĐÚNG một JSON (không markdown):\n"
            '{{"thought":"...","tool":"tên_tool hoặc null","params":{{}},"final_answer":null}}\n'
            f"3. Tools và tham số:\n"
            f"   - write_to_file: {{\"path\": \"tên_file\", \"content\": \"nội dung văn bản\"}}\n"
            f"   - view_file: {{\"path\": \"tên_file\"}}\n"
            f"   - list_dir: {{\"path\": \".\"}}\n"
            f"   - grep_search: {{\"query\": \"từ khóa\", \"path\": \".\"}}\n"
            f"   - run_command: {{\"command\": \"lệnh\"}}\n"
            f"   - replace_file_content: {{\"path\": \"tên_file\", \"TargetContent\": \"đoạn cũ\", \"ReplacementContent\": \"đoạn mới\"}}\n"
            f"   - verify_file: {{\"path\": \"tên_file\"}}\n"
            f"4. {flow_line}\n"
            f"5. Chỉ trả về final_answer khi đã hoàn thành trọn vẹn mục tiêu bằng các công cụ trên.\n"
            f"6. Chỉ thao tác TRONG `{self.base}` — không ra ngoài gốc JKAI.\n"
            f"7. Cơ Chế Tư Duy Sâu Như Gemini (Gemini-Style Structured Reasoning):\n"
            f"   Trong trường 'thought', bắt buộc tư duy khúc chiết theo 4 lớp:\n"
            f"   • [OBSERVE]: Đã thấy gì từ file thực tế? Dòng nào có vấn đề?\n"
            f"   • [ANALYSIS]: Nguyên nhân gốc rễ là gì? Rủi ro tiềm ẩn là gì?\n"
            f"   • [PLAN]: Cần dùng công cụ nào để tác động chính xác?\n"
            f"   • [VERIFY]: Kiểm chứng bằng lệnh nào để chắc chắn không gãy logic?\n"
            f"8. Kỷ Luật Phẫu Thuật Code Như Antigravity (Precision Agentic Surgery):\n"
            f"   • Ưu tiên dùng `replace_file_content` sửa đúng khối code tối thiểu, giữ nguyên mọi hàm và cấu trúc xung quanh.\n"
            f"   • Tuyệt đối KHÔNG viết mã giả, code nháp hoặc placeholder ('// TODO', '...').\n"
            f"   • Sau khi sửa code .py, LUÔN dùng `run_command` chạy test hoặc `view_file` kiểm tra lại trước khi hoàn tất.\n"
        )

    @staticmethod
    def _parse_step(raw: Any) -> Dict[str, Any]:
        return ModelOutputParser.parse(raw)

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
        checkpoint_engine = get_checkpoint_engine()
        start_step = 1
        latest_cp = checkpoint_engine.load_latest_checkpoint(task_id)
        if latest_cp and latest_cp.status == "COMPLETED" and latest_cp.state.messages:
            messages = latest_cp.state.messages
            start_step = latest_cp.step_id + 1
            self._log(f"🔄 [DURABLE-RECOVERY] Phục hồi từ Checkpoint Step {latest_cp.step_id} (bỏ qua các bước đã hoàn tất).", task_id)
        else:
            messages: List[Dict[str, str]] = [
                {"role": "system", "content": self._system_prompt(goal)},
                {"role": "user", "content": "Bắt đầu: Hãy gọi ngay công cụ list_dir với tham số path='.' để quét thư mục gốc của dự án rồi tiếp tục."},
            ]

        last_obs = ""
        for step in range(start_step, self.max_steps + 1):
            self._log(f"Bước {step}/{self.max_steps}", task_id)
            # C2: Cắt tỉa ngữ cảnh bảo vệ 85% budget token trước khi gọi LLM
            messages = context_manager.prune_messages(messages, session_id=task_id)
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
                # Giao thức TDD Kiểm chứng trước khi bàn giao:
                # CHỈ kích hoạt khi có tệp mã nguồn Python (.py) bị thay đổi
                has_py = any(f.endswith(".py") for f in self.touched_files)
                if self.mode == "fix" and has_py:
                    self._log("🔬 Đang chạy kiểm thử tự động để xác minh chất lượng code Python...", task_id)
                    try:
                        from core.utils.post_patch_verify import verify_after_repair
                        from core.utils.executor_cache import invalidate_all_executors_sync

                        ok, vmsg = verify_after_repair(
                            touched_rel_paths=self.touched_files,
                            run_compileall=False,
                            run_tests=False,
                        )
                        invalidate_all_executors_sync()
                        if not ok:
                            self._log("❌ Kiểm thử thất bại! Trả lỗi lại cho đặc vụ tự sửa.", task_id)
                            messages.append({"role": "assistant", "content": json.dumps(data, ensure_ascii=False)})
                            messages.append({
                                "role": "user", 
                                "content": f"[OBSERVATION]\n🚨 Lỗi kiểm thử xác minh (Verification Test Failed):\n{vmsg}\n\nMã nguồn bạn vừa viết không vượt qua được bài kiểm tra cú pháp. Hãy tự sửa lại lỗi logic hoặc lỗi test này trước khi nộp bài."
                            })
                            continue
                    except Exception as verify_err:
                        self._log(f"⚠️ Kiểm thử xác minh lỗi hệ thống: {verify_err}", task_id)

                self._log("✅ Hoàn tất", task_id)
                return self._finalize(str(final), task_id)

            if not tool:
                messages.append({"role": "assistant", "content": json.dumps(data, ensure_ascii=False)})
                messages.append(
                    {"role": "user", "content": "Bạn vừa trình bày suy nghĩ nhưng chưa chọn tool để thực hiện. Hãy phát hành JSON với trường 'tool' hợp lệ (ví dụ: write_to_file, view_file, run_command...) và 'params' tương ứng để tiếp tục thực hiện mục tiêu."}
                )
                continue

            # [P1-1]: Action Validator — chặn unknown/malformed tại boundary trước khi dispatch
            known_tools = set(TOOLS_FIX if self.mode == "fix" else TOOLS_AUDIT)
            verdict = validate_action(tool, params, known_tools=known_tools)
            if verdict.decision in (ActionDecision.UNKNOWN_TOOL, ActionDecision.SCHEMA_INVALID):
                self._log(f"🚧 [ACTION-VALIDATOR] {verdict.tool}: {verdict.reason}", task_id)
                messages.append({"role": "assistant", "content": json.dumps(data, ensure_ascii=False)})
                messages.append({
                    "role": "user",
                    "content": f"[OBSERVATION]\n🚧 Action không hợp lệ: {verdict.reason}\n"
                               f"Các tool hợp lệ: {', '.join(sorted(known_tools))}\n"
                               "Hãy phát hành lại JSON với tool hợp lệ và params đúng dạng object.",
                })
                continue
            tool = verdict.normalized_tool or str(tool)

            # [DURABLE-CHECKPOINT] B2 & B3: Save PENDING before tool execution
            ik = checkpoint_engine.compute_idempotency_key(task_id, step, str(tool), params)
            if checkpoint_engine.is_step_completed(ik):
                self._log(f"⏭️ [IDEMPOTENT-SKIP] Bỏ qua tool call trùng lặp: {tool}", task_id)
                continue

            envelope = StateEnvelope(
                messages=messages,
                next_step_id=step + 1,
                metadata={"tool": str(tool)}
            )
            checkpoint_engine.save_checkpoint(task_id, step, "PENDING", envelope, ik)

            messages.append({"role": "assistant", "content": json.dumps(data, ensure_ascii=False)})
            obs = await self._tool(str(tool), params, task_id, trace_id)
            last_obs = obs

            # [P2-1]: Progress Budget — phát hiện lặp cùng action / không tiến triển
            try:
                from core.kernel.progress_budget import ProgressBudget, ProgressSignal
                if getattr(self, "_budget", None) is None:
                    self._budget = ProgressBudget(max_steps=self.max_steps)
                low_obs = obs.lower()
                outcome_ok = "success" in low_obs or "thành công" in low_obs or "exit 0" in low_obs
                p_signal = self._budget.register_action(str(tool), params, outcome_ok=outcome_ok)
                if p_signal in (ProgressSignal.LOOP_DETECTED, ProgressSignal.NO_PROGRESS):
                    self._log(f"🚧 [PROGRESS-BUDGET] {p_signal.value}: '{tool}' lặp/không tiến triển. Đổi chiến lược.", task_id)
                    messages.append({
                        "role": "user",
                        "content": "[OBSERVATION]\n🚧 Agent đang lặp lại cùng hành động hoặc không tiến triển "
                                   "(LOOP_DETECTED/NO_PROGRESS). Hãy ĐỔI chiến lược: đọc file khác, đổi từ khóa grep, "
                                   "hoặc chạy lệnh kiểm tra khác. Không retry cùng tham số.",
                    })
            except Exception:
                pass

            if "Neural Circuit Breaker" in obs or "repeating excessively" in obs:
                return self._finalize(
                    "Agent dừng vì lặp tool `list_dir` (thư mục workspace không hợp lệ hoặc trống).\n"
                    "Nếu Master phân tích link GitHub: gửi lại mission sau `docker restart ai-brain` "
                    "(pipeline WEB, không Cursor Agent).\n\n"
                    + obs,
                    task_id,
                )
            messages.append({"role": "user", "content": f"[OBSERVATION]\n{obs}"})

            # [DURABLE-CHECKPOINT] Save COMPLETED after tool execution and message update
            envelope.messages = messages
            envelope.next_step_id = step + 1
            checkpoint_engine.save_checkpoint(task_id, step, "COMPLETED", envelope, ik)

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
            elif tool == "view_file":
                if self.mode == "audit":
                    audit_extra = ""
                    try:
                        last_p = getattr(self, "_last_viewed_path", None)
                        if last_p and last_p.endswith(".py"):
                            from core.utils.ast_code_auditor import format_audit_report
                            report = format_audit_report(last_p)
                            if report:
                                audit_extra = f"\n\n{report}"
                    except Exception as audit_ex:
                        logger.warning("Audit extra failed: %s", audit_ex)

                    messages.append(
                        {
                            "role": "user",
                            "content": (
                                f"Bạn đã đọc xong nội dung tệp. Vì đang ở chế độ kiểm tra (audit, tuyệt đối KHÔNG sửa file), "
                                f"dưới đây là kết quả rà soát chi tiết của hệ thống:\n{audit_extra}\n\n"
                                f"Hãy phát hành JSON kết thúc trình bày đầy đủ 8 lỗi theo số thứ tự 1 đến 8 (kèm số dòng và lý do):\n"
                                f'{{\"thought\": \"Tổng hợp 8 lỗi từ kết quả rà soát...\", \"tool\": null, \"params\": {{}}, \"final_answer\": \"1. Dòng ...\\n2. Dòng ...\\n...\"}}\n'
                                f"LƯU Ý: Không dùng dấu ngoặc kép đôi bên trong chuỗi 'final_answer' để tránh lỗi cú pháp JSON."
                            ),
                        }
                    )
                elif self.touched_files and not any(k in goal.lower() for k in ("chạy", "test", "run", "sửa", "fix", "thay")):
                    messages.append(
                        {
                            "role": "user",
                            "content": "Bạn đã đọc xong nội dung tệp xác nhận. Hãy phát hành JSON kết thúc: {\"thought\": \"...\", \"tool\": null, \"params\": {}, \"final_answer\": \"câu trả lời cụ thể cho Master\"}.",
                        }
                    )

        return self._finalize(
            f"Đạt giới hạn {self.max_steps} bước. Xem log mission.\n{last_obs[:2000]}",
            task_id,
        )

    def _finalize(self, answer: str, task_id: str) -> str:
        # Caller ở tầng trên (task_manager / pipeline) sẽ chịu trách nhiệm publish câu trả lời JKAI chính thức duy nhất.
        has_py = any(f.endswith(".py") for f in self.touched_files)
        if self.mode == "fix" and has_py:
            try:
                from core.utils.post_patch_verify import verify_after_repair
                from core.utils.executor_cache import invalidate_all_executors_sync

                _ok, vmsg = verify_after_repair(
                    touched_rel_paths=self.touched_files,
                    run_compileall=False,
                    run_tests=False,
                )
                invalidate_all_executors_sync()
                if not _ok:
                    answer += f"\n\n{vmsg}"
            except Exception as e:
                answer += f"\n\n⚠️ Verify: {e}"
        return answer
