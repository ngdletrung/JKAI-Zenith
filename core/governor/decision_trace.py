"""
🏛️ AMG v2 — DECISION TRACE
File: core/governor/decision_trace.py

Purpose:
    Structured, append-only audit trail for every AMG governor decision.
    Provides full observability into WHY a model was selected or rejected,
    supporting post-mortem analysis, regression detection, and human oversight.

Constitutional Principle:
    Every ExecutionProfile must have a traceable, human-readable reason.
    "AMG picked this model" is NOT sufficient — the trace must show
    capability scores, hardware constraints, and candidates evaluated.

Usage:
    decision_trace = DecisionTrace.from_governor_decision(decision, latency_ms=12.0)
    tracer = DecisionTracer(redis_client=r)
    await tracer.record(task_id, decision_trace)
    # Retrieval:
    traces = await tracer.get_recent(task_id, n=10)
"""

from __future__ import annotations
import json
import logging
import time
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

logger = logging.getLogger("AMG_DecisionTrace")

# Redis key prefix for decision traces
_TRACE_KEY_PREFIX = "amg:decision_trace"
_TRACE_TTL_SECONDS = 86400  # 24 hours


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------

@dataclass
class CandidateTrace:
    """Trace record for a single evaluated candidate model."""
    model_name: str
    capability_score: float           # 0.0–1.0 — how well capabilities match
    resource_score: float             # 0.0–1.0 — how well resources fit
    quality_score: float              # 0.0–1.0 — quality alignment
    composite_score: float            # Final weighted composite
    backend: str                      # GPU / CPU / HYBRID
    gpu_memory_mb: float              # Estimated GPU footprint
    ram_memory_mb: float              # Estimated RAM footprint
    model_classes: List[str] = field(default_factory=list)
    rejected_reason: Optional[str] = None  # None = selected, str = why rejected

    @property
    def was_selected(self) -> bool:
        return self.rejected_reason is None


@dataclass
class DecisionTrace:
    """
    Immutable snapshot of a single AMG governor decision.

    Fields are intentionally human-readable — this is an audit record
    that should be parseable by non-engineers.
    """
    # Core identification
    trace_id: str                        # UUID for deduplication
    role_name: str                       # e.g. "RECEPTIONIST"
    task_id: str = ""                    # Linked task (if available)
    timestamp_utc: float = field(default_factory=time.time)

    # Decision outcome
    selected_model: str = ""             # The winning model name
    resolved_via: str = ""              # "auto" | "explicit" | "fallback" | "emergency_fallback"
    backend: str = ""                   # GPU / CPU / HYBRID
    num_ctx: int = 0
    temperature: float = 0.0

    # Reasoning (capability-driven, never name-driven)
    role_required_classes: List[str] = field(default_factory=list)
    capability_requirements: List[str] = field(default_factory=list)
    quality_target: str = "medium"       # low | medium | high | highest
    hardware_state_vram_free_mb: float = 0.0
    hardware_state_ram_free_gb: float = 0.0

    # Candidates evaluated
    candidates_evaluated: List[CandidateTrace] = field(default_factory=list)
    candidates_count: int = 0           # Total candidates before filtering

    # Performance
    decision_latency_ms: float = 0.0    # Time to reach decision

    # Human-readable summary
    decision_summary: str = ""          # One-sentence explanation

    @classmethod
    def from_governor_decision(
        cls,
        decision,                    # GovernorDecision from portfolio_governor
        role: str,
        task_id: str = "",
        latency_ms: float = 0.0,
        hw_vram_free_mb: float = 0.0,
        hw_ram_free_gb: float = 0.0,
    ) -> "DecisionTrace":
        """
        Build a DecisionTrace from a GovernorDecision (output of PortfolioGovernor).
        """
        import uuid

        candidates: List[CandidateTrace] = []
        for score in getattr(decision, "candidates_evaluated", []):
            candidates.append(CandidateTrace(
                model_name=getattr(score, "model_name", "unknown"),
                capability_score=getattr(score, "capability_score", 0.0),
                resource_score=getattr(score, "resource_score", 0.0),
                quality_score=getattr(score, "quality_score", 0.0),
                composite_score=getattr(score, "composite_score", 0.0),
                backend=getattr(score, "backend", ""),
                gpu_memory_mb=getattr(score, "gpu_memory_mb", 0.0),
                ram_memory_mb=getattr(score, "ram_memory_mb", 0.0),
                model_classes=[c.name for c in getattr(score, "model_classes", [])],
                rejected_reason=getattr(score, "rejection_reason", None),
            ))

        winner = decision.selected_model
        n_candidates = len(candidates)

        # Build one-sentence human-readable summary
        if decision.resolved_via == "emergency_fallback":
            summary = (
                f"EMERGENCY FALLBACK for role={role}: no candidate met capability thresholds. "
                f"Selected {winner!r} as last resort."
            )
        elif decision.resolved_via == "explicit":
            summary = f"Explicit model override for role={role}: {winner!r} assigned directly (no AMG scoring)."
        else:
            top = max(candidates, key=lambda c: c.composite_score) if candidates else None
            summary = (
                f"AMG selected {winner!r} for role={role} "
                f"(composite_score={top.composite_score:.3f if top else 'N/A'}) "
                f"from {n_candidates} candidates via {decision.resolved_via}."
            )

        return cls(
            trace_id=str(uuid.uuid4()),
            role_name=role.upper(),
            task_id=task_id,
            timestamp_utc=time.time(),
            selected_model=winner,
            resolved_via=decision.resolved_via,
            backend=getattr(decision, "backend", ""),
            num_ctx=getattr(decision, "num_ctx", 0),
            temperature=getattr(decision, "temperature", 0.0),
            capability_requirements=getattr(decision, "capability_requirements", []),
            quality_target=getattr(decision, "quality_target", "medium"),
            hardware_state_vram_free_mb=hw_vram_free_mb,
            hardware_state_ram_free_gb=hw_ram_free_gb,
            candidates_evaluated=candidates,
            candidates_count=n_candidates,
            decision_latency_ms=latency_ms,
            decision_summary=summary,
        )

    @classmethod
    def explicit(
        cls,
        role: str,
        model_name: str,
        task_id: str = "",
    ) -> "DecisionTrace":
        """Create a minimal trace for explicit (non-auto) model assignments."""
        import uuid
        return cls(
            trace_id=str(uuid.uuid4()),
            role_name=role.upper(),
            task_id=task_id,
            selected_model=model_name,
            resolved_via="explicit",
            decision_summary=f"Explicit: {model_name!r} assigned to role={role} directly.",
        )

    def to_dict(self) -> Dict[str, Any]:
        """Serialize to JSON-compatible dict."""
        d = asdict(self)
        return d

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)

    @classmethod
    def from_json(cls, raw: str) -> "DecisionTrace":
        data = json.loads(raw)
        candidates = [CandidateTrace(**c) for c in data.pop("candidates_evaluated", [])]
        return cls(candidates_evaluated=candidates, **data)


