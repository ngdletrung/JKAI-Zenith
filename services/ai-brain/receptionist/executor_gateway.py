import json
from dataclasses import dataclass
from core.utils.engine import engine

@dataclass(frozen=True)
class ExecutionRequest:
    trace_id: str
    capability_token: dict
    tool_name: str
    tool_args: dict
    timeout: int = 600

class ExecutorGateway:
    """
    🛠️ TẬP ĐOÀN JKAI ZENITH - EXECUTOR GATEWAY
    Giao tiếp an toàn và thực thi lệnh qua Capability Token.
    """
    def __init__(self, http_client):
        self.http_client = http_client

    def _log(self, tag, msg, task_id="manual", stealth=False):
        try:
            enhanced_msg = f"💎🫡 [ZENITH]: {msg}" if tag == "ZENITH" else msg
            engine.publish_mission_log(tag, enhanced_msg, task_id, stealth=stealth)
        except: pass

    async def execute_tool(self, request: ExecutionRequest, task_id: str) -> str:
        """Gọi Executor với Execution Contract chặt chẽ."""
        self._log("EXECUTOR", f"🛠️ Thực thi an toàn: {request.tool_name}(...) - TraceID: {request.trace_id}", task_id)
        try:
            # Truyền Capability Token để xác thực phân quyền ở đầu kia
            from core.utils.registry import registry
            executor_url = registry.get_service_url('executor')
            resp = await self.http_client.post(f"{executor_url}/call_tool", json={
                "name": request.tool_name,
                "args": request.tool_args,
                "task_id": task_id,
                "trace_id": request.trace_id,
                "token": request.capability_token
            }, timeout=request.timeout)
            
            data = resp.json()
            # Xử lý nhu cầu auth từ Executor
            if data.get("status") == "needs_auth":
                return f"⚠️ **[XÁC THỰC CHỦ QUYỀN]**: Thao tác `{request.tool_name}` vào vùng nhạy cảm đã bị chặn. Cần Mật Mã Tối Thượng thưa Master."
            
            return data.get("output", "No output.")
        except Exception as e:
            return f"Error calling executor: {e}"

    async def request_sovereign_auth(self, action: str, params: dict, task_id: str):
        """Kích hoạt Pad xác thực trên giao diện Frontend"""
        payload = {"action": action}
        payload.update(params)
        try:
            from core.utils.registry import registry
            executor_url = registry.get_service_url('executor')
            await self.http_client.post(f"{executor_url}/call_tool", json={
                "name": "request_sovereign_auth",
                "args": payload,
                "task_id": task_id
            })
        except: pass
