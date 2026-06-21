
import json
import time
import logging

logger = logging.getLogger("SESSION_CONTEXT")

class SessionContext:
    SESSION_PREFIX = "jkai:session:"
    SESSION_TTL = 86400 * 7
    MAX_HISTORY = 100

    def __init__(self, get_redis_fn):
        self._get_redis = get_redis_fn

    def _key(self, session_id: str) -> str:
        return f"{self.SESSION_PREFIX}{session_id}"

    def get_history(self, session_id: str, limit: int = 50) -> list:
        if not session_id:
            return []
        try:
            r = self._get_redis()
            raw = r.get(self._key(session_id))
            if not raw:
                return []
            data = json.loads(raw)
            history = data.get("history", [])
            messages = []
            for msg in history[-limit:]:
                role = "user" if msg.get("role") == "user" else "assistant"
                content = msg.get("content", "")
                if content:
                    messages.append({"role": role, "content": content})
            return messages
        except Exception as e:
            logger.warning(f"Failed to load session {session_id}: {e}")
            return []

    def add_message(self, session_id: str, role: str, content: str):
        if not session_id or not content:
            return
        try:
            r = self._get_redis()
            key = self._key(session_id)
            raw = r.get(key)
            if raw:
                data = json.loads(raw)
            else:
                data = {"history": [], "created": time.time()}
            data["history"].append({
                "role": role,
                "content": content,
                "ts": time.time()
            })
            data["last_activity"] = time.time()
            if len(data["history"]) > self.MAX_HISTORY:
                data["history"] = data["history"][-self.MAX_HISTORY:]
            r.setex(key, self.SESSION_TTL, json.dumps(data))
        except Exception as e:
            logger.warning(f"Failed to save session {session_id}: {e}")

    def add_user_message(self, session_id: str, goal: str):
        self.add_message(session_id, "user", goal)

    def add_assistant_message(self, session_id: str, answer: str):
        self.add_message(session_id, "assistant", answer)

    def clear(self, session_id: str):
        if not session_id:
            return
        try:
            r = self._get_redis()
            r.delete(self._key(session_id))
        except Exception as e:
            logger.warning(f"Failed to clear session {session_id}: {e}")


_session_context = None

def get_session_context(get_redis_fn=None):
    global _session_context
    if _session_context is None:
        if get_redis_fn is None:
            from core.utils.redis_client import get_redis as default_redis
            get_redis_fn = default_redis
        _session_context = SessionContext(get_redis_fn)
    return _session_context
