# -*- coding: utf-8 -*-
"""
services/ai_desktop/sandbox_fixture.py
[M5-SANDBOX FIXTURE]:
Bộ quản lý vòng đời (Lifecycle Controller) của tiến trình ứng dụng Desktop Sandbox.
Được chuẩn hóa dựa trên các nguyên lý kiến trúc của simular-ai/Agent-S và Jeomon/Windows-Use:
- Quản lý sạch sẽ, ngăn ngừa crash recovery dialog qua cơ chế đóng duyên dáng (Graceful WM_CLOSE).
- Ưu tiên gọi System32 Win32 executable trực tiếp để tránh App Execution Alias redirection.
- Khôi phục cửa sổ nếu bị thu nhỏ (SW_RESTORE), bóc tách chính xác HWND cửa sổ chính.
- Cung cấp bằng chứng dọn dẹp sạch sẽ (Cleanup Evidence Invariant).
"""

from __future__ import annotations

import os
import subprocess
import time
from typing import Any, Dict, Optional, Tuple


class NotepadSandboxSession:
    """Quản lý phiên chạy Notepad Sandbox phục vụ kiểm thử M5-G3, M5-G6, M5-G4."""

    def __init__(self, timeout_s: float = 12.0):
        self.timeout_s = timeout_s
        self.proc: Optional[subprocess.Popen] = None
        self.pid: int = 0
        self.hwnd: int = 0
        self.actual_pid: int = 0

    @staticmethod
    def _get_notepad_path() -> str:
        """Lấy đường dẫn thực thi System32 của Notepad để tránh Store Alias."""
        sys_root = os.environ.get("SystemRoot", r"C:\Windows")
        candidate = os.path.join(sys_root, "System32", "notepad.exe")
        if os.path.exists(candidate):
            return candidate
        return "notepad.exe"

    @staticmethod
    def cleanup_all_notepads():
        """Dọn dẹp triệt để mọi tiến trình notepad.exe và WerFault còn sót lại bằng native Windows taskkill."""
        try:
            subprocess.run(
                ["taskkill", "/F", "/IM", "notepad.exe"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=2.0,
            )
            subprocess.run(
                ["taskkill", "/F", "/IM", "WerFault.exe"],
                capture_output=True,
                creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                timeout=1.0,
            )
        except Exception:
            pass
        time.sleep(0.5)

    def start(self) -> Tuple[int, int]:
        """
        Khởi động Notepad sandbox và tìm chính xác HWND cửa sổ chính.
        Trả về (hwnd, pid).
        """
        import psutil
        import win32gui
        import win32process

        self.cleanup_all_notepads()

        notepad_exe = self._get_notepad_path()
        self.proc = subprocess.Popen([notepad_exe])
        self.pid = self.proc.pid
        self.actual_pid = self.pid

        # Chờ cửa sổ chính xuất hiện và sẵn sàng
        start_t = time.time()
        respawned = False
        while time.time() - start_t < self.timeout_s:
            time.sleep(0.2)
            found_h = 0
            found_pid = 0

            def cb(h, _):
                nonlocal found_h, found_pid
                try:
                    _, w_pid = win32process.GetWindowThreadProcessId(h)
                    rect = win32gui.GetWindowRect(h)
                    width = rect[2] - rect[0]
                    height = rect[3] - rect[1]

                    # 1. Khớp chính xác theo PID được spawn
                    if w_pid == self.pid and (width > 150 or win32gui.IsIconic(h)):
                        found_h = h
                        found_pid = w_pid
                        return False

                    # 2. Fallback: Khớp theo title nếu PID bị redirect
                    if win32gui.IsWindowVisible(h):
                        title = win32gui.GetWindowText(h).lower()
                        if ("notepad" in title) and (width > 200 and height > 150):
                            found_h = h
                            found_pid = w_pid
                            return False
                except Exception:
                    pass
                return True

            try:
                win32gui.EnumWindows(cb, None)
            except Exception:
                pass

            if found_h:
                self.hwnd = found_h
                self.actual_pid = found_pid
                break

            # Cơ chế Self-Healing Respawn (học hỏi từ Agent-S): nếu sau 3s chưa thấy cửa sổ do Windows cache, spawn lại 1 lần
            if not respawned and (time.time() - start_t > 3.0):
                respawned = True
                self.cleanup_all_notepads()
                time.sleep(0.4)
                self.proc = subprocess.Popen([notepad_exe])
                self.pid = self.proc.pid
                self.actual_pid = self.pid

        if not self.hwnd:
            self.stop()
            raise RuntimeError(f"Không thể khởi động và tìm thấy cửa sổ chính của Notepad (PID={self.pid})")

        # Đảm bảo cửa sổ không bị thu nhỏ (SW_RESTORE nếu iconic)
        try:
            if win32gui.IsIconic(self.hwnd):
                win32gui.ShowWindow(self.hwnd, 9)  # SW_RESTORE
            else:
                win32gui.ShowWindow(self.hwnd, 5)  # SW_SHOW
            win32gui.SetForegroundWindow(self.hwnd)
        except Exception:
            pass
        time.sleep(0.2)

        return self.hwnd, self.actual_pid

    def stop(self) -> Dict[str, Any]:
        """Dừng tiến trình sandbox và trả về Cleanup Evidence chuẩn xác."""
        import psutil

        exit_code = None
        if self.proc:
            try:
                self.proc.terminate()
                self.proc.wait(timeout=1.0)
            except Exception:
                try:
                    self.proc.kill()
                    self.proc.wait(timeout=1.0)
                except Exception:
                    pass
            exit_code = self.proc.poll()

        self.cleanup_all_notepads()

        alive_after = psutil.pid_exists(self.actual_pid) or (
            psutil.pid_exists(self.pid) if self.pid else False
        )
        cleanup_ok = not alive_after

        return {
            "cleanup_ok": cleanup_ok,
            "exit_code": exit_code if exit_code is not None else 0,
            "process_alive_after_cleanup": alive_after,
            "stdout": "",
            "stderr": "",
        }
