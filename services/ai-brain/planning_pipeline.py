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
            skill_dna = await planner._recon_skills(goal, "", task_id)
            state["skill_dna"] = skill_dna
            
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
    """Nạp bối cảnh nhất thể."""
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        try:
            planner = state["planner_instance"]
            goal = state["goal"]
            task_id = state["task_id"]
            trace_id = state.get("trace_id", "system")
            
            engine.publish_progress(20, "🌌 [T2: CONTEXT] Đang đồng hóa tri thức và bối cảnh nhất thể...", "context", task_id, trace_id)
            
            complexity = state.get("complexity", "complex")
            neural_context = await planner._prepare_neural_context(goal, task_id, complexity)
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

        specialist_prompt = await planner._forge.forge_specialist_prompt(
            goal=goal, 
            context=context, 
            skills_summary=skill_dna, 
            fast_mode=(mode == "fast")
        )
        
        system_prompt = await planner._build_system_prompt(
            neural_context, 
            specialist_prompt, 
            skill_dna
        )
        
        messages = [{"role": "system", "content": system_prompt}, {"role": "user", "content": goal}]
        
        # 🛡️ [RETRY-ESCALATION-STRATEGY]: Tự tăng bậc ràng buộc khi gặp lỗi
        for attempt in range(1, 4):
            current_role = "PLANNER" if attempt == 1 else "RESERVE_AGENT"
            
            if attempt == 2:
                messages.append({
                    "role": "user",
                    "content": "⚠️ [ESCALATION]: Previous response was not valid JSON. You MUST respond with ONLY a valid, strict JSON object. No explanations, no markdown block wrappers."
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
            raw_res = await engine.call_chat(
                messages, 
                role=current_role, 
                format="json" if attempt < 3 else None, 
                task_id=task_id, 
                trace_id=trace_id
            )
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

                # 🛡️ [SCHEMA-FIREWALL]: Rào chắn lọc sạch ảo giác trước khi validate
                if not isinstance(parsed_json, dict):
                    raise ValueError("Blueprint response must be a JSON dictionary.")
                
                if "ambiguous" not in parsed_json:
                    parsed_json["ambiguous"] = False
                    
                if "clarification_question" not in parsed_json:
                    parsed_json["clarification_question"] = ""
                
                if "steps" not in parsed_json or not isinstance(parsed_json["steps"], list):
                    parsed_json["steps"] = []
                    
                if "thought" not in parsed_json or not isinstance(parsed_json["thought"], str):
                    parsed_json["thought"] = "Tự động khôi phục luồng tư duy."
                
                # Chuẩn hóa từng bước thực thi để loại bỏ lỗi truyền nhận tham số
                cleaned_steps = []
                for i, step in enumerate(parsed_json["steps"]):
                    if not isinstance(step, dict): continue
                    if "id" not in step: step["id"] = f"step_{i}"
                    if "tool" not in step: step["tool"] = "SEARCH_WEB_GLOBAL"
                    if "args" not in step: step["args"] = {}
                    if "description" not in step: step["description"] = "Automatic recovery step"
                    cleaned_steps.append(step)
                parsed_json["steps"] = cleaned_steps

                # 🛡️ [QUERY-SANITY-FIREWALL]: Ngăn chặn Planner nhúng tư duy nội tâm vào query tìm kiếm
                internal_markers = ["mục tiêu của tôi", "tôi cần", "tôi sẽ", "lập kế hoạch", "lộ trình chiến lược", "master leetrung", "nhiệm vụ của master"]
                for step in parsed_json["steps"]:
                    if not isinstance(step, dict): continue
                    tool = str(step.get("tool", "")).upper()
                    if tool in ["SEARCH_WEB_GLOBAL", "SEARCH_WEB", "WEB_SEARCH"]:
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
                    import json
                    reg_path = "d:/Docker/N8N/intelligence/registry_Map_skills.json"
                    if not os.path.exists(reg_path):
                        reg_path = "/workspace/intelligence/registry_Map_skills.json"
                    
                    with open(reg_path, "r", encoding="utf-8") as f:
                        reg_data = json.load(f)
                    available_tools = [k.upper() for k in reg_data.get("skills", {}).keys()]
                except Exception as e:
                    logger.warning(f"⚠️ [TOOL-SANITY-LOAD-ERR]: Error loading registry_Map_skills.json: {e}")
                    available_tools = []
                    
                valid_tool_names = set(available_tools + ["SEARCH_WEB_GLOBAL", "BROWSER_CONTROL", "CODE_EXECUTION", "READ_FILE", "LLM_ANALYSIS", "ASK_USER", "FILE_WARDEN", "PYTHON_REPL", "SYSTEM_CMD"])
                
                dropped_ids = set()
                dropped_tools = []
                valid_steps = []
                
                for step in parsed_json["steps"]:
                    if not isinstance(step, dict): continue
                    tool = str(step.get("tool", "")).upper()
                    if tool in valid_tool_names:
                        valid_steps.append(step)
                    else:
                        logger.warning(f"⚠️ [TOOL-SANITY]: Hallucinated tool `{tool}`. Dropping step.")
                        dropped_tools.append(tool)
                        if "id" in step:
                            dropped_ids.add(step["id"])
                            
                # 🔄 [SELF-CORRECTION-REFLEX]: Ép AI làm lại nếu bịa ra tool (Chỉ kích hoạt ở attempt 1 & 2)
                if dropped_tools and attempt < 3:
                    engine.publish_mission_log("WARN", f"⚠️ [SELF-CORRECTION]: Phát hiện AI ảo giác tạo tool giả {dropped_tools}. Đang ép buộc suy nghĩ lại!", task_id, trace_id, stealth=False, channels=["progress"])
                    raise ValueError(f"You hallucinated invalid tools: {dropped_tools}. You MUST use ONLY valid tools like SEARCH_WEB_GLOBAL, CODE_EXECUTION, READ_FILE, etc. Please rewrite the ENTIRE plan.")
                elif dropped_tools and attempt == 3:
                    engine.publish_mission_log("WARN", f"⚠️ [TOOL-SANITY]: Lần thử cuối vẫn ảo giác tool {dropped_tools}. Đành phải tước bỏ bước này để cứu kế hoạch.", task_id, trace_id, stealth=False)
                
                # Dọn dẹp depends_on mồ côi do xóa step
                for step in valid_steps:
                    if "depends_on" in step and isinstance(step["depends_on"], list):
                        step["depends_on"] = [d for d in step["depends_on"] if d not in dropped_ids]
                        
                parsed_json["steps"] = valid_steps

                from planner import Blueprint
                blueprint = Blueprint.model_validate(parsed_json)
                
                # 🛡️ [EMPTY-PLAN-SHIELD]: Nếu không có bước nào và kế hoạch không yêu cầu làm rõ, tự phục hồi
                if not blueprint.steps and not blueprint.ambiguous:
                    from planner import PlanStep
                    blueprint.steps = [PlanStep(
                        id="auto_recovery_01",
                        tool="SEARCH_WEB_GLOBAL",
                        args={"query": goal},
                        description=f"Auto-recovery: global web search for: {goal}",
                        expert_mindset="Execute immediately.",
                        verification="Search results obtained"
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
                temp_obj = Blueprint.model_validate(final_plan)
                final_obj = planner._inject_prevention_steps(temp_obj, state["pre_flight"])
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
                
            # 🛡️ [PARTIAL-COGNITIVE-SURVIVAL]: Shield bảo vệ, không để lỗi một nhánh kéo đổ toàn hệ thống
            results = await asyncio.gather(run_recon(), run_context(), return_exceptions=True)
            recon_res, context_res = results
            
            # Kiểm thử và cấu trúc cứu vớt thông tin
            if isinstance(recon_res, Exception):
                logger.error(f"🚨 [PARTIAL-FAILURE]: Nhánh ReconStage lỗi: {recon_res}")
                recon_res = {
                    "skill_dna": "[SKILL DNA]: Fallback global search active.", 
                    "pre_flight": []
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
                    
        # Chạy các stage còn lại tuần tự
        for stage in remaining_stages:
            logger.info(f"🚀 [STAGE]: {stage.__class__.__name__} starting...")
            try:
                # 🕒 [STAGE-TIMEOUT-GUARD]: Timeout 300s
                state = await asyncio.wait_for(stage.run(state), timeout=300.0)
            except asyncio.TimeoutError:
                err_msg = f"Stage {stage.__class__.__name__} timed out after 300 seconds."
                logger.error(f"🚨 [STAGE-FAULT]: {err_msg}")
                raise TimeoutError(err_msg)
            except Exception as e:
                logger.error(f"🚨 [STAGE-FAULT]: Stage {stage.__class__.__name__} timed out or failed: {e}")
                raise e
            
        return state
