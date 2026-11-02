# -*- coding: utf-8 -*-
"""
Test Suite for M5 Isolated Desktop Sandbox.
Kiểm thử thực địa môi trường Windows Desktop cô lập (Dedicated Disposable Desktop):
1. Khởi tạo và đóng Desktop ảo cô lập an toàn qua Win32 API.
2. Quản lý vòng đời tiến trình con bên trong Desktop cô lập.
3. Gửi thông điệp Win32 thực tế làm biến đổi trạng thái UI của cửa sổ trong Desktop cô lập mà không chạm tới màn hình Master.
4. Tự động giải phóng và dọn dẹp sạch sẽ tài nguyên.
5. Thực thi toàn diện chu trình DesktopOSActuator (Native Mouse Adapter) & Central Gateway Verifier trên Notepad thật trong Isolated Desktop Sandbox.
6. Đo đạc bằng chứng thực tế Before/After Target Mutation Effect trong Isolated Desktop.
"""

import json
import sys
import time
import pytest
import win32gui
import win32process
from services.ai_desktop import (
    IsolatedDesktopSandbox,
)


def _run_in_desktop(sandbox, request, timeout=40):
    """Chạy thao tác Win32/UIA bên trong Desktop cô lập.

    HWND thuộc phạm vi desktop: tiến trình ở Default desktop không thể đọc hoặc
    gửi thông điệp tới cửa sổ trong desktop khác, nên mọi tương tác phải chạy
    trong một tiến trình được sandbox khởi chạy với lpDesktop trỏ đúng desktop.
    """
    proc = sandbox.spawn_process(
        [sys.executable, "-m", "tests.sandbox_desktop_helper", json.dumps(request)]
    )
    out, err = proc.communicate(timeout=timeout)
    payload = None
    for line in reversed((out or "").strip().splitlines()):
        try:
            payload = json.loads(line)
            break
        except Exception:
            continue
    assert payload is not None, f"Helper không trả JSON. rc={proc.returncode} out={out!r} err={err!r}"
    assert payload.get("ok") is True, payload
    return payload["result"]