# ---------------------------------------------------------------------------
# Tracer — Redis-backed persistence (optional, graceful fallback)
# ---------------------------------------------------------------------------

class DecisionTracer:
    """
    Persists DecisionTrace objects to Redis for observability.
    Falls back to in-memory deque when Redis is unavailable.
    """
    MAX_IN_MEMORY = 50   # Per-role, in-memory fallback

    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._in_memory: Dict[str, List[DecisionTrace]] = {}

    def record(self, trace: DecisionTrace) -> None:
        """
        Record a DecisionTrace synchronously.
        Redis: append to per-role sorted set (score = timestamp).
        Fallback: in-memory list (latest N).
        """
        key = f"{_TRACE_KEY_PREFIX}:{trace.role_name}"
        raw = trace.to_json()

        if self._redis:
            try:
                pipe = self._redis.pipeline()
                pipe.zadd(key, {raw: trace.timestamp_utc})
                # Keep only the last 100 entries per role
                pipe.zremrangebyrank(key, 0, -101)
                pipe.expire(key, _TRACE_TTL_SECONDS)
                pipe.execute()
                return
            except Exception as e:
                logger.warning(f"[TRACE-REDIS-FAIL]: {e} — falling back to in-memory")

        # In-memory fallback
        if trace.role_name not in self._in_memory:
            self._in_memory[trace.role_name] = []
        buf = self._in_memory[trace.role_name]
        buf.append(trace)
        if len(buf) > self.MAX_IN_MEMORY:
            self._in_memory[trace.role_name] = buf[-self.MAX_IN_MEMORY:]

    def get_recent(self, role: str, n: int = 10) -> List[DecisionTrace]:
        """Retrieve the N most recent traces for a role."""
        key = f"{_TRACE_KEY_PREFIX}:{role.upper()}"

        if self._redis:
            try:
                raws = self._redis.zrevrange(key, 0, n - 1)
                return [DecisionTrace.from_json(r if isinstance(r, str) else r.decode()) for r in raws]
            except Exception as e:
                logger.warning(f"[TRACE-REDIS-READ-FAIL]: {e}")

        buf = self._in_memory.get(role.upper(), [])
        return list(reversed(buf[-n:]))

    def get_last(self, role: str) -> Optional[DecisionTrace]:
        """Get the single most recent trace for a role."""
        recent = self.get_recent(role, n=1)
        return recent[0] if recent else None

    def clear(self, role: Optional[str] = None) -> None:
        """Clear traces (used in tests)."""
        if role:
            self._in_memory.pop(role.upper(), None)
            if self._redis:
                try:
                    self._redis.delete(f"{_TRACE_KEY_PREFIX}:{role.upper()}")
                except Exception:
                    pass
        else:
            self._in_memory.clear()


# ---------------------------------------------------------------------------
# Module-level singleton tracer (lazy Redis init)
# ---------------------------------------------------------------------------

_tracer: Optional[DecisionTracer] = None


def get_tracer() -> DecisionTracer:
    """Get or create the module-level DecisionTracer (lazy Redis init)."""
    global _tracer
    if _tracer is None:
        redis_client = None
        try:
            from core.utils.redis_client import redis_safe
            redis_client = redis_safe(lambda r: r)
        except Exception:
            pass
        _tracer = DecisionTracer(redis_client=redis_client)
    return _tracer
