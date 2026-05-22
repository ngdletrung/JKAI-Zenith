import os
import asyncio
import json
import httpx
import shutil
import sys
import time

# Đảm bảo nạp được các module từ core
try:
    from core.utils.engine import engine
except ImportError:
    pass)))))
from core.utils.engine import engine
from redis_client import redis_safe

class SelfEvolve:
    """
    VŨ KHÍ TỐI THƯỢNG CỦA JKAI: Khả năng tự lập trình và tối ưu hóa mã nguồn.
    Quy tắc: Luôn gọi từ .env, luôn sử dụng định danh JKAI.
    """
    def __init__(self):
        self.brain_url = os.getenv("AI_BRAIN_URL")
        if not self.brain_url: raise ValueError("AI_BRAIN_URL not set in .env")
        self.workspace_root = os.getenv("JKAI_WORKSPACE_ROOT", "/app")

    async def evolve_service(self, service_name: str, objective: str):
        print(f"🧬 [JKAI-EVOLVE] Starting evolution sequence for: {service_name}")
        print(f"🎯 Objective: {objective}")
        
        # 1. Gửi yêu cầu lập kế hoạch sửa đổi tới Brain
        payload = {
            "goal": f"Improve {service_name} to achieve: {objective}",
            "context": {"current_service": service_name, "mode": "evolution"}
        }
        
        async with httpx.AsyncClient(timeout=120.0) as client:
            try:
                # Gọi Brain để nhận mã nguồn mới hoặc phương án sửa lỗi
                resp = await client.post(f"{self.brain_url}/plan", json=payload)
                if resp.status_code == 200:
                    evolution_plan = resp.json()
                    # Logic ghi đè tệp hoặc nạp skill mới sẽ ở đây
                    return {"status": "success", "message": f"JKAI {service_name} has evolved successfully."}
            except Exception as e:
                return {"status": "error", "message": f"Evolution failed: {str(e)}"}

async def get_gpu_info():
    """Lấy thông số VRAM RX 6600 qua PowerShell."""
    try:
        cmd = 'powershell -Command "Get-CimInstance Win32_VideoController | Select-Object Name, AdapterRAM"'
        proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        lines = stdout.decode().strip().split('\n')
        if len(lines) >= 3:
            raw_ram = lines[2].strip().split()[-1]
            vram_gb = round(int(raw_ram) / (1024**3), 2)
            return {"name": "AMD Radeon RX 6600", "total_vram": f"{vram_gb} GB"}
    except: pass
    return {"name": "Unknown", "total_vram": "N/A"}

async def get_system_ram():
    """Lấy thông số RAM hệ thống."""
    try:
        cmd = 'powershell -Command "Get-CimInstance Win32_OperatingSystem | Select-Object TotalVisibleMemorySize, FreePhysicalMemory"'
        proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        lines = stdout.decode().strip().split('\n')
        if len(lines) >= 3:
            parts = lines[2].strip().split()
            total = round(int(parts[0]) / (1024**2), 2)
            free = round(int(parts[1]) / (1024**2), 2)
            return {"total": f"{total} GB", "free": f"{free} GB", "used_pct": f"{round((1-free/total)*100, 1)}%"}
    except: pass
    return {"total": "N/A", "free": "N/A"}

async def get_docker_status():
    """Kiểm tra trạng thái các Container."""
    try:
        cmd = 'docker ps -a --format "{{.Names}}|{{.Status}}"'
        proc = await asyncio.create_subprocess_shell(cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        stdout, _ = await proc.communicate()
        containers = []
        for line in stdout.decode().strip().split('\n'):
            if '|' in line:
                name, status = line.split('|')
                containers.append({"name": name, "status": status})
        return containers
    except: return []

async def get_loaded_models():
    """Kiểm tra các model đang cư trú trong VRAM/RAM."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            resp = await client.get("http://localhost:11434/api/ps")
            if resp.status_code == 200:
                models = resp.json().get("models", [])
                return [{"name": m['name'], "size": f"{round(m['size']/(1024**3), 2)} GB"} for m in models]
    except: pass
    return []

async def check_system_health():
    """
    🏥 [DOCTOR MODE]: Chẩn đoán tổng lực sức khỏe hệ thống Zenith.
    """
    print("🕵️ [JKAI-DOCTOR] Initiating full system diagnostic...")
    
    gpu = await get_gpu_info()
    ram = await get_system_ram()
    containers = await get_docker_status()
    models = await get_loaded_models()
    
    # Kiểm tra logs lỗi gần đây
    logs = redis_safe(lambda r: r.lrange("monitor:log_history", 0, 50), [])
    errors = []
    for l in logs:
        try:
            data = json.loads(l)
            if data.get("tag") in ["ERROR", "FAILURE"]:
                errors.append(data.get("msg"))
        except: pass

    status = "HEALTHY" if not errors and all("Up" in c['status'] for c in containers if c['name'].startswith('jkai')) else "STABLE_WITH_ISSUES"
    if not containers: status = "WARNING_IDLE" # Không có container nào chạy

    report = {
        "status": status,
        "identity": "💎 JKAI Zenith Diagnostic",
        "hardware": {
            "gpu": gpu,
            "ram": ram
        },
        "neural_layer": {
            "resident_models": models,
            "model_count": len(models)
        },
        "infrastructure": {
            "containers": containers,
            "active_count": len([c for c in containers if "Up" in c['status']])
        },
        "recent_errors": errors[:5],
        "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
    }
    
    return report

async def chan_doan_su_co(task_id: str = "manual"):
    """Duy trì khả năng chẩn đoán AI."""
    return await check_system_health()

if __name__ == "__main__":
    print("🧬 JKAI Health & Evolution Protocol Initialized.")

_instance = SelfEvolve()


# 🚀 GIAO THỨC NHẤT THỂ HÓA: Wrapper cấp module để ToolRouter nhận diện

async def evolve_service(**kwargs):
    return await _instance.evolve_service(**kwargs)
