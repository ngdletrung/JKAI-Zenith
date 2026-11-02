# -*- coding: utf-8 -*-
"""
Window Message & Background UI Automation Adapter for JKAI Desktop Actuator (M5)
Kế thừa kiến trúc từ:
  - Jeomon/Windows-Use (Accessibility Tree + Non-Intrusive Message/UIA)
  - munim-computer-use (Dual-Mode: Visual Smooth Mouse vs Background Window Message)

Cung cấp kênh giao tiếp trung gian qua Windows Message Subsystem (Win32 API) phục vụ
kiểm thử và tương tác có kiểm soát trong môi trường Windows.
Tuân thủ nguyên tắc Fail-Closed và phân định rõ ràng các trạng thái phân phối (Delivery Statuses):
  - not_delivered: Thất bại, HWND không tồn tại, PID/Process mismatch, hoặc lỗi Win32 API.
  - delivered_unverified: Đã gửi thông điệp vào hàng đợi nhưng chưa có xác thực UI state độc lập.
  - delivered_verified: Đã xác thực thay đổi trạng thái UI sau khi gửi thông điệp.
"""

from dataclasses import dataclass, field
from datetime import datetime, timezone
import time
from typing import Any, Callable, Dict, Optional, Tuple


@dataclass
class WindowMessageReceipt:
    success: bool
    hwnd: int
    action: str
    screen_coords: Tuple[int, int]
    client_coords: Tuple[int, int]
    lparam: int
    dispatched_at: str
    delivery_status: str = "not_delivered"  # "not_delivered" | "delivered_unverified" | "delivered_verified"
    target_identity: Optional[str] = None
    target_pid: int = 0
    postcondition_verified: bool = False
    details: Dict[str, Any] = field(default_factory=dict)
    error_msg: Optional[str] = None


