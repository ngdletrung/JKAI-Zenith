import asyncio
import logging
import copy
import time
import os
from typing import Any, Dict, List, Optional
from pydantic import BaseModel
from core.utils.engine import engine

logger = logging.getLogger("JKAI.PlanningPipeline")

class PlanningStage:
    """Base class cho các nơ-ron lập kế hoạch."""
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

class ReconStage(PlanningStage):
    """Trinh sát thực địa và kỹ năng."""
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            goal = state["goal"]
            task_id = state["task_id"]
            trace_id = state.get("trace_id", "system")
            planner = state["planner_instance"]
            
            engine.publish_progress(10, "🔍 [T2: CONTEXT] Đang trinh sát thực địa và kỹ năng...", "recon", task_id, trace_id)
            
            # 1. Skill DNA Recon
            domain = state.get("domain", "GENERAL")
            skill_dna, top_k_ids = await planner._recon_skills(goal, "", task_id, domain)
            state["skill_dna"] = skill_dna
            state["top_k_ids"] = top_k_ids
            
            # 2. Failure Memory Pre-flight
            from core.utils.failure_memory import failure_memory
            task_type = state.get("context", {}).get("task_type", "general")
            pre_flight = await failure_memory.pre_flight_check(goal, task_type)
            state["pre_flight"] = pre_flight
            
            return state
        except Exception as e:
            engine.publish_mission_log("ERROR", f"🚨 [STAGE-FAULT]: ReconStage thất bại - {str(e)}", state.get("task_id", "sys"), state.get("trace_id", "system"))
            raise e

class ContextStage(PlanningStage):
    """Nạp bối cảnh nhất thể + KB retrieval song song (zero latency overhead)."""
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        import asyncio as _asyncio  # [HOT-RELOAD-SAFE]: import tường minh tránh NameError khi StatReload
        try:
            planner = state["planner_instance"]
            goal = state["goal"]
            task_id = state["task_id"]
            trace_id = state.get("trace_id", "system")

            engine.publish_progress(20, "🌌 [T2: CONTEXT] Đang đồng hóa tri thức, bối cảnh và KB Qdrant...", "context", task_id, trace_id)

            complexity = state.get("complexity", "complex")

            attempt = state.get("attempt", 0)
            if attempt == 0:
                top_k = 5
                expansion_radius = 1000
            elif attempt == 1:
                top_k = 3
                expansion_radius = 3000
            else:
                top_k = 2
                expansion_radius = 6000

            async def _safe_kb_retrieve():
                try:
                    return await planner.orchestrator.smart_retrieve(
                        goal, task_id, top_k=top_k, expansion_radius=expansion_radius
                    )
                except Exception as kb_err:
                    logger.warning("[ContextStage] smart_retrieve failed (non-fatal): %s", kb_err)
                    return {}

            neural_context, kb_intel = await _asyncio.gather(
                planner._prepare_neural_context(goal, task_id, complexity),
                _safe_kb_retrieve(),
            )

            # Gắn KB data vào neural_context để ForgeStage dùng
            kb_ctx = (kb_intel or {}).get("context", "").strip()
            structured = (kb_intel or {}).get("structured", [])
            # Lọc các chunk có score >= 0.45 (loại bỏ noise)
            structured = [d for d in structured if d.get("score", 0) >= 0.45]
            high_quality = [d for d in structured if d.get("score", 0) >= 0.72]

            # 🛡️ Anti-Hallucination Firewall: Chỉ giữ kb_context nếu có ít nhất 1 chunk chất lượng cao (>=0.72)
            # Tránh rác bối cảnh rò rỉ làm nghiêng lệch mô hình PLANNER với các truy vấn chung
            if len(high_quality) > 0:
                neural_context["kb_context"] = kb_ctx
            else:
                neural_context["kb_context"] = ""

            neural_context["kb_structured"] = structured
            neural_context["kb_sufficient"] = (
                len(high_quality) >= 2 and len(kb_ctx) >= 200
            )
            neural_context["kb_high_quality_count"] = len(high_quality)

            if kb_ctx:
                engine.publish_mission_log(
                    "BRAIN",
                    f"📚 [KB-RETRIEVED]: {len(structured)} chunks (≥0.45), {len(high_quality)} high-quality (≥0.72). "
                    f"Sufficient={neural_context['kb_sufficient']}",
                    task_id, trace_id, stealth=True
                )
            else:
                engine.publish_mission_log(
                    "BRAIN", "📭 [KB-EMPTY]: Không tìm thấy tài liệu liên quan trong Qdrant.",
                    task_id, trace_id, stealth=True
                )

            state["neural_context"] = neural_context
            return state
        except Exception as e:
            engine.publish_mission_log("ERROR", f"🚨 [STAGE-FAULT]: ContextStage thất bại - {str(e)}", state.get("task_id", "sys"), state.get("trace_id", "system"))
            raise e


