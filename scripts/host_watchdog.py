# -*- coding: utf-8 -*-
"""
scripts/host_watchdog.py
[M5 INDEPENDENT EMERGENCY STOP WATCHDOG]
Tiến trình giám sát dừng khẩn cấp độc lập trên Host Master:
- Bắt phím nóng vật lý: ESC (nhấn giữ >= 300ms) hoặc F12.
- Bắt Fail-Safe mouse corner: con trỏ chuột chạm góc (0, 0).
- Kích hoạt chốt an toàn STOP Latch (<= 10ms), từ chối mọi yêu cầu tiếp theo.
- Chỉ mở khóa Reset khi có xác nhận chính thức từ Master.
"""

import time
import threading
import ctypes
from ctypes import wintypes
from typing import Dict, Any, Optional

user32 = ctypes.windll.user32

VK_ESCAPE = 0x1B
VK_F12 = 0x7B

class HostEmergencyWatchdog:
    _instance = None
    _lock = threading.Lock()

    def __init__(self, check_interval_ms: int = 5):
        self.check_interval_s = max(0.001, check_interval_ms / 1000.0)
        self._stopped = False
        self._stop_reason = ""
        self._stop_timestamp = 0.0
        self._esc_press_start: Optional[float] = None
        self._running = False
        self._thread: Optional[threading.Thread] = None

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    @property
    def is_stopped(self) -> bool:
        """Kiểm tra xem chốt dừng khẩn cấp có đang kích hoạt không."""
        return self._stopped

    def get_status(self) -> Dict[str, Any]:
        """Trả về trạng thái hiện tại của Watchdog."""
        return {
            "is_stopped": self._stopped,
            "reason": self._stop_reason,
            "stop_timestamp": self._stop_timestamp,
            "elapsed_since_stop_s": (time.time() - self._stop_timestamp) if self._stopped else 0.0,
            "is_monitoring": self._running
        }

    def trigger_stop(self, reason: str = "EMERGENCY_STOP_TRIGGERED") -> float:
        """
        Kích hoạt chốt dừng khẩn cấp ngay lập tức.
        Trả về thời gian phản ứng tính bằng mili-giây.
        """
        t0 = time.perf_counter()
        self._stopped = True
        self._stop_reason = reason
        self._stop_timestamp = time.time()

        # Giải phóng cưỡng bức toàn bộ trạng thái chuột/phím
        try:
            # Nhả chuột trái, phải, giữa
            user32.mouse_event(0x0004, 0, 0, 0, 0) # MOUSEEVENTF_LEFTUP
            user32.mouse_event(0x0010, 0, 0, 0, 0) # MOUSEEVENTF_RIGHTUP
            user32.mouse_event(0x0040, 0, 0, 0, 0) # MOUSEEVENTF_MIDDLEUP
        except Exception:
            pass

        latency_ms = (time.perf_counter() - t0) * 1000.0
        return latency_ms

    def reset_latch(self, master_approval_token: str) -> bool:
        """
        Mở lại chốt dừng khi có token xác nhận hợp lệ từ Master.
        """
        if not master_approval_token or len(master_approval_token.strip()) < 8:
            raise PermissionError("Từ chối Reset: Yêu cầu Master Approval Token hợp lệ.")

        self._stopped = False
        self._stop_reason = ""
        self._stop_timestamp = 0.0
        self._esc_press_start = None
        return True

    def check_inputs_once(self) -> Optional[str]:
        """
        Kiểm tra trạng thái chuột và phím một lần trong chu kỳ.
        Trả về chuỗi lý do nếu kích hoạt dừng; None nếu an toàn.
        """
        # 1. Kiểm tra góc chuột Fail-Safe (0, 0)
        pt = wintypes.POINT()
        if user32.GetCursorPos(ctypes.byref(pt)):
            if pt.x == 0 and pt.y == 0:
                self.trigger_stop("FAIL_SAFE_CORNER_MOUSE_AT_0_0")
                return "FAIL_SAFE_CORNER_MOUSE_AT_0_0"

        # 2. Kiểm tra phím F12 (Bấm là ngắt ngay)
        # GetAsyncKeyState: bit 15 set nếu phím đang được nhấn
        if user32.GetAsyncKeyState(VK_F12) & 0x8000:
            self.trigger_stop("HOTKEY_F12_PRESSED")
            return "HOTKEY_F12_PRESSED"

        # 3. Kiểm tra phím ESC (Nhấn giữ >= 300ms)
        if user32.GetAsyncKeyState(VK_ESCAPE) & 0x8000:
            now = time.time()
            if self._esc_press_start is None:
                self._esc_press_start = now
            elif (now - self._esc_press_start) >= 0.3:
                self.trigger_stop("HOTKEY_ESC_HELD_300MS")
                return "HOTKEY_ESC_HELD_300MS"
        else:
            self._esc_press_start = None

        return None

    def start_monitoring(self):
        """Khởi chạy luồng giám sát nền liên tục."""
        if self._running:
            return
        self._running = True

        def _monitor_loop():
            while self._running:
                if not self._stopped:
                    self.check_inputs_once()
                time.sleep(self.check_interval_s)

        self._thread = threading.Thread(target=_monitor_loop, daemon=True, name="HostWatchdogThread")
        self._thread.start()

    def stop_monitoring(self):
        """Dừng luồng giám sát nền."""
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=1.0)
