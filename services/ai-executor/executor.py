import asyncio
from typing import List, Dict, Any, Optional, Union
import os
import json
import time
import httpx
import psutil
import hashlib

from core.utils.engine import engine
from core.utils.knowledge_brain import knowledge_brain
from core.config import settings
from tool_router import ToolRouter
from redis_client import redis_safe

from enum import Enum

# 🏛️ [ZENITH-CORE-MODULAR]: Nạp các module tối thượng
from core.utils.sovereign_guard import SovereignGuard
from core.utils.crdt_engine import ZenithCRDT
from core.utils.security import security_engine
from core.utils.execution_policy import get_policy_engine, WorldState, ReasoningDepth, ExecutionPolicy
from core.utils.failure_memory import failure_memory, FailureStage
from core.utils.cognitive_guardrails import guardrail_registry, GuardrailException
from core.utils.doctrine_engine import doctrine_engine

class FailureType(str, Enum):
    NETWORK = "NETWORK"
    AUTH    = "AUTH"
    SCHEMA  = "SCHEMA"
    SEMANTIC = "SEMANTIC"
    TIMEOUT = "TIMEOUT"
    UNKNOWN = "UNKNOWN"

guard = SovereignGuard("Zenith Warrior")

class Executor:
    """
    🏛️ JKAI ZENITH: BAN THỰC THI (COGNITIVE EXECUTION RUNTIME) v12.0
    Hệ thống điều phối thực thi phi tập trung.
    """
    def __init__(self):
        self.router = ToolRouter()
        self.client = httpx.AsyncClient(
            timeout=httpx.Timeout(900.0, connect=60.0),
            limits=httpx.Limits(max_keepalive_connections=50, max_connections=100)
        )
        self.policy_engine = get_policy_engine(failure_memory.get_tool_failure_rate)
        self._session_failures = 0

    def _get_redis(self):
        # Tránh lỗi circular import
        import redis
        return redis.Redis(host=os.getenv("REDIS_HOST", "redis"), port=6379, db=0, decode_responses=True)

    # ── PUBLIC API ────────────────────────────────────────────────────────────

    async def call_tool(self, tool_name: str, args: dict, task_id: str = "unknown", 
                        trace_id: str = "system",
                        expert_mindset: str = None, assigned_agent: str = None, 
                        policy_override: dict = None):
        """
        🚀 [DECENTRALIZED-PIPELINE]: Khởi tạo luồng thực thi phi tập trung.
        """
        from execution_pipeline import ExecutionPipeline, PreflightStage, PolicyResolutionStage, \
                                     IntelligenceInjectionStage, ReflectionStage, \
                                     SurgicalExecutionStage, HarvestStage
        
        start_time = time.time()
        
        pipeline = ExecutionPipeline([
            PreflightStage(),
            PolicyResolutionStage(),
            IntelligenceInjectionStage(),
            ReflectionStage(),
            SurgicalExecutionStage(),
            HarvestStage()
        ])
        
        state = {
            "tool_name": tool_name,
            "args": args,
            "task_id": task_id,
            "trace_id": trace_id,
            "expert_mindset": expert_mindset,
            "assigned_agent": assigned_agent,
            "policy_override": policy_override,
            "start_time": start_time,
            "executor_instance": self
        }
        
        try:
            final_state = await pipeline.execute(state)
            return final_state["final_response"]
        except GuardrailException as ge:
            self._log("GUARDRAIL", f"🛑 [CHẶN]: {ge}", task_id, trace_id)
            return {"status": "error", "msg": f"Guardrail Violation: {ge}"}
        except InterruptedError:
            return {"status": "error", "msg": "Nhiệm vụ đã dừng theo lệnh Master."}
        except Exception as e:
            self._log("CRITICAL", f"🚨 [SỰ CỐ HỆ THỐNG]: {e}", task_id, trace_id)
            return {"status": "error", "msg": str(e)}
        finally:
            # 🔓 [RELEASE-LOCK]: Giải phóng phong ấn
            if "crdt_obj" in state:
                state["crdt_obj"].release_lock()

    # ── PIPELINE STEPS (PRIVATE) ──────────────────────────────────────────────

    async def _pre_flight_check(self, tool_name: str, args: dict, task_id: str, trace_id: str = "system"):
        self._check_abort(task_id)
        guard = guardrail_registry.get_or_create(task_id)
        violation = guard.check_before_tool(tool_name, args)
        if violation.should_abort: raise GuardrailException(violation.reason)
        
        # 🔒 [CRDT-SOVEREIGN-LOCKING]: Bảo vệ tính toàn vẹn
        write_ops = ["write", "patch", "replace", "create", "save", "edit", "append"]
        target_path = args.get("path") or args.get("target") or args.get("file_path") or args.get("TargetFile")
        if any(w in tool_name.lower() for w in write_ops) and target_path:
            crdt = ZenithCRDT(target_path)
            owner = crdt.get_lock_owner()
            current_role = os.getenv("EXECUTOR_ROLE", "ALPHA")
            
            if owner and owner != current_role:
                self._log("CRDT", f"🔒 [COLLISION]: Tập tin `{os.path.basename(target_path)}` đang được phẫu thuật bởi {owner}. Đang chờ nơ-ron rảnh...", task_id)
                # Chờ đợi kiên nhẫn
                for _ in range(10): 
                    await asyncio.sleep(1)
                    if not crdt.get_lock_owner(): break
                else:
                    self._log("CRDT", f"⚠️ [TIMEOUT]: {current_role} buộc phải tiếp quản quyền ghi từ {owner}.", task_id)
            
            # Đặt phong ấn mới
            crdt.acquire_lock(current_role)
            state["crdt_obj"] = crdt # Giữ để release sau

    async def _resolve_execution_policy(self, tool_name: str, args: dict, task_id: str, override: dict) -> ExecutionPolicy:
        ws = WorldState(cpu_percent=psutil.cpu_percent(), ram_percent=psutil.virtual_memory().percent, tool_failures=self._session_failures)
        policy = await self.policy_engine.resolve({"tool": tool_name, "description": args.get("description", "")}, {"task_id": task_id}, ws)
        if override:
            for k, v in override.items():
                if hasattr(policy, k): setattr(policy, k, v)
        return policy

    async def _inject_intelligence(self, tool_name: str, args: dict, task_id: str, 
                                 mindset: str, agent: str, policy: ExecutionPolicy) -> dict:
        if not (mindset or agent): return args
        agent_soul = await engine.get_brain_knowledge(agent) if agent else ""
        
        # 📚 [CONTEXT-COMPRESSION]: Nén bối cảnh
        insights = engine.get_insights(task_id)
        # Chỉ lấy 3 insight gần nhất để tránh context explosion
        compressed_insights = dict(list(insights.items())[-3:]) if insights else {}
        insight_header = f"🧬 [TRI THỨC RÚT GỌN]:\n" + "\n".join([f"• {k}: {v}" for k, v in compressed_insights.items()]) + "\n\n" if compressed_insights else ""

        full_mindset = f"{agent_soul}\n\n{insight_header}--- [MISSION] ---\n{mindset or ''}"
        args["expert_mindset"] = full_mindset
        return args

    async def _should_run_critic(self, tool_name: str, policy: ExecutionPolicy) -> bool:
        if policy.reasoning_depth == ReasoningDepth.CRITICAL: return True
        if policy.reasoning_depth == ReasoningDepth.SHALLOW: return False
        return policy.use_critic

    async def _reflect_suitability(self, tool_name: str, args: dict, task_id: str, policy: ExecutionPolicy):
        check_prompt = f"Mục tiêu: {args.get('expert_mindset', 'N/A')}\nCông cụ: {tool_name}\n\nPhù hợp không thưa Đặc vụ? Trả về 'REJECT: lý do' hoặc 'APPROVE'."
        current_role = os.getenv("EXECUTOR_ROLE", "ALPHA").upper()
        critic_role = f"CRITIC_{current_role}" if current_role in ["ALPHA", "BETA"] else "CRITIC"
        suitability = await engine.call_chat([{"role": "user", "content": check_prompt}], role=critic_role, task_id=task_id)
        if "REJECT" in suitability.upper():
            raise GuardrailException(f"Executor REJECT: {suitability}")

    async def _execute_with_retry(self, tool_name: str, args: dict, task_id: str, policy: ExecutionPolicy) -> Any:
        # 🛡️ [HARDENED-LOOP-PROTECTION]: Băm JSON đã sắp xếp
        args_str = json.dumps(args, sort_keys=True)
        loop_key = f"zenith:loop:{task_id}:{tool_name}:{hashlib.md5(args_str.encode()).hexdigest()}"
        try:
            loop_count = int(self._get_redis().incr(loop_key))
            self._get_redis().expire(loop_key, 3600)
            if loop_count > 2:
                self._log("GUARDRAIL", f"🛑 [LOOP-DETECTED]: Ngắt mạch lặp nơ-ron cho `{tool_name}`.", task_id)
                return {"status": "error", "msg": "Neural Loop Protection Triggered."}
        except: pass

        last_error = None
        for attempt in range(policy.max_retry):
            try:
                self._check_abort(task_id)
                args["task_id"] = task_id
                result = await asyncio.wait_for(self.router.call_tool(tool_name, **args), timeout=policy.timeout)
                if not (isinstance(result, dict) and result.get("status") == "error"): return result
                last_error = result.get("msg") or str(result)
                # Phân loại lỗi
                fail_type = self._classify_failure(last_error)
                if fail_type == FailureType.AUTH: break # Lỗi quyền không retry
            except Exception as e:
                last_error = str(e)
                if "abort" in last_error.lower(): raise

        self._session_failures += 1
        return {"status": "error", "msg": f"Thất bại sau {policy.max_retry} lần: {last_error}"}

    def _classify_failure(self, error_msg: str) -> FailureType:
        """🔍 [FAILURE-TAXONOMY]: Phân loại lỗi để thích nghi."""
        err = error_msg.lower()
        if any(x in err for x in ["timeout", "deadline"]): return FailureType.TIMEOUT
        if any(x in err for x in ["auth", "permission", "denied", "401", "403"]): return FailureType.AUTH
        if any(x in err for x in ["network", "connection", "refused", "reachable"]): return FailureType.NETWORK
        if any(x in err for x in ["schema", "validation", "format", "missing"]): return FailureType.SCHEMA
        return FailureType.UNKNOWN

    async def _harvest_and_verify(self, tool_name: str, result: Any, task_id: str, 
                                 policy: ExecutionPolicy, start_time: float, args: dict) -> dict:
        latency_ms = (time.time() - start_time) * 1000
        is_success = isinstance(result, dict) and result.get("status") != "error"
        
        # 1. [EVENT-STORE]: Ghi nhận Telemetry chuẩn của Zenith
        from core.utils.event_store import event_store
        event_store.log_event(
            task_id=task_id,
            agent_id=os.getenv("EXECUTOR_ROLE", "ALPHA"),
            event_type="SKILL_EXECUTION",
            payload={"tool": tool_name, "success": is_success, "latency": latency_ms}
        )

        # 2. [FAILURE-MEMORY]: Khởi hoạt luồng tự học (Self-Healing) khi fail
        if not is_success:
            from core.utils.failure_memory import failure_memory, FailureStage
            error_detail = result.get("msg") if isinstance(result, dict) else str(result)
            goal_desc = args.get("expert_mindset", f"Thực thi công cụ {tool_name}")
            await failure_memory.record_failure(
                task_id=task_id,
                goal=goal_desc,
                task_type="general",
                failure_stage=FailureStage.TOOL_EXECUTION,
                error_detail=error_detail,
                failed_tools=[tool_name]
            )
        
        if is_success:
            content = result.get("content") or result.get("data") or result.get("path")
            if content: engine.set_insight(task_id, f"res_{tool_name}", content)
            
            # Elite Logging
            path_arg = args.get("path") or args.get("TargetFile") or ""
            target = os.path.basename(str(path_arg)) or tool_name
            self._log("EXECUTOR", f"Successfully executed {target}.", task_id)
            return {"status": "success", "output": result}
        
        return result

    def _check_abort(self, task_id: str):
        def _check(r): return r.get("agent:stop_signal") == "true" or r.get(f"agent:stop_signal:{task_id}") == "true"
        if redis_safe(_check): raise InterruptedError("Stopped by Master.")

    def _log(self, tag: str, msg: str, task_id: str, trace_id: str = "system"):
        role = os.getenv("EXECUTOR_ROLE", "ALPHA")
        engine.publish_mission_log(f"{tag}:{role}", msg, task_id, trace_id)

    async def run_steps(self, steps: List[Dict[str, Any]], task_id: str = "unknown", trace_id: str = "system") -> dict:
        """
        🚀 [PARALLEL-SWARM-EXECUTION]: Thực thi lộ trình đa luồng.
        Phối hợp Alpha và Beta tác chiến song song nếu không có phụ thuộc logic.
        """
        results = {}
        executed_steps = set()
        
        while len(executed_steps) < len(steps):
            # 1. Tìm các bước có thể chạy ngay (đã xong dependencies)
            ready_steps = [
                s for s in steps 
                if s["id"] not in executed_steps and all(d in executed_steps for d in s.get("depends_on", []))
            ]
            
            if not ready_steps: break # Bế tắc logic
            
            # 2. Phân nhóm: Parallel vs Sequential
            parallel_batch = [s for s in ready_steps if s.get("parallel", False)]
            sequential_step = ready_steps[0] if not parallel_batch else None
            
            tasks = []
            if parallel_batch:
                self._log("SYSTEM", f"⚡ [SWARM-MODE]: Kích hoạt {len(parallel_batch)} nơ-ron thực thi song song.", task_id)
                for s in parallel_batch:
                    tasks.append(self.call_tool(
                        s["tool"], s.get("args", {}), task_id, trace_id,
                        expert_mindset=s.get("expert_mindset"),
                        assigned_agent=s.get("assigned_agent"),
                        policy_override=s.get("policy")
                    ))
            elif sequential_step:
                tasks.append(self.call_tool(
                    sequential_step["tool"], sequential_step.get("args", {}), task_id, trace_id,
                    expert_mindset=sequential_step.get("expert_mindset"),
                    assigned_agent=sequential_step.get("assigned_agent"),
                    policy_override=sequential_step.get("policy")
                ))

            # 3. Kích nổ thực thi
            batch_results = await asyncio.gather(*tasks)
            
            # 4. Ghi nhận và kiểm tra lỗi
            current_batch = parallel_batch if parallel_batch else [sequential_step]
            for step, res in zip(current_batch, batch_results):
                results[step["id"]] = res
                executed_steps.add(step["id"])
                if isinstance(res, dict) and res.get("status") == "error":
                    err_msg = res.get("msg", "Unknown error")
                    self._log("CRITICAL", f"🛑 [STOP]: Bước `{step['id']}` thất bại: {err_msg}. Ngắt chuỗi hành pháp.", task_id)
                    return {"status": "failed", "results": results}
                    
        return {"status": "completed", "results": results}

    async def _self_heal_step(self, step: dict, error_msg: str, task_id: str) -> dict:
        """
        GIAO THỨC TỰ PHỤC HỒI (SELF-HEALING) v1.5
        Dựa trên Failure Taxonomy.
        """
        fail_type = self._classify_failure(error_msg)
        
        # 1. Deterministic paths
        if fail_type == FailureType.TIMEOUT:
            step["policy"] = step.get("policy", {})
            step["policy"]["timeout"] = step["policy"].get("timeout", 30) * 2
            return await self.call_tool(step["tool"], step["args"], task_id, policy_override=step["policy"])
            
        # 2. Cognitive paths
        prompt = f"Lỗi loại {fail_type}: {error_msg}. Đề xuất args mới cho {step['tool']}. Trả về JSON."
        correction = await engine.call_chat([{"role": "user", "content": prompt}], role="CRITIC", json_mode=True)
        if isinstance(correction, dict):
            action_desc = f"Áp dụng mã tự phục hồi (Code Fix) cho công cụ {step['tool']}. Thay đổi: {json.dumps(correction, ensure_ascii=False)}"
            is_approved = await guard.ensure_approval(task_id, action_desc, is_core=True)
            if is_approved:
                self._log("SYSTEM", f"✅ [SELF-HEAL]: Master đã cấp phép. Đang áp dụng mã phục hồi...", task_id)
                return await self.call_tool(step["tool"], correction, task_id)
            else:
                self._log("SYSTEM", f"🛑 [SELF-HEAL]: Master từ chối cấp phép. Không áp dụng mã phục hồi.", task_id)
                return {"status": "error", "msg": "Tự phục hồi bị từ chối bởi Master."}
        return {"status": "error", "msg": "Không thể phục hồi."}

# *Sovereign Property of Master LeeTrung. Optimized for v12.0 Execution Fabric. 🏛️⚔️🚀*
