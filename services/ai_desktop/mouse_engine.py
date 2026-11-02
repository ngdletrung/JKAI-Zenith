# -*- coding: utf-8 -*-
"""
services/ai_desktop/mouse_engine.py
[M5-G2 / M5-G6 MOUSE ENGINE & HUMAN PACING]:
Bộ động cơ mô phỏng chuyển động chuột tự nhiên, mượt mà (Smooth Mouse Movement)
với đường cong Bézier bậc ba và phân bổ thời gian sinh học (Human Pacing).
Loại bỏ hoàn toàn hiện tượng nhảy giật tọa độ tức thời (Teleportation).
"""

from __future__ import annotations

import math
import random
import time
from typing import Callable, List, Optional, Protocol, Tuple


class CursorActionError(RuntimeError):
    """Lỗi khi thao tác con trỏ native thất bại hoặc bị chặn bởi Windows Desktop Isolation."""
    pass


class CursorReadbackDriftError(CursorActionError):
    """Lỗi khi vị trí con trỏ sau lệnh di chuyển bị lệch vượt ngưỡng cho phép."""
    pass


class DesktopMouseAdapterProtocol(Protocol):
    """Giao thức chuẩn cho bộ điều phối chuột (Native hoặc Mock)."""

    def get_position(self) -> Tuple[int, int]:
        ...

    def move_to(self, x: int, y: int) -> None:
        ...

    def mouse_down(self, button: str = "left") -> None:
        ...

    def mouse_up(self, button: str = "left") -> None:
        ...

    def click(self, x: int, y: int, button: str = "left") -> None:
        ...


class MockDesktopMouseAdapter:
    """Bộ giả lập chuột phục vụ kiểm thử đơn vị độc lập và môi trường không có GUI thật."""

    def __init__(
        self,
        initial_pos: Tuple[int, int] = (100, 100),
        fail_api: bool = False,
        drift_readback: bool = False,
        drift_offset: Tuple[int, int] = (84, 1),
    ):
        self.pos = initial_pos
        self.history: List[Tuple[str, Any]] = []
        self.trajectory_log: List[Tuple[int, int]] = []
        self.click_log: List[Dict[str, Any]] = []
        self.mouse_state: str = "UP"
        self.failsafe_triggered: bool = False
        self.fail_api: bool = fail_api
        self.drift_readback: bool = drift_readback
        self.drift_offset: Tuple[int, int] = drift_offset

    def get_position(self) -> Tuple[int, int]:
        if self.drift_readback:
            return (self.pos[0] + self.drift_offset[0], self.pos[1] + self.drift_offset[1])
        return self.pos

    def move_to(self, x: int, y: int) -> None:
        if self.fail_api:
            raise CursorActionError("MOCK_FAIL_CLOSED: win32api.SetCursorPos thất bại (Desktop Isolation)")
        if self.failsafe_triggered:
            return
        self.pos = (int(x), int(y))
        if x == 0 and y == 0:
            self.failsafe_triggered = True
        self.trajectory_log.append(self.pos)
        self.history.append(("move_to", self.pos))

    def mouse_down(self, button: str = "left") -> None:
        self.mouse_state = "DOWN"
        self.click_log.append({"event": "down", "button": button, "x": self.pos[0], "y": self.pos[1]})
        self.history.append(("mouse_down", button, self.pos))

    def mouse_up(self, button: str = "left") -> None:
        self.mouse_state = "UP"
        self.click_log.append({"event": "up", "button": button, "x": self.pos[0], "y": self.pos[1]})
        self.history.append(("mouse_up", button, self.pos))

    def click(self, x: int, y: int, button: str = "left") -> None:
        self.move_to(x, y)
        self.mouse_down(button)
        self.mouse_up(button)
        self.history.append(("click", button, (int(x), int(y))))


