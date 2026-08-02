"""
╔══════════════════════════════════════════════════════════════════╗
║   JKAI ZENITH — CENTRAL HOMEOSTASIS ENGINE                       ║
║   Động Cơ Cân Bằng Nội Môi & Kiểm Soát Tài Nguyên Vĩ Mô          ║
╚══════════════════════════════════════════════════════════════════╝
*Thuộc Ban Quản Trị Tài Nguyên & Sinh Tồn của Tập đoàn JKAI. 🌌🏢🔋*
"""

try:
    import psutil
except ImportError:
    psutil = None
import time
import os
import asyncio
import logging
from typing import Dict, Any, List

from core.utils.engine import engine
from core.utils.purge_vram import purge_ollama

logger = logging.getLogger("HomeostasisEngine")

class HomeostasisEngine:
    """
    🏢 BAN ĐIỀU PHỐI NỘI MÔI (Homeostasis & Resource Governor)
    Giám sát các chỉ số sinh tồn vĩ mô của máy chủ: RAM, CPU, VRAM.
    Điều tiết luồng xử lý song song để tránh sự cố treo hệ thống (OOM/Overload).
    """
    def __init__(self, max_ram_percent: float = 85.0, max_cpu_percent: float = 90.0):
        self.max_ram_percent = max_ram_percent
        self.max_cpu_percent = max_cpu_percent
        self._last_purge_time = 0.0
        self._purge_cooldown = 60.0  # Chống spam giải phóng VRAM liên tục

    def check_vitals(self) -> Dict[str, Any]:
        """
        📊 [ĐO NHỊP TIM HỆ THỐNG]: Thống kê tài nguyên thực tế của máy chủ.
        """
        try:
            if psutil is None:
                raise ImportError("Thư viện 'psutil' chưa được cài đặt.")
            ram = psutil.virtual_memory().percent
            cpu = psutil.cpu_percent(interval=0.05)
            
            danger = False
            warnings = []
            
            if ram > self.max_ram_percent:
                danger = True
                warnings.append(f"RAM OVERLOAD ({ram}%) - Nguy cơ OOM (Out of Memory) Crash!")
                
            if cpu > self.max_cpu_percent:
                danger = True
                warnings.append(f"CPU OVERLOAD ({cpu}%) - Nguy cơ treo luồng xử lý!")
                
            return {
                "survival_threat": danger,
                "vitals": {
                    "ram": ram,
                    "cpu": cpu
                },
                "warnings": warnings
            }
        except Exception as e:
            # Fallback nếu psutil lỗi (Ví dụ chạy trong môi trường tối giản)
            return {
                "survival_threat": False, 
                "vitals": {"ram": 50.0, "cpu": 50.0}, 
                "warnings": [f"⚠️ Cảnh báo Ban Thư ký: Lỗi đo chỉ số ({str(e)}). Chuyển chế độ dự phòng."]
            }

    async def enforce_homeostasis(self, task_id: str = "sys", trace_id: str = "sys") -> int:
        """
        🛡️ [ĐIỀU TIẾT PHÂN BỔ]: Trả về mức độ song song (concurrency) tối ưu dựa trên nhịp tim hệ thống.
        Nếu RAM/CPU quá cao, hệ thống tự động bóp nghẹt băng thông song song hoặc kích hoạt xả VRAM.
        """
        health = self.check_vitals()
        vitals = health["vitals"]
        ram, cpu = vitals.get("ram", 0.0), vitals.get("cpu", 0.0)
        
        # 🏢 LOG VĂN PHÒNG CHUẨN DOANH NGHIỆP
        engine.publish_mission_log(
            "HOMEOSTASIS",
            f"📈 [BAN ĐIỀU HÀNH VĨ MÔ] Chỉ số tài nguyên: RAM {ram}% | CPU {cpu}%",
            task_id,
            trace_id
        )

        if health["survival_threat"]:
            for warning in health["warnings"]:
                engine.publish_mission_log(
                    "HOMEOSTASIS_WARNING",
                    f"🚨 [CẢNH BÁO NGUY HIỂM] {warning}",
                    task_id,
                    trace_id
                )
            
            # 🧬 ĐỒNG BỘ NHÂN QUẢ: Phát sóng tín hiệu VRAM_PRESSURE_HIGH lên hệ thần kinh trung ương thưa Master
            try:
                from core.kernel.cognitive_event_bus import cognitive_event_bus, CognitiveEvent
                import uuid
                asyncio.create_task(cognitive_event_bus.publish(CognitiveEvent(
                    event_id=f"evt-hmt-{uuid.uuid4().hex[:6]}",
                    event_type="VRAM_PRESSURE_HIGH",
                    task_id=task_id,
                    agent_id="HomeostasisEngine",
                    payload={"vitals": vitals, "warnings": health["warnings"]}
                )))
            except Exception as e:
                logger.error(f"❌ [HOMEOSTASIS-BUS-ERR]: Không thể phát sóng sự kiện vĩ mô: {e}")

            # Kích hoạt dọn dẹp khẩn cấp nếu bị nghẽn do VRAM mô hình
            now = time.time()
            if now - self._last_purge_time > self._purge_cooldown:
                engine.publish_mission_log(
                    "HOMEOSTASIS_ACTION",
                    "♻️ [QUYẾT ĐỊNH BAN ĐIỀU HÀNH] Kích hoạt khẩn cấp giải phóng GPU VRAM Ollama để hồi sức máy chủ...",
                    task_id,
                    trace_id
                )
                try:
                    await purge_ollama()
                    self._last_purge_time = now
                except Exception as e:
                    engine.publish_mission_log(
                        "ERROR",
                        f"❌ [LỖI GIẢI PHÓNG VRAM] {str(e)}",
                        task_id,
                        trace_id
                    )

            # Thắt chặt luồng song song ở mức tối thiểu để bảo toàn mạng sống
            return 2
        
        # Trạng thái khỏe mạnh bình thường
        if ram > 70.0 or cpu > 75.0:
            engine.publish_mission_log(
                "HOMEOSTASIS",
                "⚠️ [BAN ĐIỀU HÀNH VĨ MÔ] Tài nguyên tiệm cận mức báo động. Đề xuất bóp luồng song song trung bình.",
                task_id,
                trace_id
            )
            return 3  # Medium throttle
            
        return 8  # Full scale concurrency

homeostasis_engine = HomeostasisEngine()

