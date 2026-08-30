# -*- coding: utf-8 -*-
"""
🏛️ [FAST PIPELINE SPECULATIVE STATE MACHINE]
File: core/kernel/fast_state.py

Cấu trúc trạng thái bất biến (Immutable State Ledger) cho FastPipeline Speculative Stage Machine.
Quản lý trạng thái phân nhánh song song (Fork-Join), Token Budget, và Circuit Breaker.
"""

from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional
from core.os.routing.intent_router import RouteDecision, IntentMode


@dataclass
class FastState:
    goal: str
    task_id: str
    trace_id: str
    decision: RouteDecision
    
    # Context & Step Goal
    step_goal: str = ""
    system_prompt: str = ""
    messages: List[Dict[str, Any]] = field(default_factory=list)
    kb_context: str = ""
    is_kb_sufficient: bool = False
    
    # Token Budget Management
    token_usage: int = 0
    max_token_budget: int = 6000
    
    # Execution Observations & Signals
    observations: List[Dict[str, Any]] = field(default_factory=list)
    tool_signals: List[str] = field(default_factory=list)
    artifacts_created: List[str] = field(default_factory=list)
    
    # Speculative Execution Results
    cached_response: Optional[str] = None
    math_response: Optional[str] = None
    search_response: Optional[str] = None
    reflex_response: Optional[str] = None
    
    # Flow Control
    turn_count: int = 0
    max_turns: int = 1               # Mặc định 1 pass cho Speculative Fast Path
    is_completed: bool = False
    final_answer: str = ""
    error_message: Optional[str] = None
    circuit_breaker_triggered: bool = False
    
    # Observability & Timing (ms)
    latency_breakdown: Dict[str, float] = field(default_factory=dict)
    
    def record_latency(self, stage_name: str, duration_ms: float) -> None:
        self.latency_breakdown[stage_name] = round(duration_ms, 2)
        
    def add_artifact(self, file_path: str) -> None:
        if file_path and file_path not in self.artifacts_created:
            self.artifacts_created.append(file_path)
            
    def append_tool_signal(self, signal: str) -> None:
        if signal:
            self.tool_signals.append(signal)

    def estimate_tokens(self) -> int:
        """Ước lượng số token trong ngữ cảnh hiện tại (1 token ~ 4 ký tự)."""
        total_chars = sum(len(str(m.get("content", ""))) for m in self.messages)
        self.token_usage = total_chars // 4
        return self.token_usage