class NativeWindowsMouseAdapter:
    """
    Bộ điều khiển chuột vật lý sử dụng trực tiếp Windows API (win32api / ctypes).
    Di chuyển con trỏ chuột vật lý thật của hệ điều hành Windows trước mắt Master.
    Đã bọc High-DPI Awareness và liên kết Desktop tương tác trực tiếp ('default').
    """

    def __init__(self):
        self._ensure_interactive_desktop()
        self._ensure_dpi_awareness()

    def _ensure_interactive_desktop(self):
        """
        [M5-DESKTOP BINDING]: Gắn Thread vào Desktop tương tác trực tiếp của người dùng
        thông qua OpenInputDesktop để có quyền điều khiển con trỏ chuột vật lý thật trước mắt Master.
        """
        try:
            import ctypes
            h_desk = ctypes.windll.user32.OpenInputDesktop(0, False, 0x01FF)
            if not h_desk:
                h_desk = ctypes.windll.user32.OpenDesktopW("Default", 0, False, 0x01FF)
            if h_desk:
                ctypes.windll.user32.SetThreadDesktop(h_desk)
        except Exception:
            pass

    def _ensure_dpi_awareness(self):
        try:
            import ctypes
            # PROCESS_PER_MONITOR_DPI_AWARE = 2
            ctypes.windll.shcore.SetProcessDpiAwareness(2)
        except Exception:
            try:
                import ctypes
                ctypes.windll.user32.SetProcessDPIAware()
            except Exception:
                pass

    def get_position(self) -> Tuple[int, int]:
        import win32api
        try:
            return win32api.GetCursorPos()
        except Exception:
            try:
                self._ensure_interactive_desktop()
                return win32api.GetCursorPos()
            except Exception:
                return (0, 0)

    def move_to(self, x: int, y: int, verify_readback: bool = False, tolerance: int = 10) -> None:
        import win32api
        target_pt = (int(x), int(y))
        try:
            win32api.SetCursorPos(target_pt)
        except Exception as e:
            self._ensure_interactive_desktop()
            try:
                win32api.SetCursorPos(target_pt)
            except Exception as e2:
                raise CursorActionError(
                    f"FAIL_CLOSED: win32api.SetCursorPos({target_pt}) thất bại (Session/Desktop Isolation): {e2}"
                ) from e2

        if verify_readback:
            actual = self.get_position()
            import math
            dist = math.hypot(actual[0] - target_pt[0], actual[1] - target_pt[1])
            if dist > tolerance:
                raise CursorReadbackDriftError(
                    f"FAIL_CLOSED: Cursor readback drift vượt ngưỡng: yêu cầu {target_pt}, thực tế {actual} (drift={dist:.1f}px > {tolerance}px)"
                )

    def mouse_down(self, button: str = "left") -> None:
        import win32api
        import win32con
        flag = win32con.MOUSEEVENTF_LEFTDOWN if button == "left" else win32con.MOUSEEVENTF_RIGHTDOWN
        x, y = self.get_position()
        try:
            win32api.mouse_event(flag, x, y, 0, 0)
        except Exception:
            self._ensure_interactive_desktop()
            win32api.mouse_event(flag, x, y, 0, 0)

    def mouse_up(self, button: str = "left") -> None:
        import win32api
        import win32con
        flag = win32con.MOUSEEVENTF_LEFTUP if button == "left" else win32con.MOUSEEVENTF_RIGHTUP
        x, y = self.get_position()
        try:
            win32api.mouse_event(flag, x, y, 0, 0)
        except Exception:
            self._ensure_interactive_desktop()
            win32api.mouse_event(flag, x, y, 0, 0)

    def click(self, x: int, y: int, button: str = "left") -> None:
        self.move_to(x, y)
        self.mouse_down(button)
        time.sleep(0.04)
        self.mouse_up(button)