class ForgeStage(PlanningStage):
    """Đúc kết Blueprint qua LLM (Đã tối ưu hóa Escalation & Schema Firewall)."""
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        planner = state["planner_instance"]
        goal = state["goal"]
        context = state["context"]
        mode = state["mode"]
        task_id = state["task_id"]
        trace_id = state.get("trace_id", "system")
        
        engine.publish_progress(40, "⚒️ [T3: FORGE] Đang đúc kết Blueprint chiến lược...", "forge", task_id, trace_id)
        
        skill_dna = state.get("skill_dna", "[SKILL DNA]: Auto web search enabled.")
        neural_context = state.get("neural_context", {})

        # [SMART-GATE]: KB sufficient + LOOKUP/CHAT → skip LLM forge, use web search directly
        nc = neural_context if isinstance(neural_context, dict) else {}
        kb_sufficient = nc.get("kb_sufficient", False)
        kb_context = nc.get("kb_context", "").strip()
        if kb_sufficient and kb_context:
            from prompt_assembler import ZenithPromptAssembler
            task_type = ZenithPromptAssembler.classify_task(goal)
            if task_type in ("LOOKUP", "CHAT"):
                engine.publish_mission_log(
                    "FORGE",
                    f"⚡ [SMART-GATE]: KB sufficient + task={task_type}. Skip LLM forge, answer from KB.",
                    task_id, trace_id, stealth=True
                )
                from planner import Blueprint, PlanStep, HardwareTarget
                blueprint = Blueprint(
                    thought=f"KB already sufficient for {task_type} task. Search with KB context.",
                    optimization_review="Single search step — no complex planning needed.",
                    steps=[
                        PlanStep(
                            id="step_01",
                            tool="SEARCH_WEB_GLOBAL",
                            args={"query": goal},
                            description=f"Search web for: {goal[:120]}",
                            assigned_agent="agent_executor_beta.md",
                            hardware_target=HardwareTarget.BETA,
                            expert_mindset=f"KB Context:\n{kb_context[:2500]}\n\nAnswer based on KB data above. Search web only if needed.",
                            verification="Found answer from KB or web search."
                        )
                    ],
                    rationale="KB context has relevant data. Search to verify or supplement.",
                    failure_speculation="KB data may be outdated.",
                    ambiguous=False,
                    complexity_score=1,
                    estimated_duration="10-20s",
                    team_pattern="single",
                    recommended_critic=False,
                )
                state["blueprint_obj"] = blueprint
                state["raw_blueprint"] = blueprint.model_dump()
                return state

        specialist_prompt = await planner._forge.forge_specialist_prompt(
            goal=goal,
            context=context,
            skills_summary=skill_dna,
            fast_mode=(mode == "fast"),
            task_id=task_id
        )

        from planner import _FEW_SHOT_EXAMPLES
        agent_role = context.get("agent_role") if isinstance(context, dict) else None
        
        # 🧠 [ZAP-v2-INTEGRATION]: Lắp ráp Prompt thông minh qua ZenithPromptAssembler
        from prompt_assembler import ZenithPromptAssembler
        
        kb_ctx = nc.get("kb_context", "").strip()
        kb_sufficient = nc.get("kb_sufficient", False)
        kb_hq_count = nc.get("kb_high_quality_count", 0)
        
        # 1. Sinh cấu trúc prompt & goal từ Assembler
        assembled_sys, enriched_goal = ZenithPromptAssembler.assemble_prompt(
            goal=goal,
            manifesto=nc.get("manifesto", ""),
            skills_dna=skill_dna,
            kb_context=kb_ctx,
            kb_sufficient=kb_sufficient
        )
        
        # 2. Xây dựng specialist prompt nền của Planner
        base_sys = planner._build_system_prompt(
            "",
            specialist_prompt,
            "",
            nc.get("level", "medium"),
            nc.get("budget", 5),
            False,
            "",
        )
        
        # 3. Hợp nhất kiến trúc: Antigravity Sovereign Lean Skeleton (Khung xương Nơ-ron Đẳng cấp Antigravity)
        system_prompt = (
            f"<sovereign_identity>\nYou are JKAI Zenith Sovereign Planner (Antigravity Architecture), engineered by Master LeeTrung. Your focus is architecting precise, lean execution steps.\n</sovereign_identity>\n\n"
            f"<executive_runtime_rules>\n{base_sys}\n</executive_runtime_rules>\n\n"
            f"<antigravity_orientation>\n"
            f"CRITICAL INSTRUCTION 1: Ưu tiên tuyệt đối tốc độ phản xạ và sự rõ ràng kiến trúc! Mọi trường JSON (description, expert_mindset, verification) BẮT BUỘC súc tích dưới 25 từ.\n"
            f"CRITICAL INSTRUCTION 2: Sinh tối đa 3-5 bước milestone chiến lược trong checklist động (task.md), không lan man dư thừa.\n"
            f"CRITICAL INSTRUCTION 3: CHỈ sử dụng các công cụ trong danh sách hợp lệ: BROWSER_CONTROL, OMNI_SEARCH_ENGINE, SEARCH_WEB_GLOBAL, CODE_EXECUTION, READ_FILE, REWRITE_FILE, VIEW_FILE, PYTHON_REPL, SYSTEM_CMD, FILESYSTEM, DOCKER, LLM_ANALYSIS, BASH, EXECUTE_COMMAND.\n"
            f"</antigravity_orientation>"
        )

        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": enriched_goal}]
        
        # 🛡️ [RETRY-ESCALATION-STRATEGY]: Tự tăng bậc ràng buộc khi gặp lỗi
        for attempt in range(1, 4):
            current_role = "PLANNER" if attempt == 1 else "RESERVE_AGENT"
            
            if attempt == 2:
                messages.append({
                    "role": "user",
                    "content": (
                        "⚠️ [ESCALATION]: Bước trước không phải JSON Object hợp lệ. "
                        "Bạn PHẢI trả về một JSON OBJECT (không phải Array) với cấu trúc chính xác: "
                        '{"thought": "<string>", "pre_computation_reflection": "<string>", "steps": [{"id": "step_01", "tool": "<valid_tool_id>", "args": {}, "description": "<string>", "assigned_agent": "agent_executor_alpha.md", "hardware_target": "ALPHA", "expert_mindset": "<string>", "verification": "<string>"}], '
                        '"rationale": "<string>", "failure_speculation": "<string>", "ambiguous": false}. '
                        "Không có markdown, không có giải thích bên ngoài JSON."
                    )
                })
            elif attempt == 3:
                messages.append({
                    "role": "user",
                    "content": "⚠️ [EMERGENCY-COMPACT]: Deep JSON decoding failure. Return ONLY a minified JSON containing keys: 'thought' (string) and 'steps' (a simple array of execution step objects)."
                })
            
            engine.publish_mission_log(
                "INFO", 
                f"🧠 [PLANNER-ATTEMPT-{attempt}]: Đang đúc kết chiến lược bằng vai trò `{current_role}`...", 
                task_id, 
                trace_id
            )
            
            start_time = time.time()
            # [FIX-ARCH]: Truyền schema=Blueprint.model_json_schema() giống generate_plan()
            # để model biết chính xác format cần trả về thay vì tự đoán
            from planner import Blueprint as _BlueprintSchema
            schema = _BlueprintSchema.model_json_schema() if attempt < 3 else None
            
            # 🛡️ [DYNAMIC TOOL ENUM]: Build schema dynamically
            if schema:
                try:
                    available_tools = state.get("top_k_ids", [])
                    if not available_tools:
                        skills_dict = await planner.orchestrator.get_all_skills_dict()
                        available_tools = [k.upper() for k in skills_dict.keys()][:10]
                    planner._inject_plan_schema_enums(schema, available_tools)
                except Exception as e:
                    logger.debug(f"[DYNAMIC-SCHEMA] ForgeStage failed to inject enum: {e}")

            try:
                raw_res = await asyncio.wait_for(
                    engine.call_chat(
                        messages,
                        role=current_role,
                        schema=None, # 🚀 [SPEED-LIBERATION]: Giải phóng trần tạo token tự do (tránh nghẽn Constrained Decoding)
                        json_mode=True if attempt < 3 else False,
                        format="json" if attempt < 3 else None,
                        task_id=task_id,
                        trace_id=trace_id,
                        skip_build_final=True,
                    ),
                    timeout=240.0 # 🛡️ [DYNAMIC-TIMEOUT]: Cho phép thời gian suy luận rộng rãi cho các task kiến trúc phức tạp
                )
            except asyncio.TimeoutError:
                logger.warning(f"⚠️ [FORGE-ATTEMPT-{attempt}-TIMEOUT]: Model `{current_role}` timed out after 240s. Chuyển sang trạm nơ-ron kế tiếp...")
                if attempt < 3:
                    continue
                raise
            latency = time.time() - start_time
            engine.publish_mission_log("LATENCY", f"⏱️ [FORGE-ATTEMPT-{attempt}]: Model `{current_role}` response time: {round(latency, 2)}s.", task_id, trace_id)
            
            try:
                if not raw_res: raise ValueError("AI trả về chuỗi rỗng.")
                
                # 🔄 [ULTRA-PARSING & REPAIR]
                import json
                from core.utils.json_repair import repair_json
                
                parsed_json = None
                if isinstance(raw_res, dict):
                    parsed_json = raw_res
                elif isinstance(raw_res, str):
                    json_str = repair_json(raw_res)
                    if not json_str: 
                        engine.publish_mission_log("WARN", f"⚠️ [PARSING-FAULT]: Không phát hiện định dạng JSON từ `{current_role}`.", task_id, trace_id)
                        raise ValueError("Không tìm thấy JSON.")
                    parsed_json = json.loads(json_str)

                # [FIX-ARCH]: Normalization layer — xử lý Array trước khi đẩy lên Schema Firewall.
                # Model đôi khi trả về danh sách bước thô (Array) thay vì Blueprint dict.
                # Nếu Array chứa item có 'tool' hợp lệ → tự bọc thành Blueprint.
                # Nếu Array là rác thuần (lý thuyết, không tool) → raise để retry với message rõ ràng.
                if isinstance(parsed_json, list):
                    has_tool_steps = any(
                        isinstance(item, dict) and item.get("tool")
                        for item in parsed_json
                    )
                    if has_tool_steps:
                        logger.warning("[FORGE-NORMALIZE]: Model trả Array có steps. Tự bọc thành Blueprint dict.")
                        parsed_json = {
                            "thought": "Auto-normalized from array response.",
                            "steps": parsed_json,
                            "rationale": "Recovered from raw array output.",
                            "failure_speculation": "Model ignored Blueprint schema.",
                            "ambiguous": False,
                        }
                    else:
                        raise ValueError(
                            "You returned a JSON Array of theoretical steps without 'tool' fields. "
                            "Return a JSON OBJECT with keys: 'thought', 'steps' (each step needs 'tool'), "
                            "'rationale', 'failure_speculation', 'ambiguous'."
                        )

                if not isinstance(parsed_json, dict):
                    raise ValueError(
                        "Response must be a JSON OBJECT, not an array or primitive. "
                        'Return: {"thought": "...", "steps": [...], "rationale": "...", "ambiguous": false}'
                    )
                
                if "ambiguous" not in parsed_json:
                    parsed_json["ambiguous"] = False
                    
                if "clarification_question" not in parsed_json:
                    parsed_json["clarification_question"] = ""
                
                if "steps" not in parsed_json or not isinstance(parsed_json["steps"], list):
                    parsed_json["steps"] = []
                    
                if "thought" not in parsed_json or not isinstance(parsed_json["thought"], str):
                    parsed_json["thought"] = "Tự động khôi phục luồng tư duy."
                
                # Chuẩn hóa từng bước thực thi để loại bỏ lỗi truyền nhận tham số và lỗi thiếu trường
                cleaned_steps = []
                for i, step in enumerate(parsed_json["steps"]):
                    if not isinstance(step, dict):
                        raise ValueError(f"CRITICAL ERROR: Step {i} is a STRING instead of a JSON OBJECT. You MUST format steps as objects: {{\"id\": \"...\", \"tool\": \"...\", \"args\": {{...}}}}. Fix this immediately!")
                    if "id" not in step: step["id"] = f"step_{i}"
                    if "tool" not in step: step["tool"] = "OMNI_SEARCH_ENGINE"
                    if "args" not in step: step["args"] = {}
                    if "description" not in step: step["description"] = "Automatic recovery step"
                    if "assigned_agent" not in step: step["assigned_agent"] = "agent_executor_alpha.md"
                    if "hardware_target" not in step: step["hardware_target"] = "ALPHA"
                    if "expert_mindset" not in step: step["expert_mindset"] = "Tập trung chuẩn xác, tối ưu hiệu suất Antigravity."
                    if "verification" not in step or not str(step["verification"]).strip(): 
                        step["verification"] = "Hoàn tất kiểm định tự động (Automated Antigravity Parity Verification)."
                    cleaned_steps.append(step)
                parsed_json["steps"] = cleaned_steps

                # 🛡️ [QUERY-SANITY-FIREWALL]: Ngăn chặn Planner nhúng tư duy nội tâm vào query tìm kiếm
                internal_markers = ["mục tiêu của tôi", "tôi cần", "tôi sẽ", "lập kế hoạch", "lộ trình chiến lược", "master leetrung", "nhiệm vụ của master"]
                for step in parsed_json["steps"]:
                    if not isinstance(step, dict): continue
                    tool = str(step.get("tool", "")).upper()
                    if tool in ["SEARCH_WEB_GLOBAL", "SEARCH_WEB", "WEB_SEARCH", "OMNI_SEARCH_ENGINE"]:
                        raw_query = str(step.get("args", {}).get("query", ""))
                        is_hallucinated = (
                            len(raw_query) > 120 or
                            any(marker in raw_query.lower() for marker in internal_markers) or
                            not any(word.lower() in raw_query.lower() for word in goal.split() if len(word) > 3)
                        )
                        if is_hallucinated:
                            logger.warning(f"⚠️ [QUERY-SANITY]: Detected hallucinated query, reverting to original goal.")
                            step.setdefault("args", {})["query"] = goal

                # 🛡️ [TOOL-SANITY-FIREWALL]: Ngăn chặn AI bịa ra tool ảo (Hallucination)
                try:
                    skills_dict = await planner.orchestrator.get_all_skills_dict()
                    available_tools = [k.upper() for k in skills_dict.keys()]
                except Exception as e:
                    logger.warning(f"⚠️ [TOOL-SANITY-LOAD-ERR]: Error loading registry_Map_skills.json: {e}")
                    available_tools = []
                    
                valid_tool_names = set(available_tools + ["OMNI_SEARCH_ENGINE", "SEARCH_WEB_GLOBAL", "BROWSER_CONTROL", "CODE_EXECUTION", "READ_FILE", "REWRITE_FILE", "VIEW_FILE", "LLM_ANALYSIS", "ASK_USER", "FILE_WARDEN", "PYTHON_REPL", "SYSTEM_CMD", "FILESYSTEM", "DOCKER", "BASH", "EXECUTE_COMMAND", "MISSION_CONTROL", "SCAFFOLD_PROJECT", "WRITE_CODE", "RUN_TEST", "WRITE_FILE", "CREATE_FILE", "PYTHON_EXECUTE", "ANALYSIS", "ARCHITECTURE_DESIGN"])
                
                dropped_ids = set()
                dropped_tools = []
                valid_steps = []
                
                for step in parsed_json["steps"]:
                    if not isinstance(step, dict): continue
                    tool = str(step.get("tool", "")).upper()
                    if tool in valid_tool_names or any(t in tool for t in ["WRITE_", "READ_", "RUN_", "TEST", "CODE", "ANALYS", "EXEC", "DOCKER"]):
                        valid_steps.append(step)
                    else:
                        logger.warning(f"⚠️ [TOOL-SANITY]: Hallucinated tool `{tool}`. Dropping step.")
                        dropped_tools.append(tool)
                        if "id" in step:
                            dropped_ids.add(step["id"])
                            
                # 🔄 [SELF-CORRECTION-REFLEX]: Ép AI làm lại nếu bịa ra tool (Chỉ kích hoạt ở attempt 1 & 2)
                if dropped_tools and attempt < 3:
                    engine.publish_mission_log("WARN", f"⚠️ [SELF-CORRECTION]: Phát hiện AI ảo giác tạo tool giả {dropped_tools}. Đang ép buộc suy nghĩ lại!", task_id, trace_id, stealth=False)
                    raise ValueError(f"You hallucinated invalid tools: {dropped_tools}. You MUST use ONLY valid tools like SEARCH_WEB_GLOBAL, CODE_EXECUTION, WRITE_CODE, RUN_TEST, READ_FILE, REWRITE_FILE, VIEW_FILE, FILESYSTEM, DOCKER, SYSTEM_CMD. Please rewrite the ENTIRE plan.")
                elif dropped_tools and attempt == 3:
                    engine.publish_mission_log("WARN", f"⚠️ [TOOL-SANITY]: Lần thử cuối vẫn ảo giác tool {dropped_tools}. Đành phải tước bỏ bước này để cứu kế hoạch.", task_id, trace_id, stealth=False)
                
                # Dọn dẹp depends_on mồ côi do xóa step
                for step in valid_steps:
                    if "depends_on" in step and isinstance(step["depends_on"], list):
                        step["depends_on"] = [d for d in step["depends_on"] if d not in dropped_ids]
                        
                parsed_json["steps"] = valid_steps

                from planner import Blueprint
                blueprint = Blueprint.model_validate(parsed_json)
                planner._normalize_blueprint_agents(
                    blueprint, context.get("agent_role") if isinstance(context, dict) else None
                )
                
                # 🛡️ [EMPTY-PLAN-SHIELD]: Nếu không có bước nào và kế hoạch không yêu cầu làm rõ, tự phục hồi
                if not blueprint.steps and not blueprint.ambiguous:
                    from planner import PlanStep, HardwareTarget
                    blueprint.steps = [PlanStep(
                        id="auto_recovery_01",
                        tool="OMNI_SEARCH_ENGINE",
                        args={"query": goal},
                        description=f"Auto-recovery: omni search (Tavily/Cloud/Browse) for: {goal}",
                        assigned_agent="agent_executor_beta.md",
                        hardware_target=HardwareTarget.BETA,
                        expert_mindset="Execute immediately using the best available search source.",
                        verification="Search results obtained from at least one source."
                    )]

                state["blueprint_obj"] = blueprint
                state["raw_blueprint"] = blueprint.model_dump()
                return state
                
            except Exception as e:
                logger.warning(f"⚠️ [FORGE-RETRY-{attempt}]: {e}")
                if attempt == 1:
                    messages.append({"role": "user", "content": "[RETRY REQUIRED] Your previous response was invalid. Respond with ONLY a valid JSON object. No markdown, no explanations, no text outside the JSON. Follow the schema exactly."})
                if attempt == 3: raise e
        
        return state

