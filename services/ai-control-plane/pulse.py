import asyncio
import json
import os
import time
import httpx
from redis_client import redis_safe

class ZenithPulse:
    """
    💓 JKAI ZENITH: PROACTIVE PULSE SERVICE
    Chỉ cảnh báo khi có sự cố. Im lặng khi mọi thứ ổn định.
    """
    def __init__(self):
        self.tg_token = os.getenv("TELEGRAM_TOKEN")
        self.master_id = os.getenv("MASTER_ID")
        self.brain_url = os.getenv("AI_BRAIN_URL", "http://ai-brain:8000")
        self.last_status = "OPTIMAL"  # Trạng thái trước đó
        # 💎 Synapse vĩnh cửu
        self.client = httpx.AsyncClient(timeout=15.0)
        self.satellite_url = "http://host.docker.internal:9997"
        self.akai_token = os.getenv("AKAI_PRIME_TOKEN", "AKAI_PRIME_SUPER_SECRET_999")

    async def _send_tg(self, message: str):
        """Gửi tin nhắn Telegram tới Master."""
        if not self.tg_token or not self.master_id: return
        try:
            await self.client.post(
                f"https://api.telegram.org/bot{self.tg_token}/sendMessage",
                json={"chat_id": self.master_id, "text": message[:4000], "parse_mode": "Markdown"},
                timeout=10.0
            )
        except Exception as e:
            print(f"❌ [PULSE-TG-ERR] {e}")

    async def _call_satellite(self, command: str) -> str:
        """Thực thi lệnh trực tiếp trên máy chủ Windows của Master."""
        try:
            res = await self.client.post(
                f"{self.satellite_url}/terminal",
                json={"command": command, "shell": "powershell"},
                headers={"X-AKAI-TOKEN": self.akai_token},
                timeout=10.0
            )
            if res.status_code == 200:
                data = res.json()
                return data.get("stdout", data.get("output", ""))
        except Exception as e:
            print(f"❌ [PULSE-SATELLITE-ERR] {e}")
        return ""

    async def get_system_health(self):
        """Thu thập chỉ số sức khỏe toàn hệ thống song song."""
        health = {"status": "OPTIMAL", "details": []}
        
        # 🌐 [HTTP-CHECK]: Cac dich vu co Port
        services = {
            "📡 AI-Control-Plane": "http://localhost:8000/health",
            "🧠 AI-Brain": f"{self.brain_url.rstrip('/')}/health",
            "🦾 AI-Executor-Alpha": "http://ai-executor-1:8000/health",  # Cập nhật tên container đúng của Executor Alpha (Port 8002)
            "🦾 AI-Executor-Beta": "http://ai-executor-2:8000/health",
            "🏢 Mission-Control": "http://mission-control:9998/api/system_status",
            "🛡️ File-Warden": "http://zenith-file-warden:8005/",
            "🔗 N8N-Main": "http://n8n-main:5678/healthz",
            "📚 RAG-Service": "http://rag-service:8000/health",
            "🔍 Qdrant DB": "http://qdrant:6333/healthz",
            "👁️ AI-Browser": "http://ai-browser:8000/health",
        }
        
        async def check_service(name, url):
            try:
                r = await self.client.get(url, timeout=2.0)
                if r.status_code in [200, 204]:
                    return f"{name}: `Online` ✅", "OPTIMAL"
                else:
                    return f"{name}: `Unstable` ⚠️", "DEGRADED"
            except Exception:
                return f"{name}: `Offline` ❌", "DEGRADED"

        tasks = [check_service(name, url) for name, url in services.items()]
        results = await asyncio.gather(*tasks)
        
        for detail, status in results:
            health["details"].append(detail)
            if status == "DEGRADED":
                health["status"] = "DEGRADED"

        # 🐳 [DOCKER-CHECK]: Cac dich vu Worker (khong Port)
        try:
            import docker
            client = docker.from_env()
            workers = {
                "👷 AI-Worker": "ai-worker",
                "👷 N8N-Worker": "n8n-worker"
            }
            for name, cname in workers.items():
                try:
                    container = client.containers.get(cname)
                    if container.status == "running":
                        health["details"].append(f"{name}: `Running` ✅")
                    else:
                        health["details"].append(f"{name}: `Stopped` ⚠️")
                        health["status"] = "DEGRADED"
                except Exception:
                    health["details"].append(f"{name}: `Missing` ❌")
                    health["status"] = "DEGRADED"
        except Exception as e:
            print(f"⚠️ [DOCKER-PULSE-ERR]: {e}")

        is_redis = redis_safe(lambda r: r.ping(), False)
        health["details"].append(f"📡 Redis AI: {'`Online` ✅' if is_redis else '`Offline` ❌'}")
        if not is_redis: health["status"] = "CRITICAL"
        
        return health

    async def get_hardware_stats(self):
        """🌐 [TELEMETRY]: Thu thập nhịp tim phần cứng thực tế qua API siêu tốc."""
        cpu = 0
        ram = 0
        gpu = 0
        try:
            import psutil
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
        except Exception:
            pass

        # Truy vấn trực tiếp API từ Host Bridge siêu tốc (0.5s)
        try:
            res = await self.client.get(
                f"{self.satellite_url}/telemetry",
                headers={"X-AKAI-TOKEN": self.akai_token},
                timeout=5.0
            )
            if res.status_code == 200:
                data = res.json()
                cpu = int(round(float(data.get("cpu", cpu))))
                ram = int(round(float(data.get("ram", ram))))
                gpu = int(round(float(data.get("gpu", gpu))))
        except Exception as e:
            print(f"⚠️ [PULSE-HOST-QUERY-ERR]: {e}")
            
        return {"cpu": cpu, "ram": ram, "gpu": gpu, "ts": time.time()}

    async def run_forever(self):
        """Vòng lặp nhịp đập v31.0 - Thấu thị và Cảnh báo."""
        print("💓 [PULSE-v31.0] Quantum Pulse Service is Online. Đang thấu thị tài nguyên...")
        await asyncio.sleep(2)
        
        cached_health = {"status": "OPTIMAL", "details": []}
        last_health_check = 0.0
        
        while True:
            try:
                now = time.time()
                # 1. Chỉ kiểm tra sức khỏe Service mỗi 30 giây để tránh làm nghẽn luồng realtime
                if now - last_health_check > 30:
                    cached_health = await self.get_system_health()
                    last_health_check = now
                
                # 2. Thu thập Telemetry phần cứng (Realtime 2s)
                stats = await self.get_hardware_stats()
                
                # 3. Publish lên Dashboard qua Redis
                pulse_data = {
                    "cpu": stats["cpu"],
                    "ram": stats["ram"],
                    "gpu": stats["gpu"],
                    "status": cached_health["status"],
                    "health": cached_health,
                    "active_thoughts": "IDLE",
                    "ts": stats["ts"]
                }
                
                log = json.dumps({"tag": "PULSE", "data": pulse_data, "ts": time.time()}, ensure_ascii=False)
                # 📡 [BROADCAST]: Phát sóng lên Dashboard
                redis_safe(lambda r: r.publish("monitor:pulse_channel", log))
                # 🧠 [NEURAL-CACHE]: Lưu vào bộ nhớ đệm cho Giao thức Nhật ký Thông minh
                redis_safe(lambda r: r.set("hardware_pulse_cache", json.dumps(pulse_data), ex=60))

                # 📝 [SHARED-FILE-WRITE]: Ghi trực tiếp vào tệp tin dùng chung để mission-control phát đi chính xác
                try:
                    pulse_file = "/intelligence/protocols/hardware_pulse.json"
                    os.makedirs(os.path.dirname(pulse_file), exist_ok=True)
                    with open(pulse_file, 'w', encoding='utf-8') as f:
                        json.dump(pulse_data, f, ensure_ascii=False, indent=4)
                except Exception as json_err:
                    print(f"⚠️ [PULSE-JSON-WRITE-ERR]: {json_err}")

                # 🛡️ Cảnh báo Telegram khi có biến động lớn
                current_status = cached_health["status"]
                if current_status != self.last_status:
                    if current_status != "OPTIMAL":
                        alert = [
                            f"🚨 *[ZENITH ALERT — {current_status}]*",
                            f"📊 *CPU:* {stats['cpu']}% | *RAM:* {stats['ram']}%",
                            f"📅 _{time.strftime('%H:%M:%S')}_",
                            "\n".join(cached_health['details']),
                            "⚠️ *Master, hệ thống đang mất ổn định!*"
                        ]
                        await self._send_tg("\n".join(alert))
                    else:
                        await self._send_tg(f"✅ *[ZENITH RECOVERED]*\n💎 *Hệ thống đã đạt trạng thái Optimal.*")
                    self.last_status = current_status

            except Exception as e:
                print(f"⚠️ [PULSE-LOOP-ERR] {e}")
            
            await asyncio.sleep(2)  # Đưa về 2 giây để cực nhạy và realtime cho Master thưa Master

async def start_pulse():
    """Hàm khởi động Nhịp đập từ main.py."""
    await pulse.run_forever()

pulse = ZenithPulse()
