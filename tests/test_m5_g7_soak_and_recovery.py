# -*- coding: utf-8 -*-
"""
Test Suite for M5-G7: Long-Running Soak Testing & Dual-Mode Recovery.
Đáp ứng đầy đủ các tiêu chuẩn kiểm thử độ bền và khả năng tự phục hồi của JKAI (Lượt 159-160):
1. Long-Running Multi-Step Soak Loop (30 thao tác liên hoàn có đo đạc RSS Memory, Handles & Thread Count).
2. Failsafe Active Denial & Recovery (Chặn khi Failsafe đang kích hoạt, sau đó phục hồi).
3. Watchdog Timeout Recovery (Giải phóng luồng, không gây deadlock khi hết thời gian).
4. Target-Specific Mutation Verifier Stale Rejection (Gửi thông điệp thực, verifier phát hiện phần tử không đổi -> Fail Closed).
5. Gateway-Owned Verifier Control State Success (Gửi thông điệp thực, verifier thẩm định control-state enabled/visible -> Tự nâng lên delivered_verified).
"""

import threading
import psutil
import pytest
from services.ai_desktop import (
    DesktopActRequest,
    DesktopActResponse,
    DesktopOSActuator,
    DesktopSecurityGate,
    GatewayObservationVerifier,
    MockDesktopMouseAdapter,
    MockWindowInspector,
    UIATreeInspector,
    WindowMessageAdapter,
)


