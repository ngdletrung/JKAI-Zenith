import json
from core.redis_client import redis_safe

def publish_event(socketio, event, data):
    """Phát sự kiện tới Dashboard qua SocketIO và lưu vào Redis log."""
    socketio.emit(event, data)
    def _log(r):
        payload = json.dumps(data)
        # 1. Lưu vào history list (không pop)
        r.lpush("monitor:log_history", payload)
        r.ltrim("monitor:log_history", 0, 499)
        # 2. Phát qua Pub/Sub cho broadcaster
        r.publish("monitor:log_channel", payload)
    redis_safe(_log)