class DAGOptimizerStage(PlanningStage):
    """Phẫu thuật đồ thị phụ thuộc (DAG Optimization & Race Condition Prevention)."""
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            blueprint_obj = state["blueprint_obj"]
            task_id = state["task_id"]
            trace_id = state.get("trace_id", "system")
            
            engine.publish_progress(70, "🕸️ [T3: DAG] Đang kiểm duyệt & tối ưu đồ thị phụ thuộc...", "dag", task_id, trace_id)
            
            steps = blueprint_obj.steps
            
            # 1. Cycle Detection (Topological Sort)
            adj = {s.id: set(s.depends_on) for s in steps}
            in_degree = {s.id: 0 for s in steps}
            for s_id, deps in adj.items():
                for d in deps:
                    if d in in_degree:
                        in_degree[s_id] += 1
            
            q = [k for k, v in in_degree.items() if v == 0]
            visited = 0
            while q:
                curr = q.pop(0)
                visited += 1
                for s_id, deps in adj.items():
                    if curr in deps:
                        in_degree[s_id] -= 1
                        if in_degree[s_id] == 0:
                            q.append(s_id)
            
            if visited != len(steps) and len(steps) > 1:
                engine.publish_mission_log("WARN", "⚠️ [DAG-FAULT]: Phát hiện đồ thị vòng lặp vô tận (Deadlock). Đang bẻ gãy liên kết...", task_id, trace_id)
                for i in range(1, len(steps)):
                    steps[i].depends_on = [steps[i-1].id]
                    steps[i].parallel = False
                steps[0].depends_on = []
                steps[0].parallel = False

            # 2. Race Condition Prevention (CRDT Pre-flight)
            write_tools = {"WRITE_TO_FILE", "REPLACE_FILE_CONTENT", "MULTI_REPLACE_FILE_CONTENT", "FILE_WARDEN", "PYTHON_REPL"}
            target_map = {}
            for s in steps:
                if str(s.tool).upper() in write_tools:
                    args = s.args or {}
                    target = args.get("path") or args.get("TargetFile") or args.get("target")
                    if target:
                        if target in target_map:
                            prev_step_id = target_map[target]
                            if prev_step_id not in s.depends_on:
                                s.depends_on.append(prev_step_id)
                                s.parallel = False
                                engine.publish_mission_log("INFO", f"🛡️ [DAG-CRDT]: Đã vá Race Condition cho `{target}` (Ép {s.id} đợi {prev_step_id})", task_id, trace_id, stealth=True)
                        target_map[target] = s.id

            # 3. Auto-Parallelization
            read_tools = {"OMNI_SEARCH_ENGINE", "SEARCH_WEB_GLOBAL", "READ_FILE", "VIEW_FILE", "LIST_DIR"}
            for s in steps:
                if str(s.tool).upper() in read_tools and not s.depends_on:
                    s.parallel = True
                    
            # 4. Topological Wave Generation (SOTA 2026 Parallel Accelerator)
            from core.utils.dag_runner import build_dag_waves
            state["execution_waves"] = build_dag_waves([s.model_dump() for s in steps])
            engine.publish_mission_log("INFO", f"⚡ [DAG-WAVES]: Đã phân tầng {len(state['execution_waves'])} sóng thực thi song song cho {len(steps)} bước.", task_id, trace_id, stealth=True)

            state["blueprint_obj"] = blueprint_obj
            return state
            
        except Exception as e:
            engine.publish_mission_log("ERROR", f"🚨 [STAGE-FAULT]: DAGOptimizerStage thất bại - {str(e)}", state.get("task_id", "sys"), state.get("trace_id", "system"))
            raise e

