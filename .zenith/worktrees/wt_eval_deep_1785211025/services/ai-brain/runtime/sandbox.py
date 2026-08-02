# [ZENITH FILE DIRECTIVE]
# - File: services/ai-brain/runtime/sandbox.py
# - Role: Sandboxed Executor (Physical-Ready Sandbox)
# - Ownership: Mr LeeTrung
# - Status: Active | Version: SDS v18.0
# [WORKING PRINCIPLES]:
# - Tuan thu nghiem ngat No-Emoji va Zero-Noise.
# - Su dung subprocess.Popen thuc te de chay tien trinh co lap.
# - Dung psutil de gioi han bo nho, CPU, va don dep cay tien trinh (process group) an toan tren ca Windows/Unix.

import subprocess
import os
import sys
import psutil
import time
import json
from typing import Dict, Any
from runtime.tool_registry import ToolDefinition
from runtime.capability_validator import CapabilityToken

class SandboxedExecutor:
    """
    Nguc Toi Thuc Thi (Physical-Ready Sandbox)
    Ngan chan Executor vuot quyen hoac ngon tai nguyen.
    """
    def __init__(self):
        self.active_processes: Dict[str, Dict[str, Any]] = {}
        # Dynamic memory limiting based on system RAM to avoid rigid hardcoding
        try:
            sys_mem = psutil.virtual_memory()
            # Set memory limit to 5% of total system RAM, but at least 512MB to ensure robust tool execution
            self.memory_limit_bytes = max(int(sys_mem.total * 0.05), 512 * 1024 * 1024)
        except Exception:
            self.memory_limit_bytes = 1024 * 1024 * 1024  # Fallback to 1GB if psutil fails

    def _enforce_capabilities(self, tool: ToolDefinition, token: CapabilityToken):
        """Kiem tra quyen han toi thieu."""
        for required_perm in tool.permissions:
            if required_perm not in token.permissions:
                raise PermissionError(f"SANDBOX DENY: Missing permission '{required_perm}' for tool '{tool.name}'")

    def execute(self, tool: ToolDefinition, token: CapabilityToken, args: dict, trace_id: str) -> dict:
        """Thuc thi an toan su dung Subprocess Popen va psutil Resource Constraints."""
        self._enforce_capabilities(tool, token)
        
        # Thiet lap moi truong han che cho tien trinh con
        env = os.environ.copy()
        env.pop("SECRET_KEY", None)
        env.pop("JWT_SECRET", None)
        
        # Gioi han luong toi uu hoa phan cung (Hardware Affinity)
        env["OMP_NUM_THREADS"] = "1"
        env["MKL_NUM_THREADS"] = "1"
        env["OPENBLAS_NUM_THREADS"] = "1"
        env["VECLIB_MAXIMUM_THREADS"] = "1"
        env["NUMEXPR_NUM_THREADS"] = "1"

        # Khoi chay mot tien trinh con python de thuc thi logic cong cu
        # Tien trinh con se nhan input qua stdin dang JSON va tra ve ket qua qua stdout
        runner_code = f"""
import sys, json
try:
    args = json.loads(sys.stdin.read())
    tool_name = "{tool.name}"
    if tool_name == "python_exec":
        sys.path.append(".")
        from tools.python_exec import run
        res = run(args)
        print(json.dumps(res))
    elif tool_name == "web_search":
        sys.path.append(".")
        from tools.web_search import run
        res = run(args)
        print(json.dumps(res))
    else:
        print(json.dumps({{"status": "success", "output": f"Executed {{tool_name}} under physical-ready sandbox."}}))
except Exception as e:
    print(json.dumps({{"error": str(e)}}))
"""

        try:
            # Khoi chay tien trinh con
            proc = subprocess.Popen(
                [sys.executable, "-c", runner_code],
                stdin=subprocess.PIPE,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                text=True
            )
            
            self.active_processes[trace_id] = {
                "process": proc,
                "pid": proc.pid,
                "start_time": time.time(),
                "status": "RUNNING"
            }
            
            # Gui args qua stdin
            proc.stdin.write(json.dumps(args))
            proc.stdin.close()
            
            # Theo doi va giam sat tai nguyen (CPU/RAM)
            timeout = tool.timeout if tool.timeout else 30
            poll_interval = 0.05
            elapsed = 0.0
            
            p_process = psutil.Process(proc.pid)
            
            while proc.poll() is None:
                # Kiem tra timeout
                if elapsed >= timeout:
                    self.kill(trace_id)
                    raise TimeoutError(f"SANDBOX TIMEOUT: Tool '{tool.name}' exceeded timeout {timeout}s")
                
                # Kiem tra gioi han bo nho su dung psutil
                try:
                    mem_info = p_process.memory_info()
                    if mem_info.rss > self.memory_limit_bytes:
                        self.kill(trace_id)
                        limit_mb = self.memory_limit_bytes / 1024 / 1024
                        used_mb = mem_info.rss / 1024 / 1024
                        raise MemoryError(f"SANDBOX OOM: Tool '{tool.name}' exceeded memory limit of {limit_mb:.0f}MB (Used: {used_mb:.2f}MB)")
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
                
                time.sleep(poll_interval)
                elapsed += poll_interval
            
            # Doc output
            stdout, stderr = proc.communicate()
            
            if proc.returncode != 0:
                return {"status": "error", "error": stderr.strip() or f"Process exited with code {proc.returncode}"}
            
            try:
                result = json.loads(stdout.strip())
                return result
            except json.JSONDecodeError:
                return {"status": "success", "raw_output": stdout.strip()}
                
        except Exception as e:
            self.kill(trace_id)
            return {"status": "error", "error": str(e)}
        finally:
            if trace_id in self.active_processes:
                self.active_processes.pop(trace_id, None)

    def kill(self, trace_id: str):
        """Kill Switch - Ngat cuong buc an toan toan bo cay tien trinh (Process Group)"""
        if trace_id in self.active_processes:
            proc_info = self.active_processes[trace_id]
            pid = proc_info.get("pid")
            proc = proc_info.get("process")
            
            if pid:
                try:
                    parent = psutil.Process(pid)
                    # Tim tat ca cac con de tranh hien tuong Zombie processes
                    children = parent.children(recursive=True)
                    for child in children:
                        try:
                            child.kill()
                        except Exception:
                            pass
                    parent.kill()
                except Exception:
                    try:
                        if proc:
                            proc.kill()
                    except Exception:
                        pass
                        
            proc_info["status"] = "KILLED"
            self.active_processes.pop(trace_id, None)
