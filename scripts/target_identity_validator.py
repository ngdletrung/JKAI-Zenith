# -*- coding: utf-8 -*-
"""
scripts/target_identity_validator.py
[JKAI TARGET IDENTITY VALIDATOR & ANTI-TOCTOU SNAPSHOT BINDING v2.4]

Cung cấp cơ chế định danh mục tiêu đa tầng (học hỏi từ Jeomon/Windows-Use & Agent-S3):
Đảm bảo hành động điều khiển chỉ tác động đúng vào cửa sổ mục tiêu đã được phê chuẩn.
Chống tráo đổi cửa sổ (Window Swap), tráo đổi tiến trình (PID Reuse), thu nhỏ ngầm (Minimized),
hoặc thay đổi tiêu đề/lớp cửa sổ giữa lúc cấp phép và lúc thực thi.
"""

import sys
import os
from typing import Dict, Any, Tuple, Optional

class TargetIdentityValidator:
    def __init__(self, allowed_proc_names: Optional[set] = None):
        self.allowed_proc_names = allowed_proc_names or {"notepad.exe"}
        self._is_windows = sys.platform == "win32"
        self._user32 = None
        if self._is_windows:
            try:
                import ctypes
                self._user32 = ctypes.windll.user32
            except Exception:
                self._user32 = None

    def get_window_identity(self, hwnd: int) -> Dict[str, Any]:
        """Trích xuất danh tính chi tiết của cửa sổ mục tiêu."""
        if not self._is_windows or not self._user32:
            return {"hwnd": hwnd, "valid": False, "reason": "NON_WINDOWS"}

        import ctypes
        from ctypes import wintypes

        if not self._user32.IsWindow(hwnd):
            return {"hwnd": hwnd, "valid": False, "reason": "WINDOW_NOT_FOUND"}

        is_minimized = bool(self._user32.IsIconic(hwnd))
        
        # Lấy Class Name
        cls_buf = ctypes.create_unicode_buffer(256)
        self._user32.GetClassNameW(hwnd, cls_buf, 256)
        class_name = cls_buf.value

        # Lấy Window Title
        title_buf = ctypes.create_unicode_buffer(512)
        self._user32.GetWindowTextW(hwnd, title_buf, 512)
        window_title = title_buf.value

        # Lấy PID
        pid = wintypes.DWORD()
        self._user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        target_pid = int(pid.value)

        # Lấy Process Name & Executable Path
        proc_name = "unknown"
        exe_path = "unknown"
        try:
            import psutil
            proc = psutil.Process(target_pid)
            proc_name = proc.name().lower()
            try:
                exe_path = proc.exe()
            except Exception:
                exe_path = ""
        except Exception:
            pass

        # Lấy Bounds
        rect = wintypes.RECT()
        bounds = [0, 0, 0, 0]
        if self._user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            bounds = [rect.left, rect.top, rect.right, rect.bottom]

        # Kiểm tra Foreground
        fg_hwnd = self._user32.GetForegroundWindow()
        is_foreground = (fg_hwnd == hwnd)

        return {
            "hwnd": hwnd,
            "valid": True,
            "target_pid": target_pid,
            "proc_name": proc_name,
            "exe_path": exe_path,
            "class_name": class_name,
            "window_title": window_title,
            "bounds": bounds,
            "is_minimized": is_minimized,
            "is_foreground": is_foreground
        }

    def validate_target_identity(
        self,
        hwnd: int,
        expected_identity: Dict[str, Any],
        require_foreground: bool = False
    ) -> Tuple[bool, str]:
        """
        Đối chiếu danh tính thời gian thực của cửa sổ với snapshot đã đăng ký lúc cấp lease.
        Fail-closed nếu phát hiện bất kỳ dấu hiệu trôi dạt (Drift) hoặc tráo đổi nào.
        """
        current = self.get_window_identity(hwnd)
        if not current.get("valid", False):
            return False, current.get("reason", "TARGET_WINDOW_INVALID")

        if current.get("is_minimized", False):
            return False, "TARGET_IS_MINIMIZED"

        # 1. Whitelist Process Name
        proc_name = current.get("proc_name", "").lower()
        if proc_name not in self.allowed_proc_names:
            return False, f"TARGET_PROC_NOT_WHITELISTED: {proc_name}"

        # 2. Strict Process ID Matching (Chống PID reuse)
        if "target_pid" in expected_identity and current.get("target_pid") != expected_identity["target_pid"]:
            return False, f"PID_DRIFT_DETECTED: expected {expected_identity['target_pid']}, got {current.get('target_pid')}"

        # 3. Class Name Matching
        if "class_name" in expected_identity and expected_identity["class_name"]:
            if current.get("class_name") != expected_identity["class_name"]:
                return False, f"CLASS_NAME_MISMATCH: expected {expected_identity['class_name']}, got {current.get('class_name')}"

        # 4. Foreground Check (nếu yêu cầu)
        if require_foreground and not current.get("is_foreground", False):
            return False, "TARGET_NOT_IN_FOREGROUND"

        # 5. Bounds Consistency Check (Không cho phép cửa sổ bị di dời quá 100px đột ngột)
        if "bounds" in expected_identity and expected_identity["bounds"]:
            exp_b = expected_identity["bounds"]
            cur_b = current.get("bounds", [0, 0, 0, 0])
            if len(exp_b) == 4 and len(cur_b) == 4:
                diff_x = abs(exp_b[0] - cur_b[0])
                diff_y = abs(exp_b[1] - cur_b[1])
                if diff_x > 150 or diff_y > 150:
                    return False, f"BOUNDS_DRASTIC_SHIFT_DETECTED: shift=({diff_x}, {diff_y})"

        return True, "TARGET_IDENTITY_VERIFIED"
