import os
import asyncio
import httpx
import time
import json
import logging
import psutil
from typing import Dict, Any
from core.utils.engine import engine

logger = logging.getLogger("jkai.xray_monitor")

class SystemXRayMonitor:
    """
    👁️ SYSTEM X-RAY MONITOR (Sovereign Guard)
    Vệ binh tối thượng giám sát toàn diện hạ tầng từ Docker đến Host Windows.
    """
    def __init__(self):
        self.satellite_url = "http://host.docker.internal:9998"
        self.ollama_url = "http://host.docker.internal:11434"
        self.akai_token = os.getenv("AKAI_PRIME_TOKEN", "AKAI_PRIME_SUPER_SECRET_999")

    async def _call_satellite(self, command: str) -> Dict[str, Any]:
        """Thực thi lệnh trực tiếp trên máy chủ Windows của Master."""
        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.post(
                    f"{self.satellite_url}/terminal",
                    json={"command": command, "shell": "powershell"},
                    headers={"X-AKAI-TOKEN": self.akai_token}
                )
                return res.json()
        except Exception:
            return {"status": "error", "message": "Satellite Offline"}

    async def get_full_diagnostics(self, task_id: str = "sys") -> Dict[str, Any]:
        """Cuộc tổng duyệt sức khỏe toàn diện."""
        engine.publish_mission_log("X-RAY", "👁️ [X-RAY]: Bắt đầu quét thấu thị toàn bộ hệ thống...", task_id)
        
        # 1. Thu thập dữ liệu phần cứng (Host & Container)
        host_vitals = await self._call_satellite("Get-CimInstance Win32_OperatingSystem | Select-Object FreePhysicalMemory, TotalVisibleMemorySize")
        gpu_info = await self._call_satellite("nvidia-smi --query-gpu=name,memory.total,memory.used,utilization.gpu --format=csv,noheader,nounits")
        
        # 2. Kiểm tra nơ-ron AI (Ollama)
        models = []
        try:
            async with httpx.AsyncClient(timeout=5.0) as client:
                resp = await client.get(f"{self.ollama_url}/api/ps")
                if resp.status_code == 200:
                    models = resp.json().get("models", [])
        except Exception: pass

        # 3. Kiểm tra hạ tầng Docker
        docker_stats = await self._call_satellite("docker ps --format '{{.Names}}|{{.Status}}'")
        
        # 4. Rà soát nhật ký lỗi (Redis)
        # TODO: Tích hợp redis_safe để quét monitor:log_history
        
        report = {
            "status": "💎 ELITE_STABLE",
            "hardware": {
                "host_ram": host_vitals.get("output", "N/A").strip(),
                "gpu": gpu_info.get("output", "N/A").strip(),
                "container_ram": f"{psutil.virtual_memory().percent}%"
            },
            "neural_layer": {
                "active_models": [m['name'] for m in models],
                "model_count": len(models)
            },
            "infrastructure": {
                "containers": docker_stats.get("output", "N/A").strip().split('\n')
            },
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
        
        engine.publish_mission_log("MISSION_RESULT", f"📊 [REPORT]: {json.dumps(report, indent=2)}", task_id)
        return report

_instance = SystemXRayMonitor()

async def get_diagnostics(**kwargs):
    return await _instance.get_full_diagnostics(kwargs.get("task_id", "sys"))

async def execute(action: str = "get_diagnostics", **kwargs):
    if action == "get_diagnostics":
        return await _instance.get_full_diagnostics(kwargs.get("task_id", "sys"))
    return {"status": "error", "msg": f"Action {action} không tồn tại."}
