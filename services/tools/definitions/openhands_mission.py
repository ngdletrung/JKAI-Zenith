import os
import json
import logging
import httpx

logger = logging.getLogger("OpenHandsMissionTool")

def run_openhands_mission(query: str) -> dict:
    """
    🛠️ Native Tool: Chạy nhiệm vụ lập trình cô lập qua OpenHands hoặc Docker Executor.
    """
    logger.info(f"[OPENHANDS-MISSION] Executing mission query: {query}")
    try:
        executor_url = os.getenv("EXECUTOR_URL", "http://ai-executor-1:8000")
        with httpx.Client(timeout=60.0) as client:
            resp = client.post(f"{executor_url}/execute", json={"command": "python", "script": query})
            if resp.status_code == 200:
                return {"status": "success", "result": resp.json()}
            else:
                return {"status": "error", "error": f"Executor returned HTTP {resp.status_code}"}
    except Exception as e:
        logger.error(f"[OPENHANDS-ERR] {e}")
        return {"status": "error", "error": str(e)}
