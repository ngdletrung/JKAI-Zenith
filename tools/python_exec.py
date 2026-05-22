description = "Execute Python code safely (via ai-worker)"
schema = {
    "code": "string"
}
timeout = 30

def run(input_data):
    import json
    import redis
    import time
    import os
    import uuid

    code = input_data.get("code", "")
    if not code:
        return {"error": "No code provided"}

    # Gửi code đến ai-worker qua Redis exec_queue
    REDIS_HOST = os.getenv("REDIS_HOST", "redis")
    REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
    REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
    r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASSWORD or None, decode_responses=True)

    task_id = f"py_{int(time.time())}_{uuid.uuid4().hex[:8]}"
    r.rpush("exec_queue", json.dumps({"task_id": task_id, "code": code, "timeout": 60}))
    data = r.brpop(f"result_queue:{task_id}", timeout=65)
    if not data:
        return {"error": "Timeout waiting for worker"}
    res = json.loads(data[1])
    if res.get("status") == "success":
        return {"output": res.get("stdout", "")}
    else:
        return {"error": res.get("stderr", "Unknown error")}