class PolicyStage(PlanningStage):
    """Chấp pháp và hoàn thiện."""
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            planner = state["planner_instance"]
            blueprint_obj = state["blueprint_obj"]
            context = state["context"]
            task_id = state["task_id"]
            trace_id = state.get("trace_id", "system")
            
            # 1. Attach Policies (Dump và xử lý an toàn)
            blueprint_dict = blueprint_obj.model_dump()
            engine.publish_progress(80, "⚖️ [T3: FORGE] Đang áp chế chính sách thực thi...", "policy", task_id, trace_id)
            final_plan = await planner._attach_policies(blueprint_dict, context, task_id)
            
            # 2. Inject Prevention Steps
            if "pre_flight" in state:
                from planner import Blueprint
                from core.utils.failure_memory import PreFlightWarning
                pre_flight_data = state["pre_flight"]
                if isinstance(pre_flight_data, PreFlightWarning):
                    pre_flight_data = pre_flight_data.warnings
                temp_obj = Blueprint.model_validate(final_plan)
                final_obj = planner._inject_prevention_steps(temp_obj, pre_flight_data)
                final_plan = final_obj.model_dump()
                
            state["final_plan"] = final_plan
            return state
        except Exception as e:
            engine.publish_mission_log("ERROR", f"🚨 [STAGE-FAULT]: PolicyStage thất bại - {str(e)}", state.get("task_id", "sys"), state.get("trace_id", "system"))
            raise e

