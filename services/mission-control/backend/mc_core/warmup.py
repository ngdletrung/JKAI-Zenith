import time
import json
from mc_core.redis_client import redis_safe

_REDIS_UNAVAILABLE = object()


def acquire_action_slot(action: str, seconds: int = 10) -> bool:
    """Cross-worker cooldown for dashboard actions; fails open when Redis is down."""
    key = f"mc:action_lock:{action}"
    result = redis_safe(lambda r: r.set(key, "1", nx=True, ex=seconds), _REDIS_UNAVAILABLE)
    if result is _REDIS_UNAVAILABLE:
        return True
    return bool(result)


def start_warmup_sequence(socketio):
    """Announce recovery in the dashboard; real warmup is owned by ai-brain."""
    print(" [JKAI] Warmup Sequence Starting...")
    time.sleep(2)

    messages = [
        {"tag": "JKAI", "msg": "JKAI đã trực tuyến. Bảng điều khiển sẵn sàng nhận lệnh thưa Master.", "ts": time.time()},
        {"tag": "SYSTEM", "msg": "Bộ nhớ đệm tri thức do ai-brain đảm nhiệm; dùng nút Warmup khi cần nạp lại.", "ts": time.time() + 0.3},
    ]

    for msg in messages:
        payload = json.dumps(msg, ensure_ascii=False)
        redis_safe(lambda r: r.publish("monitor:log_channel", payload))
        redis_safe(lambda r: r.lpush("monitor:log_history", payload))
        time.sleep(0.4)

    print(" [JKAI] Warmup complete.")
