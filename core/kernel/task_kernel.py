from __future__ import annotations
import time
import json
from typing import List, Dict, Any, Optional, Tuple, Set
from dataclasses import dataclass, field, replace

from core.kernel.state_machine import TaskState, StateTransitionGraph, StateInvariantViolation
from core.kernel.event_journal import event_journal
from core.redis_client import redis_safe
from core.utils.engine import engine

from enum import Enum

class StepStatus(str, Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED  = "failed"
    ABORTED = "aborted"

@dataclass(frozen=True)
class CognitiveState:
    """
    🧠 JKAI ZENITH: IMMUTABLE COGNITIVE STATE v5.0
    The clean, immutable snapshot of the task's state, beliefs, and telemetry.
    """
    task_id: str
    session_id: str
    goal: str
    mode: str = "fast"
    current_state: TaskState = TaskState.RECEIVED
    
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
    working_memory: Dict[str, Any] = field(default_factory=lambda: {
        "sensory": [], "working": [], "episodic": [], "semantic": {}
    })
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
            "status": self.current_state.value,
            "progress": f"{self.steps_done}/{self.steps_total}",
            "confidence": round(1.0 - (len(self.contradictions) * 0.1) - (self.replan_count * 0.05), 2),
            "budget": self.cognitive_budget,
            "replan_count": self.replan_count,
            "facts_count": len(self.beliefs),
            "version": self.version,
            "updated_at": time.time()
        }