class PlanningPipeline:
    """Điều phối luồng tư duy đa tầng."""
    def __init__(self, stages: List[PlanningStage]):
        self.stages = stages

    async def execute(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        state = initial_state
        
        recon_stage = None
        context_stage = None
        remaining_stages = []
        
        for stage in self.stages:
            if isinstance(stage, ReconStage):
                recon_stage = stage
            elif isinstance(stage, ContextStage):
                context_stage = stage
            else:
                remaining_stages.append(stage)
                
        if recon_stage and context_stage:
            logger.info("⚡ [PARALLEL-PLANNING]: Kích hoạt luồng song song ReconStage + ContextStage...")
            
            # 🛡️ [DEEPCOPY-ISOLATION]: Sử dụng deepcopy để triệt tiêu hoàn toàn race conditions
            async def run_recon():
                recon_state = copy.deepcopy(state)
                return await recon_stage.run(recon_state)
                
            async def run_context():
                context_state = copy.deepcopy(state)
                return await context_stage.run(context_state)
                
            import asyncio as _asyncio
            # 🛡️ [PARTIAL-COGNITIVE-SURVIVAL]: Shield bảo vệ, không để lỗi một nhánh kéo đổ toàn hệ thống
            results = await _asyncio.gather(run_recon(), run_context(), return_exceptions=True)
            recon_res, context_res = results
            
            # Kiểm thử và cấu trúc cứu vớt thông tin
            if isinstance(recon_res, Exception):
                logger.error(f"🚨 [PARTIAL-FAILURE]: Nhánh ReconStage lỗi: {recon_res}")
                recon_res = {
                    "skill_dna": "[SKILL DNA]: Fallback global search active.",
                    "pre_flight": [],
                    "top_k_ids": ["OMNI_SEARCH_ENGINE"]
                }
            if isinstance(context_res, Exception):
                logger.error(f"🚨 [PARTIAL-FAILURE]: Nhánh ContextStage lỗi: {context_res}")
                context_res = {
                    "neural_context": {
                        "reliability": "DEGRADED", 
                        "experience": "Fallback active.", 
                        "manifesto": "Zenith Protocol Active."
                    }
                }
            
            # Hợp nhất an toàn kết quả
            state["skill_dna"] = recon_res.get("skill_dna")
            state["pre_flight"] = recon_res.get("pre_flight")
            state["neural_context"] = context_res.get("neural_context")
            state["top_k_ids"] = recon_res.get("top_k_ids", [])
        else:
            # Luồng tuần tự dự phòng
            for stage in self.stages:
                if isinstance(stage, (ReconStage, ContextStage)):
                    logger.info(f"🚀 [STAGE]: {stage.__class__.__name__} starting...")
                    try:
                        # Canh gác treo Stage bằng Timeout 120s
                        state = await asyncio.wait_for(stage.run(state), timeout=120.0)
                    except asyncio.TimeoutError:
                        logger.error(f"🚨 [STAGE-TIMEOUT]: Stage {stage.__class__.__name__} timed out after 120 seconds.")
                    except Exception as e:
                        logger.error(f"🚨 [STAGE-FAULT]: Stage {stage.__class__.__name__} failed: {e}")
                    
        # Chạy các stage còn lại tuần tự với State Checkpointing (SOTA 2026)
        for stage in remaining_stages:
            stage_name = stage.__class__.__name__
            task_id = state.get("task_id", "sys")

            # 📦 [CHECKPOINT-RESUME]: Kiểm tra xem stage này đã được thực thi và lưu checkpoint trước đó chưa
            try:
                from core.utils.state_checkpoint import load_checkpoint, save_checkpoint
                cached_state = load_checkpoint(task_id, stage_name)
                if cached_state and ("raw_blueprint" in cached_state or "final_plan" in cached_state):
                    logger.info(f"⚡ [CHECKPOINT-RESUME]: Task {task_id} nạp lại kết quả stage {stage_name} từ disk, bỏ qua LLM call.")
                    state.update(cached_state)
                    continue
            except Exception as ckpt_err:
                logger.debug(f"[CHECKPOINT-CHECK] {stage_name}: {ckpt_err}")

            logger.info(f"🚀 [STAGE]: {stage_name} starting...")
            try:
                # 🕒 [STAGE-TIMEOUT-GUARD]: Timeout 600s
                state = await asyncio.wait_for(stage.run(state), timeout=600.0)

                # 💾 [CHECKPOINT-SAVE & WORLD-STATE-UPDATE]: Lưu trạng thái stage thành công và cập nhật World State 7 chiều
                try:
                    from core.utils.state_checkpoint import save_checkpoint
                    from core.os.world_state import update_mission_world_state, record_causality_link
                    save_checkpoint(task_id, stage_name, state)
                    update_mission_world_state(task_id, "state_data", {stage_name: "COMPLETED"})
                    record_causality_link(task_id, cause=f"Stage_{stage_name}", effect=f"Stage {stage_name} output generated", status="SUCCESS")
                except Exception as save_err:
                    logger.debug(f"[CHECKPOINT-SAVE-ERR] {stage_name}: {save_err}")
            except asyncio.TimeoutError:
                err_msg = f"Stage {stage_name} timed out after 600 seconds."
                logger.error(f"🚨 [STAGE-FAULT]: {err_msg}")
                raise TimeoutError(err_msg)
            except Exception as e:
                logger.error(f"🚨 [STAGE-FAULT]: Stage {stage_name} timed out or failed: {e}")
                raise e

        # Clear checkpoints upon mission completion
        try:
            from core.utils.state_checkpoint import clear_checkpoints
            clear_checkpoints(state.get("task_id", "sys"))
        except Exception:
            pass

        return state
