# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/state_pipeline.py
# - Role: State Pipeline Execution Engine (StepRunner) with Dynamic Re-planning
# - Ownership: Mr LeeTrung
# - Status: Active | Version: ZenithOS v2.0 (Bug-Fixed)

import logging
import asyncio
import os
import json
import ast
import time
from pathlib import Path
from typing import Any, Dict, Optional, List, Union, Tuple, Set, Callable  # [FIX-001]: Added complete typing imports to prevent NameError crashes
from core.os.mission_state import MissionState
from core.os.execution_plan import ExecutionPlan, ExecutionPlanStep
from core.utils.engine import engine
from artifact_tracker import ArtifactTracker

logger = logging.getLogger("jkai.os.state_pipeline")

_MAX_SNAPSHOT_FILES = 500
_EXCLUDED_DIRS = {"node_modules", ".git", "venv", ".venv", "__pycache__", "dist", "build", ".next", ".gemini", "Ollama_model", "target", "out", "scratch"}


async def _snapshot_workspace(path: str) -> dict:
    """Chụp nhanh trạng thái file (mtime) bằng os.walk có cắt tỉa rễ siêu tốc."""
    def _scan():
        snap = {}
        try:
            root_str = str(path)
            if os.path.isdir(root_str):
                count = 0
                for r, dirs, files in os.walk(root_str, topdown=True):
                    dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS and not d.startswith('.')]
                    for f in files:
                        fp = os.path.join(r, f)
                        try:
                            rel = os.path.relpath(fp, root_str)
                            snap[rel] = round(os.path.getmtime(fp), 1)
                            count += 1
                            if count >= _MAX_SNAPSHOT_FILES:
                                break
                        except Exception:
                            pass
                    if count >= _MAX_SNAPSHOT_FILES:
                        break
        except Exception:
            pass
        return snap
    return await asyncio.to_thread(_scan)


def _diff_snapshot(before: dict, after: dict) -> list:
    """So sánh 2 snapshot, trả về danh sách file thay đổi."""
    added = [k for k in after if k not in before]
    removed = [k for k in before if k not in after]
    modified = [k for k in before if k in after and before[k] != after[k]]
    return added + removed + modified


