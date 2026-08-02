#!/usr/bin/env python3
"""
🌟 End-to-End Autonomous Goal Solver Engine for JKAI Zenith.
Orchestrates Master Prompt Architect, Agent Router, Context Manager, Guardrails,
and Autonomous Repair Loop into a seamless execution pipeline.
"""

import os
import json
import logging
import asyncio
from typing import Dict, Any, Optional, List

from intelligence.agents.agent_router import agent_router
from core.kernel.context_manager import context_manager
from core.guardrails.tool_schema_validator import tool_schema_validator
from core.kernel.autonomous_repair_loop import autonomous_repair_loop

logger = logging.getLogger("AgentGoalSolver")


class AgentGoalSolver:
    """
    Primary Autonomous Orchestration Engine for JKAI Zenith.
    Executes user goals end-to-end with planning, tool invocation, and self-healing.
    """
    def __init__(self):
        self.active_tasks: Dict[str, Dict[str, Any]] = {}

    async def solve_goal(self, user_prompt: str, task_id: str = "task_001", max_steps: int = 10) -> Dict[str, Any]:
        """
        Executes a user request autonomously:
        1. Routes task to specialized Agent
        2. Builds system prompt & applies .jkairules.json
        3. Enforces Context Pruner
        4. Runs execution loop with tool validation & autonomous self-repair fallback
        """
        logger.info(f"🚀 [GOAL-SOLVER-START] Initiating Goal Task `{task_id}`: '{user_prompt[:80]}...'")

        # Step 1: Select Specialized Agent
        agent = agent_router.route_task(user_prompt)
        logger.info(f"🤖 [GOAL-SOLVER] Selected Agent: `{agent['name']}` (Model: `{agent.get('model_preference', 'qwen3.5:4b')}`)")

        # Step 2: Build Master Prompt
        from core.utils.engine import engine
        
        messages = [
            {"role": "system", "content": agent["system_prompt"]},
            {"role": "user", "content": user_prompt}
        ]

        steps_taken = 0
        execution_trace = []

        while steps_taken < max_steps:
            steps_taken += 1
            logger.info(f"🔄 [GOAL-SOLVER-STEP {steps_taken}/{max_steps}] Querying Model...")

            # Step 3: Prune context to fit token window
            pruned_msgs = context_manager.prune_messages(messages)

            # Step 4: Call LLM Engine
            try:
                response_text = await engine.call_chat(
                    pruned_msgs,
                    role=agent["name"].upper(),
                    task_id=task_id,
                    skip_build_final=False
                )
            except Exception as e:
                logger.error(f"❌ [GOAL-SOLVER-ERR] Engine call failed: {e}")
                return {"status": "error", "task_id": task_id, "error": str(e), "steps": steps_taken}

            messages.append({"role": "assistant", "content": response_text})
            execution_trace.append({"step": steps_taken, "response": response_text})

            # Check if LLM requested a Tool Call
            tool_name, args, err = tool_schema_validator.parse_tool_call(response_text)

            if not tool_name:
                # LLM produced non-tool conversational output -> Goal Complete or direct answer
                logger.info(f"✅ [GOAL-SOLVER-COMPLETE] Goal solved in {steps_taken} steps!")
                return {
                    "status": "success",
                    "task_id": task_id,
                    "agent": agent["name"],
                    "final_output": response_text,
                    "steps_taken": steps_taken,
                    "trace": execution_trace
                }

            if tool_name and args is not None:
                logger.info(f"🛠️ [GOAL-SOLVER-TOOL] Invoking tool `{tool_name}` with args: {args}")
                
                # Special handle: Python script execution -> Send to Autonomous Repair Loop
                if tool_name in ["run_python_script", "execute_script", "python_runner"] and "script_path" in args:
                    script_path = args["script_path"]
                    repair_result = await autonomous_repair_loop.execute_and_self_heal(script_path, task_id=task_id)
                    tool_output = json.dumps(repair_result, ensure_ascii=False)
                else:
                    # Mock or invoke tool from registry
                    tool_output = f"Tool `{tool_name}` executed successfully."

                messages.append({"role": "user", "content": f"[TOOL_OUTPUT for {tool_name}]:\n{tool_output}"})

        return {
            "status": "partial",
            "task_id": task_id,
            "agent": agent["name"],
            "msg": f"Reached max steps limit ({max_steps})",
            "trace": execution_trace
        }


agent_goal_solver = AgentGoalSolver()