class SmoothMouseEngine:
    """
    Bộ động cơ tạo đường cong Bezier và nhịp điệu người thật (Human Pacing).
    Biến hành vi di chuột của AI thành một dòng chuyển động mượt mà, trực quan.
    """

    @staticmethod
    def _ease_in_out(t: float) -> float:
        """Hàm gia tốc mượt mà hai đầu (Smoothstep: chậm lúc khởi hành, chậm lúc về đích)."""
        return t * t * (3.0 - 2.0 * t)

    @staticmethod
    def _bezier_point(
        p0: Tuple[float, float],
        p1: Tuple[float, float],
        p2: Tuple[float, float],
        p3: Tuple[float, float],
        t: float,
    ) -> Tuple[float, float]:
        """Tính tọa độ tại điểm t (0..1) trên đường cong Cubic Bezier 4 điểm."""
        u = 1.0 - t
        tt = t * t
        uu = u * u
        uuu = uu * u
        ttt = tt * t

        x = uuu * p0[0] + 3 * uu * t * p1[0] + 3 * u * tt * p2[0] + ttt * p3[0]
        y = uuu * p0[1] + 3 * uu * t * p1[1] + 3 * u * tt * p2[1] + ttt * p3[1]
        return x, y

    @classmethod
    def calculate_trajectory(
        cls,
        start_pos: Tuple[int, int],
        end_pos: Tuple[int, int],
        steps: int = 25,
        wobble_px: float = 3.0,
    ) -> List[Tuple[int, int]]:
        """
        Sinh danh sách các điểm tọa độ nội suy theo đường cong Bezier tự nhiên.
        Đảm bảo không bao giờ nhảy giật cục (Zero Teleportation).
        """
        x0, y0 = float(start_pos[0]), float(start_pos[1])
        x3, y3 = float(end_pos[0]), float(end_pos[1])

        dist = math.hypot(x3 - x0, y3 - y0)
        if dist < 2.0:
            return [(int(x3), int(y3))]

        # Tạo 2 điểm kiểm soát ngẫu nhiên lệch nhẹ theo phương vuông góc
        dx = x3 - x0
        dy = y3 - y0
        ctrl1_factor = 0.3
        ctrl2_factor = 0.7

        # Độ lệch ngẫu nhiên tạo độ võng tự nhiên của tay người
        offset1 = (random.random() - 0.5) * min(dist * 0.2, 50.0)
        offset2 = (random.random() - 0.5) * min(dist * 0.2, 50.0)

        p1 = (x0 + dx * ctrl1_factor - dy * 0.1 + offset1, y0 + dy * ctrl1_factor + dx * 0.1 + offset1)
        p2 = (x0 + dx * ctrl2_factor + dy * 0.05 + offset2, y0 + dy * ctrl2_factor - dx * 0.05 + offset2)

        trajectory: List[Tuple[int, int]] = []
        dynamic_steps = max(steps, int(dist / 18.0))
        actual_steps = max(10, min(dynamic_steps, 80))

        for i in range(1, actual_steps + 1):
            progress = i / actual_steps
            eased_t = cls._ease_in_out(progress)
            bx, by = cls._bezier_point((x0, y0), p1, p2, (x3, y3), eased_t)

            # Rung nhẹ tự nhiên (Micro-wobble) giảm dần khi gần đích
            if wobble_px > 0 and i < actual_steps:
                wobble_decay = 1.0 - progress
                bx += (random.random() - 0.5) * wobble_px * wobble_decay
                by += (random.random() - 0.5) * wobble_px * wobble_decay

            trajectory.append((int(round(bx)), int(round(by))))

        return trajectory

    @classmethod
    def execute_smooth_move(
        cls,
        adapter: DesktopMouseAdapterProtocol,
        target_x: int,
        target_y: int,
        steps: int = 25,
        step_delay_s: float = 0.008,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> List[Tuple[int, int]]:
        """
        Thực thi di chuột mượt mà qua Adapter với nhịp nghỉ kiểm soát được.
        Trả về danh sách các điểm đã ghé qua.
        """
        start_pos = adapter.get_position()
        points = cls.calculate_trajectory(start_pos, (target_x, target_y), steps=steps)

        visited: List[Tuple[int, int]] = []
        for pt in points:
            if cancel_check and cancel_check():
                break
            adapter.move_to(pt[0], pt[1])
            visited.append(pt)
            if step_delay_s > 0:
                time.sleep(step_delay_s)

        # Đảm bảo điểm kết thúc luôn khớp tuyệt đối mục tiêu
        if visited and visited[-1] != (target_x, target_y):
            adapter.move_to(target_x, target_y)
            visited.append((target_x, target_y))

        return visited

    @classmethod
    def execute_smooth_click(
        cls,
        adapter: DesktopMouseAdapterProtocol,
        target_x: int,
        target_y: int,
        button: str = "left",
        aim_pause_s: float = 0.08,
        hold_time_s: float = 0.05,
        cancel_check: Optional[Callable[[], bool]] = None,
    ) -> List[Tuple[int, int]]:
        """
        Thực hiện toàn bộ chuỗi động tác: Di chuột mượt -> Dừng ngắm (Aim Pause) -> Nhấp chuột (Down-Hold-Up).
        Trả về danh sách các điểm tọa độ đã di chuyển qua.
        """
        # 1. Di chuyển mượt đến mục tiêu
        visited = cls.execute_smooth_move(adapter, target_x, target_y, cancel_check=cancel_check)

        if cancel_check and cancel_check():
            return visited

        # 2. Dừng ngắm thị giác (Aim Pause để người quan sát nhận diện điểm chuẩn bị bấm)
        if aim_pause_s > 0:
            time.sleep(aim_pause_s)

        if cancel_check and cancel_check():
            return visited

        # 3. Thao tác nhấp chuột vật lý
        adapter.mouse_down(button)
        if hold_time_s > 0:
            time.sleep(hold_time_s)
        adapter.mouse_up(button)
        return visited