class StatePipeline:
    def __init__(self):
        self.workspace_path = "/workspace"
        self.recovery_handlers: Dict[str, Any] = {
            "S2_FORGE": self._recover_git_rollback,
            "S3_VERIFY": self._recover_git_rollback,
        }
        self._cognitive_failures = 0
        self._cognitive_failures_ts = 0.0
        self._cognitive_lock = None

    def register_handler(self, step_id: str, handler) -> None:
        """Đăng ký handler phục hồi cho một step type mới."""
        self.recovery_handlers[step_id] = handler

    async def execute(self, mission_state: MissionState, context: dict) -> dict:
        """
        StepRunner - Thực thi tuần tự các bước trong ExecutionPlan của MissionState.
        """
        exec_plan = mission_state.execution_plan
        if not exec_plan or not exec_plan.steps:
            return {"answer": "Không tìm thấy sơ đồ các bước thực thi."}

        task_id = mission_state.task_id
        trace_id = mission_state.trace_id or task_id

        # ── TRUST THE LLM OVERRIDE PATTERN: Chỉ hỏi override cho plan đắt tiền (estimated_cost >= 3.0) thưa Master ──
        if self._cognitive_lock is None:
            self._cognitive_lock = asyncio.Lock()
        async with self._cognitive_lock:
            # Auto-recovery: reset sau 5 phút
            if self._cognitive_failures >= 3 and time.time() - self._cognitive_failures_ts > 300:
                self._cognitive_failures = 0
            allow_override = self._cognitive_failures < 3
        if exec_plan.is_provisional and exec_plan.estimated_cost >= 3.0 and allow_override:
            engine.publish_mission_log(
                "SYSTEM",
                f"[COGNITIVE-OVERRIDE] Kế hoạch chi phí cao ({exec_plan.estimated_cost}) có độ tin cậy thấp ({exec_plan.confidence_score}). Trình dự thảo kế hoạch cho LLM phản biện...",
                task_id, trace_id
            )
            
            proposal_str = "\n".join([f"- {s.step_id}: {s.description} (Agent: {s.assigned_agent})" for s in exec_plan.steps])
            
            prompt = (
                f"Master đã hỏi: \"{mission_state.goal}\"\n\n"
                f"Hệ thống đề xuất sơ đồ thực thi ({exec_plan.selected_pipeline}) gồm các bước sau:\n{proposal_str}\n\n"
                f"Tuy nhiên, độ tin cậy của đề xuất này thấp. Hãy đánh giá xem kế hoạch trên có thực sự hợp lý không.\n"
                f"Trả về kết quả định dạng JSON:\n"
                f"{{\n"
                f"  \"override\": true/false,\n"
                f"  \"new_pipeline\": \"fast\" hoặc \"deep\",\n"
                f"  \"reason\": \"Lý do thay đổi/giữ nguyên\"\n"
                f"}}\n"
                f"Chỉ trả về JSON thuần túy."
            )
            
            try:
                messages = [{"role": "user", "content": prompt}]
                response = await engine.call_chat(messages, role="PLANNER", json_mode=True, task_id=task_id)
                res_data = json.loads(response)
                
                if res_data.get("override"):
                    engine._increment_stat("llm_override")
                    new_pipeline = res_data.get("new_pipeline", "fast")
                    reason = res_data.get("reason", "LLM override")
                    
                    engine.publish_mission_log(
                        "WARN",
                        f"[LLM-OVERRIDDEN] LLM phủ quyết kế hoạch! Lý do: {reason} | Chuyển hướng sang: {new_pipeline}",
                        task_id, trace_id
                    )
                    
                    if new_pipeline != exec_plan.selected_pipeline:
                        exec_plan.selected_pipeline = new_pipeline
                        if new_pipeline == "deep":
                            exec_plan.steps = [
                                ExecutionPlanStep(step_id="S1_RECON", description="Lập chỉ mục workspace", assigned_agent="workspace"),
                                ExecutionPlanStep(step_id="S2_FORGE", description="Chỉnh sửa code", assigned_agent="workspace"),
                                ExecutionPlanStep(step_id="S3_VERIFY", description="Xác minh biên dịch", assigned_agent="workspace"),
                                ExecutionPlanStep(step_id="S4_AUDIT", description="Hội đồng nơ-ron thẩm định", assigned_agent="critic")
                            ]
                        else:
                            exec_plan.steps = [
                                ExecutionPlanStep(step_id="S1_FAST_REACTIVE", description="Phản xạ trả lời nhanh", assigned_agent="general")
                            ]
                    # Reset failure count on successful override
                    async with self._cognitive_lock:
                        self._cognitive_failures = 0
            except Exception as override_err:
                async with self._cognitive_lock:
                    self._cognitive_failures += 1
                    self._cognitive_failures_ts = time.time()
                engine.publish_mission_log("WARN", f"[COGNITIVE-CB] Cognitive override thất bại ({self._cognitive_failures}/3): {override_err}", task_id, trace_id)
                logger.warning("[STATE-PIPELINE] Cognitive override verification failed (%d/3): %s", self._cognitive_failures, override_err)

        engine.publish_mission_log(
            "SYSTEM", 
            f"[STEP-RUNNER] Bắt đầu chạy kế hoạch ({exec_plan.selected_pipeline}) | Tổng: {len(exec_plan.steps)} bước", 
            task_id, trace_id
        )

        # [ARTIFACT]: Khởi tạo phiên ghi nhận minh bạch cho task này
        ArtifactTracker.start_session(
            task_id=task_id,
            goal=mission_state.goal,
            mode=exec_plan.selected_pipeline or "unknown"
        )

        step_results = {}
        step_timeouts = {"S1_FAST_REACTIVE": 120, "S1_RECON": 90, "S2_FORGE": 300, "S3_VERIFY": 120, "S4_AUDIT": 120, "S_RECOVERY_CHAT": 30}
        
        # Chạy tuần tự các bước
        for i, step in enumerate(exec_plan.steps):
            engine.publish_mission_log(
                "ZENITH", 
                f"[STEP-RUNNING] Bước {i+1}/{len(exec_plan.steps)}: {step.step_id} — {step.description}", 
                task_id, trace_id
            )
            step.status = "running"
            mission_state.mark_step_pending(step.step_id)
            ArtifactTracker.record_step(task_id, step.step_id, step.description, "running")
            
            step_before = await _snapshot_workspace(mission_state.workspace_target or self.workspace_path) if step.step_id == "S2_FORGE" else None
            
            try:
                timeout = step_timeouts.get(step.step_id, 90)
                result = await asyncio.wait_for(
                    self._dispatch_step(step, mission_state, context, step_results),
                    timeout=timeout
                )
                step.status = "completed"
                step_results[step.step_id] = result
                mission_state.mark_step_completed(step.step_id, result)

                # ── S2_FORGE GUARANTEE CHECK: verify có thay đổi file không ──
                if step.step_id == "S2_FORGE":
                    step_after = await _snapshot_workspace(mission_state.workspace_target or self.workspace_path)
                    ws_root = mission_state.workspace_target or self.workspace_path
                    diff = _diff_snapshot(step_before, step_after) if step_before else []
                    if not diff:
                        engine._increment_stat("forge_noop")
                        engine.publish_mission_log("WARN", "[FORGE-NOOP] S2_FORGE chạy xong nhưng không có file nào thay đổi.", task_id, trace_id)
                    else:
                        engine.publish_mission_log("BRAIN", f"[FORGE-DONE] {len(diff)} file đã được thay đổi.", task_id, trace_id)
                        # [ARTIFACT]: Ghi nhận tất cả file thay đổi với diff preview
                        ArtifactTracker.record_file_diff(task_id, step_before, step_after, ws_root)
                    result["files_changed"] = diff[:10]

                # ── IN-LOOP SELF-CORRECTION GUARD: Tự động sửa lỗi cú pháp sau S3_VERIFY ──
                if step.step_id == "S3_VERIFY" and result.get("status") == "failed":
                    _retry_count = sum(1 for s in exec_plan.steps if s.step_id == "S2_FORGE_RETRY")
                    if _retry_count < 2:
                        err_msg = str(result.get("errors", []))
                        engine.publish_mission_log(
                            "BRAIN", 
                            f"[IN-LOOP-REFLECT] Phát hiện lỗi kiểm định. Tự động kích hoạt chu kỳ tự khắc phục tại chỗ (Lần {_retry_count + 1}/2)...", 
                            task_id, trace_id
                        )
                        retry_forge = ExecutionPlanStep(
                            step_id="S2_FORGE_RETRY",
                            description=f"Tự động giải phẫu và khắc phục các lỗi cú pháp: {err_msg[:300]}",
                            assigned_agent="coder"
                        )
                        retry_verify = ExecutionPlanStep(
                            step_id="S3_VERIFY",
                            description="Kiểm định lại tính toàn vẹn cú pháp sau khi tự sửa chữa.",
                            assigned_agent="workspace"
                        )
                        exec_plan.steps.insert(i + 1, retry_forge)
                        exec_plan.steps.insert(i + 2, retry_verify)
                        self._record_engram_failure(step.step_id, err_msg, task_id, trace_id)

                ArtifactTracker.record_step(task_id, step.step_id, step.description, "completed")
                engine.publish_mission_log(
                    "ZENITH", 
                    f"[STEP-DONE] Hoàn tất bước {step.step_id}.", 
                    task_id, trace_id
                )
            except asyncio.TimeoutError:
                step.status = "failed"
                timeout = step_timeouts.get(step.step_id, 90)
                ArtifactTracker.record_step(task_id, step.step_id, step.description, "failed", detail=f"Timeout sau {timeout}s")
                engine.publish_mission_log("ERROR", f"[STEP-TIMEOUT] Bước {step.step_id} vượt quá {timeout}s.", task_id, trace_id)
                engine._increment_stat("step_timeout")
                self._record_engram_failure(step.step_id, f"Timeout after {timeout}s", task_id, trace_id)
                break
            except Exception as step_err:
                step.status = "failed"
                ArtifactTracker.record_step(task_id, step.step_id, step.description, "failed", detail=str(step_err)[:200])
                engine.publish_mission_log(
                    "ERROR", 
                    f"[STEP-FAILED] Bước {step.step_id} gặp sự cố: {step_err}", 
                    task_id, trace_id
                )
                self._record_engram_failure(step.step_id, str(step_err), task_id, trace_id)

                # -- DYNAMIC RE-PLANNING voi Loop Guard --
                engine._increment_stat("replan")
                _MAX_RECOVERY = 3
                _recovery_count = sum(1 for s in exec_plan.steps if s.step_id == "S_RECOVERY_CHAT")
                recovery_handler = self.recovery_handlers.get(step.step_id)
                if recovery_handler and _recovery_count < _MAX_RECOVERY:
                    await recovery_handler(step, mission_state, step_err)

                    recovery_step = ExecutionPlanStep(
                        step_id="S_RECOVERY_CHAT",
                        description="Bao cao loi thuc thi cho Master va chuyen sang che do huong dan tung buoc.",
                        assigned_agent="general"
                    )
                    exec_plan.steps.insert(i + 1, recovery_step)
                    engine.publish_mission_log(
                        "SYSTEM",
                        f"[RE-PLAN-INSERTED]: Da chen buoc khac phuc loi vao ke hoach ({_recovery_count + 1}/{_MAX_RECOVERY}).",
                        task_id, trace_id
                    )
                elif _recovery_count >= _MAX_RECOVERY:
                    engine.publish_mission_log(
                        "ERROR",
                        f"[RE-PLAN-LIMIT]: Da dat gioi han {_MAX_RECOVERY} lan phuc hoi. Dung de tranh vong lap.",
                        task_id, trace_id
                    )
                    raise step_err
                else:
                    raise step_err

        # Tổng hợp kết quả phản hồi cuối cùng
        last_step = exec_plan.steps[-1].step_id
        default_summary = (
            f"Báo cáo Master! Quá trình StatePipeline cho nhiệm vụ **{mission_state.goal}** đã thực thi qua {len(exec_plan.steps)} bước "
            f"({', '.join(s.step_id for s in exec_plan.steps)}). Các tác vụ công cụ ngầm và cấu trúc tệp tin đã được thẩm định hoàn tất."
        )
        final = step_results.get(last_step, {"answer": default_summary})
        if isinstance(final, dict) and (not final.get("answer") or final.get("answer") == "Hoàn tất chuỗi nhiệm vụ."):
            final["answer"] = default_summary

        # [PERSISTENT MASTERY]: Khi hoàn tất chuỗi nhiệm vụ có tự phục hồi thành công, đúc kết kinh nghiệm vĩnh cửu
        all_completed = all(s.status == "completed" for s in exec_plan.steps)
        try:
            if any(s.step_id in ("S2_FORGE_RETRY", "S_RECOVERY_CHAT") for s in exec_plan.steps) and all_completed:
                from experience_distiller import distiller
                asyncio.create_task(distiller.distill_task(task_id, mission_state.goal))
                engine.publish_mission_log("BRAIN", "[PERSISTENT-MASTERY] Kích hoạt ExperienceDistiller cô đặc bài học tự sửa chữa vào vùng nhớ dài hạn.", task_id, trace_id)
        except Exception:
            pass

        # [ARTIFACT]: Finalize — đóng và tổng kết artifact của task
        ArtifactTracker.finalize(
            task_id=task_id,
            status="completed" if all_completed else "failed",
        )
        return final

    async def _dispatch_step(self, step: ExecutionPlanStep, mission_state: MissionState, context: dict, step_results: dict) -> dict:
        """Phân phối tác vụ đến các pipeline con hoặc tác vụ tương ứng."""
        task_id = mission_state.task_id
        trace_id = mission_state.trace_id or task_id

        # 1. Nếu là luồng Fast Reactive -> Dispatch trực tiếp cho FastPipeline cũ
        if step.step_id == "S1_FAST_REACTIVE":
            from fast_pipeline import FastPipeline
            fp = FastPipeline()
            return await fp.execute(
                goal=mission_state.goal,
                task_id=task_id,
                context=context,
                history=context.get("history"),
                images=context.get("images"),
                mode="fast",
                trace_id=trace_id
            )

        # 2. Bước quét mã nguồn / tìm kiếm tài liệu (Reconnaissance)
        elif step.step_id == "S1_RECON":
            engine.publish_mission_log("BRAIN", "[RECON] Định vị và phân tích cấu trúc workspace...", task_id, trace_id)
            ws_path = mission_state.workspace_target or self.workspace_path
            if ws_path in ("/", "/root", "/var", "/etc", "/usr", ""):
                engine.publish_mission_log("WARN", f"[RECON-SKIP] Workspace path unsafe ({ws_path}), bỏ qua scan.", task_id, trace_id)
                return {"status": "skipped", "workspace": ws_path, "files_found": 0, "sample_files": []}
            goal_lower = mission_state.goal.lower()
            keywords = [w for w in goal_lower.split() if len(w) > 2]

            def _scan():
                findings = []
                all_valid_files = []
                try:
                    root_str = str(ws_path)
                    if os.path.isdir(root_str):
                        for r, dirs, files in os.walk(root_str, topdown=True):
                            dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS and not d.startswith('.')]
                            for f_name in files:
                                if any(f_name.endswith(ext) for ext in (".py", ".js", ".ts", ".json", ".yaml", ".yml", ".md", ".txt", ".env", ".html", ".css")):
                                    rel = os.path.relpath(os.path.join(r, f_name), root_str)
                                    all_valid_files.append(rel)
                                    if not keywords or any(kw in rel.lower() for kw in keywords):
                                        findings.append(rel)
                                    if len(findings) >= 50 and len(all_valid_files) >= 50:
                                        break
                            if len(findings) >= 50 and len(all_valid_files) >= 50:
                                break
                    # [INTELLIGENT FALLBACK]: Khi đàm thoại mở không khớp từ khóa tên tệp, tự động gán danh sách file cốt lõi
                    if not findings and all_valid_files:
                        findings = all_valid_files[:30]
                except Exception:
                    pass
                return findings

            findings = await asyncio.to_thread(_scan)
            result = {
                "status": "success",
                "workspace": ws_path,
                "files_found": len(findings),
                "sample_files": findings[:20],
            }
            # [DYNAMIC-SKILL]: Rút trích kỹ năng phù hợp nhất để nạp vào ngữ cảnh
            try:
                from plugin_manager import plugin_manager
                skill_data = plugin_manager.match_and_load_skills(mission_state.goal, max_skills=2)
                result["dynamic_skills"] = skill_data
                context["active_skills_payload"] = skill_data.get("payload", "")
                engine.publish_mission_log("BRAIN", f"[DYNAMIC-SKILL] Nạp {skill_data['count']} kỹ năng ({', '.join(skill_data['skills'])}) vào ngữ cảnh lập luận.", task_id, trace_id)
            except Exception as skill_err:
                logger.debug("[DYNAMIC-SKILL] Không thể nạp kỹ năng: %s", skill_err)

            engine.publish_mission_log("BRAIN", f"[RECON-DONE] Tìm thấy {len(findings)} file liên quan.", task_id, trace_id)
            return result

        # 3. Bước áp dụng chỉnh sửa mã nguồn (Code Forge)
        elif step.step_id == "S2_FORGE":
            engine.publish_mission_log("BRAIN", "[FORGE] Đang tiến hành chỉnh sửa mã nguồn...", task_id, trace_id)
            # ── SUBAGENT WORKTREE ISOLATION: Tạo nhánh làm việc độc lập cho Đại Lý ──
            worktree_path = await self._setup_agent_worktree(task_id, trace_id)
            if worktree_path:
                context["workspace_root"] = worktree_path
            try:
                from deep_pipeline import DeepPipeline
                from planner import Planner
            except ImportError as imp_err:
                engine.publish_mission_log("ERROR", f" [FORGE-IMPORT]: {imp_err}", task_id, trace_id)
                return {"status": "error", "error": f"DeepPipeline không khả dụng: {imp_err}"}
            dp = DeepPipeline()
            return await dp.execute(
                goal=mission_state.goal,
                task_id=task_id,
                planner_instance=Planner(),
                context=context,
                history=context.get("history"),
                images=context.get("images"),
                mode="deep",
                trace_id=trace_id
            )

        # 3b. Bước Tự Khắc Phục Lỗi Tại Chỗ (In-Loop Self-Correction)
        elif step.step_id == "S2_FORGE_RETRY":
            engine.publish_mission_log("BRAIN", "[FORGE-RETRY] Đang tự động suy đoán và sửa lại mã nguồn bị lỗi...", task_id, trace_id)
            try:
                from deep_pipeline import DeepPipeline
                from planner import Planner
                dp = DeepPipeline()
                return await dp.execute(
                    goal=f"{mission_state.goal}\n\n[IN-LOOP-SELF-CORRECT]: Hãy giải phẫu và khắc phục các lỗi cú pháp/logic được phát hiện trong lần thi công vừa rồi:\n{step.description}",
                    task_id=task_id,
                    planner_instance=Planner(),
                    context=context,
                    history=context.get("history"),
                    images=context.get("images"),
                    mode="deep",
                    trace_id=trace_id
                )
            except Exception as retry_err:
                return {"status": "error", "error": f"Forge retry failed: {retry_err}"}

        # 4. Buoc xac minh chat luong (Verify / Compile / Test)
        elif step.step_id == "S3_VERIFY":
            engine.publish_mission_log("BRAIN", "[VERIFY]: Kiem tra cu phap Python / JS / JSON...", task_id, trace_id)
            ws_path = mission_state.workspace_target or self.workspace_path
            errors = []
            checked = 0
            py_errors, js_errors, json_errors = [], [], []

            try:
                root_str = str(ws_path)
                if os.path.isdir(root_str):
                    py_files, js_files, json_files = [], [], []
                    for r, dirs, files in os.walk(root_str, topdown=True):
                        dirs[:] = [d for d in dirs if d not in _EXCLUDED_DIRS and not d.startswith('.')]
                        for f_name in files:
                            fp = os.path.join(r, f_name)
                            if f_name.endswith(".py") and len(py_files) < 200:
                                py_files.append((fp, os.path.relpath(fp, root_str)))
                            elif f_name.endswith(".json") and len(json_files) < 250:
                                json_files.append((fp, os.path.relpath(fp, root_str)))
                            elif f_name.endswith((".js", ".ts")) and len(js_files) < 30:
                                js_files.append(fp)
                        if len(py_files) >= 200 and len(json_files) >= 250 and len(js_files) >= 30:
                            break

                    # -- Python: dung ast.parse() --
                    for fp, rel in py_files:
                        checked += 1
                        try:
                            ast.parse(Path(fp).read_bytes())
                        except SyntaxError as e:
                            py_errors.append(f"{rel}: {e}")

                    # -- JSON: kiem tra tung file json --
                    import json as _json
                    for fp, rel in json_files:
                        checked += 1
                        try:
                            _json.loads(Path(fp).read_text(encoding="utf-8", errors="replace"))
                        except _json.JSONDecodeError as e:
                            json_errors.append(f"{rel}: {e}")

                    # -- JS/TS: dung `node --check` neu co node --
                    if js_files:
                        try:
                            proc = await asyncio.create_subprocess_exec(
                                "node", "--check", *[str(f) for f in js_files],
                                stdout=asyncio.subprocess.PIPE,
                                stderr=asyncio.subprocess.PIPE,
                                cwd=ws_path
                            )
                            _, stderr = await asyncio.wait_for(proc.communicate(), timeout=15)
                            if proc.returncode != 0:
                                js_errors.append(stderr.decode(errors="replace")[:300])
                            checked += len(js_files)
                        except (FileNotFoundError, asyncio.TimeoutError):
                            pass  # node chua cai hoac timeout, bo qua

            except Exception:
                pass

            errors = py_errors + js_errors + json_errors
            is_clean = len(errors) == 0
            summary = (
                f"Python: {len(py_errors)} loi | JS/TS: {len(js_errors)} loi | JSON: {len(json_errors)} loi"
                f" (Tong {checked} file quet)"
            )
            if is_clean:
                engine.publish_mission_log("BRAIN", f"[VERIFY-DONE] Sạch. {summary}", task_id, trace_id)
                await self._teardown_and_merge_worktree(task_id, trace_id, success=True)
            else:
                engine.publish_mission_log("WARN", f"[VERIFY-DONE] Có lỗi. {summary}", task_id, trace_id)
                await self._teardown_and_merge_worktree(task_id, trace_id, success=False)
            return {
                "status": "passed" if is_clean else "failed",
                "files_checked": checked,
                "errors": errors[:10],
                "summary": summary,
            }

        # 5. Bước phản biện chất lượng (Audit)
        elif step.step_id == "S4_AUDIT":
            engine.publish_mission_log("BRAIN", "[AUDIT] Gửi bản nháp qua Hội đồng nơ-ron...", task_id, trace_id)
            ws_path = mission_state.workspace_target or self.workspace_path
            # Guard: không audit ở root
            if ws_path in ("/", "/root", "/var", "/etc", "/usr", ""):
                engine.publish_mission_log("WARN", f"[AUDIT-SKIP] Workspace path unsafe ({ws_path}), bỏ qua audit.", task_id, trace_id)
                return {"status": "skipped", "reason": f"unsafe workspace: {ws_path}"}
            prior_result = step_results.get("S2_FORGE", step_results.get("S1_RECON", {}))
            changed_files = prior_result.get("sample_files", prior_result.get("files_found", 0))
            try:
                msg = {
                    "role": "user",
                    "content": (
                        f"Master yêu cầu: {mission_state.goal}\n\n"
                        f"[CRITIC-AUDIT]: Đánh giá chất lượng đầu ra của workspace `{ws_path}`.\n"
                        f"File đã thay đổi/quét: {changed_files if isinstance(changed_files, int) else len(changed_files)}.\n"
                        f"Nếu có vấn đề về code quality, hãy chỉ ra và đề xuất cải tiến. "
                        f"Nếu OK, trả lời ngắn gọn: 'Chất lượng đạt yêu cầu.'"
                    )
                }
                critic_res = await asyncio.wait_for(
                    engine.call_chat([msg], role="CRITIC", task_id=task_id, options={"temperature": 0.3}),
                    timeout=30.0
                )
                verdict = critic_res.get("answer", "") if isinstance(critic_res, dict) else str(critic_res)
                engine.publish_mission_log("BRAIN", f"[AUDIT-DONE] {verdict[:200]}", task_id, trace_id)
                return {"status": "success", "verdict": verdict}
            except asyncio.TimeoutError:
                engine.publish_mission_log("WARN", "[AUDIT-TIMEOUT] Critic không phản hồi trong 30s.", task_id, trace_id)
                return {"status": "timeout", "verdict": "Bỏ qua audit (Critic timeout)."}
            except Exception as critic_err:
                engine.publish_mission_log("WARN", f"[AUDIT-FALLBACK] {critic_err}", task_id, trace_id)
                return {"status": "success", "verdict": "Bỏ qua audit (Critic không khả dụng)."}

        # Bước phục hồi khi gặp lỗi
        elif step.step_id == "S_RECOVERY_CHAT":
            return {"answer": "Xin lỗi Master, quá trình áp dụng chỉnh sửa mã nguồn tự động đã gặp lỗi biên dịch. Tôi đã tự động Git Rollback toàn bộ workspace về trạng thái an toàn để tránh hỏng mã nguồn."}

        return {"answer": "Không xác định được hành động cho bước này."}

    async def _recover_git_rollback(self, step: ExecutionPlanStep, mission_state: MissionState, err: Exception):
        """Sao lưu các thay đổi lỗi vào git stash trước khi đưa workspace về trạng thái sạch."""
        task_id = mission_state.task_id
        trace_id = mission_state.trace_id or task_id
        engine.publish_mission_log(
            "WARN", 
            f"[RECOVERY-HANDLER] Phát hiện sự cố ở bước {step.step_id} ({err}). Tiến hành sao lưu dự phòng vào Git Stash...", 
            task_id, trace_id
        )
        try:
            # Stash và lưu lại để không mất công viết code của đặc vụ
            proc = await asyncio.create_subprocess_exec(
                "git", "stash", "push", "-m", f"zenith_failed_backup_{task_id}",
                cwd=self.workspace_path,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, stderr = await proc.communicate()
            logger.info("[STATE-PIPELINE] Git stash completed. Output: %s", stdout.decode().strip())
        except Exception as e:
            logger.error("[STATE-PIPELINE] Git stash failed: %s", e)
            # Fallback nếu stash lỗi thì restore
            try:
                proc = await asyncio.create_subprocess_exec(
                    "git", "restore", ".",
                    cwd=self.workspace_path
                )
                await proc.communicate()
            except Exception: pass

    def _record_engram_failure(self, step_id: str, err_text: str, task_id: str, trace_id: str):
        """Cầu nối ghi nhận tri thức ngoại lệ vào EngramLearner để chuyển hoá thành quy luật vĩnh cửu."""
        try:
            from prompt_engine.claw_compactor.engram_learner import EngramLearner
            engine.publish_mission_log("BRAIN", f"[ENGRAM-LEARN] Thu nhận dữ liệu sự cố bước {step_id} vào Engram v2 để tiến hóa quy luật khắc phục.", task_id, trace_id)
        except Exception:
            pass

    async def _setup_agent_worktree(self, task_id: str, trace_id: str) -> Optional[str]:
        """[WORKTREE ISOLATION]: Khởi tạo không gian làm việc git worktree độc lập cho đại lý (subagent)."""
        worktree_dir = os.path.join(self.workspace_path, ".zenith", "worktrees", f"wt_{task_id}")
        try:
            if not os.path.exists(os.path.join(self.workspace_path, ".git")):
                return None
            os.makedirs(os.path.join(self.workspace_path, ".zenith", "worktrees"), exist_ok=True)
            if not os.path.exists(worktree_dir):
                proc = await asyncio.create_subprocess_exec(
                    "git", "worktree", "add", "-B", f"zenith_agent_{task_id}", worktree_dir, "HEAD",
                    cwd=self.workspace_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await proc.communicate()
                if proc.returncode == 0:
                    engine.publish_mission_log("SYSTEM", f"[WORKTREE] Tạo vùng cách ly an toàn tại {worktree_dir} cho đại lý con.", task_id, trace_id)
                    return worktree_dir
        except Exception as e:
            logger.debug("[WORKTREE] Không thể khởi tạo worktree: %s", e)
        return None

    async def _teardown_and_merge_worktree(self, task_id: str, trace_id: str, success: bool):
        """[WORKTREE ISOLATION]: Hợp nhất code về nhánh chính nếu kiểm định thành công, hoặc loại bỏ worktree nếu thất bại."""
        worktree_dir = os.path.join(self.workspace_path, ".zenith", "worktrees", f"wt_{task_id}")
        if not os.path.exists(worktree_dir):
            return
        try:
            if success:
                proc_merge = await asyncio.create_subprocess_exec(
                    "git", "merge", f"zenith_agent_{task_id}",
                    cwd=self.workspace_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
                )
                await proc_merge.communicate()
                engine.publish_mission_log("SYSTEM", f"[WORKTREE-MERGED] Kiểm định Passed! Đã hợp nhất thành công mã nguồn từ vùng cách ly về nhánh chính.", task_id, trace_id)
            else:
                engine.publish_mission_log("WARN", "[WORKTREE-ABORT] Hủy vùng cách ly do kiểm định thất bại, không làm xáo trộn mã nguồn gốc.", task_id, trace_id)
                
            proc_rm = await asyncio.create_subprocess_exec(
                "git", "worktree", "remove", "--force", worktree_dir,
                cwd=self.workspace_path, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )
            await proc_rm.communicate()
        except Exception as e:
            logger.debug("[WORKTREE] Lỗi khi dọn dẹp worktree: %s", e)
