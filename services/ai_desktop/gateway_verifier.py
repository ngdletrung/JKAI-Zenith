# -*- coding: utf-8 -*-
"""
Central Gateway Independent Observation Verifier for JKAI Desktop Actuator (M5)
Kế thừa kiến trúc từ:
  - Jeomon/Windows-Use & simular-ai/Agent-S (AOM Observation Feedback)

Cung cấp bộ thẩm định hậu thực thi độc lập (Gateway-owned Independent Verifier):
  - Tự động ghi nhận UIA Tree Snapshot trước thao tác.
  - So sánh đối chiếu trạng thái UIA Tree Snapshot sau thao tác.
  - TARGET-SPECIFIC MUTATION: Xác minh chính xác phần tử mục tiêu (Automation ID) bị biến đổi,
    chống false-positive khi thao tác tác động sai phần tử.
"""

from typing import Callable, Optional
from .uia_tree_inspector import UIATreeInspector, UIATreeSnapshot


class GatewayObservationVerifier:
    """
    Bộ thẩm định hậu thực thi độc lập thuộc sở hữu của Central Gateway.
    """

    @classmethod
    def create_target_mutation_verifier(
        cls,
        hwnd: int,
        target_automation_id: str,
        is_live_mode: bool = False,
    ) -> Callable[[int], bool]:
        """
        Tạo hàm verifier đối chiếu trạng thái của CHÍNH PHẦN TỬ MỤC TIÊU (Target-Specific Mutation)
        trước và sau thao tác, ngăn chặn triệt để false-positive do phần tử khác đổi hash.
        """
        inspector = UIATreeInspector(is_live_mode=is_live_mode)
        snap_before = inspector.inspect_tree(hwnd)

        # Lấy hash ban đầu của phần tử mục tiêu
        node_before = next((el for el in snap_before.elements if el.automation_id == target_automation_id), None)
        before_hash = node_before.element_hash if node_before else ""

        def verify(target_hwnd: int) -> bool:
            snap_after = inspector.inspect_tree(target_hwnd)
            node_after = next((el for el in snap_after.elements if el.automation_id == target_automation_id), None)
            if not node_after:
                return False
            # Nếu hash của chính node mục tiêu thay đổi -> Target Mutation thành công
            return node_after.element_hash != before_hash

        return verify

    @classmethod
    def create_tree_mutation_verifier(
        cls,
        hwnd: int,
        is_live_mode: bool = False,
        expected_mutation: bool = True,
    ) -> Callable[[int], bool]:
        """
        Tạo hàm verifier đối chiếu UIA Tree Snapshot trước và sau khi thao tác.
        Nếu expected_mutation=True: Yêu cầu snapshot_hash sau thao tác phải khác trước thao tác.
        Nếu expected_mutation=False (read-only): Yêu cầu snapshot_hash được giữ nguyên ổn định.
        """
        inspector = UIATreeInspector(is_live_mode=is_live_mode)
        snap_before = inspector.inspect_tree(hwnd)

        def verify(target_hwnd: int) -> bool:
            snap_after = inspector.inspect_tree(target_hwnd)
            has_changed = (snap_after.snapshot_hash != snap_before.snapshot_hash)
            if expected_mutation:
                return has_changed
            else:
                return not has_changed

        return verify

    @classmethod
    def create_control_state_verifier(
        cls,
        hwnd: int,
        target_automation_id: str,
        is_live_mode: bool = False,
    ) -> Callable[[int], bool]:
        """
        Tạo hàm verifier kiểm tra sự tồn tại và tính hợp lệ của phần tử mục tiêu.
        """
        inspector = UIATreeInspector(is_live_mode=is_live_mode)

        def verify(target_hwnd: int) -> bool:
            if not target_automation_id or target_automation_id in ("Custom Coordinate", "target"):
                import win32gui
                return bool(win32gui.IsWindow(target_hwnd) and win32gui.IsWindowVisible(target_hwnd) and win32gui.IsWindowEnabled(target_hwnd))
            snap = inspector.inspect_tree(target_hwnd)
            for el in snap.elements:
                if el.automation_id == target_automation_id or el.name == target_automation_id:
                    return el.is_enabled and el.is_visible
            return False

        return verify

    @classmethod
    def create_expected_title_verifier(
        cls,
        hwnd: int,
        expected_title: str,
        exact: bool = True,
        is_live_mode: bool = False,
        max_wait_s: float = 1.0,
    ):
        """
        Tạo hàm verifier xác minh sự biến đổi tiêu đề cửa sổ theo kỳ vọng chính xác (Expected Effect Verifier).
        Thực hiện polling độc lập đối chiếu GetWindowText với expected_title.
        """
        import time

        def verify(target_hwnd: int) -> bool:
            exp_clean = (expected_title or "").strip()
            deadline = time.time() + max_wait_s
            while True:
                actual_title = ""
                try:
                    import win32gui
                    if win32gui.IsWindow(target_hwnd):
                        actual_title = win32gui.GetWindowText(target_hwnd)
                except Exception:
                    actual_title = ""

                matched = (actual_title == exp_clean) if exact else (exp_clean in actual_title)
                if matched:
                    return True

                if time.time() >= deadline:
                    break
                time.sleep(0.05)

            return False

        return verify

    @classmethod
    def create_expected_text_verifier(
        cls,
        hwnd: int,
        expected_text: str,
        exact: bool = True,
        is_live_mode: bool = False,
        max_wait_s: float = 1.0,
    ):
        """
        Tạo hàm verifier xác minh nội dung văn bản bên trong ô nhập liệu (Edit Control).
        Thực hiện polling độc lập đối chiếu WM_GETTEXT (qua SendMessageW buffer) với expected_text,
        hoạt động tin cậy 100% xuyên tiến trình (Cross-Process Edit Control Inspection).
        """
        import time
        import ctypes
        import win32con

        def verify(target_hwnd: int, *args) -> bool:
            exp_clean = (expected_text or "").strip()
            deadline = time.time() + max_wait_s
            while True:
                actual_text = ""
                # 1. Sử dụng SendMessageW(WM_GETTEXT) đọc trực tiếp từ Edit Control của tiến trình khác
                try:
                    buf = ctypes.create_unicode_buffer(1024)
                    ctypes.windll.user32.SendMessageW(target_hwnd, win32con.WM_GETTEXT, 1024, buf)
                    actual_text = buf.value
                except Exception:
                    actual_text = ""

                # 2. Fallback nếu control là top-level window
                if not actual_text:
                    try:
                        import win32gui
                        if win32gui.IsWindow(target_hwnd):
                            actual_text = win32gui.GetWindowText(target_hwnd)
                    except Exception:
                        pass

                matched = (actual_text == exp_clean) if exact else (exp_clean in actual_text)
                if matched:
                    return True

                if time.time() >= deadline:
                    break
                time.sleep(0.05)

            return False

        return verify

    @classmethod
    def create_visual_diff_verifier(
        cls,
        hwnd: int,
        is_live_mode: bool = False,
        expected_diff: bool = True,
    ) -> Callable[[int], bool]:
        """
        Tạo hàm verifier đối chiếu Visual Difference (M5-G3) trước và sau thao tác.
        Nếu expected_diff=True: Yêu cầu giao diện cửa sổ có sự biến đổi thị giác (diff_detected=True).
        Nếu expected_diff=False (read-only): Yêu cầu giao diện hoàn toàn tĩnh (exact_pixel_match=True).
        """
        from .visual_engine import VisualWindowCaptureEngine
        engine = VisualWindowCaptureEngine(is_live_mode=is_live_mode)
        snap_before = engine.capture_window(hwnd)

        def verify(target_hwnd: int) -> bool:
            snap_after = engine.capture_window(target_hwnd)
            res = engine.compute_visual_difference(snap_before, snap_after)
            if expected_diff:
                return res["diff_detected"]
            else:
                return not res["diff_detected"]

        return verify