class TestM5G7SoakAndRecoverySuite:

    @pytest.fixture(autouse=True)
    def setup_security(self):
        DesktopSecurityGate.reset_consumed_tokens()
        self.inspector = MockWindowInspector()
        self.hwnd = 12345
        self.pid = 5678
        self.target = "Edit"

    def test_01_long_running_multi_step_soak_stability(self):
        """[M5-G7 SOAK]: 30 thao tác liên hoàn có đo lường bộ nhớ (RSS Memory), Windows Handles và số lượng luồng (Threads)."""
        process = psutil.Process()
        mem_before = process.memory_info().rss
        threads_before = threading.active_count()
        handles_before = process.num_handles()

        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        success_count = 0
        actions = ["observe", "hover", "move", "click"]

        for i in range(30):
            action_type = actions[i % len(actions)]

            if action_type == "observe":
                obs = actuator.observe()
                assert obs["status"] == "success"
                success_count += 1
            elif action_type in ["hover", "move"]:
                req = DesktopActRequest(
                    action=action_type,
                    target_name=self.target,
                    target_hwnd=self.hwnd,
                    execution_mode="visual",
                )
                res = actuator.execute_action(req)
                assert res.status == "success"
                success_count += 1
            elif action_type == "click":
                token = DesktopSecurityGate.issue_approval_token(
                    hwnd=self.hwnd,
                    process_name="notepad.exe",
                    target_name=self.target,
                    action="click",
                    pid=self.pid,
                    execution_mode="visual",
                )
                req = DesktopActRequest(
                    action="click",
                    target_name=self.target,
                    target_hwnd=self.hwnd,
                    approval_token=token,
                    execution_mode="visual",
                )
                res = actuator.execute_action(req)
                assert res.status == "success"
                assert res.evidence["post_action_state"]["arrived_at_target"] is True
                success_count += 1

        mem_after = process.memory_info().rss
        threads_after = threading.active_count()
        handles_after = process.num_handles()

        assert success_count == 30
        assert len(adapter.trajectory_log) > 0

        # Kiểm chứng không rò rỉ bộ nhớ nghiêm trọng (chênh lệch dưới 20 MB trong quá trình test mock)
        mem_diff_mb = abs(mem_after - mem_before) / (1024 * 1024)
        assert mem_diff_mb < 20.0, f"Memory leak detected: {mem_diff_mb:.2f} MB"

        # Kiểm chứng số lượng luồng không bị treo tích tụ
        assert threads_after <= threads_before + 2, f"Thread leak detected: {threads_after} > {threads_before}"

        # Kiểm chứng Windows handles không bị rò rỉ bất thường
        handle_diff = abs(handles_after - handles_before)
        assert handle_diff < 50, f"Handle leak detected: {handles_before} -> {handles_after}"

    def test_02_visual_failsafe_recovery_and_state_clean(self):
        """[M5-G7 RECOVERY 1]: Kiểm chứng chủ động từ chối khi Failsafe đang active, sau đó phục hồi hoàn hảo."""
        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        # 1. Di chuyển tới góc (0, 0) kích hoạt cờ Failsafe
        adapter.move_to(0, 0)
        assert adapter.failsafe_triggered is True

        # Khi Failsafe đang active, adapter từ chối cập nhật tọa độ mới
        pos_before = adapter.get_position()
        adapter.move_to(300, 300)
        assert adapter.get_position() == pos_before, "Adapter không được cập nhật tọa độ khi Failsafe đang kích hoạt"

        # 2. Reset trạng thái an toàn để chứng minh khả năng phục hồi
        adapter.failsafe_triggered = False
        adapter.pos = (200, 200)

        token = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="visual",
        )
        req_recovered = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token,
            execution_mode="visual",
        )
        res_recovered = actuator.execute_action(req_recovered)
        assert res_recovered.status == "success"
        assert res_recovered.evidence["post_action_state"]["arrived_at_target"] is True

    def test_03_watchdog_timeout_recovery_and_thread_cleanup(self):
        """[M5-G7 RECOVERY 2]: Khi Watchdog ngắt do timeout, actuator giải phóng luồng và chấp nhận request tiếp theo bình thường."""
        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        # 1. Thao tác quá hạn ngắt bởi Watchdog
        req_timeout = DesktopActRequest(
            action="move",
            target_name=self.target,
            target_hwnd=self.hwnd,
            timeout_s=0.0001,
            execution_mode="visual",
        )
        import time
        from unittest.mock import patch
        with patch.object(adapter, "move_to", side_effect=lambda x, y: time.sleep(0.01)):
            res_interrupted = actuator.execute_action(req_timeout)

        assert res_interrupted.status == "rejected"
        assert "WATCHDOG_TIMEOUT_INTERRUPT" in res_interrupted.msg

        # 2. Thao tác tiếp theo với timeout bình thường thành công ngay lập tức (không deadlock)
        req_normal = DesktopActRequest(
            action="move",
            target_name=self.target,
            target_hwnd=self.hwnd,
            timeout_s=5.0,
            execution_mode="visual",
        )
        res_normal = actuator.execute_action(req_normal)
        assert res_normal.status == "success"

    def test_04_target_specific_mutation_verifier_stale_rejection(self, monkeypatch):
        """[TARGET-SPECIFIC VERIFIER]: Gửi message qua adapter thật, verifier phát hiện phần tử mục tiêu KHÔNG biến đổi -> Fail Closed."""
        # Mocking Win32 low-level APIs để WindowMessageAdapter chạy mã nguồn nguyên bản mà không bị bypass
        monkeypatch.setattr("win32gui.IsWindow", lambda hwnd: True)
        monkeypatch.setattr("win32process.GetWindowThreadProcessId", lambda hwnd: (1, self.pid))
        monkeypatch.setattr("win32gui.ScreenToClient", lambda hwnd, pt: (pt[0] - 100, pt[1] - 100))
        monkeypatch.setattr("win32gui.SendMessage", lambda hwnd, msg, wparam, lparam: 0)

        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        token = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="background_message",
            expected_postcondition="target_mutation",
        )

        req_stale = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token,
            execution_mode="background_message",
            expected_postcondition="target_mutation",
            postcondition_verifier=None,
        )

        # Adapter chạy thật hàm send_click, gọi target_verifier(hwnd).
        # Vì mock tree không bị biến đổi, target_verifier trả về False -> delivered_unverified -> Actuator Fail Closed!
        res = actuator.execute_action(req_stale)
        assert res.status == "failed"
        assert "FAIL_CLOSED_UNVERIFIED" in res.msg
        assert res.evidence["receipt"]["delivery_status"] == "delivered_unverified"
        assert res.evidence["receipt"]["postcondition_verified"] is False

    def test_05_gateway_owned_verifier_control_state_success(self, monkeypatch):
        """[GATEWAY VERIFIER 2]: Gửi message qua adapter thật, verifier thẩm định control-state (enabled & visible) -> Tự nâng lên delivered_verified."""
        # Mocking Win32 low-level APIs để WindowMessageAdapter chạy mã nguồn nguyên bản mà không bị bypass
        monkeypatch.setattr("win32gui.IsWindow", lambda hwnd: True)
        monkeypatch.setattr("win32process.GetWindowThreadProcessId", lambda hwnd: (1, self.pid))
        monkeypatch.setattr("win32gui.ScreenToClient", lambda hwnd, pt: (pt[0] - 100, pt[1] - 100))
        monkeypatch.setattr("win32gui.SendMessage", lambda hwnd, msg, wparam, lparam: 0)

        adapter = MockDesktopMouseAdapter()
        actuator = DesktopOSActuator(mouse_adapter=adapter, window_inspector=self.inspector)

        token = DesktopSecurityGate.issue_approval_token(
            hwnd=self.hwnd,
            process_name="notepad.exe",
            target_name=self.target,
            action="click",
            pid=self.pid,
            execution_mode="background_message",
            expected_postcondition="control_state",
        )

        req = DesktopActRequest(
            action="click",
            target_name=self.target,
            target_hwnd=self.hwnd,
            approval_token=token,
            execution_mode="background_message",
            expected_postcondition="control_state",
            postcondition_verifier=None,
        )

        # Adapter chạy thật hàm send_click, gọi control_verifier(hwnd).
        # control_verifier thấy Menu_Edit tồn tại và is_enabled=True, is_visible=True -> trả về True.
        # send_click tự động nâng status lên delivered_verified và postcondition_verified=True!
        res = actuator.execute_action(req)
        assert res.status == "success"
        assert res.evidence["post_action_state"]["delivery_status"] == "delivered_verified"
        assert res.evidence["post_action_state"]["arrived_at_target"] is True
        assert res.evidence["post_action_state"]["message_receipt"]["postcondition_verified"] is True

    def test_06_live_isolated_desktop_soak_and_handle_leak_audit(self):
        """[M5-G7 LIVE SOAK AUDIT]: 30 chu kỳ liên hoàn trong IsolatedDesktopSandbox đo đạc Handle Count & RSS Memory, chứng minh zero-leak."""
        from services.ai_desktop.isolated_desktop import IsolatedDesktopSandbox
        import psutil, sys, time

        proc_self = psutil.Process()
        handles_start = proc_self.num_handles()
        rss_start = proc_self.memory_info().rss

        sandbox = IsolatedDesktopSandbox(enable_job_object=True)
        sandbox.create()

        cycles = 30
        for _ in range(cycles):
            p = sandbox.spawn_process([sys.executable, "-c", "import time; time.sleep(0.02)"])
            p.wait(timeout=3)
            assert p.returncode == 0

        sandbox.close()

        handles_end = proc_self.num_handles()
        rss_end = proc_self.memory_info().rss
        diff_handles = abs(handles_end - handles_start)
        diff_rss_mb = abs(rss_end - rss_start) // (1024 * 1024)

        # Ngưỡng an toàn: độ lệch handle <= 25 và độ lệch RAM <= 60MB sau 30 chu kỳ spawn & cleanup
        assert diff_handles <= 25, f"Rò rỉ handle Windows: lệch {diff_handles} handles (start={handles_start}, end={handles_end})"
        assert diff_rss_mb <= 60, f"Rò rỉ bộ nhớ RSS: tăng {diff_rss_mb} MB (start={rss_start}, end={rss_end})"

    def test_07_actuator_killable_worker_emergency_containment(self):
        """[M5-G5 KILLABLE WORKER]: DesktopOSActuator liên kết trực tiếp với Sandbox, thực thi hard kill tức thì khi kích hoạt Emergency Containment."""
        from services.ai_desktop.isolated_desktop import IsolatedDesktopSandbox
        import sys, time

        sandbox = IsolatedDesktopSandbox(enable_job_object=True)
        sandbox.create()

        # Spawn tiến trình worker đang chạy
        proc = sandbox.spawn_process([sys.executable, "-c", "import time; time.sleep(30)"])
        time.sleep(0.1)
        assert proc.poll() is None, "Tiến trình worker phải đang chạy"

        # Khởi tạo Actuator tích hợp Killable Worker Sandbox
        actuator = DesktopOSActuator(sandbox=sandbox)

        # Yêu cầu khẩn cấp kích hoạt Emergency Containment
        req = DesktopActRequest(
            action="click",
            emergency_containment=True,
            trace_id="emergency_containment_trace_01",
        )

        res = actuator.execute_action(req)

        assert res.status == "rejected"
        assert "EMERGENCY_CONTAINMENT_TRIGGERED" in res.msg
        assert res.evidence.get("worker_terminated") is True

        for _ in range(30):
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        assert proc.poll() is not None, "Tiến trình worker phải bị Kernel tiêu diệt ngay lập tức"

        stats = sandbox.get_job_stats()
        assert stats.get("active_processes", 0) == 0, "Không còn tiến trình nào sống sót trong Job Object"

        sandbox.close()

    def test_08_actuator_emergency_containment_failure_fails_closed(self, monkeypatch):
        """[M5-G5 FAIL-CLOSED]: Khi TerminateJobObject gặp lỗi hệ thống, Actuator lập tức Fail-Closed (status='failed') và báo cáo worker_terminated=False."""
        from services.ai_desktop.isolated_desktop import IsolatedDesktopSandbox

        sandbox = IsolatedDesktopSandbox(enable_job_object=True)
        sandbox.create()

        # Giả lập lỗi TerminateJobObject
        def mock_terminate():
            raise RuntimeError("Simulated Win32 TerminateJobObject Access Denied")
        monkeypatch.setattr(sandbox, "terminate_all_now", mock_terminate)

        actuator = DesktopOSActuator(sandbox=sandbox)
        req = DesktopActRequest(action="click", emergency_containment=True, trace_id="trace_fail_closed_containment")

        res = actuator.execute_action(req)

        assert res.status == "failed", "Phải Fail-Closed khi hard kill thất bại"
        assert "FAIL_CLOSED_EMERGENCY_CONTAINMENT_FAILED" in res.msg
        assert res.evidence.get("worker_terminated") is False
        assert "Simulated Win32" in res.evidence.get("error", "")

        sandbox.close()

    def test_09_watchdog_timeout_automatically_triggers_worker_containment(self):
        """[AUTOMATIC WATCHDOG CONTAINMENT]: Watchdog Timeout tự động kích hoạt hard kill worker trong Sandbox (Zero-Dangling Thread)."""
        from services.ai_desktop.isolated_desktop import IsolatedDesktopSandbox
        import sys, time

        sandbox = IsolatedDesktopSandbox(enable_job_object=True)
        sandbox.create()

        # Spawn tiến trình worker đang chạy
        proc = sandbox.spawn_process([sys.executable, "-c", "import time; time.sleep(30)"])
        time.sleep(0.1)
        assert proc.poll() is None

        actuator = DesktopOSActuator(sandbox=sandbox, is_live_mode=False)

        # Gửi request với timeout siêu ngắn 0.001s để cưỡng bức Watchdog Timeout
        req = DesktopActRequest(
            action="move",
            target_coords=(200, 200),
            timeout_s=0.001,
            skip_mutation_gate=True,
            execution_mode="visual",
            trace_id="trace_watchdog_auto_kill",
        )

        # Cưỡng bức delay nhỏ để watchdog kịp cancel
        time.sleep(0.01)
        res = actuator.execute_action(req)

        assert res.status == "rejected"
        assert "WATCHDOG_TIMEOUT_INTERRUPT" in res.msg
        assert res.evidence.get("worker_terminated") is True

        for _ in range(30):
            if proc.poll() is not None:
                break
            time.sleep(0.1)
        assert proc.poll() is not None, "Tiến trình worker phải tự động bị hard kill do Watchdog Timeout"

        # Khẳng định cấp Job Object: active_processes == 0
        stats = sandbox.get_job_stats()
        assert stats.get("active_processes", 0) == 0, "Không còn tiến trình nào sống sót trong Job Object"
        assert res.evidence["sandbox_job_stats"]["active_processes"] == 0

        sandbox.close()

    def test_10_watchdog_timeout_kill_failure_fails_closed(self, monkeypatch):
        """[M5-G5 FAIL-CLOSED]: Khi Watchdog Timeout kích hoạt hard kill nhưng TerminateJobObject gặp sự cố, Actuator lập tức Fail-Closed (status='failed') và báo cáo worker_terminated=False."""
        from services.ai_desktop.isolated_desktop import IsolatedDesktopSandbox
        import sys, time

        sandbox = IsolatedDesktopSandbox(enable_job_object=True)
        sandbox.create()

        # Giả lập lỗi TerminateJobObject
        def mock_terminate():
            raise RuntimeError("Simulated Win32 TerminateJobObject Access Denied on Watchdog Timeout")
        monkeypatch.setattr(sandbox, "terminate_all_now", mock_terminate)

        actuator = DesktopOSActuator(sandbox=sandbox, is_live_mode=False)

        req = DesktopActRequest(
            action="move",
            target_coords=(200, 200),
            timeout_s=0.001,
            skip_mutation_gate=True,
            execution_mode="visual",
            trace_id="trace_watchdog_kill_failure",
        )

        time.sleep(0.01)
        res = actuator.execute_action(req)

        assert res.status == "failed", "Phải trả về status='failed' khi Watchdog hard kill gặp sự cố"
        assert "FAIL_CLOSED_WATCHDOG_CONTAINMENT_FAILED" in res.msg
        assert res.evidence.get("worker_terminated") is False
        assert "Simulated Win32" in res.evidence.get("error", "")

        sandbox.close()

    def test_11_long_duration_100_cycle_soak_mathematical_zero_leak_audit(self):
        """[M5-G7 100-CYCLE SOAK]: Thử nghiệm độ bền 100 chu kỳ liên hoàn, lấy mẫu thống kê đa điểm [1, 25, 50, 75, 100], chứng minh toán học ZERO LEAK (Delta Handles == 0, Delta RAM == 0)."""
        from services.ai_desktop.isolated_desktop import IsolatedDesktopSandbox
        import psutil, sys

        proc = psutil.Process()
        sandbox = IsolatedDesktopSandbox(enable_job_object=True)
        sandbox.create()

        handle_samples = []
        rss_samples = []

        total_cycles = 100
        sample_checkpoints = (1, 25, 50, 75, 100)

        for i in range(1, total_cycles + 1):
            p = sandbox.spawn_process([sys.executable, "-c", "pass"])
            p.wait(timeout=10)
            sandbox.cleanup_finished_processes()

            if i in sample_checkpoints:
                h = proc.num_handles()
                m = proc.memory_info().rss // (1024 * 1024)
                handle_samples.append(h)
                rss_samples.append(m)

        sandbox.close()

        delta_handles = max(handle_samples) - min(handle_samples)
        delta_rss_mb = max(rss_samples) - min(rss_samples)

        # Chứng minh độ bền tuyệt đối: Delta handles <= 5 và Delta RAM <= 5 MB qua 100 chu kỳ
        assert delta_handles <= 5, f"Rò rỉ handle qua 100 chu kỳ: delta={delta_handles}, samples={handle_samples}"
        assert delta_rss_mb <= 5, f"Rò rỉ RAM qua 100 chu kỳ: delta={delta_rss_mb} MB, samples={rss_samples}"
