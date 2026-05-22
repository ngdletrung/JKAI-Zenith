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
        self.client = httpx.AsyncClient(timeout=5.0)

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

    async def get_system_health(self):
        """Thu thập chỉ số sức khỏe toàn hệ thống."""
        health = {"status": "OPTIMAL", "details": []}
        
        # 🌐 [HTTP-CHECK]: Cac dich vu co Port
        services = {
            "📡 AI-Control-Plane": "http://localhost:8000/health",
            "🧠 AI-Brain": f"{self.brain_url.rstrip('/')}/health",
            "🦾 AI-Executor-Alpha": "http://ai-executor-1:8000/health",
            "🦾 AI-Executor-Beta": "http://ai-executor-2:8000/health",
            "🏢 Mission-Control": "http://mission-control:9998/api/system_status",
            "🛡️ File-Warden": "http://zenith-file-warden:8005/",
            "🔗 N8N-Main": "http://n8n-main:5678/healthz",
            "📚 RAG-Service": "http://rag-service:8000/health",
            "🔍 Qdrant DB": "http://qdrant:6333/healthz",
            "👁️ AI-Browser": "http://ai-browser:8000/health",
            "🕵️ Jaeger Trace": "http://jaeger:16686/"
        }
        
        for name, url in services.items():
            try:
                r = await self.client.get(url, timeout=5.0)
                if r.status_code in [200, 204]:
                    health["details"].append(f"{name}: `Online` ✅")
                else:
                    health["details"].append(f"{name}: `Unstable` ⚠️")
                    health["status"] = "DEGRADED"
            except:
                health["details"].append(f"{name}: `Offline` ❌")
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
                except:
                    health["details"].append(f"{name}: `Missing` ❌")
                    health["status"] = "DEGRADED"
        except Exception as e:
            print(f"⚠️ [DOCKER-PULSE-ERR]: {e}")

        is_redis = redis_safe(lambda r: r.ping(), False)
        health["details"].append(f"📡 Redis AI: {'`Online` ✅' if is_redis else '`Offline` ❌'}")
        if not is_redis: health["status"] = "CRITICAL"
        
        return health
        
        return health

    async def get_hardware_stats(self):
        """🌐 [TELEMETRY]: Thu thập nhịp tim phần cứng thực tế."""
        try:
            import psutil
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
            # 💎 GIAO THỨC THẤU THỊ GPU (Chỉ dành cho Master LeeTrung)
            # Giả lập hoặc gọi rocm-smi nếu có
            gpu = 0 
            try:
                # Thử lấy dữ liệu GPU nếu có agent sensor
                pass
            except: pass
            
            return {"cpu": cpu, "ram": ram, "gpu": gpu, "ts": time.time()}
        except:
            return {"cpu": 0, "ram": 0, "gpu": 0, "ts": time.time()}

    async def run_forever(self):
        """Vòng lặp nhịp đập v31.0 - Thấu thị và Cảnh báo."""
        print("💓 [PULSE-v31.0] Quantum Pulse Service is Online. Đang thấu thị tài nguyên...")
        await asyncio.sleep(5)
        
        while True:
            try:
                # 1. Kiểm tra sức khỏe Service
                health = await self.get_system_health()
                
                # 2. Thu thập Telemetry phần cứng
                stats = await self.get_hardware_stats()
                
                # 3. Publish lên Dashboard qua Redis
                # 💎 [TELEMETRY-FLATTEN]: Đưa các chỉ số ra root để UI Dashboard dễ dàng tiếp nhận
                pulse_data = {
                    "cpu": stats["cpu"],
                    "ram": stats["ram"],
                    "gpu": stats["gpu"],
                    "status": health["status"],
                    "health": health,
                    "active_thoughts": "IDLE",
                    "ts": stats["ts"]
                }
                
                log = json.dumps({"tag": "PULSE", "data": pulse_data, "ts": time.time()}, ensure_ascii=False)
                # 📡 [BROADCAST]: Phát sóng lên Dashboard
                redis_safe(lambda r: r.publish("monitor:pulse_channel", log))
                # 🧠 [NEURAL-CACHE]: Lưu vào bộ nhớ đệm cho Giao thức Nhật ký Thông minh
                redis_safe(lambda r: r.set("hardware_pulse_cache", json.dumps(pulse_data), ex=60))

                # 🛡️ Cảnh báo Telegram khi có biến động lớn
                current_status = health["status"]
                if current_status != self.last_status:
                    if current_status != "OPTIMAL":
                        alert = [
                            f"🚨 *[ZENITH ALERT — {current_status}]*",
                            f"📊 *CPU:* {stats['cpu']}% | *RAM:* {stats['ram']}%",
                            f"📅 _{time.strftime('%H:%M:%S')}_",
                            "\n".join(health['details']),
                            "⚠️ *Master, hệ thống đang mất ổn định!*"
                        ]
                        await self._send_tg("\n".join(alert))
                    else:
                        await self._send_tg(f"✅ *[ZENITH RECOVERED]*\n💎 *Hệ thống đã đạt trạng thái Optimal.*")
                    self.last_status = current_status

            except Exception as e:
                print(f"⚠️ [PULSE-LOOP-ERR] {e}")
            
            await asyncio.sleep(60)  # Tăng giãn cách quét lên 60 giây theo lệnh Master

async def start_pulse():
    """Hàm khởi động Nhịp đập từ main.py."""
    await pulse.run_forever()

pulse = ZenithPulse()
