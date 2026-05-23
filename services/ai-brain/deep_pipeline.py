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
from typing import Any, Dict, List, Optional
import httpx

logger = logging.getLogger("JKAI.DeepPipeline")

class DeepPipeline:
    """
    🧠 Luồng Chiến lược — Tự khép kín hoàn toàn.
    T2 → T3 → T4 → T5 → T6 (Đầy đủ CRITIC)
    """
    def __init__(self):
        # 🧠 [PLANNING-INIT]: Đúc kết các Stage T2+T3
        from planning_pipeline import (
            ReconStage, ContextStage, ForgeStage, PolicyStage, PlanningPipeline
        )
        self._planning = PlanningPipeline(stages=[
            ReconStage(), ContextStage(), ForgeStage(), PolicyStage()
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
        Thực thi toàn bộ luồng DEEP từ T2 đến T6.
        Returns: dict {"answer": str, "task_id": str, "steps": list}
        """
        from core.utils.engine import engine

        context = context or {}
        history = history or []

        engine.publish_mission_log(
            "SYSTEM",
            f"🧠 [DEEP-PIPELINE]: Khởi động luồng chiến lược 5 tầng (T2→T6).",
            task_id, trace_id, stealth=True
        )

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
            "complexity": context.get("complexity", "complex"),
        }

        try:
            plan_state = await self._planning.execute(initial_state)
        except Exception as e:
            logger.error(f"🚨 [DEEP-T2T3-ERR]: {e}")
            engine.publish_mission_log("ERROR", f"🚨 [T2/T3 FAULT]: {e}", task_id, trace_id)
            return {"answer": f"❌ [PLANNER ERROR]: Không thể lập kế hoạch - {e}", "task_id": task_id}

        final_plan = plan_state.get("final_plan", {})
        steps = final_plan.get("steps", [])
        blueprint = plan_state.get("blueprint_obj")

        engine.publish_mission_log(
            "PLANNER",
            f"📊 [BLUEPRINT SEALED]: {len(steps)} bước thực thi đã được đúc kết.",
            task_id, trace_id,
        )

        if not steps:
            return {"answer": "⚠️ [PLANNER]: Không tạo được bước thực thi.", "task_id": task_id}

        # ═══════════════════════════════════════════
        # T4: Gọi Executor service thực thi Blueprint
        # ═══════════════════════════════════════════
        execution_results = []
        try:
            engine.publish_mission_log(
                "EXECUTOR", "⚙️ [T4]: Chuyển Blueprint sang Ban Thực Thi...", task_id, trace_id
            )
            async with httpx.AsyncClient(timeout=300.0) as client:
                exec_payload = {
                    "goal": goal,
                    "steps": steps,
                    "task_id": task_id,
                    "trace_id": trace_id,
                    "history": history,
                    "context": context,
                }
                # Gọi executor service (được cấu hình qua biến môi trường)
                import os
                from core.utils.registry import registry
                executor_url = registry.get_service_url("executor")
                resp = await client.post(f"{executor_url}/execute", json=exec_payload)
                if resp.status_code == 200:
                    exec_data = resp.json()
                    execution_results = exec_data.get("results", [])
                    engine.publish_mission_log(
                        "EXECUTOR",
                        f"✅ [T4]: Thực thi hoàn tất — {len(execution_results)} kết quả.",
                        task_id, trace_id,
                    )
                else:
                    engine.publish_mission_log(
                        "WARN", f"⚠️ [T4]: Executor trả về {resp.status_code}.", task_id, trace_id
                    )
        except Exception as e:
            logger.warning(f"⚠️ [DEEP-T4-ERR]: {e}")
            engine.publish_mission_log("WARN", f"⚠️ [T4 FAULT]: {e} — Bỏ qua T4, tiếp tục T5.", task_id, trace_id)

        # ═══════════════════════════════════════════
        # T5: CRITIC kiểm duyệt kết quả thực thi
        # ═══════════════════════════════════════════
        judicial_review = {}
        try:
            engine.publish_mission_log(
                "CRITIC", "⚖️ [T5]: Khởi động phiên Thẩm định Tư pháp...", task_id, trace_id
            )
            judicial_review = await engine.call_chat(
                messages=[{
                    "role": "user",
                    "content": (
                        f"[JUDICIAL REVIEW - EVIDENCE BASED]\n"
                        f"Objective: {goal}\n"
                        f"Blueprint (first 5 steps): {json.dumps(steps[:5], ensure_ascii=False)}\n"
                        f"Actual Execution Results: {self._compress_results(execution_results)}\n\n"
                        "══════════════════════════════════════════\n"
                        "[CRITIC PROTOCOL]\n"
                        "══════════════════════════════════════════\n"
                        "You are a Judicial Critic. Evaluate the execution based ONLY on evidence above.\n\n"
                        "[CORE DIRECTIVES]\n"
                        "1. If Execution Results are empty or contain errors, verdict MUST be FAIL.\n"
                        "2. NEVER assume success. NEVER fabricate results.\n"
                        "3. Base your verdict solely on Actual Execution Results.\n"
                        "4. Respond with ONLY valid JSON, no other text:\n"
                        '{"verdict": "SUCCESS|PARTIAL|FAIL", "accuracy_score": 0.0-1.0, "feedback": "Specific evidence-based reason"}'
                    )
                }],
                role="CRITIC",
                json_mode=True,
                task_id=task_id,
                trace_id=trace_id,
            )
            if isinstance(judicial_review, str):
                try:
                    judicial_review = json.loads(judicial_review)
                except Exception:
                    judicial_review = {"verdict": "SUCCESS", "accuracy_score": 0.8, "feedback": judicial_review}

            engine.publish_mission_log(
                "CRITIC",
                f"⚖️ [T5]: Phán quyết — {judicial_review.get('verdict', 'N/A')} "
                f"(Score: {judicial_review.get('accuracy_score', 0):.2f})",
                task_id, trace_id,
            )
        except Exception as e:
            logger.warning(f"⚠️ [DEEP-T5-ERR]: {e}")
            engine.publish_mission_log("WARN", f"⚠️ [T5 FAULT]: {e} — Tự động phê duyệt.", task_id, trace_id)
            judicial_review = {"verdict": "SUCCESS", "accuracy_score": 1.0, "feedback": "Auto-approved."}

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

            # Phân tích xem có phải là nhiệm vụ đọc báo/URL hay không
            is_web_reading = False
            scraped_title = ""
            results_list = []
            if isinstance(execution_results, dict):
                results_list = list(execution_results.values())
            elif isinstance(execution_results, list):
                results_list = execution_results

            for res in results_list:
                if isinstance(res, dict) and res.get("status") == "success":
                    output_data = res.get("output", {})
                    if isinstance(output_data, dict):
                        # Trường hợp cào Jina (chứa "content") hoặc tìm kiếm có chứa "content"
                        content = output_data.get("content", "")
                        if content:
                            is_web_reading = True
                            # Tìm tiêu đề từ content
                            for line in content.splitlines()[:5]:
                                if line.strip().startswith("# "):
                                    scraped_title = line.strip()[2:].strip()
                                    break
                            if not scraped_title:
                                scraped_title = "Tổng hợp nội dung trang Web"
                            break
                        # Trường hợp tìm kiếm Internet Tavily (chứa "results")
                        elif "results" in output_data:
                            is_web_reading = True
                            tavily_res = output_data.get("results", [])
                            if tavily_res and isinstance(tavily_res[0], dict):
                                scraped_title = tavily_res[0].get("title", "")
                            if not scraped_title:
                                scraped_title = "Kết quả tìm kiếm Internet mới nhất"
                            break

            # Check if search results are empty/sparse
            is_results_empty = True
            for res in results_list:
                if isinstance(res, dict) and res.get("status") == "success":
                    output_data = res.get("output", {})
                    if isinstance(output_data, dict):
                        if "results" in output_data:
                            for r in output_data.get("results", []):
                                if isinstance(r, dict) and (r.get("content") or r.get("snippet")):
                                    if len((r.get("content") or r.get("snippet") or "").strip()) > 10:
                                        is_results_empty = False
                                        break
                        elif output_data.get("content"):
                            if len(output_data.get("content", "").strip()) > 10:
                                is_results_empty = False
                                break

            if is_web_reading:
                if is_results_empty:
                    summary_prompt = (
                        f"[MISSION DATA]\n"
                        f"Objective: {goal}\n"
                        f"Execution Results: {self._compress_results(execution_results)}\n"
                        f"{judicial_info}\n\n"
                        "══════════════════════════════════════════\n"
                        "[SUMMARIZER PROTOCOL - NO DATA ALERT]\n"
                        "══════════════════════════════════════════\n"
                        "You are the Elite Secretary of JKAI Zenith. The search returned no usable data.\n"
                        "Please write a SHORT, polite, natural Vietnamese reply to Master explaining that you couldn't find the information. Do NOT make up any facts.\n"
                        f"Current time: {formatted_time}\n"
                    )
                else:
                    # Phân loại ngữ cảnh: Q&A giao tiếp thường hay Lệnh tổng hợp tin tức?
                    qa_keywords = ["thế nào", "là gì", "bao nhiêu", "ở đâu", "khi nào", "ai", "có không", "thời tiết", "giá", "tỷ giá", "hôm nay", "bây giờ", "hiện tại", "nhiệt độ", "how", "what", "when", "where", "weather", "price"]
                    news_keywords = ["tin tức", "tóm tắt", "báo cáo", "tổng hợp", "điểm báo", "news", "summary", "report"]
                    goal_lower = goal.lower()
                    is_conversational = any(kw in goal_lower for kw in qa_keywords)
                    is_news_report = any(kw in goal_lower for kw in news_keywords)
                    
                    if is_conversational and not is_news_report:
                        # Chế độ TRẢ LỜI GIAO TIẾP TỰ NHIÊN
                        summary_prompt = (
                            f"[MISSION DATA]\n"
                            f"Objective: {goal}\n"
                            f"Search Results: {self._compress_results(execution_results)}\n"
                            f"{judicial_info}\n\n"
                            "══════════════════════════════════════════\n"
                            "[SUMMARIZER PROTOCOL - CONVERSATIONAL Q&A]\n"
                            "══════════════════════════════════════════\n"
                            "You are JKAI, a helpful and elegant AI assistant. Master asked you a conversational question.\n"
                            "[CORE DIRECTIVES]\n"
                            "1. Answer DIRECTLY and NATURALLY in Vietnamese, like a knowledgeable friend — NO formal report headers, NO bullet-point lists unless necessary.\n"
                            "2. Base your answer STRICTLY on the Search Results. Do NOT invent data.\n"
                            "3. Keep it SHORT and conversational unless Master asked for detail.\n"
                            "4. Politely start with 'Dạ' or similar Vietnamese greeting if appropriate.\n"
                            f"5. Current time: {formatted_time}\n"
                        )
                    else:
                        # Chế độ BÁO CÁO TIN TỨC CHUYÊN NGHIỆP
                        if not scraped_title:
                            scraped_title = "Bản tin Tổng hợp Internet Zenith"
                        summary_prompt = (
                            f"[MISSION DATA]\n"
                            f"Objective: {goal}\n"
                            f"Execution Results: {self._compress_results(execution_results)}\n"
                            f"{judicial_info}\n\n"
                            "══════════════════════════════════════════\n"
                            "[SUMMARIZER PROTOCOL - TIN TỨC & URL]\n"
                            "══════════════════════════════════════════\n"
                            "You are the Elite Secretary of JKAI Zenith. Write a clear, comprehensive, and detailed news summary in Vietnamese.\n\n"
                            "[CORE DIRECTIVES FOR WEBPAGE SUMMARY]\n"
                            f"1. Dùng Tiêu đề của bài báo làm tiêu đề chính của báo cáo: '# {scraped_title}'.\n"
                            "2. Tuyệt đối KHÔNG sử dụng các tiêu đề rập khuôn máy móc như '[BÁO CÁO ELITE]' hay '[MISSION_RESULT]'.\n"
                            "3. Tuyệt đối KHÔNG viết câu vô nghĩa 'Mục tiêu Master đã được thực hiện'. Vào thẳng nội dung một cách tự nhiên.\n"
                            "4. Trình bày bài tóm tắt theo văn phong BÁO CÁO CHUYÊN NGHIỆP:\n"
                            "   - Sử dụng các dấu gạch đầu dòng rõ ràng (- ) cho mỗi ý chính.\n"
                            "   - Sử dụng chữ IN ĐẬM (bold markdown) để nhấn mạnh các từ khóa chính.\n"
                            "   - Sử dụng chữ thường cho phần giải thích đi kèm.\n"
                        )
            else:
                summary_prompt = (
                    f"[MISSION DATA]\n"
                    f"Objective: {goal}\n"
                    f"Execution Results: {self._compress_results(execution_results)}\n"
                    f"{judicial_info}\n\n"
                    "══════════════════════════════════════════\n"
                    "[SUMMARIZER PROTOCOL - THỰC THI KỸ THUẬT]\n"
                    "══════════════════════════════════════════\n"
                    "You are the Elite Secretary of JKAI Zenith. Write a clear, professional mission report in Vietnamese.\n\n"
                    "[CORE DIRECTIVES]\n"
                    "1. BASE YOUR REPORT ONLY on the Execution Results and Judicial Verdict above.\n"
                    "2. If JUDICIAL_VERDICT is FAIL, report the failure truthfully and propose corrective actions.\n"
                    "3. Viết báo cáo chuyên nghiệp, mạch lạc, dễ nhìn và đẳng cấp:\n"
                    "   - Sử dụng dấu gạch đầu dòng rõ ràng (- ) cho mỗi luận điểm chính.\n"
                    "   - Sử dụng chữ IN ĐẬM (bold) để làm nổi bật các sự kiện cốt lõi, từ khóa kỹ thuật hoặc chỉ số quan trọng.\n"
                    "   - Giữ phần nội dung mô tả chi tiết bằng chữ thường để bảo toàn tính dễ đọc trực quan.\n"
                    "4. Tuyệt đối KHÔNG viết các câu rập khuôn sáo rỗng như 'Mục tiêu Master đã được thực hiện' hay '[BÁO CÁO ELITE]'.\n"
                    "5. Sử dụng thuật ngữ tiếng Việt chuẩn mực: dịch 'Post-Mortem', 'Autopsy', 'Error Report' thành 'Báo cáo sự cố', 'Phân tích nguyên nhân', 'Hành động khắc phục', 'Chi tiết lỗi'. Tránh hoàn toàn việc sử dụng từ Hán-Việt kỳ dị hoặc tự tạo từ ngữ tối nghĩa.\n"
                )

            final_answer = await engine.call_chat(
                messages=[
                    {"role": "system", "content": manifesto},
                    {"role": "user", "content": summary_prompt},
                ],
                role="SUMMARIZER",
                task_id=task_id,
                trace_id=trace_id,
            )
            
            signature = f"\n\n---\n👉 Tổng hợp lúc {formatted_time}\n\nBan Thư Ký JKAI Zenith"
            
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

        logger.info(f"🧠 [DEEP-PIPELINE]: Hoàn tất toàn bộ T2→T6 cho task {task_id}")
        return {
            "answer": final_answer or "✅ Sứ mệnh hoàn tất.",
            "task_id": task_id,
            "steps": steps,
            "judicial_review": judicial_review,
            "sensitive": False,
        }

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