class TestM5IsolatedDesktopSandboxSuite:

    def test_01_create_and_close_isolated_desktop(self):
        """[ISOLATED DESKTOP 1]: Khởi tạo và đóng Desktop ảo cô lập an toàn."""
        sandbox = IsolatedDesktopSandbox()
        h_desk = sandbox.create()
        assert h_desk > 0, "Handle của Desktop ảo phải là số nguyên dương hợp lệ"
        assert sandbox._is_active is True

        sandbox.close()
        assert sandbox._is_active is False
        assert sandbox.h_desktop is None

    def test_02_spawn_process_lifecycle_in_sandbox(self):
        """[ISOLATED DESKTOP 2]: Quản lý vòng đời tiến trình con trong context manager."""
        with IsolatedDesktopSandbox() as sandbox:
            proc = sandbox.spawn_process([sys.executable, "-c", "import time; time.sleep(10)"])
            assert proc.pid > 0
            assert proc.poll() is None, "Tiến trình con phải đang chạy trong Desktop cô lập"

        # Sau khi thoát khỏi context manager, tiến trình con phải được dọn dẹp
        time.sleep(0.5)
        assert proc.poll() is not None, "Tiến trình con phải được terminate tự động khi đóng Desktop"

    def test_03_live_message_mutation_inside_isolated_desktop(self):
        """[LIVE ISOLATED MUTATION]: Gửi thông điệp Win32 thực tế làm biến đổi UI thật trong Desktop ảo cô lập."""
        child_app_code = """
import sys, time, win32gui, win32con
def wndproc(hwnd, msg, wp, lp):
    return win32gui.DefWindowProc(hwnd, msg, wp, lp)

wc = win32gui.WNDCLASS()
wc.lpfnWndProc = wndproc
wc.lpszClassName = 'JKAI_Isolated_App_Class'
win32gui.RegisterClass(wc)
hwnd = win32gui.CreateWindow('JKAI_Isolated_App_Class', 'Initial Title', win32con.WS_OVERLAPPEDWINDOW, 100, 100, 400, 300, 0, 0, 0, None)
print(f'HWND:{hwnd}')
sys.stdout.flush()

for _ in range(60):
    win32gui.PumpWaitingMessages()
    txt = win32gui.GetWindowText(hwnd)
    if txt != 'Initial Title':
        print(f'MUTATED:{txt}')
        sys.stdout.flush()
        break
    time.sleep(0.05)
"""
        with IsolatedDesktopSandbox() as sandbox:
            proc = sandbox.spawn_process([sys.executable, "-c", child_app_code])

            # Đọc HWND từ stdout của tiến trình con trong Sandbox
            line = proc.stdout.readline().strip()
            assert line.startswith("HWND:"), f"Expected HWND line, got '{line}'"
            target_hwnd = int(line.split(":")[1])
            assert target_hwnd > 0

            # Gửi thông điệp Win32 thực tế từ một tiến trình CÙNG desktop cô lập
            new_title = "JKAI Sandbox Mutation Verified!"
            sent = _run_in_desktop(sandbox, {"op": "send_text", "hwnd": target_hwnd, "text": new_title})
            assert sent["ret"] == 1, f"SendMessage WM_SETTEXT must return 1, got {sent['ret']}"
            assert sent["before"]["is_window"] is True
            assert sent["after"]["title"] == new_title

            # Kiểm chứng tiến trình con xác nhận biến đổi thành công
            mutated_line = proc.stdout.readline().strip()
            assert mutated_line == f"MUTATED:{new_title}", f"Expected mutation confirmation, got '{mutated_line}'"

    def test_04_desktop_cleanup_terminates_multiple_processes(self):
        """[ISOLATED DESKTOP 4]: Dọn dẹp đồng loạt nhiều tiến trình khi đóng sandbox."""
        sandbox = IsolatedDesktopSandbox()
        sandbox.create()

        p1 = sandbox.spawn_process([sys.executable, "-c", "import time; time.sleep(10)"])
        p2 = sandbox.spawn_process([sys.executable, "-c", "import time; time.sleep(10)"])

        assert p1.poll() is None
        assert p2.poll() is None

        sandbox.close()
        time.sleep(0.5)

        assert p1.poll() is not None
        assert p2.poll() is not None

    def test_05_actuator_gateway_execution_inside_isolated_desktop(self):
        """[LIVE GATEWAY ACTUATOR IN SANDBOX]: Chạy chu trình DesktopOSActuator (Native Mouse Adapter) + Gateway Verifier trên Notepad trong Desktop cô lập."""
        with IsolatedDesktopSandbox() as sandbox:
            proc = sandbox.spawn_process(["notepad.exe"])
            time.sleep(1.5)
            pid = proc.pid

            target_hwnd = None

            def cb(h, l):
                nonlocal target_hwnd
                try:
                    _, p = win32process.GetWindowThreadProcessId(h)
                    if p == pid and win32gui.IsWindowVisible(h):
                        target_hwnd = h
                except Exception:
                    pass
                return True

            win32gui.EnumDesktopWindows(sandbox.h_desktop, cb, 0)
            assert target_hwnd is not None, f"Không tìm thấy HWND của Notepad PID {pid} trong Desktop cô lập"

            result = _run_in_desktop(sandbox, {
                "op": "actuator",
                "hwnd": target_hwnd,
                "pid": pid,
                "action": "click",
                "target_name": None,
                "execution_mode": "background_message",
                "expected_postcondition": "control_state",
            })
            assert result["process_name"] == "notepad.exe"
            assert result["status"] == "success", f"Actuator execution failed: {result['msg']}"
            evidence = result["evidence"]
            assert evidence["post_action_state"]["delivery_status"] == "delivered_verified"
            assert evidence["post_action_state"]["arrived_at_target"] is True

            prov = evidence["verifier_provenance"]
            assert prov["synthesized_by"] == "CENTRAL_GATEWAY"
            assert prov["expected_postcondition"] == "control_state"

    def test_06_live_before_after_target_mutation_effect_in_isolated_desktop(self):
        """[BEFORE/AFTER EFFECT PROOF]: Đo đạc trạng thái cửa sổ trước và sau dispatch trong Isolated Desktop."""
        child_app_code = """
import sys, time, win32gui, win32con
def wndproc(hwnd, msg, wp, lp):
    return win32gui.DefWindowProc(hwnd, msg, wp, lp)

wc = win32gui.WNDCLASS()
wc.lpfnWndProc = wndproc
wc.lpszClassName = 'JKAI_Effect_Target_Class'
win32gui.RegisterClass(wc)
hwnd = win32gui.CreateWindow('JKAI_Effect_Target_Class', 'Initial Title Before', win32con.WS_OVERLAPPEDWINDOW, 100, 100, 400, 300, 0, 0, 0, None)
print(f'HWND:{hwnd}')
sys.stdout.flush()

for _ in range(80):
    win32gui.PumpWaitingMessages()
    txt = win32gui.GetWindowText(hwnd)
    if txt != 'Initial Title Before':
        print(f'MUTATED:{txt}')
        sys.stdout.flush()
        break
    time.sleep(0.05)
"""
        with IsolatedDesktopSandbox() as sandbox:
            proc = sandbox.spawn_process([sys.executable, "-c", child_app_code])
            line = proc.stdout.readline().strip()
            target_hwnd = int(line.split(":")[1])

            # 1-3. Before-state, dispatch và after-state đều đo từ trong desktop cô lập
            new_title = "Mutated Title After Expected Effect"
            sent = _run_in_desktop(sandbox, {"op": "send_text", "hwnd": target_hwnd, "text": new_title})
            assert sent["ret"] == 1
            assert sent["before"]["title"] == "Initial Title Before"
            assert sent["after"]["title"] == new_title
            assert sent["after"]["title"] != sent["before"]["title"], "Cửa sổ mục tiêu phải chứng minh được sự biến đổi trạng thái (Before/After Effect)"

            mutated_line = proc.stdout.readline().strip()
            assert mutated_line == f"MUTATED:{new_title}"
    def test_07_end_to_end_gateway_orchestration_with_observed_mutation_in_isolated_desktop(self):
        """[END-TO-END CAUSAL MUTATION & EXPECTED EFFECT]: Actuator click kích hoạt UI handler, Gateway Verifier thẩm định chính xác Expected Effect."""
        child_app_code = """
import sys, time, win32gui, win32con
def wndproc(hwnd, msg, wp, lp):
    if msg == win32con.WM_LBUTTONUP:
        win32gui.SetWindowText(hwnd, 'Mutated Directly By Actuator Click!')
    return win32gui.DefWindowProc(hwnd, msg, wp, lp)

wc = win32gui.WNDCLASS()
wc.lpfnWndProc = wndproc
wc.lpszClassName = 'JKAI_Causal_Class'
win32gui.RegisterClass(wc)
hwnd = win32gui.CreateWindow('JKAI_Causal_Class', 'Initial E2E Title Before', win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE, 100, 100, 400, 300, 0, 0, 0, None)
print(f'HWND:{hwnd}')
sys.stdout.flush()

for _ in range(100):
    win32gui.PumpWaitingMessages()
    txt = win32gui.GetWindowText(hwnd)
    if txt != 'Initial E2E Title Before':
        print(f'MUTATED:{txt}')
        sys.stdout.flush()
        for _ in range(30):
            win32gui.PumpWaitingMessages()
            time.sleep(0.1)
        break
    time.sleep(0.05)
"""
        with IsolatedDesktopSandbox() as sandbox:
            proc = sandbox.spawn_process([sys.executable, "-c", child_app_code])
            line = proc.stdout.readline().strip()
            target_hwnd = int(line.split(":")[1])
            pid = proc.pid

            expected_title_target = "Mutated Directly By Actuator Click!"
            result = _run_in_desktop(sandbox, {
                "op": "actuator",
                "hwnd": target_hwnd,
                "pid": pid,
                "action": "click",
                "allow_python": True,
                "execution_mode": "background_message",
                "expected_postcondition": f"expected_title:{expected_title_target}",
            })
            assert result["status"] == "success", result
            evidence = result["evidence"]
            assert evidence["verifier_result"] is True
            assert evidence["verifier_provenance"]["expected_postcondition"] == f"expected_title:{expected_title_target}"
            assert evidence["before_after_state"]["title_before"] == "Initial E2E Title Before"
            assert evidence["before_after_state"]["title_after"] == expected_title_target
            assert evidence["before_after_state"]["effect_detected"] is True
            assert evidence["post_action_state"]["delivery_status"] == "delivered_verified"
            assert evidence["post_action_state"]["arrived_at_target"] is True

            # 3. Independent Observation sau dispatch (đọc lại từ trong desktop cô lập)
            observed = _run_in_desktop(sandbox, {"op": "read_window", "hwnd": target_hwnd})
            assert observed["window"]["title"] == expected_title_target

            mutated_line = proc.stdout.readline().strip()
            assert mutated_line == f"MUTATED:{expected_title_target}"

    def test_08_gateway_verifier_expected_effect_negative_test_fails_closed(self):
        """[NEGATIVE TEST]: Click dispatch thành công nhưng effect không khớp kỳ vọng -> Fail Closed (delivered_unverified)."""
        child_app_code = """
import sys, time, win32gui, win32con
def wndproc(hwnd, msg, wp, lp):
    if msg == win32con.WM_LBUTTONUP:
        win32gui.SetWindowText(hwnd, 'Actual Mutation Title')
    return win32gui.DefWindowProc(hwnd, msg, wp, lp)

wc = win32gui.WNDCLASS()
wc.lpfnWndProc = wndproc
wc.lpszClassName = 'JKAI_Negative_Test_Class'
win32gui.RegisterClass(wc)
hwnd = win32gui.CreateWindow('JKAI_Negative_Test_Class', 'Initial Negative Title', win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE, 100, 100, 400, 300, 0, 0, 0, None)
print(f'HWND:{hwnd}')
sys.stdout.flush()

for _ in range(100):
    win32gui.PumpWaitingMessages()
    txt = win32gui.GetWindowText(hwnd)
    if txt != 'Initial Negative Title':
        print(f'MUTATED:{txt}')
        sys.stdout.flush()
        for _ in range(30):
            win32gui.PumpWaitingMessages()
            time.sleep(0.1)
        break
    time.sleep(0.05)
"""
        with IsolatedDesktopSandbox() as sandbox:
            proc = sandbox.spawn_process([sys.executable, "-c", child_app_code])
            line = proc.stdout.readline().strip()
            target_hwnd = int(line.split(":")[1])
            pid = proc.pid

            # Cố tình đưa vào kỳ vọng SAI lệch không bao giờ xảy ra
            wrong_expected_title = "Totally Different NonExistent Title"
            result = _run_in_desktop(sandbox, {
                "op": "actuator",
                "hwnd": target_hwnd,
                "pid": pid,
                "action": "click",
                "allow_python": True,
                "execution_mode": "background_message",
                "expected_postcondition": f"expected_title:{wrong_expected_title}",
            })

            # Dispatch thông điệp: thông điệp đến HWND nhưng Verifier phát hiện Expected Effect không khớp!
            assert result["status"] == "failed", result
            assert "FAIL_CLOSED_UNVERIFIED" in result["msg"]
            evidence = result["evidence"]
            assert evidence["receipt"]["delivery_status"] == "delivered_unverified"
            assert evidence["receipt"]["postcondition_verified"] is False

            # Chứng minh mutation THỰC SỰ xảy ra: đây là negative test thật, không phải click trượt
            observed = _run_in_desktop(sandbox, {"op": "read_window", "hwnd": target_hwnd})
            assert observed["window"]["title"] == "Actual Mutation Title"

    def test_09_job_object_kernel_cleanup_and_terminate_all(self):
        """[JOB OBJECT KERNEL GUARD]: Windows Job Object tự động tiêu diệt tiến trình con ở cấp Kernel khi đóng Sandbox."""
        sandbox = IsolatedDesktopSandbox()
        sandbox.create()
        assert sandbox.h_job is not None, "Windows Job Object phải được khởi tạo thành công"

        # Spawn một worker chạy sleep dài hạn
        proc = sandbox.spawn_process([sys.executable, "-c", "import time; time.sleep(100)"])
        assert proc.poll() is None, "Tiến trình worker phải đang chạy"

        # Đóng sandbox -> Windows Kernel tự động trigger JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
        sandbox.close()
        time.sleep(0.5)
        assert proc.poll() is not None, "Tiến trình worker bắt buộc phải bị tiêu diệt bởi Windows Kernel"
        assert sandbox.h_job is None

    def test_10_job_object_grandchild_containment(self):
        """[GRANDCHILD CONTAINMENT]: Windows Kernel tự động tiêu diệt cả tiến trình con và cháu thuộc Job Object khi đóng Sandbox."""
        import psutil
        with IsolatedDesktopSandbox() as sandbox:
            code = """
import subprocess, sys, time
p = subprocess.Popen([sys.executable, '-c', 'import time; time.sleep(100)'])
print(f'GRANDCHILD:{p.pid}', flush=True)
time.sleep(100)
"""
            proc = sandbox.spawn_process([sys.executable, "-c", code])
            line = proc.stdout.readline().strip()
            assert line.startswith("GRANDCHILD:"), f"Expected grandchild line, got {line}"
            grandchild_pid = int(line.split(":")[1])

            # Cả hai tiến trình đều đang sống
            assert psutil.pid_exists(proc.pid)
            assert psutil.pid_exists(grandchild_pid)

        # Sau khi sandbox thoát (đóng Job Object) -> CẢ CON VÀ CHÁU BỊ DIỆT
        for _ in range(30):
            if not psutil.pid_exists(proc.pid):
                break
            time.sleep(0.1)
        assert not psutil.pid_exists(proc.pid), "Process con phải bị Kernel tiêu diệt"
        gc_alive = False
        try:
            p = psutil.Process(grandchild_pid)
            gc_alive = p.is_running() and p.status() != psutil.STATUS_ZOMBIE
        except Exception:
            gc_alive = False
        assert not gc_alive, "Process cháu bắt buộc phải bị tiêu diệt bởi Kernel Job Containment"

    def test_11_job_object_assignment_failure_fails_closed(self, monkeypatch):
        """[JOB ASSIGNMENT FAIL-CLOSED]: Nếu không thể gán tiến trình vào Job Object, lập tức tiêu diệt và từ chối spawn."""
        import win32job
        def mock_assign_fail(job, proc_h):
            raise OSError(5, "Access is denied (Mock Failure)")

        monkeypatch.setattr(win32job, "AssignProcessToJobObject", mock_assign_fail)

        sandbox = IsolatedDesktopSandbox()
        sandbox.create()

        with pytest.raises(RuntimeError, match="JOB_ASSIGNMENT_FAILED"):
            sandbox.spawn_process([sys.executable, "-c", "import time; time.sleep(50)"])

        # Không có tiến trình nào được phép tồn tại ngoài Job Object
        sandbox.close()

    def test_12_job_object_emergency_terminate_all(self):
        """[EMERGENCY TERMINATE]: Hard kill tức thì toàn bộ tiến trình qua TerminateJobObject."""
        sandbox = IsolatedDesktopSandbox()
        sandbox.create()

        proc = sandbox.spawn_process([sys.executable, "-c", "import time; time.sleep(100)"])
        assert proc.poll() is None

        # Kích hoạt Emergency Hard Kill
        sandbox.terminate_all_now()
        for _ in range(30):
            if proc.poll() is not None:
                break
            time.sleep(0.1)

        assert proc.poll() is not None, "Tiến trình phải bị hard kill bởi TerminateJobObject"
        sandbox.close()

    def test_13_job_object_active_process_limit_enforced(self):
        """[RESOURCE LIMIT ENFORCEMENT]: Windows Kernel từ chối spawn tiến trình khi vượt quá ActiveProcessLimit (Quota 1816)."""
        # Khởi tạo sandbox chỉ cho phép tối đa 2 tiến trình hoạt động đồng thời
        sandbox = IsolatedDesktopSandbox(max_active_processes=2)
        sandbox.create()

        p1 = sandbox.spawn_process([sys.executable, "-c", "import time; time.sleep(50)"])
        p2 = sandbox.spawn_process([sys.executable, "-c", "import time; time.sleep(50)"])
        assert p1.poll() is None
        assert p2.poll() is None

        # Tiến trình thứ 3 bắt buộc phải bị Kernel từ chối (Quota 1816) và Sandbox thực thi Fail-Closed
        with pytest.raises(RuntimeError, match="JOB_ASSIGNMENT_FAILED"):
            sandbox.spawn_process([sys.executable, "-c", "import time; time.sleep(50)"])

        stats = sandbox.get_job_stats()
        assert stats["active"] is True
        assert stats["active_processes"] <= 2, "Số lượng active processes không được vượt quá quota 2"

        sandbox.close()

    def test_14_job_object_creation_failure_fails_closed(self, monkeypatch):
        """[JOB CREATION FAIL-CLOSED]: Nếu không thể khởi tạo Job Object, đóng Desktop ngay và từ chối kích hoạt Sandbox."""
        import win32job
        def mock_create_fail(sec, name):
            raise OSError(5, "Access is denied (Mock Job Creation Failure)")

        monkeypatch.setattr(win32job, "CreateJobObject", mock_create_fail)

        sandbox = IsolatedDesktopSandbox(enable_job_object=True)
        with pytest.raises(RuntimeError, match="JOB_OBJECT_CREATION_FAILED"):
            sandbox.create()

        # Fail-closed: Desktop phải bị đóng và không được ở trạng thái active
        assert sandbox._is_active is False
        assert sandbox.h_desktop is None

    def test_15_job_handle_cleanup_on_configuration_failure(self, monkeypatch):
        """[HANDLE CLEANUP ON CONFIG FAILURE]: Đóng cả Job Handle lẫn Desktop Handle khi cấu hình SetInformationJobObject thất bại (No Kernel Leak)."""
        import win32api, win32job
        closed_job_handles = []
        real_close = win32api.CloseHandle

        def spy_close_handle(handle):
            closed_job_handles.append(handle)
            return real_close(handle)

        monkeypatch.setattr(win32api, "CloseHandle", spy_close_handle)

        def mock_set_info_fail(job, info_class, info):
            raise OSError(87, "The parameter is incorrect (Mock Config Failure)")

        monkeypatch.setattr(win32job, "SetInformationJobObject", mock_set_info_fail)

        sandbox = IsolatedDesktopSandbox(enable_job_object=True)
        with pytest.raises(RuntimeError, match="JOB_OBJECT_CREATION_FAILED"):
            sandbox.create()

        # Xác minh toàn vẹn: Không rò rỉ desktop handle, không rò rỉ job handle
        assert sandbox._is_active is False
        assert sandbox.h_job is None
        assert sandbox.h_desktop is None
        assert len(closed_job_handles) > 0, "Job Handle bắt buộc phải được đóng giải phóng tài nguyên Kernel"

    def test_16_zero_race_suspended_process_assignment(self):
        """[ZERO-RACE ASSIGNMENT]: Tiến trình được spawn ở trạng thái SUSPENDED, gán vào Job Object trước khi chạy bất kỳ mã nào."""
        import psutil
        with IsolatedDesktopSandbox(enable_job_object=True) as sandbox:
            code = """
import time, sys
print('STARTED_INSIDE_JOB', flush=True)
time.sleep(50)
"""
            proc = sandbox.spawn_process([sys.executable, "-c", code])
            # Đọc output sau khi đã được resume an toàn
            line = proc.stdout.readline().strip()
            assert line == "STARTED_INSIDE_JOB", f"Output phải là STARTED_INSIDE_JOB, got {line}"

            stats = sandbox.get_job_stats()
            assert stats["active"] is True
            assert stats["active_processes"] >= 1

        # Khi sandbox đóng, tiến trình con bị Kernel kill ngay lập tức
        for _ in range(30):
            if not psutil.pid_exists(proc.pid):
                break
            time.sleep(0.1)
        assert not psutil.pid_exists(proc.pid), "Process phải bị tiêu diệt sạch sẽ khi sandbox đóng"

    def test_17_resume_process_failure_fails_closed(self, monkeypatch):
        """[RESUME FAIL-CLOSED]: Nếu NtResumeProcess trả về NTSTATUS != 0, tiến trình bị tiêu diệt ngay lập tức và từ chối spawn."""
        import ctypes
        def mock_resume_fail(handle):
            # Giả lập NTSTATUS STATUS_ACCESS_DENIED = 0xC0000022
            return 0xC0000022

        monkeypatch.setattr(ctypes.windll.ntdll, "NtResumeProcess", mock_resume_fail)

        sandbox = IsolatedDesktopSandbox(enable_job_object=True)
        sandbox.create()

        with pytest.raises(RuntimeError, match="PROCESS_RESUME_FAILED"):
            sandbox.spawn_process([sys.executable, "-c", "import time; time.sleep(50)"])

        # Xác minh fail-closed: Không có tiến trình nào được đưa vào danh sách spawned_processes
        assert len(sandbox.spawned_processes) == 0, "Tiến trình lỗi resume không được phép lưu trong spawned_processes"
        sandbox.close()

    def test_18_job_object_memory_limit_enforced(self):
        """[MEMORY QUOTA ENFORCEMENT]: Windows Kernel từ chối cấp phát bộ nhớ vượt quá JobMemoryLimit (50MB vs 150MB).
        Chứng minh nguyên nhân trực tiếp từ Kernel Job Object qua cả Win32 VirtualAlloc (ERROR_COMMITMENT_LIMIT 1455)
        lẫn Python MemoryError và Job Object stats."""
        # 1. Khởi tạo sandbox với giới hạn bộ nhớ 50MB
        sandbox = IsolatedDesktopSandbox(enable_job_object=True, memory_limit_mb=50)
        sandbox.create()

        # Kiểm tra cấu hình Job Object qua QueryInformationJobObject
        stats = sandbox.get_job_stats()
        assert stats["active"] is True
        assert stats["job_memory_limit"] == 50 * 1024 * 1024

        # 2. Causal attribution cấp Kernel: Gọi trực tiếp VirtualAlloc commit 150MB
        # Windows Kernel Job Object bắt buộc trả về NULL (0) với LastError = 1455 (ERROR_COMMITMENT_LIMIT) hoặc 1816
        va_code = """import ctypes, sys
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
size = 150 * 1024 * 1024
ptr = ctypes.windll.kernel32.VirtualAlloc(0, size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
err = ctypes.GetLastError()
print(f'VA_PTR:{ptr},VA_ERR:{err}', flush=True)
sys.exit(42 if ptr == 0 and err in (1455, 1816) else 0)
"""
        proc_va = sandbox.spawn_process([sys.executable, "-c", va_code])
        out_va, err_va = proc_va.communicate(timeout=5)
        assert "VA_PTR:0" in out_va, f"VirtualAlloc phải trả về NULL khi vượt JobMemoryLimit, out: {out_va}"
        assert ("VA_ERR:1455" in out_va or "VA_ERR:1816" in out_va), f"Lỗi Win32 phải là ERROR_COMMITMENT_LIMIT(1455) hoặc ERROR_NOT_ENOUGH_QUOTA(1816), out: {out_va}"
        assert proc_va.returncode == 42, f"Mã thoát phải là 42 (xác nhận lỗi quota kernel), nhận được: {proc_va.returncode}"
        sandbox.cleanup_finished_processes()

        # 3. Positive control: Cấp phát 10MB (nằm an toàn trong quota 50MB) phải thành công
        va_ok_code = """import ctypes, sys
MEM_COMMIT = 0x1000
MEM_RESERVE = 0x2000
PAGE_READWRITE = 0x04
size = 2 * 1024 * 1024
ptr = ctypes.windll.kernel32.VirtualAlloc(0, size, MEM_COMMIT | MEM_RESERVE, PAGE_READWRITE)
sys.exit(0 if ptr != 0 else 99)
"""
        proc_ok = sandbox.spawn_process([sys.executable, "-c", va_ok_code])
        proc_ok.communicate(timeout=5)
        assert proc_ok.returncode == 0, "Cấp phát trong quota phải thành công"

        # 4. Tác động lên Runtime Python: bytearray(150MB) phải ném MemoryError rõ ràng trong stderr
        py_code = "b = bytearray(150 * 1024 * 1024)"
        proc_py = sandbox.spawn_process([sys.executable, "-c", py_code])
        out_py, err_py = proc_py.communicate(timeout=5)
        assert proc_py.returncode is not None and proc_py.returncode != 0, "Tiến trình Python phải kết thúc bất thường"
        assert "MemoryError" in err_py, f"stderr phải chứa rõ ràng MemoryError, nhận được: {err_py}"

        sandbox.close()

    def test_19_end_to_end_text_input_with_observed_text_mutation(self):
        """[END-TO-END TEXT INPUT]: Actuator nhập liệu văn bản vào Edit Control, Gateway Verifier xác thực đúng expected_text."""
        child_app_code = """
import sys, time, win32gui, win32con

wc = win32gui.WNDCLASS()
wc.lpfnWndProc = win32gui.DefWindowProc
wc.lpszClassName = 'JKAI_Edit_Host_Class'
win32gui.RegisterClass(wc)

hwnd_parent = win32gui.CreateWindow('JKAI_Edit_Host_Class', 'Edit Host Window', win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE, 100, 100, 400, 300, 0, 0, 0, None)
hwnd_edit = win32gui.CreateWindow('edit', '', win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_BORDER, 10, 10, 300, 30, hwnd_parent, 1001, 0, None)
print(f'HWND_EDIT:{hwnd_edit}', flush=True)

for _ in range(100):
    win32gui.PumpWaitingMessages()
    txt = win32gui.GetWindowText(hwnd_edit)
    if txt == 'JKAI Text Input Verified':
        print('TEXT_MUTATED_SUCCESS', flush=True)
        for _ in range(30):
            win32gui.PumpWaitingMessages()
            time.sleep(0.1)
        break
    time.sleep(0.05)
"""
        with IsolatedDesktopSandbox() as sandbox:
            proc = sandbox.spawn_process([sys.executable, "-c", child_app_code])
            line = proc.stdout.readline().strip()
            assert line.startswith("HWND_EDIT:"), f"Expected HWND_EDIT, got '{line}'"
            target_edit_hwnd = int(line.split(":")[1])
            pid = proc.pid

            expected_content = "JKAI Text Input Verified"
            result = _run_in_desktop(sandbox, {
                "op": "actuator",
                "hwnd": target_edit_hwnd,
                "pid": pid,
                "action": "type",
                "text": expected_content,
                "allow_python": True,
                "execution_mode": "background_message",
                "expected_postcondition": f"expected_text:{expected_content}",
            })
            assert result["status"] == "success", result
            evidence = result["evidence"]
            assert evidence["verifier_result"] is True
            assert evidence["receipt"]["delivery_status"] == "delivered_verified"
            assert evidence["receipt"]["action"] == "type_text"

            # Xác thực độc lập nội dung ô Edit từ trong desktop cô lập qua SendMessageW WM_GETTEXT
            observed = _run_in_desktop(sandbox, {"op": "get_text", "hwnd": target_edit_hwnd})
            assert observed["text"] == expected_content, f"Nội dung ô Edit phải khớp kỳ vọng, got '{observed['text']}'"

    def test_20_text_input_negative_mismatch_fails_closed(self):
        """[NEGATIVE TEXT INPUT]: Nhập văn bản vào Edit control nhưng token kỳ vọng nội dung khác -> Fail-Closed."""
        child_app_code = """
import sys, time, win32gui, win32con

wc = win32gui.WNDCLASS()
wc.lpfnWndProc = win32gui.DefWindowProc
wc.lpszClassName = 'JKAI_Edit_Host_Class_Neg'
win32gui.RegisterClass(wc)

hwnd_parent = win32gui.CreateWindow('JKAI_Edit_Host_Class_Neg', 'Edit Host Window Neg', win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE, 100, 100, 400, 300, 0, 0, 0, None)
hwnd_edit = win32gui.CreateWindow('edit', '', win32con.WS_CHILD | win32con.WS_VISIBLE | win32con.WS_BORDER, 10, 10, 300, 30, hwnd_parent, 1001, 0, None)
print(f'HWND_EDIT:{hwnd_edit}', flush=True)

for _ in range(100):
    win32gui.PumpWaitingMessages()
    time.sleep(0.05)
"""
        with IsolatedDesktopSandbox() as sandbox:
            proc = sandbox.spawn_process([sys.executable, "-c", child_app_code])
            line = proc.stdout.readline().strip()
            target_edit_hwnd = int(line.split(":")[1])
            pid = proc.pid

            # Cố tình đưa vào kỳ vọng sai lệch
            wrong_expected_text = "Completely Different Unmatched String"
            result = _run_in_desktop(sandbox, {
                "op": "actuator",
                "hwnd": target_edit_hwnd,
                "pid": pid,
                "action": "type",
                "text": "Actual Text Sent",
                "allow_python": True,
                "execution_mode": "background_message",
                "expected_postcondition": f"expected_text:{wrong_expected_text}",
            })

            assert result["status"] == "failed", result
            assert "FAIL_CLOSED_UNVERIFIED" in result["msg"]
            evidence = result["evidence"]
            assert evidence["receipt"]["delivery_status"] == "delivered_unverified"
            assert evidence["receipt"]["postcondition_verified"] is False

            # Chứng minh text THỰC SỰ đã được gửi: verify trượt vì kỳ vọng sai, không phải vì input rỗng
            observed = _run_in_desktop(sandbox, {"op": "get_text", "hwnd": target_edit_hwnd})
            assert observed["text"] == "Actual Text Sent"

    def test_21_native_com_uia3_tree_inspection(self):
        """[UIA3 COM TREE INSPECTION]: Bóc tách cây phần tử trợ năng thực địa qua COM Native IUIAutomation (UIAutomationCore.dll)."""
        from services.ai_desktop.uia_tree_inspector import UIATreeInspector
        import win32gui, win32con, time

        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = win32gui.DefWindowProc
        wc.lpszClassName = 'JKAI_UIA3_Live_Test_Class'
        try:
            win32gui.RegisterClass(wc)
        except Exception:
            pass

        hwnd = win32gui.CreateWindow(
            'JKAI_UIA3_Live_Test_Class',
            'JKAI UIA3 Test Window',
            win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE,
            100, 100, 400, 300, 0, 0, 0, None
        )
        assert hwnd != 0, "Phải tạo được cửa sổ test"
        btn = win32gui.CreateWindow('BUTTON', 'Confirm Order', win32con.WS_CHILD | win32con.WS_VISIBLE, 20, 20, 120, 30, hwnd, 201, 0, None)
        edit = win32gui.CreateWindow('EDIT', 'Customer Address', win32con.WS_CHILD | win32con.WS_VISIBLE, 20, 70, 200, 30, hwnd, 202, 0, None)

        for _ in range(5):
            win32gui.PumpWaitingMessages()
            time.sleep(0.01)

        try:
            inspector = UIATreeInspector(is_live_mode=True)
            snap = inspector.inspect_tree(hwnd)

            assert snap.hwnd == hwnd
            assert snap.engine == "NATIVE_COM_UIA3", f"Engine phải là NATIVE_COM_UIA3, nhận được: {snap.engine}"
            assert snap.element_count >= 2, f"Phải tìm thấy ít nhất 2 phần tử UIA, nhận được: {snap.element_count}"
            assert snap.snapshot_hash.startswith("sha256_"), "Snapshot hash phải có định dạng sha256_"

            # Kiểm tra phần tử Button
            btn_node = next((el for el in snap.elements if el.name == "Confirm Order" or el.control_type == "Button"), None)
            assert btn_node is not None, "Phải tìm thấy phần tử Button trong cây UIA"
            assert "InvokePattern" in btn_node.supported_patterns

            # Kiểm tra phần tử Edit
            edit_node = next((el for el in snap.elements if el.control_type == "Edit"), None)
            assert edit_node is not None, "Phải tìm thấy phần tử Edit trong cây UIA"
            assert "ValuePattern" in edit_node.supported_patterns
        finally:
            win32gui.DestroyWindow(hwnd)

    def test_22_native_com_uia3_in_isolated_desktop_sandbox(self):
        """[UIA3 IN ISOLATED DESKTOP]: Bóc tách cây phần tử trợ năng native qua IUIAutomation bên trong IsolatedDesktopSandbox."""
        sandbox = IsolatedDesktopSandbox(enable_job_object=True)
        sandbox.create()

        child_code = '''
import sys, time, win32gui, win32con
wc = win32gui.WNDCLASS()
wc.lpfnWndProc = win32gui.DefWindowProc
wc.lpszClassName = 'JKAI_Isolated_UIA_Class_22'
win32gui.RegisterClass(wc)
hwnd = win32gui.CreateWindow('JKAI_Isolated_UIA_Class_22', 'Isolated UIA Host 22', win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE, 100, 100, 400, 300, 0, 0, 0, None)
btn = win32gui.CreateWindow('BUTTON', 'Sandbox Button 22', win32con.WS_CHILD | win32con.WS_VISIBLE, 20, 20, 120, 30, hwnd, 301, 0, None)
edit = win32gui.CreateWindow('EDIT', 'Sandbox Edit 22', win32con.WS_CHILD | win32con.WS_VISIBLE, 20, 70, 200, 30, hwnd, 302, 0, None)
print(f'HWND:{hwnd}', flush=True)
for _ in range(200):
    win32gui.PumpWaitingMessages()
    time.sleep(0.02)
'''

        try:
            proc = sandbox.spawn_process([sys.executable, "-c", child_code])
            hwnd = None
            for _ in range(50):
                line = proc.stdout.readline()
                if "HWND:" in line:
                    hwnd = int(line.strip().split(":")[1])
                    break
                time.sleep(0.1)

            assert hwnd is not None, "Phải lấy được HWND của cửa sổ trong isolated desktop"

            # UIA COM cũng bị giới hạn theo desktop: phải bóc cây từ trong desktop cô lập.
            snap = _run_in_desktop(sandbox, {"op": "uia", "hwnd": hwnd})

            assert snap["hwnd"] == hwnd
            assert snap["engine"] == "NATIVE_COM_UIA3", f"Engine phải là NATIVE_COM_UIA3 trong isolated desktop, nhận: {snap['engine']}"
            assert snap["element_count"] >= 2, f"Phải tìm thấy ít nhất 2 phần tử trong isolated desktop, nhận: {snap['element_count']}"
            assert snap["snapshot_hash"].startswith("sha256_"), "Snapshot hash phải có định dạng sha256_"

            btn_node = next(
                (el for el in snap["elements"] if el["name"] == "Sandbox Button 22" or el["control_type"] == "Button"),
                None,
            )
            assert btn_node is not None, "Phải tìm thấy Button trong isolated desktop"
            assert "InvokePattern" in btn_node["supported_patterns"], "Button phải hỗ trợ InvokePattern qua GetCurrentPattern"

            edit_node = next((el for el in snap["elements"] if el["control_type"] == "Edit"), None)
            assert edit_node is not None, "Phải tìm thấy Edit trong isolated desktop"
            assert "ValuePattern" in edit_node["supported_patterns"], "Edit phải hỗ trợ ValuePattern qua GetCurrentPattern"
        finally:
            sandbox.close()

    def test_23_uia_com_unavailable_fallback(self):
        """[UIA FALLBACK SURVIVAL]: Khi COM UIA không khả dụng hoặc bị cưỡng bức, hệ thống tự động fallback 100% về WIN32_ACCESSIBILITY_FALLBACK."""
        from services.ai_desktop.uia_tree_inspector import UIATreeInspector
        import win32gui, win32con, time

        wc = win32gui.WNDCLASS()
        wc.lpfnWndProc = win32gui.DefWindowProc
        wc.lpszClassName = 'JKAI_Fallback_Test_Class'
        try:
            win32gui.RegisterClass(wc)
        except Exception:
            pass

        hwnd = win32gui.CreateWindow('JKAI_Fallback_Test_Class', 'Fallback Test Window', win32con.WS_OVERLAPPEDWINDOW | win32con.WS_VISIBLE, 100, 100, 400, 300, 0, 0, 0, None)
        btn = win32gui.CreateWindow('BUTTON', 'Fallback Button', win32con.WS_CHILD | win32con.WS_VISIBLE, 20, 20, 100, 30, hwnd, 401, 0, None)
        for _ in range(5):
            win32gui.PumpWaitingMessages()
            time.sleep(0.01)

        try:
            # Khởi tạo với force_fallback=True giả lập tình huống COM UIA3 không khả dụng
            inspector = UIATreeInspector(is_live_mode=True, force_fallback=True)
            snap = inspector.inspect_tree(hwnd)

            assert snap.hwnd == hwnd
            assert snap.engine == "WIN32_ACCESSIBILITY_FALLBACK", f"Engine phải fallback về WIN32_ACCESSIBILITY_FALLBACK, nhận: {snap.engine}"
            assert snap.element_count >= 1, "Fallback engine phải bóc tách được ít nhất 1 control con"
            assert snap.snapshot_hash.startswith("sha256_"), "Fallback engine phải sinh snapshot hash sha256_"
        finally:
            win32gui.DestroyWindow(hwnd)

    def test_24_live_killed_process_handle_cleanup_on_close(self):
        """[HANDLE CLEANUP ON CLOSE]: Khi sandbox.close() kích hoạt Job Object Auto-Kill, toàn bộ OS pipes (stdout, stderr) và process handles của tiến trình đang chạy đều được thu hồi 100%."""
        import sys, time

        sandbox = IsolatedDesktopSandbox(enable_job_object=True)
        sandbox.create()

        proc = sandbox.spawn_process([sys.executable, "-c", "import time; time.sleep(30)"])
        time.sleep(0.1)
        assert proc.poll() is None, "Tiến trình phải đang chạy trước khi close"

        # Đóng sandbox: Job Object kill tiến trình và cleanup toàn bộ handles
        sandbox.close()

        assert proc.poll() is not None, "Tiến trình phải bị tiêu diệt sau khi close"
        assert proc.stdout.closed is True, "stdout pipe phải được đóng triệt để"
        assert proc.stderr.closed is True, "stderr pipe phải được đóng triệt để"
        assert len(sandbox.spawned_processes) == 0, "Danh sách tiến trình quản lý phải được dọn sạch hoàn toàn"

    def test_25_child_process_is_bound_to_sandbox_desktop(self):
        """[LP DESKTOP BINDING REGRESSION]: Tiến trình con phải thực sự chạy trên desktop cô lập, không rơi về Default."""
        code = """
import ctypes
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32
h_desk = user32.GetThreadDesktop(kernel32.GetCurrentThreadId())
buf = ctypes.create_unicode_buffer(256)
needed = wintypes.DWORD()
user32.GetUserObjectInformationW(h_desk, 2, buf, ctypes.sizeof(buf), ctypes.byref(needed))
print(f'DESKTOP_NAME:{buf.value}', flush=True)
"""
        with IsolatedDesktopSandbox() as sandbox:
            proc = sandbox.spawn_process([sys.executable, "-c", code])
            line = proc.stdout.readline().strip()
            assert line.startswith("DESKTOP_NAME:"), f"Expected DESKTOP_NAME line, got '{line}'"
            observed_desktop = line.split(":", 1)[1]
            assert observed_desktop == sandbox.desktop_name, (
                f"Tiến trình con phải chạy trên '{sandbox.desktop_name}', nhận '{observed_desktop}'. "
                "subprocess.STARTUPINFO không có lpDesktop; phải dùng CreateProcess + STARTUPINFO.lpDesktop."
            )
