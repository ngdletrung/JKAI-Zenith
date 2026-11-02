# -*- coding: utf-8 -*-
"""
services/ai_desktop/window_inspector.py
[M5-G1 & M5-G3] Window & Control Element Inspector.
Trích xuất cây điều khiển, BoundingBox, Native Elevation và Monitor/DPI thông số
của các phần tử giao diện trên Windows phục vụ thao tác chuột chính xác và an toàn.
"""

from __future__ import annotations

import ctypes
import os
from ctypes import wintypes
from dataclasses import dataclass
from typing import Any, Dict, List, Optional, Protocol, Tuple


def check_process_elevation(pid: int) -> Tuple[bool, str]:
    """
    [M5-G0/G3 NATIVE ELEVATION CHECK]:
    Xác định tiến trình có chạy dưới quyền Administrator (Elevated) hay không
    sử dụng Windows NT Security Token Information (TokenElevation).
    Trả về (is_elevated: bool, status: str).
    """
    if os.name != "nt" or not pid:
        return False, "NON_WINDOWS_OR_ZERO_PID"

    PROCESS_QUERY_LIMITED_INFORMATION = 0x1000
    TOKEN_QUERY = 0x0008
    TokenElevation = 20

    class TOKEN_ELEVATION(ctypes.Structure):
        _fields_ = [("TokenIsElevated", wintypes.DWORD)]

    kernel32 = ctypes.windll.kernel32
    advapi32 = ctypes.windll.advapi32

    h_process = kernel32.OpenProcess(PROCESS_QUERY_LIMITED_INFORMATION, False, pid)
    if not h_process:
        err = kernel32.GetLastError()
        # Lỗi Access Denied (5) thường là do process chạy dưới quyền Administrator hoặc SYSTEM
        if err == 5:
            return True, "ACCESS_DENIED_LIKELY_ELEVATED_OR_SYSTEM"
        return False, f"OPEN_PROCESS_FAILED_{err}"

    h_token = wintypes.HANDLE()
    try:
        if not advapi32.OpenProcessToken(h_process, TOKEN_QUERY, ctypes.byref(h_token)):
            err = kernel32.GetLastError()
            if err == 5:
                return True, "TOKEN_ACCESS_DENIED_LIKELY_ELEVATED"
            return False, f"OPEN_TOKEN_FAILED_{err}"

        try:
            elevation = TOKEN_ELEVATION()
            cb_size = wintypes.DWORD(ctypes.sizeof(elevation))
            ret_len = wintypes.DWORD(0)
            if advapi32.GetTokenInformation(
                h_token, TokenElevation, ctypes.byref(elevation), cb_size, ctypes.byref(ret_len)
            ):
                is_elevated = bool(elevation.TokenIsElevated)
                return is_elevated, "VERIFIED_ELEVATED" if is_elevated else "VERIFIED_STANDARD"
            return False, f"GET_TOKEN_INFO_FAILED_{kernel32.GetLastError()}"
        finally:
            kernel32.CloseHandle(h_token)
    finally:
        kernel32.CloseHandle(h_process)


@dataclass
class WindowElementRef:
    """Tham chiếu phần tử giao diện trên màn hình Windows."""
    name: str
    control_type: str
    automation_id: str
    rect: Tuple[int, int, int, int]  # (left, top, right, bottom)
    hwnd: int = 0

    @property
    def center(self) -> Tuple[int, int]:
        """Tọa độ tâm điểm để click an toàn."""
        left, top, right, bottom = self.rect
        return (left + right) // 2, (top + bottom) // 2

    @property
    def width(self) -> int:
        return self.rect[2] - self.rect[0]

    @property
    def height(self) -> int:
        return self.rect[3] - self.rect[1]


class WindowInspectorProtocol(Protocol):
    """Protocol trừu tượng hóa việc đọc cửa sổ để phục vụ Mock và Native."""

    def get_foreground_window_info(self) -> Dict[str, Any]: ...
    def get_window_info(self, hwnd: Optional[int] = None) -> Dict[str, Any]: ...
    def inspect_window_elements(self, hwnd: int) -> List[WindowElementRef]: ...
    def find_element_by_name(self, hwnd: int, name: str) -> Optional[WindowElementRef]: ...


