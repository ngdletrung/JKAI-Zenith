from runtime.tool_registry import ToolDefinition
from runtime.capability_validator import CapabilityToken

class SandboxedExecutor:
    """
    🛡️ Ngục Tối Thực Thi (Physical-Ready Sandbox)
    Ngăn chặn Executor vượt quyền hoặc ngốn tài nguyên.
    """
    def __init__(self):
        self.active_processes = {}

    def _enforce_capabilities(self, tool: ToolDefinition, token: CapabilityToken):
        """Kiểm tra quyền hạn tối thiểu."""
        for required_perm in tool.permissions:
            if required_perm not in token.permissions:
                raise PermissionError(f"SANDBOX DENY: Missing permission '{required_perm}' for tool '{tool.name}'")

    def execute(self, tool: ToolDefinition, token: CapabilityToken, args: dict, trace_id: str):
        """Giả lập việc khởi chạy an toàn (Resource Isolation/Syscalls)"""
        self._enforce_capabilities(tool, token)
        
        # TODO: Cắm subprocess/seccomp wrapper tại đây (Phase tương lai)
        self.active_processes[trace_id] = "RUNNING"
        
        return {"status": "success", "simulated_output": f"Executed {tool.name} under Sandbox"}

    def kill(self, trace_id: str):
        """Kill Switch - Ngắt cưỡng bức từ Runtime Scheduler"""
        if trace_id in self.active_processes:
            self.active_processes[trace_id] = "KILLED"
            # TODO: os.kill(pid)
