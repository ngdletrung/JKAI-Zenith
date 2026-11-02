# -*- coding: utf-8 -*-
"""
scripts/bounds_validator.py
[M5 BOUNDS & FORBIDDEN ZONES VALIDATOR]
Đảm bảo kỷ luật tuyệt đối: JKAI CHỈ ĐƯỢC PHÉP thao tác bên trong Bounding Box của cửa sổ chỉ định.
CẤM TUYỆT ĐỐI mọi tọa độ rơi ngoài vùng cho phép hoặc rơi vào vùng hệ thống (Taskbar, Start, Desktop).
"""

import ctypes
from ctypes import wintypes
from typing import Dict, Any, Tuple, Optional

class OutOfBoundsSecurityError(Exception):
    """Ngoại lệ an ninh khi tọa độ rơi ngoài vùng cho phép."""
    pass

class WindowTargetMismatchError(Exception):
    """Ngoại lệ khi HWND không hợp lệ hoặc mục tiêu bị tráo đổi."""
    pass

# Blacklist các class hệ thống nhạy cảm
FORBIDDEN_SYSTEM_CLASSES = {
    "Shell_TrayWnd",       # Taskbar Windows chính
    "Shell_SecondaryTrayWnd", # Taskbar trên màn hình phụ
    "TrayNotifyWnd",       # Khay hệ thống (System Tray)
    "Start",               # Nút Start Menu
    "Windows.UI.Core.CoreWindow", # Windows Shell flyouts
    "Progman",             # Desktop Windows
    "WorkerW"              # Desktop background worker
}

user32 = ctypes.windll.user32

class DesktopBoundsValidator:
    def __init__(self, safe_inset: int = 8):
        """
        :param safe_inset: Khoảng cách thụt lề an toàn tính bằng pixel từ các mép cửa sổ
                           để tránh bấm nhầm viền resize hoặc nút đóng/thu nhỏ.
        """
        self.safe_inset = max(0, safe_inset)

    @staticmethod
    def get_window_rect(hwnd: int) -> Tuple[int, int, int, int]:
        """Lấy tọa độ cửa sổ thực tế (left, top, right, bottom)."""
        if not user32.IsWindow(hwnd):
            raise WindowTargetMismatchError(f"HWND {hwnd} không phải là cửa sổ hợp lệ.")
        if user32.IsIconic(hwnd):
            raise WindowTargetMismatchError(f"Cửa sổ HWND {hwnd} đang bị thu nhỏ (minimized).")

        rect = wintypes.RECT()
        if not user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise WindowTargetMismatchError(f"Không thể đọc GetWindowRect cho HWND {hwnd}.")
        return rect.left, rect.top, rect.right, rect.bottom

    @staticmethod
    def get_window_class(hwnd: int) -> str:
        """Lấy tên Window Class của cửa sổ."""
        buf = ctypes.create_unicode_buffer(256)
        user32.GetClassNameW(hwnd, buf, 256)
        return buf.value

    def validate_coordinate(self, hwnd: int, x: int, y: int) -> Dict[str, Any]:
        """
        Kiểm tra nghiêm ngặt tọa độ (x, y) đối với HWND được chỉ định.
        Trả về thông tin chi tiết nếu hợp lệ; ném ngoại lệ nếu vi phạm.
        """
        # 1. Kiểm tra HWND còn sống không
        if not user32.IsWindow(hwnd):
            raise WindowTargetMismatchError(f"HWND {hwnd} không tồn tại hoặc đã bị đóng.")

        # 2. Kiểm tra cửa sổ có phải vùng cấm hệ thống không
        cls_name = self.get_window_class(hwnd)
        if cls_name in FORBIDDEN_SYSTEM_CLASSES:
            raise OutOfBoundsSecurityError(f"Từ chối: Cửa sổ thuộc vùng cấm hệ thống (Class: '{cls_name}').")

        # 3. Lấy rect thực tế
        left, top, right, bottom = self.get_window_rect(hwnd)
        width = right - left
        height = bottom - top

        # 4. Tính toán vùng an toàn (Safe Bounding Box)
        safe_left = left + self.safe_inset
        safe_top = top + self.safe_inset
        safe_right = right - self.safe_inset
        safe_bottom = bottom - self.safe_inset

        # 5. Phán quyết an ninh
        if not (safe_left <= x <= safe_right and safe_top <= y <= safe_bottom):
            err_msg = (
                f"🚨 [VI PHẠM RANH GIỚI AN NINH]: Tọa độ ({x}, {y}) nằm NGOÀI vùng an toàn cho phép!\n"
                f"- Cửa sổ HWND {hwnd} (Class: {cls_name}): L={left}, T={top}, R={right}, B={bottom} ({width}x{height})\n"
                f"- Vùng an toàn với inset={self.safe_inset}px: L={safe_left}, T={safe_top}, R={safe_right}, B={safe_bottom}"
            )
            raise OutOfBoundsSecurityError(err_msg)

        # 6. Kiểm tra xem điểm (x, y) có đang thực sự trúng cửa sổ này không (chống bị che khuất)
        point = wintypes.POINT(x, y)
        target_at_point = user32.WindowFromPoint(point)
        # Tìm root ancestor của window tại điểm đó
        ancestor = user32.GetAncestor(target_at_point, 2) # GA_ROOT = 2
        if ancestor != hwnd and target_at_point != hwnd:
            # Điểm này bị che bởi cửa sổ khác đè lên
            raise OutOfBoundsSecurityError(
                f"🚨 [CỬA SỔ BỊ CHE KHUẤT]: Điểm ({x}, {y}) đang bị che bởi cửa sổ khác (HWND tại điểm: {target_at_point}, Root: {ancestor}, Mong đợi: {hwnd})."
            )

        return {
            "status": "APPROVED",
            "hwnd": hwnd,
            "class_name": cls_name,
            "target_rect": [left, top, right, bottom],
            "safe_rect": [safe_left, safe_top, safe_right, safe_bottom],
            "point": [x, y],
            "margin_left": x - safe_left,
            "margin_right": safe_right - x,
            "margin_top": y - safe_top,
            "margin_bottom": safe_bottom - y
        }
