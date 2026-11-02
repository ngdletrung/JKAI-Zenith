# -*- coding: utf-8 -*-
"""
tests/test_m5_g3_visual_diff.py
[M5-G3 VISUAL DIFF & SET-OF-MARKS (SoM) VERIFICATION SUITE]:
Kiểm chứng năng lực Thị giác & Nhận thức giao diện (Visual Perception & Diff Verification)
theo chuẩn kiến trúc của UI-TARS-desktop, Agent-S và Windows-Use:
1. Chụp ảnh cửa sổ mục tiêu không xâm lấn (Non-invasive Win32 PrintWindow / DC capture).
2. Tính toán Visual Hash (Pixel SHA-256 + 64-bit dHash gradient).
3. Tự động đánh nhãn số Set-of-Marks (SoM) cho Vision-Language Grounding.
4. Gateway synthesis xác thực biến đổi thị giác (Visual Diff Verifier) với cơ chế Fail-Closed.
5. Kiểm chứng thực địa bên trong Isolated Desktop Sandbox, an toàn tuyệt đối 100% với màn hình Host.
6. Live SoM extraction từ UIA3 Element Tree.
7. Live before/after visual mutation verification trong Isolated Desktop.
"""

import sys
import time
import pytest
from services.ai_desktop import (
    DesktopActRequest,
    DesktopOSActuator,
    DesktopSecurityGate,
    GatewayObservationVerifier,
    IsolatedDesktopSandbox,
    MockDesktopMouseAdapter,
    MockWindowInspector,
    VisualWindowCaptureEngine,
    WindowVisualSnapshot,
)


def _find_desktop_window(sandbox, pid, timeout=6.0):
    """Tìm HWND của PID trong Desktop cô lập (EnumWindows không thấy cửa sổ khác desktop)."""
    import ctypes
    from ctypes import wintypes

    import win32gui

    user32 = ctypes.windll.user32
    deadline = time.time() + timeout
    while time.time() < deadline:
        found = []

        def cb(h, _):
            try:
                window_pid = wintypes.DWORD()
                user32.GetWindowThreadProcessId(h, ctypes.byref(window_pid))
                if window_pid.value == pid and user32.IsWindowVisible(h):
                    found.append(h)
            except Exception:
                pass
            return True

        try:
            win32gui.EnumDesktopWindows(sandbox.h_desktop, cb, 0)
        except Exception:
            # CreateProcess vừa mở desktop có thể khiến handle chưa enumerable trong vài ms.
            pass
        if found:
            return found[0]
        time.sleep(0.1)
    return None


