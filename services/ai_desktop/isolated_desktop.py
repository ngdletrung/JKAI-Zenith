# -*- coding: utf-8 -*-
"""
services/ai_desktop/isolated_desktop.py
[M5-G4/G7] Dedicated Isolated Desktop Sandbox for JKAI Desktop Actuator.
Kế thừa kiến trúc bảo mật từ:
- Windows Desktop Isolation (Win32 CreateDesktop / SetThreadDesktop / CloseDesktop)
- Zero Trust Host Isolation: Cô lập 100% cửa sổ và thông điệp Windows trong Desktop ảo riêng biệt,
  tuyệt đối không đè, chiếm focus hoặc gián đoạn màn hình làm việc của Master.
"""

from __future__ import annotations

import ctypes
from ctypes import wintypes
import logging
import msvcrt
import os
import subprocess
import time
import uuid
from typing import Any, Dict, List, Optional, Tuple

try:
    import win32api
    import win32con
    import win32job
    import win32pipe
    import win32process
    import pywintypes
    HAS_WIN32JOB = True
except ImportError:
    HAS_WIN32JOB = False

logger = logging.getLogger("ai-desktop-sandbox")

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

# Win32 Desktop Access Rights
DESKTOP_CREATEWINDOW = 0x0002
DESKTOP_ENUMERATE = 0x0040
DESKTOP_WRITEOBJECTS = 0x0080
DESKTOP_READOBJECTS = 0x0001
DESKTOP_ALL = 0x01FF


class SandboxProcess:
    """Popen-compatible wrapper around a process started with CreateProcessW.

    Python's subprocess.STARTUPINFO has no lpDesktop field, so processes launched
    through subprocess.Popen always land on the caller's desktop. Everything the
    sandbox starts must go through CreateProcessW with an explicit lpDesktop.
    """

    def __init__(self, h_process, h_thread, pid: int, command, stdout=None, stderr=None):
        self._handle = h_process
        self._thread_handle = h_thread
        self.pid = pid
        self.args = command
        self.stdout = stdout
        self.stderr = stderr
        self._returncode: Optional[int] = None

    def poll(self) -> Optional[int]:
        if self._returncode is not None:
            return self._returncode
        code = win32process.GetExitCodeProcess(self._handle)
        if code == win32con.STILL_ACTIVE:
            return None
        self._returncode = int(code)
        return self._returncode

    @property
    def returncode(self) -> Optional[int]:
        return self.poll()

    def wait(self, timeout: Optional[float] = None) -> int:
        started = time.time()
        while True:
            code = self.poll()
            if code is not None:
                return code
            if timeout is not None and time.time() - started > timeout:
                raise subprocess.TimeoutExpired(self.args, timeout)
            time.sleep(0.02)

    def terminate(self) -> None:
        if self.poll() is None:
            win32api.TerminateProcess(self._handle, 1)

    def kill(self) -> None:
        self.terminate()

    def communicate(self, input: Optional[bytes] = None, timeout: Optional[float] = None):
        if input is not None:
            raise ValueError("SandboxProcess.communicate does not support stdin writes")
        import threading

        captured: Dict[str, str] = {"stdout": "", "stderr": ""}

        def _drain(name: str, stream) -> None:
            try:
                if stream:
                    captured[name] = stream.read()
            except Exception:
                pass

        threads = [
            threading.Thread(target=_drain, args=("stdout", self.stdout), daemon=True),
            threading.Thread(target=_drain, args=("stderr", self.stderr), daemon=True),
        ]
        for thread in threads:
            thread.start()
        self.wait(timeout)
        for thread in threads:
            thread.join(5.0)
        return (
            captured["stdout"] if self.stdout else None,
            captured["stderr"] if self.stderr else None,
        )

    def close_io(self) -> None:
        for stream in (self.stdout, self.stderr):
            try:
                if stream:
                    stream.close()
            except Exception:
                pass

    def close_handles(self) -> None:
        for handle in (self._handle, self._thread_handle):
            try:
                if handle:
                    handle.Close()
            except Exception:
                pass


