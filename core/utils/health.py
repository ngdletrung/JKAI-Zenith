import time
import os
import psutil
from fastapi import APIRouter, Response, status

health_router = APIRouter(prefix="/health", tags=["Health"])

@health_router.get("", summary="Basic Liveness Check")
@health_router.get("/live", summary="Liveness Probe")
async def liveness_check():
    """🚀 [HEALTH-LIVENESS]: Kiểm tra phản xạ sống của service (Liveness Probe)."""
    return {
        "status": "UP",
        "service": os.getenv("SERVICE_NAME", "jkai-service"),
        "timestamp": time.time()
    }

@health_router.get("/ready", summary="Readiness Probe")
async def readiness_check(response: Response):
    """🧠 [HEALTH-READINESS]: Kiểm tra sự sẵn sàng chiến đấu của service (Readiness Probe)."""
    mem = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    
    checks = {
        "memory_ok": mem.percent < 95.0,
        "disk_ok": disk.percent < 95.0,
    }
    
    # Optional Redis ping check if REDIS_HOST is set
    redis_host = os.getenv("REDIS_HOST")
    if redis_host:
        try:
            import redis
            r = redis.Redis(host=redis_host, port=int(os.getenv("REDIS_PORT", 6379)), socket_timeout=1.0)
            checks["redis_ok"] = r.ping()
        except Exception:
            checks["redis_ok"] = False

    is_ready = all(checks.values())
    if not is_ready:
        response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE

    return {
        "status": "READY" if is_ready else "UNAVAILABLE",
        "service": os.getenv("SERVICE_NAME", "jkai-service"),
        "checks": checks,
        "metrics": {
            "ram_used_pct": round(mem.percent, 1),
            "disk_used_pct": round(disk.percent, 1),
            "cpu_pct": round(psutil.cpu_percent(interval=None), 1)
        },
        "timestamp": time.time()
    }