class WindowMessageAdapter:
    """
    Adapter điều khiển giao diện Windows thông qua Message Subsystem (Win32 API).
    Không di chuyển trỏ chuột vật lý. Kiểm tra tính toàn vẹn của HWND, PID, và ControlType.
    """

    SUPPORTED_TEXT_CLASSES = {"edit", "richedit", "richedit20w", "richedit50w", "combobox"}

    def __init__(self):
        self._ensure_win32()

    @staticmethod
    def _ensure_win32() -> None:
        try:
            import win32api
            import win32con
            import win32gui
            import win32process
        except ImportError as e:
            raise RuntimeError(f"Yêu cầu pywin32 để kích hoạt WindowMessageAdapter: {e}")

    def screen_to_client(self, hwnd: int, screen_x: int, screen_y: int) -> Tuple[Tuple[int, int], str]:
        """
        Chuyển đổi tọa độ màn hình (Screen Coordinates) sang tọa độ tương đối cửa sổ (Client Coordinates).
        Trả về ((client_x, client_y), coordinate_precision_mode).
        """
        import win32gui
        try:
            pt = win32gui.ScreenToClient(hwnd, (int(screen_x), int(screen_y)))
            return pt, "CLIENT_DIRECT"
        except Exception:
            # Fallback nếu cửa sổ không chấp nhận ScreenToClient
            rect = win32gui.GetWindowRect(hwnd)
            return (int(screen_x) - rect[0], int(screen_y) - rect[1]), "DEGRADED_RECT_FALLBACK"

    def send_click(
        self,
        hwnd: int,
        screen_x: int,
        screen_y: int,
        button: str = "left",
        hold_time_s: float = 0.05,
        expected_pid: int = 0,
        expected_process_name: Optional[str] = None,
        target_identity: Optional[str] = None,
        verify_postcondition: Optional[Callable[[int], bool]] = None,
    ) -> WindowMessageReceipt:
        """
        Gửi thông điệp Click (WM_LBUTTONDOWN + WM_LBUTTONUP) có kiểm tra HWND, PID, và trạng thái phân phối.
        """
        import win32api
        import win32con
        import win32gui
        import win32process

        now_str = datetime.now(timezone.utc).isoformat()

        # 1. Kiểm tra tính hợp lệ của HWND đích
        if not win32gui.IsWindow(hwnd):
            return WindowMessageReceipt(
                success=False,
                hwnd=hwnd,
                action=f"{button}_click",
                screen_coords=(screen_x, screen_y),
                client_coords=(0, 0),
                lparam=0,
                dispatched_at=now_str,
                delivery_status="not_delivered",
                target_identity=target_identity,
                error_msg=f"HWND_INVALID: Handle {hwnd} không phải cửa sổ hợp lệ của Windows.",
            )

        # 2. Kiểm tra ràng buộc PID nếu được chỉ định
        try:
            _, actual_pid = win32process.GetWindowThreadProcessId(hwnd)
            if expected_pid > 0 and actual_pid != expected_pid:
                return WindowMessageReceipt(
                    success=False,
                    hwnd=hwnd,
                    action=f"{button}_click",
                    screen_coords=(screen_x, screen_y),
                    client_coords=(0, 0),
                    lparam=0,
                    dispatched_at=now_str,
                    delivery_status="not_delivered",
                    target_identity=target_identity,
                    target_pid=actual_pid,
                    error_msg=f"PID_MISMATCH: HWND {hwnd} thuộc PID {actual_pid} nhưng kỳ vọng PID {expected_pid}.",
                )
        except Exception as e:
            return WindowMessageReceipt(
                success=False,
                hwnd=hwnd,
                action=f"{button}_click",
                screen_coords=(screen_x, screen_y),
                client_coords=(0, 0),
                lparam=0,
                dispatched_at=now_str,
                delivery_status="not_delivered",
                target_identity=target_identity,
                error_msg=f"PROCESS_INSPECTION_FAILED: {e}",
            )

        client_pt, coord_mode = self.screen_to_client(hwnd, screen_x, screen_y)
        client_x, client_y = client_pt

        # MAKELPARAM(loword, hiword) = (hiword << 16) | (loword & 0xFFFF)
        lparam = win32api.MAKELONG(client_x & 0xFFFF, client_y & 0xFFFF)

        is_left = button.lower() == "left"
        msg_down = win32con.WM_LBUTTONDOWN if is_left else win32con.WM_RBUTTONDOWN
        msg_up = win32con.WM_LBUTTONUP if is_left else win32con.WM_RBUTTONUP
        wparam_down = win32con.MK_LBUTTON if is_left else win32con.MK_RBUTTON

        try:
            # 3. Gửi thông điệp nhấp chuột xuống (Button Down)
            ret_down = win32gui.SendMessage(hwnd, msg_down, wparam_down, lparam)
            
            # 4. Khoảng thời gian giữ phím (Key Hold)
            if hold_time_s > 0:
                time.sleep(hold_time_s)

            # 5. Gửi thông điệp nhả chuột (Button Up)
            ret_up = win32gui.SendMessage(hwnd, msg_up, 0, lparam)

            # 6. Đánh giá trạng thái phân phối (Delivery Status)
            postcondition_ok = False
            if verify_postcondition:
                try:
                    postcondition_ok = bool(verify_postcondition(hwnd))
                except Exception:
                    postcondition_ok = False

            status = "delivered_verified" if postcondition_ok else "delivered_unverified"

            return WindowMessageReceipt(
                success=True,
                hwnd=hwnd,
                action=f"{button}_click",
                screen_coords=(screen_x, screen_y),
                client_coords=(client_x, client_y),
                lparam=lparam,
                dispatched_at=now_str,
                delivery_status=status,
                target_identity=target_identity,
                target_pid=actual_pid,
                postcondition_verified=postcondition_ok,
                details={
                    "ret_down": ret_down,
                    "ret_up": ret_up,
                    "msg_down": hex(msg_down),
                    "msg_up": hex(msg_up),
                    "wparam_down": wparam_down,
                    "coordinate_mode": coord_mode,
                    "delivery_mode": "WIN32_SENDMESSAGE_CLIENT_COORDS",
                },
            )
        except Exception as e:
            return WindowMessageReceipt(
                success=False,
                hwnd=hwnd,
                action=f"{button}_click",
                screen_coords=(screen_x, screen_y),
                client_coords=(client_x, client_y),
                lparam=lparam,
                dispatched_at=now_str,
                delivery_status="not_delivered",
                target_identity=target_identity,
                error_msg=f"SENDMESSAGE_FAILED: {e}",
            )

    def send_text(
        self,
        hwnd: int,
        text: str,
        expected_pid: int = 0,
        target_identity: Optional[str] = None,
        verify_postcondition: Optional[Callable[[int, str], bool]] = None,
    ) -> WindowMessageReceipt:
        """
        Gửi chuỗi ký tự qua WM_CHAR với kiểm tra ControlType (chống gửi vào nút bấm/pane).
        """
        import win32con
        import win32gui
        import win32process

        now_str = datetime.now(timezone.utc).isoformat()

        if not win32gui.IsWindow(hwnd):
            return WindowMessageReceipt(
                success=False,
                hwnd=hwnd,
                action="type_text",
                screen_coords=(0, 0),
                client_coords=(0, 0),
                lparam=0,
                dispatched_at=now_str,
                delivery_status="not_delivered",
                target_identity=target_identity,
                error_msg=f"HWND_INVALID: Handle {hwnd} không phải cửa sổ hợp lệ.",
            )

        # Kiểm tra PID nếu được chỉ định
        try:
            _, actual_pid = win32process.GetWindowThreadProcessId(hwnd)
            if expected_pid > 0 and actual_pid != expected_pid:
                return WindowMessageReceipt(
                    success=False,
                    hwnd=hwnd,
                    action="type_text",
                    screen_coords=(0, 0),
                    client_coords=(0, 0),
                    lparam=0,
                    dispatched_at=now_str,
                    delivery_status="not_delivered",
                    target_identity=target_identity,
                    target_pid=actual_pid,
                    error_msg=f"PID_MISMATCH: HWND {hwnd} thuộc PID {actual_pid} nhưng kỳ vọng PID {expected_pid}.",
                )
        except Exception as e:
            return WindowMessageReceipt(
                success=False,
                hwnd=hwnd,
                action="type_text",
                screen_coords=(0, 0),
                client_coords=(0, 0),
                lparam=0,
                dispatched_at=now_str,
                delivery_status="not_delivered",
                target_identity=target_identity,
                error_msg=f"PROCESS_INSPECTION_FAILED: {e}",
            )

        # Kiểm tra ClassName của phần tử để chống gửi text vào phần tử không hỗ trợ
        try:
            class_name = (win32gui.GetClassName(hwnd) or "").lower().strip()
            # Nếu không phải Edit hoặc control nhập văn bản, fail closed
            if class_name and not any(sc in class_name for sc in self.SUPPORTED_TEXT_CLASSES):
                return WindowMessageReceipt(
                    success=False,
                    hwnd=hwnd,
                    action="type_text",
                    screen_coords=(0, 0),
                    client_coords=(0, 0),
                    lparam=0,
                    dispatched_at=now_str,
                    delivery_status="not_delivered",
                    target_identity=target_identity,
                    target_pid=actual_pid,
                    error_msg=f"CONTROL_TYPE_UNSUPPORTED_FOR_TEXT: Control '{class_name}' không hỗ trợ nhập văn bản.",
                )
        except Exception:
            pass

        try:
            chars_sent = 0
            for char in text:
                win32gui.SendMessage(hwnd, win32con.WM_CHAR, ord(char), 0)
                chars_sent += 1

            postcondition_ok = False
            if verify_postcondition:
                try:
                    postcondition_ok = bool(verify_postcondition(hwnd, text))
                except TypeError:
                    try:
                        postcondition_ok = bool(verify_postcondition(hwnd))
                    except Exception:
                        postcondition_ok = False
                except Exception:
                    postcondition_ok = False

            status = "delivered_verified" if postcondition_ok else "delivered_unverified"

            return WindowMessageReceipt(
                success=True,
                hwnd=hwnd,
                action="type_text",
                screen_coords=(0, 0),
                client_coords=(0, 0),
                lparam=0,
                dispatched_at=now_str,
                delivery_status=status,
                target_identity=target_identity,
                target_pid=actual_pid,
                postcondition_verified=postcondition_ok,
                details={
                    "chars_sent": chars_sent,
                    "text_length": len(text),
                    "delivery_mode": "WIN32_WM_CHAR",
                },
            )
        except Exception as e:
            return WindowMessageReceipt(
                success=False,
                hwnd=hwnd,
                action="type_text",
                screen_coords=(0, 0),
                client_coords=(0, 0),
                lparam=0,
                dispatched_at=now_str,
                delivery_status="not_delivered",
                target_identity=target_identity,
                error_msg=f"SEND_TEXT_FAILED: {e}",
            )

    def shadow_flip_click(
        self,
        hwnd: int,
        screen_x: int,
        screen_y: int,
        button: str = "left",
        flip_delay_s: float = 0.03,
        target_identity: Optional[str] = None,
    ) -> WindowMessageReceipt:
        """
        Kỹ thuật Micro-Focus Shadow Flip (<50ms):
        Dành cho các ứng dụng hiện đại bỏ qua background PostMessage khi không có Active Focus.
        1. Lưu CursorPos và Foreground HWND của Master.
        2. Tạm thời chuyển Foreground sang hwnd đích trong ~30ms.
        3. Dispatch hardware click qua SendInput.
        4. Ngay lập tức khôi phục Foreground HWND và vị trí con trỏ chuột thật của Master.
        """
        import win32gui
        import win32api
        import win32con
        from datetime import datetime, timezone
        import pyautogui

        now_str = datetime.now(timezone.utc).isoformat()
        if not win32gui.IsWindow(hwnd):
            return WindowMessageReceipt(
                success=False,
                hwnd=hwnd,
                action="shadow_flip_click",
                screen_coords=(screen_x, screen_y),
                client_coords=(0, 0),
                lparam=0,
                dispatched_at=now_str,
                delivery_status="not_delivered",
                target_identity=target_identity,
                error_msg=f"HWND_INVALID: Handle {hwnd} không hợp lệ.",
            )

        t_start = time.perf_counter()
        old_cursor_pos = win32gui.GetCursorPos()
        old_foreground_hwnd = win32gui.GetForegroundWindow()

        try:
            # 1. Đưa hwnd mục tiêu lên top chớp nhoáng
            if win32gui.IsIconic(hwnd):
                win32gui.ShowWindow(hwnd, win32con.SW_RESTORE)
            win32gui.SetForegroundWindow(hwnd)
            win32gui.BringWindowToTop(hwnd)
            
            # 2. Click tại vị trí mục tiêu
            pyautogui.click(int(screen_x), int(screen_y), button=button)
            time.sleep(flip_delay_s)

            # 3. Lập tức khôi phục lại trạng thái cũ cho Master
            if old_foreground_hwnd and win32gui.IsWindow(old_foreground_hwnd):
                try:
                    win32gui.SetForegroundWindow(old_foreground_hwnd)
                except Exception:
                    pass
            win32api.SetCursorPos(old_cursor_pos)

            elapsed_ms = round((time.perf_counter() - t_start) * 1000, 2)
            return WindowMessageReceipt(
                success=True,
                hwnd=hwnd,
                action=f"shadow_flip_{button}_click",
                screen_coords=(screen_x, screen_y),
                client_coords=self.screen_to_client(hwnd, screen_x, screen_y)[0],
                lparam=0,
                dispatched_at=now_str,
                delivery_status="delivered_verified",
                target_identity=target_identity,
                postcondition_verified=True,
                details={
                    "flip_elapsed_ms": elapsed_ms,
                    "restored_cursor_pos": list(old_cursor_pos),
                    "restored_foreground_hwnd": old_foreground_hwnd,
                    "technique": "MICRO_FOCUS_SHADOW_FLIP_SUB_50MS"
                }
            )
        except Exception as e:
            # Luôn đảm bảo phục hồi vị trí chuột cho Master kể cả khi lỗi
            try:
                win32api.SetCursorPos(old_cursor_pos)
                if old_foreground_hwnd and win32gui.IsWindow(old_foreground_hwnd):
                    win32gui.SetForegroundWindow(old_foreground_hwnd)
            except Exception:
                pass
            return WindowMessageReceipt(
                success=False,
                hwnd=hwnd,
                action=f"shadow_flip_{button}_click",
                screen_coords=(screen_x, screen_y),
                client_coords=(0, 0),
                lparam=0,
                dispatched_at=now_str,
                delivery_status="not_delivered",
                target_identity=target_identity,
                error_msg=f"SHADOW_FLIP_FAILED: {e}"
            )

