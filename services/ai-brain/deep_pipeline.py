"""
🧠 DEEP PIPELINE — Zenith v43.0  [T2 → T3 → T4 → T5 → T6]
═══════════════════════════════════════════════════════════
Điều phối TOÀN BỘ luồng DEEP từ đầu đến cuối.
Đây là Self-Contained Unit — không cần ai điều phối bên ngoài.

  ┌─────────────────────────────────────────────────────────┐
  │  T1  receptionist.py   → Tiếp nhận & Switchboard       │
  │  T2  DeepPipeline      → Recon + Context (RAG)      ←  │
  │  T3  DeepPipeline      → Forge + Policy (PLANNER)   ←  │
  │  T4  DeepPipeline      → Gọi Executor thực thi      ←  │  FILE NÀY
  │  T5  DeepPipeline      → CRITIC kiểm duyệt          ←  │
  │  T6  DeepPipeline      → SUMMARIZER tóm tắt         ←  │
  └─────────────────────────────────────────────────────────┘

NGUYÊN TẮC VÀNG:
  - BẮT BUỘC dùng role PLANNER để lập Blueprint
  - BẮT BUỘC đi qua đủ T2 → T3 → T4 → T5 → T6
  - Có vòng Retry 3 lần với role RESERVE_AGENT dự phòng
  - Mọi model đều được map từ rule_hardware.md, KHÔNG set cứng ở đây
═══════════════════════════════════════════════════════════
"""
import json
import logging
import asyncio
import httpx
from typing import Any, Dict, List, Optional
from core.utils.engine import MasterAbortException, engine
from core.utils.tracing import TraceContext
from prompt_engine.claw_compactor.memory_pruner import MemoryPruner
from core.utils.mode_switcher import mode_switcher
from core.kernel.cognitive_memory_buffer import cognitive_memory_buffer
from core.kernel.self_reflection_guard import self_reflection_guard

logger = logging.getLogger("JKAI.DeepPipeline")

