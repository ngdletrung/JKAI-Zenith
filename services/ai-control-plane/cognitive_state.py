from __future__ import annotations
import time
import json
from enum import Enum
from dataclasses import dataclass, field, replace
from typing import List, Dict, Any, Optional, Tuple

class StepStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED  = "failed"
    ABORTED = "aborted"

# ══════════════════════════════════════════════════════════════════
# [+] COGNITIVE EVENTS
# ══════════════════════════════════════════════════════════════════

class CogEventType(str, Enum):
    STEP_STARTED = "StepStarted"
    TOOL_EXECUTED = "ToolExecuted"
    TOOL_FAILED = "ToolFailed"
    BELIEF_ADDED = "BeliefAdded"
    REPLANNED = "Replanned"
    LOOP_BLOCKED = "LoopBlocked"
    TASK_FINALIZED = "TaskFinalized"
    MEMORY_PRUNED = "MemoryPruned"
    SPECULATIVE_WIN = "SpeculativeWin"
    REFLECTED = "Reflected"
    SENSORY_UPDATED = "SensoryUpdated"

@dataclass
class CogEvent:
    type: CogEventType
    timestamp: float = field(default_factory=time.time)
    payload: dict = field(default_factory=dict)

# ══════════════════════════════════════════════════════════════════
# [+] IMMUTABLE STATE
# ══════════════════════════════════════════════════════════════════

@dataclass(frozen=True)
class CognitiveState:
    """
    🧠 JKAI ZENITH: IMMUTABLE COGNITIVE STATE v4.1
    Trạng thái nhận thức bất biến.
    """
    task_id: str
    session_id: str
    goal: str
    mode: str = "fast"
    status: str = "initializing"
    
    # 📊 [EXECUTION-DAG]
    steps: Dict[str, Dict] = field(default_factory=dict)
    steps_done: int = 0
    steps_total: int = 0
    completed_steps: Tuple[str, ...] = ()
    failed_steps: Tuple[Dict, ...] = ()
    failed_fingerprints: frozenset[str] = field(default_factory=frozenset)
    
    # 🧬 [BELIEF-SYSTEM]
    beliefs: Tuple[Dict, ...] = ()
    contradictions: Tuple[Dict, ...] = ()
    working_memory: Dict[str, Any] = field(default_factory=lambda: {"sensory": [], "working": [], "episodic": [], "semantic": {}})
    attention: Tuple[Dict, ...] = ()
    reflection_notes: Tuple[Dict, ...] = ()
    
    # ⏱️ [CHRONOS-TELEMETRY]
    start_ts: float = field(default_factory=time.time)
    end_ts: Optional[float] = None
    total_latency: float = 0.0
    replan_count: int = 0
    version: int = 0
    
    # 💰 [COGNITIVE-BUDGET]
    cognitive_budget: float = 100.0
    budget_history: Tuple[Dict, ...] = ()

    def get_snapshot(self) -> dict:
        return {
            "task_id": self.task_id,
            "goal": self.goal,
            "status": self.status,
            "progress": f"{self.steps_done}/{self.steps_total}",
            "confidence": 1.0 - (len(self.contradictions) * 0.1) - (self.replan_count * 0.05),
            "budget": self.cognitive_budget,
            "replan_count": self.replan_count,
            "facts_count": len(self.beliefs),
            "version": self.version
        }

class CognitiveStateStore:
    def __init__(self, redis_fn):
        self.redis_fn = redis_fn

    def save(self, state: CognitiveState):
        def _save(r):
            # Snapshot cho Dashboard
            r.set(f"cog_state:{state.task_id}", json.dumps(state.get_snapshot(), ensure_ascii=False))
            # Full State cho Recovery
            data = state.__dict__.copy()
            data['failed_fingerprints'] = list(data['failed_fingerprints'])
            data['steps'] = dict(data['steps'])
            r.set(f"cog_state_full:{state.task_id}", json.dumps(data, ensure_ascii=False), ex=3600)
        self.redis_fn(_save)

def create_cognitive_state(task_id, session_id, goal, mode, steps=[]):
    return CognitiveState(
        task_id=task_id,
        session_id=session_id,
        goal=goal,
        mode=mode,
        steps_total=len(steps)
    )