class IsolatedDesktopSandbox:
    """
    Quản lý vòng đời của một Desktop ảo cô lập (Disposable Windows Desktop).
    Mọi ứng dụng, cửa sổ và thông điệp kiểm thử M5 đều được giam lỏng bên trong Desktop này.
    """

    def __init__(
        self,
        desktop_name: Optional[str] = None,
        enable_job_object: bool = True,
        max_active_processes: int = 16,
        memory_limit_mb: int = 1024,
    ):
        self.desktop_name = desktop_name or f"JKAI_Sandbox_{uuid.uuid4().hex[:8]}"
        self.h_desktop: Optional[int] = None
        self.h_job: Optional[int] = None
        self.enable_job_object = enable_job_object and HAS_WIN32JOB
        self.max_active_processes = max_active_processes
        self.memory_limit_mb = memory_limit_mb
        self.spawned_processes: List[SandboxProcess] = []
        self._is_active = False

    def create(self) -> int:
        """Khởi tạo Desktop ảo cô lập qua Win32 CreateDesktopW."""
        if self._is_active and self.h_desktop:
            return self.h_desktop

        h_desk = user32.CreateDesktopW(
            self.desktop_name,
            None,
            None,
            0,
            DESKTOP_ALL,
            None,
        )
        if not h_desk:
            err = kernel32.GetLastError()
            raise RuntimeError(f"CREATE_DESKTOP_FAILED: Không thể tạo desktop '{self.desktop_name}', Win32 error={err}")

        self.h_desktop = h_desk

        # Khởi tạo Windows Job Object với cờ KILL_ON_JOB_CLOSE & Resource Limits (Kernel Boundary)
        if self.enable_job_object and not self.h_job:
            temp_h_job = None
            try:
                temp_h_job = win32job.CreateJobObject(None, f"JKAI_Job_{self.desktop_name}")
                info = win32job.QueryInformationJobObject(temp_h_job, win32job.JobObjectExtendedLimitInformation)
                limit_flags = win32job.JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE
                if self.max_active_processes > 0:
                    limit_flags |= win32job.JOB_OBJECT_LIMIT_ACTIVE_PROCESS
                    info["BasicLimitInformation"]["ActiveProcessLimit"] = self.max_active_processes
                if self.memory_limit_mb > 0:
                    limit_flags |= win32job.JOB_OBJECT_LIMIT_JOB_MEMORY
                    info["JobMemoryLimit"] = self.memory_limit_mb * 1024 * 1024

                info["BasicLimitInformation"]["LimitFlags"] |= limit_flags
                win32job.SetInformationJobObject(temp_h_job, win32job.JobObjectExtendedLimitInformation, info)
                self.h_job = temp_h_job
                logger.info(f"[DESKTOP-SANDBOX] Đã kích hoạt Windows Job Object (Kernel Guard & Limits: {self.max_active_processes} procs, {self.memory_limit_mb}MB)")
            except Exception as e:
                # [FAIL-CLOSED & HANDLE CLEANUP TOÀN DIỆN]:
                # Đóng cả Job Handle lẫn Desktop Handle khi cấu hình thất bại, ngăn ngừa rò rỉ Kernel Handle
                logger.error(f"[DESKTOP-SANDBOX] FAIL-CLOSED: Khởi tạo/cấu hình Job Object thất bại: {e}. Đóng sạch Job Handle và Desktop ngay!")
                if temp_h_job:
                    try:
                        win32api.CloseHandle(temp_h_job)
                    except Exception:
                        pass
                try:
                    user32.CloseDesktop(h_desk)
                except Exception:
                    pass
                self.h_job = None
                self.h_desktop = None
                self._is_active = False
                raise RuntimeError(f"JOB_OBJECT_CREATION_FAILED: Không thể khởi tạo Job Object Kernel Guard: {e}. Desktop và Job Handle đã được dọn sạch an toàn (Fail-Closed)!")

        self._is_active = True
        logger.info(f"[DESKTOP-SANDBOX] Đã tạo thành công Desktop ảo cô lập '{self.desktop_name}' (Handle: {hex(h_desk)})")
        return h_desk

    @staticmethod
    def _open_reader(handle):
        raw = handle.Detach()
        fd = msvcrt.open_osfhandle(int(raw), os.O_RDONLY | os.O_BINARY)
        return os.fdopen(fd, "r", encoding="utf-8", errors="replace", newline="")

    @staticmethod
    def _close_all(handles: List[Any], readers: List[Any]) -> None:
        for reader in readers:
            try:
                if reader:
                    reader.close()
            except Exception:
                pass
        for handle in handles:
            try:
                if handle:
                    handle.Close()
            except Exception:
                pass

    def spawn_process(
        self,
        command: List[str] | str,
        env: Optional[Dict[str, str]] = None,
        pipe_output: bool = True,
    ) -> SandboxProcess:
        """
        Khởi chạy tiến trình gắn chặt vào Desktop ảo cô lập qua CreateProcessW + lpDesktop.
        Tiến trình này sẽ render GUI hoàn toàn trong desktop ẩn, không chạm màn hình host.
        """
        if not self._is_active:
            self.create()

        cmdline = (
            command if isinstance(command, str)
            else subprocess.list2cmdline([str(part) for part in command])
        )

        inherit_sa = pywintypes.SECURITY_ATTRIBUTES()
        inherit_sa.bInheritHandle = True

        handles: List[Any] = []
        readers: List[Any] = []
        si = win32process.STARTUPINFO()
        si.lpDesktop = self.desktop_name

        if pipe_output:
            si.dwFlags = win32con.STARTF_USESTDHANDLES
            in_r, in_w = win32pipe.CreatePipe(inherit_sa, 0)
            out_r, out_w = win32pipe.CreatePipe(inherit_sa, 0)
            err_r, err_w = win32pipe.CreatePipe(inherit_sa, 0)
            # Only the child-side ends are inheritable; parent-side ends stay private.
            for parent_end in (in_w, out_r, err_r):
                win32api.SetHandleInformation(parent_end, win32con.HANDLE_FLAG_INHERIT, 0)
            si.hStdInput = in_r
            si.hStdOutput = out_w
            si.hStdError = err_w
            handles.extend([in_r, in_w, out_r, out_w, err_r, err_w])

        creation_flags = win32con.CREATE_SUSPENDED if self.h_job else 0
        env_block = None if env is None else {str(k): str(v) for k, v in env.items()}

        try:
            h_process, h_thread, pid, _tid = win32process.CreateProcess(
                None, cmdline, None, None, bool(pipe_output), creation_flags,
                env_block, None, si,
            )
        except Exception as exc:
            self._close_all(handles, readers)
            raise RuntimeError(
                f"PROCESS_SPAWN_FAILED: Không thể khởi chạy '{cmdline}' trên desktop "
                f"'{self.desktop_name}': {exc}"
            ) from exc

        stdout_reader = stderr_reader = None
        if pipe_output:
            # Parent keeps only the read ends; closing the write ends gives the child EOF on stdin.
            for child_end in (in_r, in_w, out_w, err_w):
                try:
                    child_end.Close()
                except Exception:
                    pass
            stdout_reader = self._open_reader(out_r)
            stderr_reader = self._open_reader(err_r)
            readers.extend([stdout_reader, stderr_reader])

        if self.h_job:
            h_proc = None
            try:
                # [QUYỀN TỐI THIỂU]: PROCESS_SET_QUOTA | PROCESS_TERMINATE (0x0101)
                access_mask = win32con.PROCESS_SET_QUOTA | win32con.PROCESS_TERMINATE
                h_proc = win32api.OpenProcess(access_mask, False, pid)
                win32job.AssignProcessToJobObject(self.h_job, h_proc)
                logger.info(f"[DESKTOP-SANDBOX] Gắn PID {pid} vào Job Object thành công trong trạng thái SUSPENDED (Zero-Race) với quyền 0x{access_mask:x}")

                # [FAIL-CLOSED RESUME ENFORCEMENT]:
                # Đánh thức tiến trình sau khi đã nằm an toàn bên trong Job Object.
                resume_status = ctypes.windll.ntdll.NtResumeProcess(int(h_process))
                if resume_status != 0:
                    raise RuntimeError(f"NTSTATUS_ERROR_0x{resume_status & 0xFFFFFFFF:08x}: NtResumeProcess thất bại")
                logger.info(f"[DESKTOP-SANDBOX] Đã đánh thức PID {pid} an toàn sau khi đã thuộc Job Object (NTSTATUS 0x0)")
            except Exception as e:
                # [FAIL-CLOSED BẮT BUỘC]: Nếu gán hoặc resume thất bại, lập tức tiêu diệt tiến trình và reject
                logger.error(f"[DESKTOP-SANDBOX] FAIL-CLOSED: Gán/Resume PID {pid} thất bại: {e}. Tiêu diệt tiến trình ngay!")
                try:
                    win32api.TerminateProcess(h_process, 1)
                except Exception:
                    pass
                self._close_all(handles, readers)
                try:
                    h_process.Close()
                except Exception:
                    pass
                try:
                    h_thread.Close()
                except Exception:
                    pass
                err_type = "PROCESS_RESUME_FAILED" if "NtResumeProcess" in str(e) else "JOB_ASSIGNMENT_FAILED"
                raise RuntimeError(f"{err_type}: Không thể đưa PID {pid} vào hoạt động an toàn: {e}. Tiến trình đã bị tiêu diệt an toàn (Fail-Closed)!")
            finally:
                if h_proc:
                    try:
                        win32api.CloseHandle(h_proc)
                    except Exception:
                        pass

        proc = SandboxProcess(h_process, h_thread, pid, cmdline,
                              stdout=stdout_reader, stderr=stderr_reader)
        self.spawned_processes.append(proc)
        logger.info(f"[DESKTOP-SANDBOX] Đã spawn PID {pid} trong Desktop cô lập '{self.desktop_name}'")
        return proc

    def get_job_stats(self) -> Dict[str, Any]:
        """Đọc thông số kiểm toán tài nguyên hiện tại từ Windows Job Object."""
        if not self.h_job:
            return {"active": False, "reason": "NO_JOB_OBJECT"}
        try:
            basic = win32job.QueryInformationJobObject(self.h_job, win32job.JobObjectBasicAccountingInformation)
            ext = win32job.QueryInformationJobObject(self.h_job, win32job.JobObjectExtendedLimitInformation)
            return {
                "active": True,
                "total_processes": basic.get("TotalProcesses", 0),
                "active_processes": basic.get("ActiveProcesses", 0),
                "total_terminated_processes": basic.get("TotalTerminatedProcesses", 0),
                "job_memory_limit": ext.get("JobMemoryLimit", 0),
                "peak_job_memory_used": ext.get("PeakJobMemoryUsed", 0),
                "peak_process_memory_used": ext.get("PeakProcessMemoryUsed", 0),
            }
        except Exception as e:
            return {"active": True, "error": str(e)}

    def terminate_all_now(self) -> None:
        """Hard kill tức thì toàn bộ tiến trình thuộc Job Object cấp Kernel (Emergency / Timeout Recovery)."""
        if self.h_job:
            try:
                win32job.TerminateJobObject(self.h_job, 1)
                logger.info(f"[DESKTOP-SANDBOX] Đã TerminateJobObject cho '{self.desktop_name}'")
            except Exception as e:
                logger.error(f"[DESKTOP-SANDBOX] Lỗi TerminateJobObject: {e}")
                raise RuntimeError(f"TERMINATE_JOB_FAILED: {e}")

    def cleanup_finished_processes(self) -> int:
        """
        [KERNEL & OS HANDLE HYGIENE]:
        Thu hồi triệt để toàn bộ OS handles (stdout/stderr pipes, process handles)
        của các tiến trình con đã kết thúc để bảo đảm tuyệt đối ZERO HANDLE LEAK.
        """
        active = []
        cleaned_count = 0
        for p in self.spawned_processes:
            if p.poll() is not None:
                cleaned_count += 1
                p.close_io()
                p.close_handles()
            else:
                active.append(p)
        self.spawned_processes = active
        return cleaned_count

    def close(self) -> None:
        """Hủy diệt và dọn dẹp toàn bộ tài nguyên Desktop ảo và tiến trình con."""
        if not self._is_active:
            return

        # 0. Thu hồi toàn bộ OS pipes và process handles đã kết thúc
        self.cleanup_finished_processes()

        # 1. Đóng Job Object: Windows Kernel tự động hủy sạch toàn bộ process con (Kill on Close)
        if self.h_job:
            try:
                win32api.CloseHandle(self.h_job)
                logger.info(f"[DESKTOP-SANDBOX] Đã đóng Job Object (Kernel Auto-Kill)")
            except Exception as e:
                logger.warning(f"[DESKTOP-SANDBOX] Lỗi đóng Job Object: {e}")
            finally:
                self.h_job = None

        # 2. Thu hồi triệt để pipes và process handles cho cả các tiến trình vừa bị Job Object tiêu diệt
        for proc in self.spawned_processes:
            try:
                if proc.poll() is None:
                    proc.terminate()
                    try:
                        proc.wait(timeout=1.0)
                    except subprocess.TimeoutExpired:
                        proc.kill()
            except Exception as e:
                logger.warning(f"[DESKTOP-SANDBOX] Lỗi dọn dẹp PID {proc.pid}: {e}")
            finally:
                proc.close_io()
                proc.close_handles()
        self.spawned_processes.clear()

        # 3. Đóng handle Desktop
        if self.h_desktop:
            try:
                user32.CloseDesktop(self.h_desktop)
                logger.info(f"[DESKTOP-SANDBOX] Đã đóng thành công Desktop ảo '{self.desktop_name}'")
            except Exception as e:
                logger.error(f"[DESKTOP-SANDBOX] Lỗi CloseDesktop: {e}")
            finally:
                self.h_desktop = None

        self._is_active = False

    def __enter__(self) -> "IsolatedDesktopSandbox":
        self.create()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb) -> None:
        self.close()