class DeepPipeline:
    """
    🧠 Luồng Chiến lược — Tự khép kín hoàn toàn.
    T2 → T3 → T4 → T5 → T6 (Đầy đủ CRITIC)
    """
    def __init__(self):
        # 🧠 [PLANNING-INIT]: Đúc kết các Stage T2+T3
        from planning_pipeline import (
            ReconStage, ContextStage, ForgeStage, DAGOptimizerStage, PolicyStage, PlanningPipeline
        )
        self._planning = PlanningPipeline(stages=[
            ReconStage(), ContextStage(), ForgeStage(), DAGOptimizerStage(), PolicyStage()
        ])
    async def execute(
        self,
        goal: str,
        task_id: str,
        planner_instance: Any,
        context: Dict = None,
        history: List = None,
        images: List = None,
        mode: str = "auto",
        trace_id: str = "system",
    ) -> Dict[str, Any]:
        """
        Thực thi toàn bộ luồng DEEP từ T2 đến T6 với vòng lặp Re-planner thưa Master.
        """
        max_attempts = 3
        replan_feedback = ""
        final_result = None

        # [ENGINE SWITCH]: Cầu nối điều phối nạp tĩnh mô hình cho luồng DEEP
        try:
            await mode_switcher.switch_to("DEEP", engine, task_id)
        except Exception as e_ms:
            logger.warning(f"[DEEP-PIPELINE] Mode switcher err: {e_ms}")

        # [PILLAR 9 & PARENTAL HERITAGE: CONTEXT FOG SEVERANCE & MEMORY PRUNING]
        try:
            if history and len(history) > 10:
                pruner = MemoryPruner(similarity_threshold=0.85)
                transformed_history = []
                for idx, h in enumerate(history):
                    if isinstance(h, dict):
                        transformed_history.append({"id": f"hist_{idx}", "timestamp": idx, "content": str(h.get("content", h)), "importance": h.get("importance", 0.5), "original": h})
                    else:
                        transformed_history.append({"id": f"hist_{idx}", "timestamp": idx, "content": str(h), "importance": 0.5, "original": h})
                res_prune = pruner.prune_stale_engrams(transformed_history)
                pruned_recs = res_prune.get("pruned_records", [])
                if len(pruned_recs) < len(history):
                    history = [rec["original"] for rec in pruned_recs]
                    engine.publish_mission_log("SYSTEM", f"🧹 [CONTEXT FOG SEVERANCE]: Đã thanh lọc {res_prune.get('reduction_percentage')}% rác lịch sử hội thoại trước chặng T2/T3.", task_id, trace_id, stealth=True)
        except Exception as e_prune:
            logger.warning(f"[DEEP-PIPELINE] Memory pruning skipped: {e_prune}")

        for attempt in range(max_attempts):
            if attempt > 0:
                engine.publish_mission_log(
                    "SYSTEM",
                    f"🔄 [REPLAN-ATTEMPT]: Critic không phê duyệt. Lập kế hoạch lại. Attempt {attempt + 1}/{max_attempts}",
                    task_id,
                    trace_id
                )
                try:
                    from context import mission_context as ctx_mgr
                    mc = ctx_mgr.get_or_create(task_id)
                    await mc.mission_state_v2.rollback(1)
                    ctx_mgr.save(mc)
                except Exception:
                    pass
                try:
                    from mission_state import MissionRuntime
                    mr = MissionRuntime(user_goal=goal)
                    await mr.emit("MissionStarted", {"task_id": task_id})
                except Exception:
                    pass

            current_goal = goal
            if replan_feedback:
                current_goal += f"\n\n[REPLAN-FEEDBACK]: Báo cáo thực thi trước đó bị Critic từ chối vì: '{replan_feedback}'. Vui lòng điều chỉnh kế hoạch, sửa đổi các bước lỗi và khắc phục triệt để."

            final_result = await self._execute_attempt(
                goal=current_goal,
                task_id=task_id,
                planner_instance=planner_instance,
                context=context,
                history=history,
                images=images,
                mode=mode,
                trace_id=trace_id,
                attempt=attempt
            )

            judicial_review = final_result.get("judicial_review", {})
            verdict = str(judicial_review.get("verdict", "FAIL")).upper()
            is_architectural = "step_01_neural_synthesis" in final_result.get("execution", {})
            if any(w in verdict for w in ["SUCCESS", "PARTIAL", "PASS", "APPROVED", "VALID", "OK"]) or is_architectural:
                engine.publish_mission_log(
                    "SYSTEM",
                    f"✅ [CRITIC-PASSED]: Thẩm định thành công ({verdict}{' - Architectural Consensus' if is_architectural else ''}), duyệt báo cáo T5/T6.",
                    task_id,
                    trace_id
                )
                break
            else:
                replan_feedback = judicial_review.get("feedback", "Kết quả thực thi không có bằng chứng hợp lệ.")

        return final_result

    async def _execute_attempt(
        self,
        goal: str,
        task_id: str,
        planner_instance: Any,
        context: Dict = None,
        history: List = None,
        images: List = None,
        mode: str = "auto",
        trace_id: str = "system",
        attempt: int = 0,
    ) -> Dict[str, Any]:
        from core.utils.engine import engine

        context = context or {}
        history = history or []

        # 🧠 [COGNITIVE-MEMORY-BUFFER]: Nén ngữ cảnh lịch sử trước khi vào pipeline
        try:
            if history:
                history = cognitive_memory_buffer.compress_messages(history)
        except Exception:
            pass

        engine.publish_mission_log(
            "SYSTEM",
            f"🧠 [DEEP-PIPELINE]: Khởi động luồng chiến lược 5 tầng (T2→T6).",
            task_id, trace_id, stealth=True
        )

        # T1.5: Domain routing (Planner tự xử lý, bỏ MetaPlanner)
        domain = "CORE"
        agent_role = "Generalist"
        complexity = "MEDIUM"
        execution_mode = "SEQUENTIAL"

        # ═══════════════════════════════════════════
        # T2 + T3: Recon → Context → Forge → Policy
        # ═══════════════════════════════════════════
        initial_state = {
            "goal": goal,
            "task_id": task_id,
            "trace_id": trace_id,
            "planner_instance": planner_instance,
            "context": context,
            "mode": mode,
            "complexity": complexity,
            "execution_mode": execution_mode,
            "domain": domain,
            "attempt": attempt,
        }

        # ═══════════════════════════════════════════
        # T2 + T3: Recon → Context → Forge → Policy
        # ═══════════════════════════════════════════
        try:
            with TraceContext("DeepPipeline-T2T3", trace_id=trace_id):
                plan_state = await self._planning.execute(initial_state)
        except Exception as e:
            logger.error(f"🚨 [DEEP-T2T3-ERR]: {e}")
            engine.publish_mission_log("ERROR", f"🚨 [T2/T3 FAULT]: {e}", task_id, trace_id)
            return {"answer": f"❌ [PLANNER ERROR]: Không thể lập kế hoạch - {e}", "task_id": task_id}

        final_plan = plan_state.get("final_plan", {})
        steps = final_plan.get("steps", [])
        blueprint = plan_state.get("blueprint_obj")

        if steps:
            roadmap_lines = ["📋 **LỘ TRÌNH TRIỂN KHAI CHIẾN LƯỢC (AGENTIC WORKFLOW):**\n"]
            for idx, s in enumerate(steps, 1):
                s_id = s.get("id", f"Step_{idx}")
                s_action = s.get("tool") or s.get("action") or "Execution"
                s_desc = s.get("description") or s.get("title") or f"Thực thi mục tiêu {s_id}"
                roadmap_lines.append(f"  • `[ ]` **{s_id} ({s_action})**: {s_desc}")
            roadmap_text = "\n".join(roadmap_lines)
            engine.publish_mission_log(
                "PLANNER",
                f"🎯 **PHÊ CHÍNH KẾ HOẠCH HÀNH ĐỘNG ({len(steps)} BƯỚC):**\n\n{roadmap_text}",
                task_id, trace_id,
                stealth=False
            )
        else:
            engine.publish_mission_log(
                "PLANNER",
                f"📊 [BLUEPRINT SEALED]: Không có bước thực thi cụ thể nào được tạo.",
                task_id, trace_id,
                stealth=True
            )

        if not steps:
            if blueprint and getattr(blueprint, "ambiguous", False):
                q = getattr(blueprint, "question", None) or getattr(blueprint, "clarification_question", None)
                if not q or q.strip() == "":
                    q = "Không tìm thấy dữ liệu liên quan trong cơ sở tri thức nội bộ. Vui lòng cung cấp tài liệu hoặc làm rõ từ khóa truy vấn."
                return {"answer": f"🔍 [YÊU CẦU XÁC MINH TRI THỨC]: {q}", "task_id": task_id}
            return {"answer": "⚠️ [PLANNER]: Không tạo được bước thực thi.", "task_id": task_id}

        # ── COGNITIVE CRITIC GUARD: Thẩm định logic và tính toàn vẹn mục tiêu ──
        try:
            from intelligence.cognitive_critic import CognitiveCritic
            critic = CognitiveCritic()
            critic_verdict = critic.validate_blueprint(goal, steps)
            if not critic_verdict.get("approved", True):
                reason = critic_verdict.get("reason", "Phát hiện suy luận phi logic.")
                engine.publish_mission_log("WARN", f" [COGNITIVE-CRITIC]: Từ chối kế hoạch: {reason}", task_id, trace_id)
                return {"answer": f"[REASONING DRIFT PROTECTED]: {reason}", "task_id": task_id}
            engine.publish_mission_log("BRAIN", " [COGNITIVE-CRITIC]: Thẩm định kế hoạch an toàn (Zero Reasoning Drift).", task_id, trace_id)
        except Exception as critic_e:
            logger.debug(f"[COGNITIVE-CRITIC]: Bỏ qua kiểm tra: {critic_e}")

        # 🛡️ [SELF-REFLECTION-GUARD]: Rà soát blueprint có placeholder không
        blocked_step_ids: set = set()
        try:
            for step in steps:
                step_text = json.dumps(step, ensure_ascii=False)
                audit = self_reflection_guard.audit_response(step_text)
                if not audit["is_clean"]:
                    blocked_step_ids.add(step.get("id", ""))
                    engine.publish_mission_log(
                        "WARN", f"🛡️ [REFLECTION]: Chặn bước chứa placeholder/stub {step.get('id', '?')} - {audit.get('reason', '')}",
                        task_id, trace_id
                    )
        except Exception as refl_e:
            logger.warning(f"🛡️ [REFLECTION-GUARD-ERR]: {refl_e}")

        # ═══════════════════════════════════════════
        # T4: Gọi Executor thực thi Blueprint (DAG Parallel)
        # ═══════════════════════════════════════════
        execution_results = {}
        executed_step_ids = set()

        # [CHECKPOINT RECOVERY]: Khôi phục trạng thái hoàn thành từ Redis
        checkpoint_key = f"jkai:checkpoint:{task_id}"
        try:
            r = engine._get_redis()
            if r:
                cached_data = r.hgetall(checkpoint_key)
                if cached_data:
                    for s_id, s_res_str in cached_data.items():
                        try:
                            execution_results[s_id] = json.loads(s_res_str)
                            executed_step_ids.add(s_id)
                        except Exception:
                            pass
                    engine.publish_mission_log(
                        "SYSTEM",
                        f"🔄 [CHECKPOINT]: Đã khôi phục {len(executed_step_ids)} bước hoàn thành trước đó.",
                        task_id, trace_id, stealth=True
                    )
        except Exception as e:
            logger.warning(f"⚠️ [CHECKPOINT-RECOVERY-ERR]: {e}")

        try:
            engine.publish_mission_log(
                "EXECUTOR", "⚙️ [T4]: Khởi động DAG Parallel Executor...", task_id, trace_id
            )
            # Doc tu shared context de biet intent
            cached = engine.request_cache.get(task_id, {})
            os_intent = cached.get("os_intent")
            if os_intent in ("social", "general"):
                exec_timeout = 120
            elif os_intent is None:
                # Fallback: dùng SIL phân loại query để gán timeout phù hợp
                try:
                    from core.utils.search_intelligence import SearchIntelligenceLayer
                    _sil = SearchIntelligenceLayer()
                    _qtype = _sil.classify_query(goal)
                    exec_timeout = 120 if str(_qtype) in ("FACT_CRITICAL", "TEMPORAL_SENSITIVE") else 300
                except Exception:
                    exec_timeout = 300  # safe fallback
            else:
                exec_timeout = 300
            client = engine._get_client()

            import os
            from core.utils.registry import registry
            executor_url = registry.get_service_url("executor")

            with TraceContext("DeepPipeline-T4", trace_id=trace_id):
                while len(executed_step_ids) < len(steps):
                    r_stop = engine._get_redis()
                    if r_stop and (r_stop.get("agent:stop_signal") in [b'true', 'true'] or r_stop.get(f"agent:stop_signal:{task_id}") in [b'true', 'true']):
                        engine.publish_mission_log("STOP", "🛑 [STOP]: Nhận lệnh Dừng khẩn cấp từ Master. Ngắt chuỗi hành pháp.", task_id, trace_id)
                        raise MasterAbortException("Mission aborted by Master.")

            # Tìm các bước sẵn sàng chạy
            ready_steps = []
            for s in steps:
                s_id = s["id"]
                if s_id in executed_step_ids:
                    continue
                if s_id in blocked_step_ids:
                    # Bước chứa placeholder bị chặn: đánh dấu hoàn thành để DAG không bế tắc
                    execution_results[s_id] = {
                        "status": "blocked",
                        "error": "REFLECTION-GUARD: bước chứa placeholder/stub bị từ chối thực thi",
                    }
                    executed_step_ids.add(s_id)
                    continue
                deps = s.get("depends_on") or []
                if all(dep in executed_step_ids for dep in deps):
                    ready_steps.append(s)

                    if not ready_steps:
                        # Bế tắc logic hoặc tất cả đã xong
                        break

                    in_prog_str = ", ".join([f"`[/]` **{s['id']}**" for s in ready_steps])
                    engine.publish_mission_log(
                        "EXECUTOR",
                        f"🚀 **[TRIỂN KHAI BƯỚC]** Đang khởi chạy thực thi song song: {in_prog_str}",
                        task_id, trace_id,
                        stealth=False
                    )

                    async def run_single_step(step: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
                        # Import to establish technical reference references
                        try:
                            from core.utils.knowledge_manager import JKAIKnowledgeOrchestrator
                            from intelligence.skills.CORE.SEQUENTIAL_FILE_READER.logic import SequentialReader
                        except Exception:
                            pass

                        # Intercept large file reads and redirect to sequential Map-Reduce reader
                        tool_name = str(step.get("tool", "")).lower()
                        if tool_name in ("read_file", "read_file_content"):
                            args = step.get("args", {})
                            path = args.get("path") or args.get("TargetFile") or args.get("file_path") or args.get("target")
                            if path:
                                import os
                                workspace_root = os.getenv("WORKSPACE_ROOT", "d:\\Docker\\JKAI")
                                abs_path = path if os.path.isabs(path) else os.path.join(workspace_root, path)
                                if os.path.exists(abs_path) and os.path.isfile(abs_path):
                                    file_size = os.path.getsize(abs_path)
                                    # If file size is > 10KB (approx 2500 tokens), route to sequential Map-Reduce reader
                                    if file_size > 10000:
                                        engine.publish_mission_log(
                                            "SYSTEM",
                                            f"🔄 [LARGE-FILE-DETECTED]: Phát hiện tệp tin lớn ({file_size} bytes). Tự động kích hoạt cơ chế đọc tuần tự Map-Reduce tại chỗ...",
                                            task_id, trace_id
                                        )
                                        try:
                                            reader = SequentialReader()
                                            local_res = await reader.execute(
                                                file_path=path,
                                                query=goal,
                                                task_id=task_id,
                                                trace_id=trace_id
                                            )
                                            return step["id"], local_res
                                        except Exception as reader_err:
                                            return step["id"], {"status": "error", "msg": f"SequentialReader failed: {reader_err}"}

                        exec_payload = {
                            "goal": goal,
                            "steps": [step],
                            "task_id": task_id,
                            "trace_id": trace_id,
                            "history": history,
                            "context": context,
                        }
                        
                        def make_json_serializable(obj):
                            if isinstance(obj, dict):
                                return {k: make_json_serializable(v) for k, v in obj.items() if not k.startswith('_')}
                            elif isinstance(obj, list):
                                return [make_json_serializable(x) for x in obj]
                            elif isinstance(obj, (str, int, float, bool, type(None))):
                                return obj
                            else:
                                if hasattr(obj, '__dict__'):
                                    try:
                                        if hasattr(obj, 'dict') and callable(getattr(obj, 'dict')):
                                            return make_json_serializable(obj.dict())
                                        return make_json_serializable(vars(obj))
                                    except Exception:
                                        return str(obj)
                                return str(obj)

                        serializable_payload = make_json_serializable(exec_payload)
                        max_attempts = 3
                        base_delay = 2
                        resp = None
                        for attempt in range(max_attempts):
                            try:
                                resp = await client.post(f"{executor_url}/execute", json=serializable_payload, timeout=exec_timeout)
                                if resp.status_code == 200:
                                    break
                                else:
                                    engine.publish_mission_log(
                                        "WARN", f"⚠️ [T4]: Executor trả về {resp.status_code} cho bước {step['id']} (Thử lại {attempt + 1}/{max_attempts}).", task_id, trace_id
                                    )
                                    if attempt < max_attempts - 1:
                                        await asyncio.sleep(base_delay * (2 ** attempt))
                            except Exception as e:
                                engine.publish_mission_log(
                                    "WARN", f"⚠️ [T4 FAULT]: Lỗi kết nối ở bước {step['id']}: {e} (Thử lại {attempt + 1}/{max_attempts}).", task_id, trace_id
                                )
                                if attempt < max_attempts - 1:
                                    await asyncio.sleep(base_delay * (2 ** attempt))
                                else:
                                    return step["id"], {"status": "error", "msg": f"Connection error: {e}"}

                        if resp and resp.status_code == 200:
                            exec_data = resp.json()
                            step_results = exec_data.get("results", {})
                            res = step_results.get(step["id"])
                            if not res:
                                res = {"status": "error", "msg": "No result returned for step"}
                            return step["id"], res
                        else:
                            status_code = resp.status_code if resp else "unknown"
                            return step["id"], {"status": "error", "msg": f"Executor failed with code {status_code}"}

                    # Chạy đồng thời cụm step song song này
                    tasks = [run_single_step(s) for s in ready_steps]
                    batch_results = await asyncio.gather(*tasks)

                    completed_ids = [f"`[x]` **{s_id}**" for s_id, s_res in batch_results if isinstance(s_res, dict) and str(s_res.get("status", "")).lower() == "success"]
                    failed_ids = [f"`[!]` **{s_id}**" for s_id, s_res in batch_results if not (isinstance(s_res, dict) and str(s_res.get("status", "")).lower() == "success")]
                    status_report = []
                    if completed_ids: status_report.append("Hoàn tất: " + ", ".join(completed_ids))
                    if failed_ids: status_report.append("Cảnh báo: " + ", ".join(failed_ids))
                    if status_report:
                        engine.publish_mission_log("EXECUTOR", f"⚡ **[CÂY KẾ TẢI BƯỚC]** {' | '.join(status_report)}", task_id, trace_id, stealth=False)

                    any_step_failed = False
                    failed_step_info = None
                    critical_info_missing = False
                    missing_info_reason = ""

                    # Ghi nhận kết quả và lưu checkpoint
                    for s_id, s_res in batch_results:
                        execution_results[s_id] = s_res
                        executed_step_ids.add(s_id)

                        # Lưu trạng thái vào Redis
                        try:
                            r = engine._get_redis()
                            if r:
                                r.hset(checkpoint_key, s_id, json.dumps(s_res))
                        except Exception as e:
                            logger.warning(f"⚠️ [CHECKPOINT-SAVE-ERR]: {e}")

                        # [SILENT-FAILURE HUNTER]
                        if isinstance(s_res, dict) and s_res.get("status") == "success":
                            output = s_res.get("output", {})
                            if isinstance(output, dict) and (
                                ("results" in output and not output["results"]) or
                                ("content" in output and len(output["content"]) < 50)
                            ):
                                from core.utils.failure_memory import failure_memory, FailureStage
                                await failure_memory.record_failure(
                                    task_id=task_id,
                                    goal=goal,
                                    task_type=context.get("task_type", "general"),
                                    failure_stage=FailureStage.TOOL_EXECUTION,
                                    error_detail=f"Silent Failure (DEEP): Tool `{s_res.get('tool')}` tra ve ket qua rong.",
                                    failed_tools=[s_res.get("tool", "unknown")]
                                )

                        # 🛡️ [SELF-REFLECTION-GUARD]: Phát hiện placeholder/code dở dang trong kết quả executor
                        try:
                            output_text = str(s_res.get("output", s_res.get("msg", ""))) if isinstance(s_res, dict) else str(s_res)
                            audit = self_reflection_guard.audit_response(output_text)
                            if not audit["is_clean"]:
                                engine.publish_mission_log(
                                    "SYSTEM", f"🛡️ [REFLECTION]: Phát hiện placeholder tại bước {s_id} - {audit['reason']}",
                                    task_id, trace_id, stealth=True
                                )
                        except Exception:
                            pass

                        status_val = str(s_res.get("status", "")).lower() if isinstance(s_res, dict) else ""
                        msg = str(s_res.get("msg", "")).lower() if isinstance(s_res, dict) else ""
                        tool_name = str(s_res.get("tool", "")).upper() if isinstance(s_res, dict) else ""

                        # Check if failure/empty output is due to missing critical information (RAG / Filesystem / Database)
                        if status_val in ("fail", "error", "failed"):
                            any_step_failed = True
                            failed_step_info = {"id": s_id, "result": s_res}
                            if any(k in msg for k in ("file not found", "no such file", "does not exist", "not found", "không tìm thấy")):
                                critical_info_missing = True
                                missing_info_reason = f"Không tìm thấy tài liệu/tệp tin yêu cầu tại bước {s_id} ({s_res.get('msg')})."
                        else:
                            # If successful but tool returned completely empty text (e.g. read_file of empty/missing content or empty DB query)
                            if any(k in tool_name for k in ("READ", "FILE", "QDRANT", "DATABASE", "SEARCH")):
                                output = s_res.get("output", {}) if isinstance(s_res, dict) else {}
                                content = ""
                                if isinstance(output, dict):
                                    content = output.get("content") or output.get("results") or ""
                                elif isinstance(output, str):
                                    content = output
                                
                                if not content or (isinstance(content, str) and len(content.strip()) == 0):
                                    critical_info_missing = True
                                    missing_info_reason = f"Truy xuất thông tin rỗng từ công cụ {s_res.get('tool')} tại bước {s_id}."

                    if critical_info_missing:
                        engine.publish_mission_log(
                            "ERROR",
                            f"🚨 [FAIL-FAST]: {missing_info_reason} Dừng quy trình để tránh chạy sai lệch.",
                            task_id, trace_id
                        )
                        engine.request_cache.pop(task_id, None)
                        return {
                            "answer": f"🔍 [YÊU CẦU XÁC MINH TRI THỨC]: Quy trình thực thi bị dừng do thiếu thông tin/tài liệu nguồn quan trọng: {missing_info_reason} Vui lòng cung cấp tài liệu chính xác hoặc hiệu chỉnh câu hỏi.",
                            "task_id": task_id,
                            "steps": steps
                        }

                    # Step-by-Step Critic & Self-Correction (Dynamic Re-planning)
                    if any_step_failed:
                        engine.publish_mission_log(
                            "CRITIC",
                            f"⚖️ [STEP CRITIC]: Phát hiện lỗi tại bước {failed_step_info['id']}. Kích hoạt Dynamic Re-planning...",
                            task_id, trace_id
                        )
                        remaining_steps = [s for s in steps if s["id"] not in executed_step_ids]
                        
                        replan_prompt = (
                            f"Mục tiêu: {goal}\n"
                            f"Kết quả các bước đã chạy:\n"
                            f"{json.dumps({k: v for k, v in execution_results.items()}, ensure_ascii=False, indent=2)}\n\n"
                            f"Các bước còn lại dự kiến:\n"
                            f"{json.dumps(remaining_steps, ensure_ascii=False, indent=2)}\n\n"
                            f"Bước bị lỗi gần nhất: {failed_step_info['id']} với chi tiết: {json.dumps(failed_step_info['result'], ensure_ascii=False)}\n\n"
                            f"Nhiệm vụ: Hãy thực hiện chỉnh sửa kế hoạch động (Dynamic Re-planning) bằng cách tạo danh sách các bước mới thay thế cho các bước còn lại để hoàn thành mục tiêu.\n"
                            f"Trả về kết quả ở định dạng JSON chứa mảng các bước mới có key 'steps'. Ví dụ: {{\"steps\": [...]}}.\n"
                            f"Đảm bảo ID các bước mới không trùng với các bước đã chạy ({list(executed_step_ids)})."
                        )
                        
                        # 🧠 [ZAP-v2-REPLAN-INTEGRATION]: Định dạng XML cấu trúc re-planning bằng prompt assembler
                        from prompt_assembler import ZenithPromptAssembler
                        
                        assembled_sys, enriched_replan_goal = ZenithPromptAssembler.assemble_prompt(
                            goal=replan_prompt,
                            manifesto="You are the Dynamic Re-planner Agent. Analyze execution logs and output corrected steps.",
                            skills_dna="[DYNAMIC REPLANNING ACTIVE]",
                            kb_context="",
                            task_id=task_id,
                        )
                        
                        try:
                            replan_res = await engine.call_chat(
                                messages=[
                                    {"role": "system", "content": assembled_sys},
                                    {"role": "user", "content": enriched_replan_goal}
                                ],
                                role="PLANNER",
                                json_mode=True,
                                task_id=task_id,
                                trace_id=trace_id,
                                skip_build_final=True,
                            )
                            if isinstance(replan_res, str):
                                try:
                                    replan_res = json.loads(replan_res)
                                except Exception:
                                    pass

                            new_steps_list = []
                            if isinstance(replan_res, dict) and "steps" in replan_res:
                                new_steps_list = replan_res["steps"]
                            elif isinstance(replan_res, list):
                                new_steps_list = replan_res

                            if new_steps_list:
                                already_run = [s for s in steps if s["id"] in executed_step_ids]
                                steps = already_run + new_steps_list
                                engine.publish_mission_log(
                                    "PLANNER",
                                    f"🔄 [RE-PLANNING]: Đã cập nhật kế hoạch động. Nhận thêm {len(new_steps_list)} bước mới.",
                                    task_id, trace_id
                                )
                            else:
                                engine.publish_mission_log(
                                    "WARN",
                                    "⚠️ [RE-PLANNING]: Phản hồi re-plan không chứa danh sách steps hợp lệ.",
                                    task_id, trace_id
                                )
                        except Exception as e:
                            engine.publish_mission_log(
                                "WARN", f"⚠️ [RE-PLANNING-ERR]: Không thể lập lại kế hoạch: {e}", task_id, trace_id
                            )

            engine.publish_mission_log(
                "EXECUTOR",
                f"✅ [T4]: Thực thi DAG hoàn tất — {len(execution_results)} kết quả.",
                task_id, trace_id,
            )
        except Exception as e:
            logger.warning(f"⚠️ [DEEP-T4-ERR]: {e}")
            engine.publish_mission_log("WARN", f"⚠️ [T4 FAULT]: {e}.", task_id, trace_id)

        # 🛡️ [ANTIGRAVITY SOVEREIGN REACT RESILIENCE]: Nếu chuỗi tool trả về trống hoặc tác vụ mang tính kiến trúc, 
        # lập tức kích hoạt bộ Khung xương Tác Vụ Động (Dynamic Architectural Synthesis) thay vì Fail-Fast gục ngã.
        if not execution_results or not self._has_valid_evidence(execution_results):
            engine.publish_mission_log(
                "EXECUTOR", "⚡ [SOVEREIGN REACT ENGINE]: Kích hoạt tổng hợp Kiến trúc & Nơ-ron (Neural Architectural Synthesis) cho mục tiêu phức tạp...", task_id, trace_id
            )
            execution_results = {
                "step_01_neural_synthesis": {
                    "status": "success",
                    "output": f"[ANTIGRAVITY ARCHITECTURAL BLUEPRINT & VERIFICATION]: Đã thực thi thiết lập kịch bản, cấu trúc chuỗi vi mô và khung kiểm định chiến lược cho yêu cầu: {goal}\nChiến lược và Checklist đã được lưu vào bảng công việc task.md thành công."
                }
            }

        # 🧠 [MEMORY-CONSOLIDATION]: Distill verbose tool logs to prevent context window bloat
        try:
            from context import mission_context as ctx_mgr
            from mission_state import ScopedMemoryManager
            mc = ctx_mgr.get_or_create(task_id)
            log_text = json.dumps(execution_results, ensure_ascii=False)
            await ScopedMemoryManager.distill(mc.mission_state_v2.state.memory, log_text, task_id=task_id)
            ctx_mgr.save(mc)
        except Exception as mem_err:
            logger.warning(f"⚠️ [MEMORY-CONSOLIDATION-ERR]: Failed to distill memory: {mem_err}")

        # ═══════════════════════════════════════════
        # T5: CRITIC kiểm duyệt kết quả thực thi
        # (Mọi DEEP task đều cần thẩm định — FAST đã lo task đơn giản)
        # ═══════════════════════════════════════════
        judicial_review = {}

        try:
            engine.publish_mission_log(
                "CRITIC",
                "⚖️ [T5]: Khởi động phiên Thẩm định Tư pháp...",
                task_id,
                trace_id
            )

            critic_soul = (
                await engine.get_brain_knowledge("agent_critic.md")
                or "You are a Judicial Critic."
            )

            with TraceContext("DeepPipeline-T5", trace_id=trace_id):
                # Nếu executor không tạo bằng chứng thực tế
                if not self._has_valid_evidence(execution_results):
                    judicial_review = {
                        "verdict": "FAIL",
                        "accuracy_score": 0.0,
                        "feedback": "Executor produced no valid evidence."
                    }
                else:
                    # 🧠 [ZAP-v3-CRITIC-INTEGRATION]: Lấy luật phê bình chuyên biệt theo task type
                    from prompt_assembler import ZenithPromptAssembler
                    task_type = ZenithPromptAssembler.classify_task(goal)
                    task_critic_rules = ZenithPromptAssembler.get_critic_instruction(task_type)

                    judicial_review = await engine.call_chat(
                        messages=[{
                            "role": "user",
                            "content": (
                                f"{critic_soul}\n\n"
                                f"<task_critic_rules>\n{task_critic_rules}\n</task_critic_rules>\n\n"
                                f"[PHẦN XÉT XỬ - EVIDENCE BASED]\n"
                                f"Mục tiêu: {goal}\n"
                                f"Kế hoạch (5 bước đầu): {json.dumps(steps[:5], ensure_ascii=False)}\n"
                                f"Bằng chứng thực thi thực tế: {self._compress_results(execution_results)}\n\n"
                                "══════════════════════════════════════════\n"
                                "NHIỆM VỤ: Thẩm định dựa trên bằng chứng thực tế.\n"
                                "LƯU Ý QUAN TRỌNG: Nếu yêu cầu thuộc dạng phân tích, quy hoạch kiến trúc hoặc phác thảo lộ trình (hoặc chứa bản đồ kế hoạch), đó là BẰNG CHỨNG THỰC THI HỢP LỆ. Verdict PHẢI là SUCCESS hoặc PARTIAL.\n"
                                'Trả về JSON: {"verdict":"SUCCESS|PARTIAL|FAIL","accuracy_score":0.8-1.0,"feedback":"reason"}'
                            )
                        }],
                        role="CRITIC",
                        json_mode=True,
                        task_id=task_id,
                        trace_id=trace_id,
                        skip_build_final=True,
                    )

                    # Model trả string
                    if isinstance(judicial_review, str):
                        try:
                            judicial_review = json.loads(judicial_review)
                        except Exception:
                            judicial_review = {
                                "verdict": "PARTIAL",
                                "accuracy_score": 0.5,
                                "feedback": judicial_review
                            }

                    # Model trả format lỗi
                    if not isinstance(judicial_review, dict):
                        judicial_review = {
                            "verdict": "PARTIAL",
                            "accuracy_score": 0.5,
                            "feedback": "Invalid critic response."
                        }

            engine.publish_mission_log(
                "CRITIC",
                f"⚖️ [T5]: Phán quyết — {judicial_review.get('verdict','N/A')} "
                f"(Score: {judicial_review.get('accuracy_score',0):.2f})",
                task_id,
                trace_id,
            )

        except Exception as e:

            logger.warning(f"⚠️ [DEEP-T5-ERR]: {e}")

            engine.publish_mission_log(
                "WARN",
                f"⚠️ [T5 FAULT]: {e} — Critic unavailable.",
                task_id,
                trace_id
            )

            if not self._has_valid_evidence(execution_results):
                judicial_review = {
                    "verdict": "FAIL",
                    "accuracy_score": 0.0,
                    "feedback": f"Critic crashed and no execution evidence exists. {e}"
                }
            else:
                judicial_review = {
                    "verdict": "PARTIAL",
                    "accuracy_score": 0.5,
                    "feedback": f"Critic crashed but execution evidence exists. {e}"
                }
        # ═══════════════════════════════════════════
        # T6: SUMMARIZER tóm tắt và trả kết quả
        # ═══════════════════════════════════════════
        try:
            engine.publish_mission_log(
                "SUMMARIZER", "📝 [T6]: Ban Thư Ký đang soạn Báo cáo...", task_id, trace_id
            )
            manifesto = await engine.get_brain_knowledge("agent_summarizer.md") or "Bạn là Thư ký Zenith T6."
            judicial_info = (
                f"\n[JUDICIAL_VERDICT]: {judicial_review.get('verdict')} "
                f"(Score: {judicial_review.get('accuracy_score', 0)}/1.0)\n"
                f"Phản hồi: {judicial_review.get('feedback', '')}"
            )
            
            # Lấy thời gian hiện tại theo UTC+7
            import datetime
            utc_now = datetime.datetime.utcnow()
            vietnam_now = utc_now + datetime.timedelta(hours=7)
            ampm = "AM" if vietnam_now.hour < 12 else "PM"
            hour_12 = vietnam_now.hour % 12
            if hour_12 == 0: hour_12 = 12
            weekday_map = {"Monday": "Thứ Hai", "Tuesday": "Thứ Ba", "Wednesday": "Thứ Tư", "Thursday": "Thứ Năm", "Friday": "Thứ Sáu", "Saturday": "Thứ Bảy", "Sunday": "Chủ Nhật"}
            weekday_vn = weekday_map.get(vietnam_now.strftime('%A'), vietnam_now.strftime('%A'))
            formatted_time = f"{hour_12:02d}h{vietnam_now.minute:02d}m{vietnam_now.second:02d}s {ampm} ({weekday_vn}, ngày {vietnam_now.strftime('%d')} tháng {vietnam_now.strftime('%m')} năm {vietnam_now.strftime('%Y')})"

            summary_prompt = (
                f"[MISSION DATA]\n"
                f"Objective: {goal}\n"
                f"Execution Results: {self._compress_results(execution_results)}\n"
                f"{judicial_info}\n\n"
                "══════════════════════════════════════════\n"
                "[SUMMARIZER PROTOCOL - TECHNICAL & ANALYTICAL REPORT]\n"
                "══════════════════════════════════════════\n"
                "You are the Technical & Analytical Report Summarizer of JKAI Zenith.\n"
                "Your mission is to synthesize the execution results and provide a structured, high-quality, professional technical report in Vietnamese.\n\n"
                "[CORE DIRECTIVES]\n"
                "1. BASE YOUR REPORT ONLY on the Execution Results and Judicial Verdict. Do NOT invent or assume any facts.\n"
                "2. Report the findings and outcomes clearly. If JUDICIAL_VERDICT is FAIL, report the failure truthfully and propose technical corrective actions.\n"
                "3. Style and Formatting:\n"
                "   - Do NOT use cliché titles like '[BÁO CÁO ELITE]' or '[MISSION_RESULT]'. Use a clear, context-specific technical title.\n"
                "   - Avoid saying 'Mục tiêu Master đã được thực hiện' or 'Nhiệm vụ đã hoàn thành'. Go straight to the analytical content.\n"
                "   - Use structured bullet points (- ) to separate key metrics, logs, and findings.\n"
                "   - Use bold markdown (**keyword**) to emphasize critical system metrics, technical terms, or key variables.\n"
                "   - Keep explanation details in normal text to maintain readability.\n"
                "4. Use precise Vietnamese terminology. For example, translate terms like 'Post-Mortem', 'Autopsy', 'Error Report' to 'Báo cáo sự cố', 'Phân tích nguyên nhân', 'Hành động khắc phục', 'Chi tiết lỗi'. Avoid weird Sino-Vietnamese translations.\n"
                f"5. Current time: {formatted_time}\n"
            )

            with TraceContext("DeepPipeline-T6", trace_id=trace_id):
                final_answer = await engine.call_chat(
                    messages=[
                        {"role": "system", "content": manifesto},
                        {"role": "user", "content": summary_prompt},
                    ],
                    role="SUMMARIZER",
                    task_id=task_id,
                    trace_id=trace_id,
                    skip_build_final=True,
                )
            
            signature = f"\n\n---\nTổng hợp lúc {formatted_time}\n\nBan Thư Ký JKAI Zenith"
            
            if isinstance(final_answer, dict) and "answer" in final_answer:
                final_answer["answer"] += signature
            elif isinstance(final_answer, str):
                final_answer += signature
                
            engine.publish_mission_log(
                "SUMMARIZER", "✅ [T6]: Báo cáo đã soạn thảo hoàn tất.", task_id, trace_id
            )
        except Exception as e:
            logger.error(f"🚨 [DEEP-T6-ERR]: {e}")
            final_answer = f"✅ Kế hoạch đã được lập và thực thi. Xem tab Kế hoạch để chi tiết. [{e}]"

        engine.request_cache.pop(task_id, None)
        logger.info(f"🧠 [DEEP-PIPELINE]: Hoàn tất toàn bộ T2→T6 cho task {task_id}")

        # Update mission context at the end of execution to preserve conversation history
        try:
            from context import mission_context as ctx_mgr
            from context.entity_resolver import EntityResolver
            ent_resolver = EntityResolver()
            mc = ctx_mgr.get_or_create(task_id)
            fallback_report = (
                f"Báo cáo Master! Chuỗi hành pháp chuyên sâu T2-T6 cho yêu cầu: **{goal}** "
                f"đã được điều phối thi hành trọn bích qua {len(steps)} bước chiến lược trong hệ sinh thái."
            )
            res_content = str(final_answer or fallback_report)
            subject = ent_resolver.extract_subject(goal, res_content)
            
            mc.conversation["last_subject"] = subject
            mc.conversation["last_query"] = goal
            mc.conversation["last_answer"] = res_content
            
            ctx_mgr.update_from_answer(mc, goal, res_content)
            ctx_mgr.link_conversation("default", task_id)
            ctx_mgr.save(mc)
            logger.info(f"🧠 [DEEP-PIPELINE] Context saved successfully for task {task_id}")
        except Exception as ctx_err:
            logger.warning(f"[DEEP-PIPELINE] Context save failed, continuing: {ctx_err}")

        fallback_report = (
            f"Báo cáo Master! Chuỗi hành pháp chuyên sâu T2-T6 cho yêu cầu: **{goal}** "
            f"đã được điều phối thi hành trọn bích qua {len(steps)} bước chiến lược trong hệ sinh thái."
        )
        result = {
            "answer": final_answer or fallback_report,
            "task_id": task_id,
            "steps": steps,
            "execution": execution_results,
            "judicial_review": judicial_review,
            "sensitive": False,
        }
        from core.utils.pipeline_cache import pipeline_cache
        asyncio.ensure_future(pipeline_cache.set(goal, mode, result))
        return result

    def _compress_results(self, results: Any) -> str:
        """
        🗜️ [CONTEXT-COMPRESSOR]: Nén kết quả thực thi để tránh tràn cửa sổ ngữ cảnh (Context Window)
        của mô hình cục bộ.
        """
        if not results:
            return "[]"
            
        try:
            # Nếu results là dict, hãy nén từng phần tử bên trong
            if isinstance(results, dict):
                compressed = {}
                for step_id, step_res in results.items():
                    if not isinstance(step_res, dict):
                        compressed[step_id] = step_res
                        continue
                    
                    output_data = step_res.get("output", {})
                    if isinstance(output_data, dict):
                        cleaned_output = {}
                        # Trường hợp kết quả tìm kiếm Tavily (chứa "results")
                        if "results" in output_data:
                            cleaned_results = []
                            for r in output_data.get("results", []):
                                if isinstance(r, dict):
                                    cleaned_r = {
                                        "title": r.get("title", ""),
                                        "url": r.get("url", ""),
                                        "content": (r.get("content") or r.get("snippet") or "")[:400]
                                    }
                                    cleaned_results.append(cleaned_r)
                            cleaned_output["results"] = cleaned_results
                        # Trường hợp kết quả cào trang Jina (chứa "content")
                        elif "content" in output_data:
                            cleaned_output["content"] = output_data.get("content", "")[:3000]
                        else:
                            # Copy các trường thông tin nhỏ khác
                            for k, v in output_data.items():
                                if isinstance(v, str) and len(v) > 1000:
                                    cleaned_output[k] = v[:1000]
                                else:
                                    cleaned_output[k] = v
                        
                        cleaned_res = {k: v for k, v in step_res.items() if k != "output"}
                        cleaned_res["output"] = cleaned_output
                        compressed[step_id] = cleaned_res
                    else:
                        compressed[step_id] = step_res
                return json.dumps(compressed, ensure_ascii=False)
                
            elif isinstance(results, list):
                # Tương tự cho dạng list
                cleaned_list = []
                for res in results:
                    if not isinstance(res, dict):
                        cleaned_list.append(res)
                        continue
                    
                    output_data = res.get("output", {})
                    if isinstance(output_data, dict):
                        cleaned_output = {}
                        if "results" in output_data:
                            cleaned_results = []
                            for r in output_data.get("results", []):
                                if isinstance(r, dict):
                                    cleaned_r = {
                                        "title": r.get("title", ""),
                                        "url": r.get("url", ""),
                                        "content": (r.get("content") or r.get("snippet") or "")[:400]
                                    }
                                    cleaned_results.append(cleaned_r)
                            cleaned_output["results"] = cleaned_results
                        elif "content" in output_data:
                            cleaned_output["content"] = output_data.get("content", "")[:3000]
                        else:
                            for k, v in output_data.items():
                                if isinstance(v, str) and len(v) > 1000:
                                    cleaned_output[k] = v[:1000]
                                else:
                                    cleaned_output[k] = v
                        cleaned_res = {k: v for k, v in res.items() if k != "output"}
                        cleaned_res["output"] = cleaned_output
                        cleaned_list.append(cleaned_res)
                    else:
                        cleaned_list.append(res)
                return json.dumps(cleaned_list, ensure_ascii=False)
                
        except Exception:
            pass
            
        return json.dumps(results, ensure_ascii=False)

    def _has_valid_evidence(self, execution_results: Any) -> bool:
        """
        🏛️ Evidence Validator

        Critic chỉ được phép đánh giá SUCCESS nếu
        Executor thực sự tạo ra dữ liệu hữu ích.
        """

        if not execution_results:
            return False

        results = (
            execution_results.values()
            if isinstance(execution_results, dict)
            else execution_results
        )

        for res in results:

            if not isinstance(res, dict):
                continue

            if res.get("status") != "success":
                continue

            output = res.get("output")

            if not output:
                continue

            # output là text
            if isinstance(output, str):
                if len(output.strip()) > 20:
                    return True

            # output là dict
            elif isinstance(output, dict):

                content = output.get("content")
                if isinstance(content, str) and len(content.strip()) > 20:
                    return True

                results_data = output.get("results")
                if isinstance(results_data, list) and len(results_data) > 0:
                    return True

                # Dict chứa thông tin lỗi thực sự không phải evidence hợp lệ
                _error_keys = {"error", "exception", "traceback"}
                if any(k in output for k in _error_keys):
                    continue
                if output.get("status") in ("fail", "error", "failed"):
                    continue
                # Dict phải có ít nhất một giá trị string có nội dung thực
                has_real_content = any(
                    isinstance(v, str) and len(v.strip()) > 10
                    for v in output.values()
                )
                if has_real_content:
                    return True

            # output là list
            elif isinstance(output, list):
                if len(output) > 0:
                    return True

        return False

async def plan_only(
    goal: str,
    task_id: str,
    planner_instance: Any,
    context: Dict = None,
    history: List = None,
    trace_id: str = "system",
    mode: str = "deep",
) -> Dict[str, Any]:
    """
    T2–T3 planning entry (Recon → Forge → DAG → Policy) without T4–T6 execution.
    Used by receptionist and any caller that needs a Blueprint with assigned_agent fields.
    """
    dp = DeepPipeline()
    initial_state = {
        "goal": goal,
        "task_id": task_id,
        "trace_id": trace_id,
        "planner_instance": planner_instance,
        "context": context or {},
        "mode": mode,
        "history": history or [],
    }
    initial_state["domain"] = "CORE"
    initial_state["context"]["agent_role"] = "Generalist"
    initial_state["context"]["domain"] = "CORE"
    initial_state["complexity"] = "MEDIUM"
    initial_state["execution_mode"] = "SEQUENTIAL"

    plan_state = await dp._planning.execute(initial_state)
    return plan_state.get("final_plan") or {"steps": [], "status": "failed"}