class TestM5G3VisualDiffSuite:

    @pytest.fixture(autouse=True)
    def setup_security(self, monkeypatch):
        DesktopSecurityGate.reset_consumed_tokens()
        self.inspector = MockWindowInspector()
        self.hwnd = 12345
        self.pid = 5678
        self.target = "Edit"

        # Mock Win32 low-level APIs để WindowMessageAdapter chạy an toàn trong unit test
        monkeypatch.setattr("win32gui.IsWindow", lambda hwnd: True)
        monkeypatch.setattr("win32process.GetWindowThreadProcessId", lambda hwnd: (1, self.pid))
        monkeypatch.setattr("win32gui.ScreenToClient", lambda hwnd, pt: (pt[0] - 100, pt[1] - 100))
        monkeypatch.setattr("win32gui.SendMessage", lambda hwnd, msg, wparam, lparam: 0)

    def test_01_synthetic_visual_snapshot_and_som_generation(self):
        """[M5-G3.1]: Tạo Visual Snapshot và đánh nhãn Set-of-Marks (SoM) chuẩn xác."""
        engine = VisualWindowCaptureEngine(is_live_mode=False)

        elements = [
            {"name": "OK", "control_type": "Button", "automation_id": "btn_ok", "rect": [10, 10, 50, 30], "center": (30, 20)},
            {"name": "Input", "control_type": "Edit", "automation_id": "txt_input", "rect": [10, 50, 200, 80], "center": (105, 65)},
        ]

        snap = engine.capture_window(self.hwnd, som_elements=elements)

        assert snap.hwnd == self.hwnd
        assert snap.width == 800
        assert snap.height == 600
        assert len(snap.pixel_hash) == 64
        assert len(snap.dhash) == 16
        assert len(snap.som_marks) == 2
        assert snap.som_marks[0]["mark_id"] == 1
        assert snap.som_marks[0]["automation_id"] == "btn_ok"
        assert snap.som_marks[1]["mark_id"] == 2
        assert snap.som_marks[1]["automation_id"] == "txt_input"

    def test_02_visual_difference_metric_calculation(self):
        """[M5-G3.2]: Tính toán chỉ số sai khác thị giác (Pixel Hash Diff & Hamming Distance)."""
        snap1 = WindowVisualSnapshot(
            hwnd=self.hwnd,
            width=800,
            height=600,
            pixel_hash="a" * 64,
            dhash="0000000000000000",
            captured_at=time.time(),
            is_live_capture=False,
        )
        snap2 = WindowVisualSnapshot(
            hwnd=self.hwnd,
            width=800,
            height=600,
            pixel_hash="a" * 64,
            dhash="0000000000000000",
            captured_at=time.time(),
            is_live_capture=False,
        )
        snap3 = WindowVisualSnapshot(
            hwnd=self.hwnd,
            width=800,
            height=600,
            pixel_hash="b" * 64,
            dhash="000000000000000f",  # 4 bits khác nhau
            captured_at=time.time(),
            is_live_capture=False,
        )

        res_same = VisualWindowCaptureEngine.compute_visual_difference(snap1, snap2)
        assert res_same["diff_detected"] is False
        assert res_same["exact_pixel_match"] is True
        assert res_same["hamming_distance"] == 0

        res_diff = VisualWindowCaptureEngine.compute_visual_difference(snap1, snap3)
        assert res_diff["diff_detected"] is True
        assert res_diff["exact_pixel_match"] is False
        assert res_diff["hamming_distance"] == 4

    def test_03_gateway_synthesizes_visual_diff_verifier(self, monkeypatch):
        """[M5-G3.3]: Gateway tự động tổng hợp Visual Diff Verifier từ Token Expectation Binding."""
        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        # Cấp token ràng buộc 'visual_diff'
        token = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="background_message",
            expected_postcondition="visual_diff",
        )

        req = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token,
            execution_mode="background_message",
            expected_postcondition="visual_diff",
            postcondition_verifier=None,
        )

        # Mock visual diff engine trả về có sự biến đổi thị giác
        call_count = 0
        def mock_capture(*args, **kwargs):
            nonlocal call_count
            call_count += 1
            return WindowVisualSnapshot(
                hwnd=self.hwnd,
                width=800,
                height=600,
                pixel_hash="hash_before" if call_count == 1 else "hash_after",
                dhash="0000" if call_count == 1 else "ffff",
                captured_at=time.time(),
                is_live_capture=False,
            )

        monkeypatch.setattr(VisualWindowCaptureEngine, "capture_window", mock_capture)

        res = actuator.execute_action(req)
        assert res.status == "success"
        prov = res.evidence["verifier_provenance"]
        assert prov["synthesized_by"] == "CENTRAL_GATEWAY"
        assert prov["expected_postcondition"] == "visual_diff"
        assert f"GATEWAY_VERIFIER_VISUAL_DIFF_{self.hwnd}" in prov["verifier_id"]

    def test_04_visual_diff_fails_closed_when_screen_stale(self, monkeypatch):
        """[M5-G3.4]: Màn hình không đổi sau click -> Visual Diff Verifier phát hiện -> Fail Closed!"""
        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        token = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="background_message",
            expected_postcondition="visual_diff",
        )

        req = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token,
            execution_mode="background_message",
            expected_postcondition="visual_diff",
            postcondition_verifier=None,
        )

        # Mock màn hình bị đơ (hash không đổi giữa 2 lần chụp)
        def mock_stale_capture(*args, **kwargs):
            return WindowVisualSnapshot(
                hwnd=self.hwnd,
                width=800,
                height=600,
                pixel_hash="identical_hash_12345",
                dhash="0000111122223333",
                captured_at=time.time(),
                is_live_capture=False,
            )

        monkeypatch.setattr(VisualWindowCaptureEngine, "capture_window", mock_stale_capture)

        res = actuator.execute_action(req)
        assert res.status == "failed"
        assert "FAIL_CLOSED_UNVERIFIED" in res.msg
        assert res.evidence["receipt"]["delivery_status"] == "delivered_unverified"

    @pytest.mark.skipif(sys.platform != "win32", reason="Yêu cầu hệ điều hành Windows thật")
    def test_05_live_win32_window_capture_in_isolated_sandbox(self):
        """[M5-G3.5]: Chụp ảnh thực địa cửa sổ bên trong Isolated Desktop Sandbox qua Win32 PrintWindow."""
        from tests.sandbox_desktop_helper import run_in_sandbox

        sandbox = IsolatedDesktopSandbox()
        try:
            proc = sandbox.spawn_process(["notepad.exe"])
            target_hwnd = _find_desktop_window(sandbox, proc.pid)
            assert target_hwnd is not None, "Không tìm thấy cửa sổ Notepad trong Desktop cô lập"

            # PrintWindow phải chạy trong desktop sở hữu HWND
            snap = run_in_sandbox(sandbox, {"op": "capture", "hwnd": target_hwnd})

            assert snap["is_live_capture"] is True
            assert snap["hwnd"] == target_hwnd
            assert snap["width"] > 0
            assert snap["height"] > 0
            assert len(snap["pixel_hash"]) == 64
            assert len(snap["dhash"]) == 16
            assert snap["has_bitmap"] is True
        finally:
            sandbox.close()

    @pytest.mark.skipif(sys.platform != "win32", reason="Yêu cầu hệ điều hành Windows thật")
    def test_06_live_som_marks_from_uia3_tree_in_isolated_sandbox(self):
        """[M5-G3.6]: Trích xuất Set-of-Marks (SoM) thực địa từ Native UIA3 Tree của cửa sổ mục tiêu."""
        from tests.sandbox_desktop_helper import run_in_sandbox

        sandbox = IsolatedDesktopSandbox()
        try:
            proc = sandbox.spawn_process(["notepad.exe"])
            target_hwnd = _find_desktop_window(sandbox, proc.pid)
            assert target_hwnd is not None, "Không tìm thấy cửa sổ Notepad trong Desktop cô lập"

            # UIA COM chỉ thấy cửa sổ cùng desktop: bóc cây + sinh SoM từ trong sandbox
            res = run_in_sandbox(sandbox, {"op": "som", "hwnd": target_hwnd})

            assert res["element_count"] > 0, "Phải trích xuất được phần tử UIA3 từ cửa sổ Notepad"
            som_marks = res["som_marks"]
            assert len(som_marks) > 0, "Phải trích xuất được ít nhất 1 SoM mark từ UIA3 tree"
            for idx, mark in enumerate(som_marks, start=1):
                assert mark["mark_id"] == idx
                assert "rect" in mark
                assert "center" in mark
                assert "control_type" in mark
        finally:
            sandbox.close()

    @pytest.mark.skipif(sys.platform != "win32", reason="Yêu cầu hệ điều hành Windows thật")
    def test_07_live_visual_before_after_mutation_in_isolated_sandbox(self):
        """[M5-G3.7]: Xác thực biến đổi thị giác thực địa (Live Visual Diff) trước và sau khi gõ văn bản."""
        from tests.sandbox_desktop_helper import run_in_sandbox

        sandbox = IsolatedDesktopSandbox()
        try:
            proc = sandbox.spawn_process(["notepad.exe"])
            target_hwnd = _find_desktop_window(sandbox, proc.pid)
            assert target_hwnd is not None, "Không tìm thấy cửa sổ Notepad trong Desktop cô lập"

            # Before/after capture và mutation đều thực thi trong desktop cô lập
            res = run_in_sandbox(sandbox, {
                "op": "visual_diff",
                "hwnd": target_hwnd,
                "text": "JKAI Zenith Visual Diff Live Verification",
            })

            assert res["before"]["is_live_capture"] is True
            assert res["after"]["is_live_capture"] is True
            diff = res["diff"]
            assert diff["diff_detected"] is True, f"Visual diff không phát hiện biến đổi: {diff}"
            assert diff["exact_pixel_match"] is False
            assert res["before"]["pixel_hash"] != res["after"]["pixel_hash"]
        finally:
            sandbox.close()
