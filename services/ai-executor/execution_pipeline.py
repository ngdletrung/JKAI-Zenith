import asyncio
import json
import logging
import time
from typing import Any, Dict, List, Optional
from core.utils.engine import engine

logger = logging.getLogger("JKAI.ExecutionPipeline")

class ExecutionStage:
    """Cơ sở cho các nơ-ron hành pháp."""
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

class PreflightStage(ExecutionStage):
    """Kiểm tra an toàn và Khóa tài nguyên."""
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        executor = state["executor_instance"]
        tool_name = state["tool_name"]
        args = state["args"]
        task_id = state["task_id"]
        
        engine.publish_progress(81, f"🔬 [T4: SURGERY] [{tool_name}] Đang kiểm tra an toàn & khóa tài nguyên...", "preflight", task_id)
        await executor._pre_flight_check(tool_name, args, task_id)
        return state

class PolicyResolutionStage(ExecutionStage):
    """Quyết định chiến thuật thực thi."""
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        executor = state["executor_instance"]
        tool_name = state["tool_name"]
        args = state["args"]
        task_id = state["task_id"]
        override = state.get("policy_override")
        
        engine.publish_progress(83, f"⚖️ [T4: SURGERY] [{tool_name}] Đang áp dụng chính sách thực thi...", "policy", task_id)
        policy = await executor._resolve_execution_policy(tool_name, args, task_id, override)
        state["policy"] = policy
        return state

class IntelligenceInjectionStage(ExecutionStage):
    """Nạp DNA và Nén bối cảnh."""
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        executor = state["executor_instance"]
        task_id = state["task_id"]
        tool_name = state["tool_name"]
        
        engine.publish_progress(85, f"💉 [T4: SURGERY] [{tool_name}] Đang nạp DNA & nén bối cảnh...", "intelligence", task_id)
        # Tích hợp Context Compression
        args = await executor._inject_intelligence(
            state["tool_name"], state["args"], task_id,
            state.get("expert_mindset"), state.get("assigned_agent"), state["policy"]
        )
        state["args"] = args
        return state

class ReflectionStage(ExecutionStage):
    """Phản biện tính phù hợp (Policy-Gated)."""
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        executor = state["executor_instance"]
        policy = state["policy"]
        
        if await executor._should_run_critic(state["tool_name"], policy):
            await executor._reflect_suitability(
                state["tool_name"], state["args"], state["task_id"], policy
            )
        return state

class SurgicalExecutionStage(ExecutionStage):
    """Thực thi phẫu thuật với Adaptive Retry."""
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        executor = state["executor_instance"]
        tool_name = state["tool_name"]
        task_id = state["task_id"]
        
        engine.publish_progress(90, f"⚔️ [T4: SURGERY] [{tool_name}] Bắt đầu can thiệp thực địa...", "execution", task_id)
        result = await executor._execute_with_retry(
            tool_name, state["args"], task_id, state["policy"]
        )
        state["result"] = result
        return state

class HarvestStage(ExecutionStage):
    """Thu hoạch tri thức và Phản hồi."""
    async def run(self, state: Dict[str, Any]) -> Dict[str, Any]:
        executor = state["executor_instance"]
        final_res = await executor._harvest_and_verify(
            state["tool_name"], state["result"], state["task_id"], 
            state["policy"], state["start_time"], state["args"]
        )
        state["final_response"] = final_res
        return state

class ExecutionPipeline:
    """Điều phối luồng thực thi Nhất thể."""
    def __init__(self, stages: List[ExecutionStage]):
        self.stages = stages

    async def execute(self, initial_state: Dict[str, Any]) -> Dict[str, Any]:
        state = initial_state
        for stage in self.stages:
            logger.info(f"🔴 [EXEC-STAGE]: {stage.__class__.__name__} starting...")
            state = await stage.run(state)
        return state