class MockWindowInspector:
    """
    [M5-G1] Mock Window Inspector phục vụ Unit Test.
    Giả lập cây giao diện chuẩn xác của ứng dụng Windows (như Notepad hay Calculator)
    để kiểm thử toàn bộ luồng mà không cần chạy ứng dụng thật trên desktop.
    """

    def __init__(self):
        self.mock_foreground: Dict[str, Any] = {
            "hwnd": 12345,
            "pid": 5678,
            "process_path": "C:\\Windows\\System32\\notepad.exe",
            "title": "Untitled - Notepad",
            "process_name": "notepad.exe",
            "rect": (100, 100, 900, 700),  # (left, top, right, bottom)
            "is_elevated": False,
            "elevation_status": "VERIFIED_STANDARD",
            "monitor_id": 1,
            "dpi": 96,
            "dpi_scale": 1.0,
        }
        self.mock_elements: Dict[int, List[WindowElementRef]] = {
            12345: [
                WindowElementRef(name="File", control_type="MenuItem", automation_id="Menu_File", rect=(110, 130, 150, 155), hwnd=12345),
                WindowElementRef(name="Edit", control_type="MenuItem", automation_id="Menu_Edit", rect=(155, 130, 195, 155), hwnd=12345),
                WindowElementRef(name="View", control_type="MenuItem", automation_id="Menu_View", rect=(200, 130, 240, 155), hwnd=12345),
                WindowElementRef(name="Text Editor", control_type="Edit", automation_id="EditorArea", rect=(105, 160, 895, 690), hwnd=12345),
                WindowElementRef(name="Close", control_type="Button", automation_id="Sys_Close", rect=(860, 105, 895, 130), hwnd=12345),
            ]
        }

    def get_foreground_window_info(self) -> Dict[str, Any]:
        return self.mock_foreground

    def get_window_info(self, hwnd: Optional[int] = None) -> Dict[str, Any]:
        return self.mock_foreground

    def inspect_window_elements(self, hwnd: int) -> List[WindowElementRef]:
        return self.mock_elements.get(hwnd, [])

    def find_element_by_name(self, hwnd: int, name: str) -> Optional[WindowElementRef]:
        target = name.strip().lower()
        for elem in self.inspect_window_elements(hwnd):
            if elem.name.lower() == target:
                return elem
        return None


class NativeWindowInspector:
    """
    [M5-LIVE] Native Window Inspector: Sử dụng pywin32 và Windows NT APIs để quét
    cửa sổ Foreground thật, kiểm tra quyền Administrator thực tế, thu thập thông số
    Monitor, DPI và bóc tách các control con trên hệ điều hành Windows.
    """

    def get_window_info(self, hwnd: Optional[int] = None) -> Dict[str, Any]:
        try:
            import win32gui
            import win32process

            if not hwnd:
                hwnd = win32gui.GetForegroundWindow()

            title = win32gui.GetWindowText(hwnd) if hwnd else ""
            rect = win32gui.GetWindowRect(hwnd) if hwnd else (0, 0, 0, 0)

            pid = 0
            if hwnd:
                _, pid = win32process.GetWindowThreadProcessId(hwnd)

            process_name = "unknown.exe"
            process_path = ""
            if pid:
                try:
                    import psutil
                    proc = psutil.Process(pid)
                    process_name = proc.name().lower()
                    process_path = proc.exe()
                except Exception:
                    pass

            # [NATIVE ELEVATION DETECTION]:
            is_elevated = False
            elevation_status = "NOT_VERIFIED"
            if pid:
                try:
                    is_elevated, elevation_status = check_process_elevation(pid)
                except Exception as e:
                    elevation_status = f"NOT_VERIFIED_{e}"

            # [DPI & MONITOR DETECTION]:
            dpi = 96
            dpi_scale = 1.0
            monitor_id = 0
            if os.name == "nt":
                try:
                    if hwnd:
                        dpi = ctypes.windll.user32.GetDpiForWindow(hwnd)
                    if not dpi:
                        dpi = ctypes.windll.user32.GetDpiForSystem()
                    dpi_scale = round(dpi / 96.0, 2)
                    monitor_id = int(ctypes.windll.user32.MonitorFromWindow(hwnd, 2))
                except Exception:
                    pass

            return {
                "hwnd": hwnd,
                "pid": pid,
                "process_name": process_name,
                "process_path": process_path,
                "title": title,
                "rect": rect,
                "is_elevated": is_elevated,
                "elevation_status": elevation_status,
                "monitor_id": monitor_id,
                "dpi": dpi,
                "dpi_scale": dpi_scale,
            }
        except Exception as e:
            return {
                "hwnd": 0,
                "pid": 0,
                "title": "",
                "process_name": "",
                "process_path": "",
                "rect": (0, 0, 0, 0),
                "is_elevated": False,
                "elevation_status": "NOT_VERIFIED",
                "monitor_id": 0,
                "dpi": 96,
                "dpi_scale": 1.0,
                "error": str(e),
            }

    def get_foreground_window_info(self) -> Dict[str, Any]:
        return self.get_window_info(hwnd=None)

    def inspect_window_elements(self, hwnd: int) -> List[WindowElementRef]:
        elements: List[WindowElementRef] = []
        if not hwnd:
            return elements
        try:
            import win32gui

            def enum_child_callback(child_hwnd, _):
                try:
                    text = win32gui.GetWindowText(child_hwnd).strip()
                    cls_name = win32gui.GetClassName(child_hwnd).strip()
                    rect = win32gui.GetWindowRect(child_hwnd)
                    if win32gui.IsWindowVisible(child_hwnd) and (rect[2] > rect[0]) and (rect[3] > rect[1]):
                        elements.append(
                            WindowElementRef(
                                name=text or cls_name,
                                control_type=cls_name,
                                automation_id=f"ctrl_{child_hwnd}",
                                rect=rect,
                                hwnd=child_hwnd,
                            )
                        )
                except Exception:
                    pass
                return True

            win32gui.EnumChildWindows(hwnd, enum_child_callback, None)
        except Exception:
            pass
        return elements

    def find_element_by_name(self, hwnd: int, name: str) -> Optional[WindowElementRef]:
        target = name.strip().lower()
        for elem in self.inspect_window_elements(hwnd):
            if elem.name.lower() == target:
                return elem
        return None
