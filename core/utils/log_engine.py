import asyncio
import json
import logging
import os
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, List, Optional, Set

logger = logging.getLogger("LogEngine")

_FLUSH_INTERVAL = 0.5
_MAX_BATCH = 50


def _is_test_mode() -> bool:
    """Isolate pytest / test runs from publishing to live production Redis channels."""
    if os.getenv("JKAI_ALLOW_TEST_REDIS_PUBLISH") == "1":
        return False
    return bool(
        os.getenv("PYTEST_CURRENT_TEST")
        or os.getenv("JKAI_TEST_MODE", "").lower() in ("1", "true", "yes")
    )


def _normalize_task_id(task_id: Optional[str]) -> str:
    """Ensure task_id is never None or the literal string 'None'."""
    if task_id is None:
        return "system"
    cleaned = str(task_id).strip()
    if not cleaned or cleaned.lower() == "none":
        return "system"
    return cleaned


class LogEngine:
    def __init__(self):
        self._redis = None
        self._queue: deque[Dict[str, Any]] = deque()
        self._flush_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None
        self._stopped_tasks: Set[str] = set()
        self._global_stopped: bool = False
        self._test_log_buffer: List[Dict[str, Any]] = []
        self._discarded_after_stop_count: int = 0

    def mark_task_stopped(self, task_id: Optional[str] = None) -> int:
        """Mark a task (or global if None) as stopped and purge queued callbacks/logs."""
        if task_id and str(task_id).strip().lower() not in ("", "none", "system"):
            self._stopped_tasks.add(str(task_id).strip())
        else:
            self._global_stopped = True
        return self.clear_task_queue(task_id)

    def clear_stopped_state(self, task_id: Optional[str] = None) -> None:
        """Clear stopped state for a specific task or reset global stop."""
        if task_id:
            self._stopped_tasks.discard(str(task_id).strip())
        else:
            self._stopped_tasks.clear()
            self._global_stopped = False

    def clear_task_queue(self, task_id: Optional[str] = None) -> int:
        """Purge pending queued log/thought entries for task_id (or all if None)."""
        if not self._queue:
            return 0
        if not task_id or str(task_id).strip().lower() in ("", "none", "system"):
            removed = len(self._queue)
            self._queue.clear()
            self._discarded_after_stop_count += removed
            return removed
        target = str(task_id).strip()
        kept: deque[Dict[str, Any]] = deque()
        removed = 0
        for item in self._queue:
            if item.get("task_id") == target:
                removed += 1
            else:
                kept.append(item)
        self._queue = kept
        self._discarded_after_stop_count += removed
        return removed

    def _is_stopped(self, task_id: Optional[str], redis_conn: Any = None) -> bool:
        """Check in-memory stop token and Redis stop signal."""
        if self._global_stopped:
            return True
        norm_id = _normalize_task_id(task_id)
        if norm_id in self._stopped_tasks:
            return True
        try:
            from core.utils.engine import should_stop
            if should_stop(norm_id if norm_id != "system" else None, redis_conn):
                if norm_id != "system":
                    self._stopped_tasks.add(norm_id)
                return True
        except Exception:
            pass
        return False

    @staticmethod
    def _is_stop_control_message(tag_or_role: str, msg: str) -> bool:
        """Allow explicit STOP/STOPPED control confirmations to be recorded, block everything else after stop."""
        u_tag = str(tag_or_role or "").upper()
        if u_tag in ("STOP", "STOPPED"):
            return True
        m_up = str(msg or "").upper()
        return "[STOP]" in m_up or "[STOPPED]" in m_up or "GIAO THỨC DỪNG" in m_up

    def _get_redis(self, engine_instance=None):
        if _is_test_mode():
            return None
        if engine_instance:
            return engine_instance._get_redis()
        if self._redis is None:
            try:
                import redis as rd
                self._redis = rd.Redis(
                    host="redis-ai", port=6379, db=0,
                    password=os.getenv("REDIS_PASSWORD"),
                    socket_timeout=3, socket_connect_timeout=3,
                    decode_responses=True
                )
            except Exception:
                self._redis = False
        return self._redis if self._redis else None

    def _ensure_flush_task(self):
        try:
            loop = asyncio.get_running_loop()
            if self._flush_task is None or self._flush_task.done():
                self._flush_task = loop.create_task(self._flush_loop())
        except RuntimeError:
            pass

    async def _flush_loop(self):
        while True:
            await asyncio.sleep(_FLUSH_INTERVAL)
            if not self._queue:
                continue
            if _is_test_mode():
                self._queue.clear()
                continue
            r = self._get_redis()
            if not r:
                self._queue.clear()
                continue
            batch = []
            while self._queue and len(batch) < _MAX_BATCH:
                entry = self._queue.popleft()
                entry_tid = entry.get("task_id")
                if self._is_stopped(entry_tid, r) and not entry.get("is_stop_control"):
                    self._discarded_after_stop_count += 1
                    continue
                batch.append(entry)
            if not batch:
                continue
            try:
                pipe = r.pipeline()
                for entry in batch:
                    channel = entry["channel"]
                    payload = entry["payload"]
                    pipe.publish(channel, payload)
                    if entry.get("save_history"):
                        history_key = entry.get("history_key", "monitor:log_history")
                        max_len = entry.get("history_max", 999)
                        pipe.lpush(history_key, payload)
                        pipe.ltrim(history_key, 0, max_len)
                pipe.execute()
            except Exception as e:
                logger.warning("[LOG_FLUSH] batch=%d err=%s", len(batch), e)

    def _enqueue(self, channel: str, payload: str,
                 save_history: bool = False,
                 history_key: str = "monitor:log_history",
                 history_max: int = 999,
                 task_id: str = "system",
                 is_stop_control: bool = False):
        self._queue.append({
            "channel": channel,
            "payload": payload,
            "save_history": save_history,
            "history_key": history_key,
            "history_max": history_max,
            "task_id": _normalize_task_id(task_id),
            "is_stop_control": is_stop_control,
        })
        self._ensure_flush_task()

    def _publish_now(self, r, channel: str, payload: str,
                     save_history: bool = False,
                     history_key: str = "monitor:log_history",
                     history_max: int = 999):
        if _is_test_mode() or not r:
            return
        try:
            r.publish(channel, payload)
            if save_history:
                r.lpush(history_key, payload)
                r.ltrim(history_key, 0, history_max)
        except Exception as e:
            logger.warning("[LOG_NOW] err=%s", e)

    def publish_thought(self, role, thought, task_id="system",
                        stream_id=None, is_delta=False, is_first_chunk=False,
                        redis_conn=None, trace_id=None):
        if not thought:
            return
        safe_task_id = _normalize_task_id(task_id)
        is_stop_ctrl = self._is_stop_control_message(role, thought)
        r = None if _is_test_mode() else (redis_conn or self._get_redis())

        if self._is_stopped(safe_task_id, r) and not is_stop_ctrl:
            self._discarded_after_stop_count += 1
            self.clear_task_queue(safe_task_id)
            return

        if _is_test_mode():
            self._test_log_buffer.append({
                "type": "thought",
                "role": str(role).upper(),
                "msg": str(thought),
                "task_id": safe_task_id,
                "trace_id": trace_id or safe_task_id,
                "is_delta": bool(is_delta),
            })
            return

        if is_delta:
            if not r:
                return
            self._publish_now_delta(r, role, thought, safe_task_id, stream_id, is_first_chunk, trace_id=trace_id)
            return
        if not r:
            return
        self._enqueue_thought(r, role, thought, safe_task_id, stream_id, trace_id=trace_id, is_stop_control=is_stop_ctrl)

    def _publish_now_delta(self, r, role, thought, task_id, stream_id, is_first_chunk, trace_id=None):
        safe_task_id = _normalize_task_id(task_id)
        if self._is_stopped(safe_task_id, r) and not self._is_stop_control_message(role, thought):
            self._discarded_after_stop_count += 1
            return
        try:
            from core.utils.log_normalizer import format_thought
            iso_time = datetime.now().isoformat()
            level = self._detect_level(thought)
            if is_first_chunk:
                clean_thought = format_thought(role, thought)
                msg = f"{level} [{iso_time}] [{role}] [Task: {safe_task_id}] {clean_thought.strip()}"
            else:
                msg = thought
            tag = role.upper()
            payload = {
                "tag": tag, "msg": msg, "ts": time.time(),
                "task_id": safe_task_id, "trace_id": trace_id or safe_task_id,
                "source": tag, "iso_time": iso_time,
                "is_delta": True
            }
            if stream_id:
                payload["id"] = stream_id
                payload["pin_id"] = stream_id
            log = json.dumps(payload, ensure_ascii=False)
            r.publish("monitor:log_channel", log)
            r.publish("monitor:progress_channel", log)
        except Exception:
            pass

    def _enqueue_thought(self, r, role, thought, task_id, stream_id, trace_id=None, is_stop_control=False):
        safe_task_id = _normalize_task_id(task_id)
        iso_time = datetime.now().isoformat()
        level = self._detect_level(thought)
        try:
            from core.utils.log_normalizer import format_thought
            clean_thought = format_thought(role, thought)
        except Exception:
            clean_thought = str(thought)
        msg = f"{level} [{iso_time}] [{role}] [Task: {safe_task_id}] {clean_thought.strip()}"
        tag = role.upper()
        payload = {
            "tag": tag, "msg": msg, "ts": time.time(),
            "task_id": safe_task_id, "trace_id": trace_id or safe_task_id,
            "source": tag, "iso_time": iso_time
        }
        if stream_id:
            payload["id"] = stream_id
            payload["pin_id"] = stream_id
        log = json.dumps(payload, ensure_ascii=False)
        self._enqueue("monitor:log_channel", log, save_history=True,
                      history_key="monitor:log_history", history_max=499,
                      task_id=safe_task_id, is_stop_control=is_stop_control)
        self._enqueue("monitor:progress_channel", log, save_history=True,
                      history_key="monitor:progress_history", history_max=1999,
                      task_id=safe_task_id, is_stop_control=is_stop_control)

    def publish_mission_log(self, tag, msg, task_id="system",
                            trace_id=None, stealth=False, redis_conn=None):
        if not msg:
            return
        safe_task_id = _normalize_task_id(task_id)
        is_stop_ctrl = self._is_stop_control_message(tag, msg)
        if is_stop_ctrl and str(tag).upper() in ("STOP", "STOPPED"):
            self.mark_task_stopped(safe_task_id)

        r = None if _is_test_mode() else (redis_conn or self._get_redis())
        if self._is_stopped(safe_task_id, r) and not is_stop_ctrl:
            self._discarded_after_stop_count += 1
            self.clear_task_queue(safe_task_id)
            return

        try:
            from core.utils.log_normalizer import normalize_mission_log
            clean_msg = normalize_mission_log(tag, msg)
        except Exception:
            clean_msg = str(msg)
        if not clean_msg:
            return
        data = {
            "tag": tag, "msg": clean_msg, "ts": time.time(),
            "task_id": safe_task_id, "trace_id": trace_id or safe_task_id,
        }
        if _is_test_mode():
            self._test_log_buffer.append({"type": "mission_log", **data})
            return

        payload = json.dumps(data, ensure_ascii=False)
        if r:
            self._publish_now(r, "monitor:log_channel", payload, save_history=True)
            self._publish_now(r, "monitor:progress_channel", payload, save_history=True,
                              history_key="monitor:progress_history", history_max=1999)

        is_executor_incident = (tag == "EXECUTOR" and any(k in clean_msg.lower() for k in ("fail", "error", "warn", "down", "replan", "circuit", "unhealthy")))
        if tag in ("CRITICAL", "ERROR", "SECURITY", "POLICY", "AUDIT", "CIRCUIT_BREAKER") or is_executor_incident:
            try:
                from core.observability.structured_logger import log_structured_event
                log_structured_event(
                    message=clean_msg,
                    tool_name=tag.lower(),
                    authority_decision="DENY" if tag in ("SECURITY", "POLICY") else "ALLOW",
                    trace_id=trace_id or safe_task_id,
                    error_code=tag if tag in ("CRITICAL", "ERROR") or is_executor_incident else None,
                    extra={"task_id": safe_task_id, "tag": tag, "stealth": stealth}
                )
            except Exception:
                pass

    def publish_progress(self, pct, msg, phase="", task_id="system",
                         trace_id=None, redis_conn=None):
        safe_task_id = _normalize_task_id(task_id)
        r = None if _is_test_mode() else (redis_conn or self._get_redis())
        if self._is_stopped(safe_task_id, r):
            self._discarded_after_stop_count += 1
            return
        if _is_test_mode():
            self._test_log_buffer.append({
                "type": "progress", "pct": pct, "msg": msg,
                "task_id": safe_task_id, "phase": phase, "trace_id": trace_id or safe_task_id
            })
            return
        payload = json.dumps({
            "tag": "PROGRESS", "pct": pct, "msg": msg,
            "task_id": safe_task_id, "phase": phase,
            "trace_id": trace_id or safe_task_id, "ts": time.time()
        }, ensure_ascii=False)
        if r:
            self._publish_now(r, "monitor:log_channel", payload)
            self._publish_now(r, "monitor:progress_channel", payload)

    @staticmethod
    def _detect_level(thought: str) -> str:
        tl = thought.lower()
        if "error" in tl or "lỗi" in tl or "[err" in tl:
            return "[ERROR]"
        if "warn" in tl or "cảnh báo" in tl:
            return "[WARN]"
        if "vram" in tl or "cpu" in tl:
            return "[METRIC]"
        return "[INFO]"


log_engine = LogEngine()
