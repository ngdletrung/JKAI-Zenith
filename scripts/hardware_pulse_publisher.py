# -*- coding: utf-8 -*-
"""
JKAI Zenith — Hardware Pulse Publisher
File: scripts/hardware_pulse_publisher.py

Chay tren Windows Host (native), doc CPU/RAM/GPU AMD bang HardwareMonitor
va day vao Redis moi 0.5 giay.

mission-control Docker chi can doc Redis key "hardware_pulse_cache" --
khong can host_bridge.py nua.

Khoi dong tu Zenith_Guardian.ps1 thay the host_bridge.py.
"""
import json
import os
import sys
import time

# Them JKAI vao Python path de import HardwareMonitor
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from core.governor.hardware_monitor import HardwareMonitor

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", 6379))
REDIS_PASSWORD = os.getenv("REDIS_PASSWORD", "")
PUBLISH_INTERVAL = 0.5   # giay — near-realtime cho UI
CACHE_TTL        = 5     # Redis key het han sau 5s neu publisher die

def get_redis():
    import redis
    return redis.Redis(
        host=REDIS_HOST,
        port=REDIS_PORT,
        password=REDIS_PASSWORD or None,
        decode_responses=True,
        socket_connect_timeout=3,
        socket_timeout=3,
    )

def get_loaded_models():
    """Truy vấn các model đang nạp thực tế trong VRAM và RAM từ cả 2 cổng Ollama."""
    import urllib.request
    gpu_models, cpu_models = [], []
    try:
        req = urllib.request.Request("http://127.0.0.1:11434/api/ps", headers={"User-Agent": "JKAI-Publisher"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            gpu_models = [m.get("name") for m in data.get("models", [])]
    except Exception:
        pass
    try:
        req = urllib.request.Request("http://127.0.0.1:11435/api/ps", headers={"User-Agent": "JKAI-Publisher"})
        with urllib.request.urlopen(req, timeout=0.8) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            cpu_models = [m.get("name") for m in data.get("models", [])]
    except Exception:
        pass
    return gpu_models, cpu_models

def build_pulse(hw):
    """Tao dict pulse tu HardwareState kem model matrix thoi gian thuc."""
    gpu_mods, cpu_mods = get_loaded_models()
    return {
        "cpu":     round(hw.cpu_load_pct * 100, 1),
        "ram":     round((1 - hw.ram_free_gb / hw.ram_total_gb) * 100, 1) if hw.ram_total_gb > 0 else 0,
        "gpu":     0,                        # Win32PDH GPU util — doc ben duoi
        "vram_mb": hw.vram_total_mb - hw.vram_free_mb,
        "vram_total_mb": hw.vram_total_mb,
        "vram_free_mb":  hw.vram_free_mb,
        "vram_budget_mb": hw.vram_safe_budget_mb,
        "ai_threads": hw.get_dynamic_ai_threads(22),
        "cpu_threads": hw.cpu_count_logical,
        "ram_total_gb": round(hw.ram_total_gb, 1),
        "ram_free_gb":  round(hw.ram_free_gb, 1),
        "gpu_name": hw.gpu_name,
        "gpu_models": gpu_mods,
        "cpu_models": cpu_mods,
        "status": "OPTIMAL",
        "ts": time.time(),
    }

def try_read_gpu_util():
    """Doc GPU utilization qua Windows PDH (AMD RX 6600 Vulkan)."""
    try:
        import win32pdh
        q = win32pdh.OpenQuery()
        c = win32pdh.AddCounter(q, r"\GPU Engine(*engtype_3D)\Utilization Percentage")
        win32pdh.CollectQueryData(q)
        time.sleep(0.05)
        win32pdh.CollectQueryData(q)
        vals = win32pdh.GetFormattedCounterArray(c, win32pdh.PDH_FMT_DOUBLE)
        util = int(round(sum(v for v in vals.values() if v is not None)))
        win32pdh.CloseQuery(q)
        return min(util, 100)
    except Exception:
        return 0

def main():
    print("[HW-PULSE] JKAI Hardware Pulse Publisher ONLINE")
    print(f"[HW-PULSE] Redis: {REDIS_HOST}:{REDIS_PORT} | Interval: {PUBLISH_INTERVAL}s")
    print("[HW-PULSE] host_bridge.py khong con can thiet.")

    r = None
    consecutive_errors = 0

    while True:
        try:
            # Reconnect neu mat ket noi
            if r is None:
                r = get_redis()
                r.ping()
                print("[HW-PULSE] Redis connected.")
                consecutive_errors = 0

            hw = HardwareMonitor.get_state()
            pulse = build_pulse(hw)

            # GPU util qua PDH (nhe, ~50ms)
            pulse["gpu"] = try_read_gpu_util()

            payload = json.dumps(pulse)
            r.setex("hardware_pulse_cache", CACHE_TTL, payload)

        except Exception as e:
            consecutive_errors += 1
            print(f"[HW-PULSE] Loi ({consecutive_errors}): {e}")
            r = None   # Force reconnect
            time.sleep(2)
            continue

        time.sleep(PUBLISH_INTERVAL)

if __name__ == "__main__":
    main()
