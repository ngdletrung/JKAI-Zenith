import time
import platform
import logging

logger = logging.getLogger(__name__)

try:
    import psutil
    HAS_PSUTIL = True
except ImportError:
    HAS_PSUTIL = False
    logger.warning(", thư viện `psutil` chưa được cài đặt. World State sẽ chỉ hiển thị dữ liệu giả lập. Vui lòng cài đặt bằng: pip install psutil")

class WorldStateEngine:
    """
    Tầng Nhận Thức Môi Trường (World State)
    Giúp AI biết được giới hạn vật lý và trạng thái hệ thống hiện tại
    trước khi đưa ra quyết định (State-Centric).
    """
    
    def __init__(self):
        self.last_update = 0
        self.cache_ttl = 5  # Cache trong 5 giây để tránh poll liên tục
        self._current_state = {}

    def get_current_state(self) -> dict:
        """Lấy trạng thái tổng quan của hệ thống thực tại."""
        now = time.time()
        if now - self.last_update < self.cache_ttl and self._current_state:
            return self._current_state

        state = {
            "timestamp": now,
            "os": platform.system(),
            "cpu_percent": 0.0,
            "ram_percent": 0.0,
            "pressure_level": "normal", # normal, high, critical
            "network_status": "online"
        }

        if HAS_PSUTIL:
            try:
                # 🛡️ [NON-BLOCKING]: Không dùng interval=0.1 vì nó sẽ block toàn bộ Event Loop!
                state["cpu_percent"] = psutil.cpu_percent(interval=None)
                ram = psutil.virtual_memory()
                state["ram_percent"] = ram.percent
                
                # Phân tích mức độ áp lực (Pressure)
                if state["cpu_percent"] > 90 or state["ram_percent"] > 90:
                    state["pressure_level"] = "critical"
                elif state["cpu_percent"] > 75 or state["ram_percent"] > 80:
                    state["pressure_level"] = "high"
                else:
                    state["pressure_level"] = "normal"
            except Exception as e:
                logger.error(f"Lỗi khi đọc hardware metrics: {e}")

        self._current_state = state
        self.last_update = now
        return state

    def get_world_context_string(self) -> str:
        """Tạo chuỗi context để inject vào Prompt của System."""
        state = self.get_current_state()
        
        pressure_msg = "Ổn định"
        if state['pressure_level'] == 'high':
            pressure_msg = "Tải cao (Nên dùng Fast Mode)"
        elif state['pressure_level'] == 'critical':
            pressure_msg = "NGUY HIỂM (Chỉ thực hiện tác vụ khẩn cấp, vô hiệu hóa Deep Reasoning)"

        return (
            f"[WORLD STATE]\n"
            f"- CPU: {state['cpu_percent']}% | RAM: {state['ram_percent']}%\n"
            f"- Tình trạng: {pressure_msg}"
        )

# Global instance
world_engine = WorldStateEngine()
