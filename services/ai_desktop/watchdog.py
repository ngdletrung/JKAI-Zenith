# -*- coding: utf-8 -*-
"""
services/ai_desktop/watchdog.py
[M5-G5] Emergency Stop & Watchdog Timer Controller.
Bảo vệ chống treo luồng thao tác chuột và cung cấp cơ chế ngắt khẩn cấp (Circuit Breaker).
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

logger = logging.getLogger("ai-desktop-watchdog")


class DesktopEmergencyStop(Exception):
    """Ngoại lệ khi kích hoạt dừng khẩn cấp hoặc chạm trần Watchdog."""
    pass


class DesktopWatchdog:
    """
    [M5-G5 WATCHDOG]
    Giám sát thời gian thực thi của tác vụ chuột.
    Tự động kích hoạt cờ ngắt nếu hành động kéo dài vượt quá `timeout_s` (mặc định 10.0 giây).
    """

    def __init__(self, timeout_s: float = 10.0, on_timeout_cb: Optional[Callable[[], None]] = None):
        self.timeout_s = timeout_s
        self.on_timeout_cb = on_timeout_cb
        self._cancel_event = threading.Event()
        self._timed_out: bool = False
        self._start_time: float = 0.0
        self._is_running: bool = False
        self._timer_thread: Optional[threading.Thread] = None

    def start(self) -> None:
        """Bắt đầu đếm nhịp Watchdog."""
        self._cancel_event.clear()
        self._timed_out = False
        self._start_time = time.monotonic()
        self._is_running = True

        def _monitor():
            while self._is_running and not self._cancel_event.is_set():
                elapsed = time.monotonic() - self._start_time
                if elapsed >= self.timeout_s:
                    logger.warning(f"🚨 [WATCHDOG-TRIGGERED] Thao tác chuột bị ngắt do vượt quá timeout {self.timeout_s}s!")
                    self._timed_out = True
                    self._cancel_event.set()
                    if self.on_timeout_cb:
                        try:
                            self.on_timeout_cb()
                        except Exception:
                            pass
                    break
                time.sleep(0.05)

        self._timer_thread = threading.Thread(target=_monitor, daemon=True, name="M5-Desktop-Watchdog")
        self._timer_thread.start()

    def stop(self) -> None:
        """Dừng Watchdog an toàn khi tác vụ hoàn thành."""
        self._is_running = False

    def is_cancelled(self) -> bool:
        """Kiểm tra xem tác vụ có bị ngắt khẩn cấp hoặc timeout hay không."""
        return self._cancel_event.is_set()

    def is_timed_out(self) -> bool:
        """Kiểm tra xem watchdog có bị quá hạn thời gian hay không."""
        return self._timed_out

    def trigger_emergency_stop(self) -> None:
        """Kích hoạt ngắt khẩn cấp tức thời từ bên ngoài."""
        logger.critical("🛑 [EMERGENCY-STOP] Kích hoạt dừng khẩn cấp toàn bộ thao tác chuột!")
        self._cancel_event.set()
        self.stop()