class CognitiveTaskKernel:
    """
    🏛️ COGNITIVE TASK KERNEL (Zenith OS Kernel Core)
    The single authority controlling state transitions, event journals, 
    and persistence. Subsystems MUST query and alter state strictly via the kernel.
    """
    def __init__(self, task_id: str, initial_state: CognitiveState):
        self.task_id = task_id
        self._state = initial_state
        self.history: List[TaskState] = [initial_state.current_state]

    @property
    def current_state(self) -> TaskState:
        return self._state.current_state

    @property
    def state(self) -> CognitiveState:
        return self._state

    def get_snapshot(self) -> dict:
        return self._state.get_snapshot()

    def transition(self, 
                   new_state: TaskState, 
                   actor: str, 
                   reason: str = "", 
                   payload: Optional[Dict[str, Any]] = None) -> CognitiveState:
        """
        ⚡ ATOMIC TRANSITION GATES
        Validates transition, alters state, saves checkpoints, and appends journals.
        """
        current_state = self._state.current_state
        
        # 1. Validate Transition
        StateTransitionGraph.validate_transition(current_state, new_state)
        
        # 2. Update Immutable State State
        self._state = replace(
            self._state, 
            current_state=new_state, 
            version=self._state.version + 1
        )
        self.history.append(new_state)
        
        # 3. Log to Event Journal (Redis & SQLite)
        event_journal.append(
            task_id=self.task_id,
            trace_id=self._state.session_id,
            actor=actor,
            event_type=f"STATE_TRANSITION_{new_state.value}",
            state_before=current_state.value,
            state_after=new_state.value,
            payload={
                "reason": reason,
                "payload": payload or {}
            }
        )
        
        # 4. Save Persistent Checkpoint (Hot Path)
        self.save_checkpoint()
        
        # 5. Live Publish Telemetry
        engine.publish_mission_log(
            "KERNEL", 
            f"🌀 [STATE-TRANSITION]: {current_state.value} -> {new_state.value} (Actor: {actor} | Reason: {reason})",
            self.task_id, 
            self._state.session_id
        )
        
        return self._state

    def apply_event(self, event_type: str, actor: str, payload: Dict[str, Any]):
        """Applies a non-transition semantic event and increments version."""
        updated_state = self._state
        
        if event_type == "BELIEF_ADDED":
            beliefs_list = list(self._state.beliefs)
            beliefs_list.append(payload)
            updated_state = replace(
                self._state, 
                beliefs=tuple(beliefs_list), 
                version=self._state.version + 1
            )
        elif event_type == "TOOL_EXECUTED":
            completed_list = list(self._state.completed_steps)
            completed_list.append(payload.get("step_id", ""))
            updated_state = replace(
                self._state,
                completed_steps=tuple(completed_list),
                steps_done=self._state.steps_done + 1,
                total_latency=self._state.total_latency + payload.get("duration", 0.0),
                version=self._state.version + 1
            )
        elif event_type == "TOOL_FAILED":
            failed_list = list(self._state.failed_steps)
            failed_list.append(payload)
            
            fingerprints = set(self._state.failed_fingerprints)
            fingerprints.add(payload.get("fingerprint", ""))
            
            updated_state = replace(
                self._state,
                failed_steps=tuple(failed_list),
                failed_fingerprints=frozenset(fingerprints),
                version=self._state.version + 1
            )
        elif event_type == "REPLANNED":
            updated_state = replace(
                self._state, 
                replan_count=self._state.replan_count + 1, 
                version=self._state.version + 1
            )
        elif event_type == "REFLECTED":
            notes_list = list(self._state.reflection_notes)
            notes_list.append(payload)
            updated_state = replace(
                self._state,
                reflection_notes=tuple(notes_list),
                version=self._state.version + 1
            )
            
        self._state = updated_state
        
        # Log to Journal
        event_journal.append(
            task_id=self.task_id,
            trace_id=self._state.session_id,
            actor=actor,
            event_type=event_type,
            state_before=self._state.current_state.value,
            state_after=self._state.current_state.value,
            payload=payload
        )
        
        # Save Checkpoint
        self.save_checkpoint()

    def save_checkpoint(self):
        """Saves current mutable workspace snapshots in Redis."""
        def _save(r):
            # Compact snapshot for dashboard
            r.set(f"cog_state:{self.task_id}", json.dumps(self._state.get_snapshot(), ensure_ascii=False))
            
            # Absolute recovery checkpoint
            state_data = self._state.__dict__.copy()
            state_data['current_state'] = self._state.current_state.value
            state_data['failed_fingerprints'] = list(state_data['failed_fingerprints'])
            state_data['steps'] = dict(state_data['steps'])
            r.set(f"cog_state_full:{self.task_id}", json.dumps(state_data, ensure_ascii=False), ex=86400)
        
        redis_safe(_save)

    @classmethod
    def load_checkpoint(cls, task_id: str) -> Optional[CognitiveTaskKernel]:
        """Loads and recovers a task kernel from Redis (essential for worker crash recovery)."""
        def _load(r):
            val = r.get(f"cog_state_full:{task_id}")
            if val:
                return json.loads(val)
            return None
            
        data = redis_safe(_load)
        if not data:
            return None
            
        try:
            state = CognitiveState(
                task_id=data["task_id"],
                session_id=data["session_id"],
                goal=data["goal"],
                mode=data.get("mode", "fast"),
                current_state=TaskState(data["current_state"]),
                steps=data.get("steps", {}),
                steps_done=data.get("steps_done", 0),
                steps_total=data.get("steps_total", 0),
                completed_steps=tuple(data.get("completed_steps", [])),
                failed_steps=tuple(data.get("failed_steps", [])),
                failed_fingerprints=frozenset(data.get("failed_fingerprints", [])),
                beliefs=tuple(data.get("beliefs", [])),
                contradictions=tuple(data.get("contradictions", [])),
                working_memory=data.get("working_memory", {}),
                attention=tuple(data.get("attention", [])),
                reflection_notes=tuple(data.get("reflection_notes", [])),
                start_ts=data.get("start_ts", time.time()),
                end_ts=data.get("end_ts"),
                total_latency=data.get("total_latency", 0.0),
                replan_count=data.get("replan_count", 0),
                version=data.get("version", 0),
                cognitive_budget=data.get("cognitive_budget", 100.0),
                budget_history=tuple(data.get("budget_history", []))
            )
            return cls(task_id, state)
        except Exception as e:
            print(f"❌ [KERNEL-LOAD-ERR]: Cannot parse checkpoint state data: {e}")
            return None
            
    @property
    def fatigue_score(self) -> float:
        # Calculate dynamic fatigue score
        s = self._state
        raw = (s.replan_count * 0.12 + len(s.failed_steps) * 0.18 + s.total_latency / 280.0)
        return min(raw, 1.0)

    @property
    def confidence_score(self) -> float:
        s = self._state
        if not s.beliefs:
            return 1.0
        return sum(b.get("confidence", 0.5) for b in s.beliefs) / len(s.beliefs)
