import asyncio
import json
import logging
import time
from collections import deque
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger("LogEngine")

_FLUSH_INTERVAL = 0.5
_MAX_BATCH = 50


class LogEngine:
    def __init__(self):
        self._redis = None
        self._queue: deque[Dict[str, Any]] = deque()
        self._flush_task: Optional[asyncio.Task] = None
        self._loop: Optional[asyncio.AbstractEventLoop] = None

    def _get_redis(self, engine_instance=None):
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
        if self._flush_task is None or self._flush_task.done():
            loop = asyncio.get_event_loop()
            self._flush_task = loop.create_task(self._flush_loop())

    async def _flush_loop(self):
        while True:
            await asyncio.sleep(_FLUSH_INTERVAL)
            if not self._queue:
                continue
            r = self._get_redis()
            if not r:
                self._queue.clear()
                continue
            batch = []
            while self._queue and len(batch) < _MAX_BATCH:
                batch.append(self._queue.popleft())
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
                 history_max: int = 999):
        self._queue.append({
            "channel": channel,
            "payload": payload,
            "save_history": save_history,
            "history_key": history_key,
            "history_max": history_max,
        })
        self._ensure_flush_task()

    def _publish_now(self, r, channel: str, payload: str,
                     save_history: bool = False,
                     history_key: str = "monitor:log_history",
                     history_max: int = 999):
        try:
            r.publish(channel, payload)
            if save_history:
                r.lpush(history_key, payload)
                r.ltrim(history_key, 0, history_max)
        except Exception as e:
            logger.warning("[LOG_NOW] err=%s", e)

    def publish_thought(self, role, thought, task_id="system",
                        stream_id=None, is_delta=False, is_first_chunk=False,
                        redis_conn=None):
        if not thought:
            return
        if is_delta:
            r = redis_conn or self._get_redis()
            if not r:
                return
            self._publish_now_delta(r, role, thought, task_id, stream_id, is_first_chunk)
            return
        r = redis_conn or self._get_redis()
        if not r:
            return
        self._enqueue_thought(r, role, thought, task_id, stream_id)

    def _publish_now_delta(self, r, role, thought, task_id, stream_id, is_first_chunk):
        try:
            iso_time = datetime.now().isoformat()
            level = self._detect_level(thought)
            msg = f"{level} [{iso_time}] [{role}] [Task: {task_id}] {thought}" if is_first_chunk else thought
            tag = role.upper()
            payload = {
                "tag": tag, "msg": msg, "ts": time.time(),
                "task_id": task_id or "system", "source": tag, "iso_time": iso_time,
                "is_delta": True
            }
            if stream_id:
                payload["id"] = stream_id
                payload["pin_id"] = stream_id
            log = json.dumps(payload, ensure_ascii=False)
            # Publish delta to active WebSockets
            r.publish("monitor:log_channel", log)
            r.publish("monitor:progress_channel", log)
            # [STREAM-RETENTION]: Save delta chunk into Redis log history to survive reload
            r.lpush("monitor:log_history", log)
            r.ltrim("monitor:log_history", 0, 499)
        except Exception:
            pass

    def _enqueue_thought(self, r, role, thought, task_id, stream_id):
        iso_time = datetime.now().isoformat()
        level = self._detect_level(thought)
        msg = f"{level} [{iso_time}] [{role}] [Task: {task_id}] {thought.strip()}"
        tag = role.upper()
        payload = {
            "tag": tag, "msg": msg, "ts": time.time(),
            "task_id": task_id or "system", "source": tag, "iso_time": iso_time
        }
        if stream_id:
            payload["id"] = stream_id
            payload["pin_id"] = stream_id
        log = json.dumps(payload, ensure_ascii=False)
        self._enqueue("monitor:log_channel", log, save_history=True,
                      history_key="monitor:log_history", history_max=499)
        self._enqueue("monitor:progress_channel", log, save_history=True,
                      history_key="monitor:progress_history", history_max=1999)

    def publish_mission_log(self, tag, msg, task_id="system",
                            trace_id=None, stealth=False, redis_conn=None):
        if not msg:
            return
        data = {
            "tag": tag, "msg": msg, "ts": time.time(),
            "task_id": task_id, "trace_id": trace_id or task_id,
        }
        if stealth:
            data["stealth"] = True
        payload = json.dumps(data, ensure_ascii=False)
        r = redis_conn or self._get_redis()
        if r:
            self._publish_now(r, "monitor:log_channel", payload, save_history=True)
            self._publish_now(r, "monitor:progress_channel", payload, save_history=True,
                              history_key="monitor:progress_history", history_max=1999)

    def publish_progress(self, pct, msg, phase="", task_id="system",
                         trace_id=None, redis_conn=None):
        payload = json.dumps({
            "tag": "PROGRESS", "pct": pct, "msg": msg,
            "task_id": task_id, "phase": phase,
            "trace_id": trace_id, "ts": time.time()
        }, ensure_ascii=False)
        r = redis_conn or self._get_redis()
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
