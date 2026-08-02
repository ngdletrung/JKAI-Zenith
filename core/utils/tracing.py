import logging
import os
import time
import uuid
import contextvars
import inspect
from functools import wraps
from typing import Optional, Any, Callable

logger = logging.getLogger("jkai.core.tracing")

# Context variable to store trace_id for the current execution context (async task/thread)
_trace_id_var: contextvars.ContextVar[Optional[str]] = contextvars.ContextVar("trace_id", default=None)

def get_trace_id() -> Optional[str]:
    """Retrieve the trace_id of the current context, if any."""
    return _trace_id_var.get()

def set_trace_id(trace_id: str) -> Any:
    """Set the trace_id for the current context."""
    return _trace_id_var.set(trace_id)

def clear_trace_id(token: Any) -> None:
    """Clear/reset the trace_id using the contextvars token."""
    _trace_id_var.reset(token)

class TraceContext:
    """
    Context manager to track execution blocks, manage trace_id,
    and measure/log latency.
    """
    def __init__(self, name: str, trace_id: Optional[str] = None, **extra_attrs):
        self.name = name
        self.trace_id = trace_id or get_trace_id() or str(uuid.uuid4())
        self.extra_attrs = extra_attrs
        self.start_time = None
        self.token = None

    def __enter__(self):
        self.token = _trace_id_var.set(self.trace_id)
        self.start_time = time.perf_counter()
        attrs_str = " | ".join(f"{k}={v}" for k, v in self.extra_attrs.items())
        extra = f" | {attrs_str}" if attrs_str else ""
        logger.info(
            f"[Trace] [Start] {self.name} | trace_id={self.trace_id}{extra}"
        )
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        duration = (time.perf_counter() - self.start_time) * 1000  # in ms
        status = "SUCCESS" if exc_type is None else "FAILED"
        attrs_str = " | ".join(f"{k}={v}" for k, v in self.extra_attrs.items())
        extra = f" | {attrs_str}" if attrs_str else ""
        
        if exc_type:
            logger.error(
                f"[Trace] [End] {self.name} | trace_id={self.trace_id} | status={status} | duration={duration:.2f}ms | error={exc_val}{extra}"
            )
        else:
            logger.info(
                f"[Trace] [End] {self.name} | trace_id={self.trace_id} | status={status} | duration={duration:.2f}ms{extra}"
            )
        
        if self.token:
            _trace_id_var.reset(self.token)
        return False

def trace(name: Optional[str] = None, **extra_attrs):
    """
    Decorator supporting both sync and async functions to measure execution time,
    propagate trace_id, and structured-log execution status.
    """
    def decorator(func: Callable):
        trace_name = name or func.__qualname__ or func.__name__
        
        if inspect.iscoroutinefunction(func):
            @wraps(func)
            async def async_wrapper(*args, **kwargs):
                with TraceContext(trace_name, **extra_attrs):
                    return await func(*args, **kwargs)
            return async_wrapper
        else:
            @wraps(func)
            def sync_wrapper(*args, **kwargs):
                with TraceContext(trace_name, **extra_attrs):
                    return func(*args, **kwargs)
            return sync_wrapper
    return decorator

# Specific helper functions to record flow details:
# SIL start, end, cache hit/miss, realtime cascade result, and execution times.

def log_sil_start(query: str, trace_id: Optional[str] = None) -> str:
    """Log the start of Search Intelligence Layer (SIL) processing."""
    t_id = trace_id or get_trace_id() or str(uuid.uuid4())
    logger.info(f"[SIL] [Start] trace_id={t_id} | query={query}")
    return t_id

def log_sil_end(trace_id: str, duration_ms: float, status: str = "SUCCESS", details: Optional[str] = None):
    """Log the completion of SIL processing with execution time."""
    extra = f" | details={details}" if details else ""
    logger.info(f"[SIL] [End] trace_id={trace_id} | status={status} | duration={duration_ms:.2f}ms{extra}")

def log_cache_event(event_type: str, key: str, is_hit: bool, trace_id: Optional[str] = None):
    """Log cache hit or miss events with trace_id context."""
    t_id = trace_id or get_trace_id() or "N/A"
    hit_status = "HIT" if is_hit else "MISS"
    logger.info(f"[Cache] [{hit_status}] trace_id={t_id} | type={event_type} | key={key}")

def log_cascade_result(step_name: str, result_summary: str, duration_ms: float, trace_id: Optional[str] = None):
    """Log step-level cascade results and duration."""
    t_id = trace_id or get_trace_id() or "N/A"
    logger.info(f"[Cascade] [Step] trace_id={t_id} | step={step_name} | status=SUCCESS | duration={duration_ms:.2f}ms | result={result_summary}")

def init_tracing(service_name: str, app=None):
    """
    Backward-compatible initialization.
    No-op return for compatibility with other service files.
    """
    logger.info(f"Structured tracing initialized for service: {service_name}")
    return None
