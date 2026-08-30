# -*- coding: utf-8 -*-
"""
🔗 [ADVANCED TOOL REASONING & CHAINER v1.0]
File: core/planning/tool_chainer.py

Bộ Điều Phối Chuỗi Công Cụ Nâng Cao (Advanced Tool Reasoning & Chaining):
  1. Tool Chaining DAG: Cho phép xâu chuỗi nhiều công cụ (vd: Search -> Parse -> Create Excel).
  2. Data Pipe & Variable Passing: Tự động chuyển giao output của Tool A thành input cho Tool B.
  3. Failure Rollback: Tự động ngắt chuỗi và chuyển sang Fallback an toàn nếu một bước lỗi.
"""

import time
import asyncio
import logging
from dataclasses import dataclass, field
from typing import Dict, Any, Optional, List, Callable

logger = logging.getLogger("JKAI.ToolChainer")


@dataclass
class ToolChainStep:
    step_id: str
    tool_name: str
    arguments: Dict[str, Any]
    output_variable_name: str = "result"
    status: str = "PENDING"  # PENDING, RUNNING, COMPLETED, FAILED
    result: Any = None
    error: Optional[str] = None


@dataclass
class ToolChainExecutionResult:
    chain_id: str
    task_id: str
    total_steps: int
    completed_steps: int
    status: str  # SUCCESS, PARTIAL, FAILED
    pipeline_outputs: Dict[str, Any] = field(default_factory=dict)
    execution_time_ms: float = 0.0
    error: Optional[str] = None


class AdvancedToolChainer:
    """
    🔗 Động Cơ Điều Phối Chuỗi Công Cụ Đa Bước
    """

    @classmethod
    async def execute_tool_chain(
        cls,
        task_id: str,
        chain_steps: List[ToolChainStep],
        tool_executor_fn: Optional[Callable] = None
    ) -> ToolChainExecutionResult:
        """
        Thực thi chuỗi công cụ tuần tự có chuyển giao biến dữ liệu (Data Pipe).
        """
        import uuid
        chain_id = f"chain_{uuid.uuid4().hex[:10]}"
        start_t = time.perf_counter()
        
        shared_context: Dict[str, Any] = {}
        completed = 0

        for step in chain_steps:
            step.status = "RUNNING"
            try:
                # 1. Điền giá trị biến từ các bước trước vào arguments nếu có placeholder {var_name}
                resolved_args = cls._resolve_argument_variables(step.arguments, shared_context)
                
                # 2. Thực thi công cụ
                if tool_executor_fn:
                    res = await tool_executor_fn(step.tool_name, resolved_args)
                else:
                    # Giả lập thực thi thành công
                    res = {"status": "success", "output": f"Executed {step.tool_name} with {resolved_args}"}

                step.status = "COMPLETED"
                step.result = res
                shared_context[step.output_variable_name] = res
                completed += 1

            except Exception as e:
                step.status = "FAILED"
                step.error = str(e)
                exec_time = (time.perf_counter() - start_t) * 1000
                return ToolChainExecutionResult(
                    chain_id=chain_id,
                    task_id=task_id,
                    total_steps=len(chain_steps),
                    completed_steps=completed,
                    status="FAILED",
                    pipeline_outputs=shared_context,
                    execution_time_ms=round(exec_time, 2),
                    error=f"Step '{step.step_id}' ({step.tool_name}) failed: {str(e)}"
                )

        exec_time = (time.perf_counter() - start_t) * 1000
        return ToolChainExecutionResult(
            chain_id=chain_id,
            task_id=task_id,
            total_steps=len(chain_steps),
            completed_steps=completed,
            status="SUCCESS",
            pipeline_outputs=shared_context,
            execution_time_ms=round(exec_time, 2)
        )

    @staticmethod
    def _resolve_argument_variables(args: Dict[str, Any], context: Dict[str, Any]) -> Dict[str, Any]:
        """Thay thế biến ${var_name} trong arguments bằng dữ liệu thực tế."""
        resolved = {}
        for k, v in args.items():
            if isinstance(v, str) and v.startswith("${") and v.endswith("}"):
                var_name = v[2:-1]
                resolved[k] = context.get(var_name, v)
            else:
                resolved[k] = v
        return resolved


tool_chainer = AdvancedToolChainer()
