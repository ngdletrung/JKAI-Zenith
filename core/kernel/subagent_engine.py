import os
import sys
import uuid
import time
import json
import asyncio
import logging
from typing import Dict, Any

logger = logging.getLogger("SubagentEngine")

class SubagentDefinition:
    def __init__(self, name: str, role: str, system_prompt: str, tools: list = None):
        self.name = name
        self.role = role
        self.system_prompt = system_prompt
        self.tools = tools or []

    def to_dict(self) -> dict:
        return {
            "name": self.name,
            "role": self.role,
            "system_prompt": self.system_prompt,
            "tools": self.tools
        }

from core.kernel.subagent_workspace import subagent_workspace_manager

class SubagentEngine:
    """
    🤖 [SUBAGENT-SWARM-ENGINE]: Hệ thống quản lý vòng đời (Lifecycle), Thực thi Song song và Cô lập Workspace cho Subagents.
    Hỗ trợ: True Parallel Background Task, Workspace Isolation, list_subagents(), kill_subagent(), fetch_inbox(), status.
    """
    def __init__(self):
        self.definitions: Dict[str, SubagentDefinition] = {}
        self.active_tasks: Dict[str, asyncio.Task] = {}
        self.subagent_registry: Dict[str, Dict[str, Any]] = {}
        self.workspace_mgr = subagent_workspace_manager
        self._redis_client = None

    def _get_redis(self):
        if self._redis_client is None:
            try:
                from core.utils.engine import engine
                self._redis_client = engine._get_redis()
            except Exception:
                pass
        return self._redis_client

    def define_subagent(self, name: str, role: str, system_prompt: str, tools: list = None) -> dict:
        """Định nghĩa một chủng loại Subagent chuyên biệt mới."""
        sub_def = SubagentDefinition(name, role, system_prompt, tools)
        self.definitions[name] = sub_def
        r = self._get_redis()
        if r:
            try:
                r.hset("subagent:definitions", name, json.dumps(sub_def.to_dict()))
            except Exception as e:
                logger.warning(f"[SUBAGENT-REDIS-WARN] {e}")

        logger.info(f"🤖 [SUBAGENT-DEFINED]: Đã tạo định nghĩa Subagent `{name}` (Role: {role})")
        return {"status": "success", "name": name, "role": role}

    async def _subagent_worker_loop(self, sub_id: str, sub_def: SubagentDefinition, prompt: str, parent_task_id: str):
        """Worker loop thực thi Subagent bất đồng bộ trong nền (True Background Parallel Task)."""
        self.subagent_registry[sub_id] = {
            "id": sub_id,
            "name": sub_def.name,
            "role": sub_def.role,
            "parent_task_id": parent_task_id,
            "status": "running",
            "start_time": time.time(),
            "result": None
        }
        
        messages = [
            {"role": "system", "content": sub_def.system_prompt},
            {"role": "user", "content": prompt}
        ]

        try:
            from core.utils.engine import engine
            response = await engine.call_chat(messages=messages, role=f"SUBAGENT_{sub_def.name.upper()}", task_id=sub_id)
            self.subagent_registry[sub_id]["status"] = "completed"
            self.subagent_registry[sub_id]["result"] = response
            self.subagent_registry[sub_id]["end_time"] = time.time()
            logger.info(f"✅ [SUBAGENT-SUCCESS]: Subagent `{sub_def.name}` ({sub_id}) hoàn thành nhiệm vụ!")
        except asyncio.CancelledError:
            self.subagent_registry[sub_id]["status"] = "killed"
            logger.warning(f"🛑 [SUBAGENT-KILLED]: Subagent `{sub_id}` đã bị chấm dứt.")
        except Exception as e:
            self.subagent_registry[sub_id]["status"] = "failed"
            self.subagent_registry[sub_id]["error"] = str(e)

    async def invoke_subagent(self, subagent_name: str, prompt: str, parent_task_id: str = "sys", run_in_background: bool = True) -> dict:
        """Khởi chạy Subagent tác chiến song song thực thụ (Parallel Background Swarm)."""
        sub_id = f"sub_{uuid.uuid4().hex[:8]}"
        sub_def = self.definitions.get(subagent_name)

        if not sub_def:
            r = self._get_redis()
            if r:
                raw = r.hget("subagent:definitions", subagent_name)
                if raw:
                    data = json.loads(raw)
                    sub_def = SubagentDefinition(data["name"], data["role"], data["system_prompt"], data.get("tools"))

        if not sub_def:
            return {"status": "error", "msg": f"Subagent `{subagent_name}` chưa được định nghĩa."}

        # Đăng ký tức thì vào Registry kèm Workspace Cô lập
        ws_path = str(self.workspace_mgr.create_workspace(sub_id))
        self.subagent_registry[sub_id] = {
            "id": sub_id,
            "name": sub_def.name,
            "role": sub_def.role,
            "workspace_path": ws_path,
            "parent_task_id": parent_task_id,
            "status": "running",
            "start_time": time.time(),
            "result": None
        }

        # Khởi tạo Task chạy nền song song (True Non-Blocking Background Swarm)
        task = asyncio.create_task(self._subagent_worker_loop(sub_id, sub_def, prompt, parent_task_id))
        self.active_tasks[sub_id] = task

        if not run_in_background:
            await task
            return self.subagent_registry.get(sub_id, {})

        return {
            "status": "launched",
            "subagent_id": sub_id,
            "subagent_name": subagent_name,
            "message": f"Subagent `{subagent_name}` ({sub_id}) đã khởi chạy song song trong nền!"
        }

    def list_subagents(self) -> dict:
        """Liệt kê danh sách toàn bộ Subagents và trạng thái vòng đời."""
        return {"subagents": list(self.subagent_registry.values())}

    def get_status(self, sub_id: str) -> dict:
        """Kiểm tra trạng thái của một Subagent cụ thể."""
        return self.subagent_registry.get(sub_id, {"status": "not_found"})

    def kill_subagent(self, sub_id: str) -> dict:
        """Hủy bỏ và chấm dứt tiến trình Subagent đang chạy."""
        task = self.active_tasks.get(sub_id)
        if task and not task.done():
            task.cancel()
            if sub_id in self.subagent_registry:
                self.subagent_registry[sub_id]["status"] = "killed"
            return {"status": "success", "subagent_id": sub_id, "message": f"Đã hủy Subagent {sub_id}"}
        return {"status": "error", "msg": f"Subagent {sub_id} không hoạt động."}

    def fetch_inbox(self, subagent_id: str, count: int = 10) -> list:
        """Đọc và lấy tin nhắn đến (Inbox) của Subagent từ Redis Stream."""
        r = self._get_redis()
        messages = []
        if r:
            try:
                stream_key = f"stream:subagent:{subagent_id}"
                entries = r.xread({stream_key: "0-0"}, count=count)
                for stream_name, msg_list in entries:
                    for msg_id, msg_data in msg_list:
                        messages.append(msg_data)
            except Exception as e:
                logger.warning(f"[INBOX-READ-ERR] {e}")
        return messages

    def send_message(self, recipient_subagent_id: str, message: str) -> dict:
        """Gửi tin nhắn liên tác tử (Inter-agent messaging) qua Redis Stream."""
        r = self._get_redis()
        if r:
            try:
                r.xadd(f"stream:subagent:{recipient_subagent_id}", {"message": message, "timestamp": str(time.time())})
                return {"status": "sent", "recipient": recipient_subagent_id}
            except Exception as e:
                return {"status": "error", "error": str(e)}
        return {"status": "error", "error": "Redis unavailable"}

subagent_engine = SubagentEngine()
