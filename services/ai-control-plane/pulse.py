# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — PROACTIVE PULSE & TELEGRAM SENTINEL v32.0        ║
║   Giám Sát Nhịp Tim Hạ Tầng, Cảnh Báo Chuẩn Xác & Tin Cậy        ║
╚══════════════════════════════════════════════════════════════════╝
*Kiến Trúc Sư Trưởng Chủ Động Tối Ưu Hóa Cảnh Báo Telegram & Health Stream. 💓🏛️⚡*
"""

import asyncio
import json
import os
import time
import httpx
from redis_client import redis_safe


class ZenithPulse:
    """
    💓 JKAI ZENITH: PROACTIVE PULSE SERVICE v32.0
    - Phân tách Core Services (Sống còn) vs Auxiliary Services (Tùy chọn).
    - Chỉ phát cảnh báo Telegram khi Core Service gặp sự cố thực sự.
    - Cung cấp thông tin chuẩn xác về CPU, RAM, VRAM GPU AMD RX 6600.
    """
    def __init__(self):
        self.tg_token = os.getenv("TELEGRAM_TOKEN")
        self.master_id = os.getenv("MASTER_ID")
        self.brain_url = os.getenv("AI_BRAIN_URL", "http://ai-brain:8000")
        self.last_status = "OPTIMAL"
        self.client = httpx.AsyncClient(timeout=5.0)
        self.satellite_url = "http://host.docker.internal:9997"
        self.akai_token = os.getenv("AKAI_PRIME_TOKEN", "AKAI_PRIME_SUPER_SECRET_999")

    async def _send_tg(self, message: str):
        """Gửi tin nhắn Telegram tới Master."""
        if not self.tg_token or not self.master_id:
            return
        try:
            await self.client.post(
                f"https://api.telegram.org/bot{self.tg_token}/sendMessage",
                json={"chat_id": self.master_id, "text": message[:4000], "parse_mode": "Markdown"},
                timeout=5.0
            )
        except Exception as e:
            print(f"❌ [PULSE-TG-ERR] {e}")

    async def get_system_health(self):
        """Thu thập chỉ số sức khỏe toàn hệ thống với sự phân cấp rõ ràng."""
        health = {
            "status": "OPTIMAL",
            "core_services": {},
            "aux_services": {},
            "details": []
        }
        
        # 1. CORE SERVICES (Ảnh hưởng trực tiếp đến trạng thái OPTIMAL / DEGRADED)
        core_checks = {
            "📡 AI-Control-Plane": "http://localhost:8000/health",
            "🧠 AI-Brain": f"{self.brain_url.rstrip('/')}/health",
        }
        
        # 2. AUXILIARY SERVICES (Bổ trợ / Tùy chọn)
        aux_checks = {
            "🦾 AI-Executor": "http://ai-executor-1:8000/health",
            "🔍 Qdrant DB": "http://qdrant:6333/healthz",
            "📚 RAG-Service": "http://rag-service:8000/health",
            "🔗 N8N-Main": "http://n8n-main:5678/healthz"
        }

        async def check_url(name, url, is_core=True):
            try:
                r = await self.client.get(url, timeout=1.5)
                if r.status_code in [200, 204]:
                    return name, "Online ✅", True, is_core
                else:
                    return name, f"Degraded ({r.status_code}) ⚠️", False, is_core
            except Exception:
                return name, "Standby ⚪" if not is_core else "Offline ❌", False, is_core

        tasks = [check_url(n, u, True) for n, u in core_checks.items()] + \
                [check_url(n, u, False) for n, u in aux_checks.items()]
        results = await asyncio.gather(*tasks)

        core_failures = 0
        for name, label, is_ok, is_core in results:
            if is_core:
                health["core_services"][name] = label
                health["details"].append(f"{name}: `{label}`")
                if not is_ok:
                    core_failures += 1
            else:
                health["aux_services"][name] = label
                health["details"].append(f"{name}: `{label}`")

        # 3. Redis Health Check
        is_redis = redis_safe(lambda r: r.ping(), False)
        health["details"].append(f"📡 Redis AI: `{'Online ✅' if is_redis else 'Offline ❌'}`")
        if not is_redis:
            core_failures += 1

        # Xác định trạng thái tổng thể
        if core_failures == 0:
            health["status"] = "OPTIMAL"
        elif core_failures == 1:
            health["status"] = "DEGRADED"
        else:
            health["status"] = "CRITICAL"

        return health

    async def get_hardware_stats(self):
        """Thu thập telemetry phần cứng từ Host Bridge siêu tốc."""
        cpu = 0
        ram = 0
        gpu = 0
        vram_mb = 0
        try:
            import psutil
            cpu = psutil.cpu_percent()
            ram = psutil.virtual_memory().percent
        except Exception:
            pass

        try:
            res = await self.client.get(
                f"{self.satellite_url}/telemetry",
                headers={"X-AKAI-TOKEN": self.akai_token},
                timeout=1.5
            )
            if res.status_code == 200:
                data = res.json()
                cpu = int(round(float(data.get("cpu", cpu))))
                ram = int(round(float(data.get("ram", ram))))
                gpu = int(round(float(data.get("gpu", gpu))))
                vram_mb = int(data.get("vram_mb", 0))
        except Exception:
            pass
            
        return {"cpu": cpu, "ram": ram, "gpu": gpu, "vram_mb": vram_mb, "ts": time.time()}

    async def run_forever(self):
        """Vòng lặp nhịp đập v32.0 - Giám sát chính xác tuyệt đối."""
        print("💓 [PULSE-v32.0] Quantum Pulse Service Online. Giám sát chính xác tài nguyên...")
        await asyncio.sleep(2)
        
        cached_health = {"status": "OPTIMAL", "details": []}
        last_health_check = 0.0
        
        while True:
            try:
                now = time.time()
                # Kiểm tra sức khỏe Service mỗi 15 giây
                if now - last_health_check > 15:
                    cached_health = await self.get_system_health()
                    last_health_check = now
                
                # Thu thập Telemetry phần cứng mỗi 2s
                stats = await self.get_hardware_stats()
                
                pulse_data = {
                    "cpu": stats["cpu"],
                    "ram": stats["ram"],
                    "gpu": stats["gpu"],
                    "vram_mb": stats["vram_mb"],
                    "status": cached_health["status"],
                    "health": cached_health,
                    "active_thoughts": "IDLE",
                    "ts": stats["ts"]
                }
                
                log = json.dumps({"tag": "PULSE", "data": pulse_data, "ts": time.time()}, ensure_ascii=False)
                redis_safe(lambda r: r.publish("monitor:pulse_channel", log))
                redis_safe(lambda r: r.set("service_pulse_cache", json.dumps(pulse_data), ex=60))

                try:
                    pulse_file = "/intelligence/protocols/hardware_pulse.json"
                    os.makedirs(os.path.dirname(pulse_file), exist_ok=True)
                    with open(pulse_file, 'w', encoding='utf-8') as f:
                        json.dump(pulse_data, f, ensure_ascii=False, indent=4)
                except Exception:
                    pass

                # Cảnh báo Telegram khi có biến động thực sự
                current_status = cached_health["status"]
                if current_status != self.last_status:
                    time_str = time.strftime('%H:%M:%S %d/%m/%Y')
                    if current_status != "OPTIMAL":
                        alert = [
                            f"🚨 *[ZENITH ALERT — {current_status}]*",
                            f"📊 *CPU:* {stats['cpu']}% | *RAM:* {stats['ram']}% | *GPU:* {stats['gpu']}%",
                            f"📅 _{time_str}_",
                            "",
                            "🛠️ *Chi tiết dịch vụ:*",
                            "\n".join(f"- {d}" for d in cached_health['details']),
                            "",
                            "⚠️ *Báo cáo Master: Phát hiện biến động ở dịch vụ cốt lõi.*"
                        ]
                        await self._send_tg("\n".join(alert))
                    else:
                        recover_msg = [
                            "✅ *[ZENITH RECOVERED — OPTIMAL]*",
                            f"📊 *CPU:* {stats['cpu']}% | *RAM:* {stats['ram']}% | *GPU:* {stats['gpu']}%",
                            f"📅 _{time_str}_",
                            "",
                            "💎 *Toàn bộ các phân hệ cốt lõi đã đạt trạng thái tối ưu 100%. Sẵn sàng phục vụ Master!*"
                        ]
                        await self._send_tg("\n".join(recover_msg))
                    self.last_status = current_status

            except Exception as e:
                print(f"⚠️ [PULSE-LOOP-ERR] {e}")
            
            await asyncio.sleep(2)


async def start_pulse():
    await pulse.run_forever()


pulse = ZenithPulse()
