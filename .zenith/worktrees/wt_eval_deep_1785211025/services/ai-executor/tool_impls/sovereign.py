import httpx
import os
import json

CONTROL_PLANE_URL = os.getenv("CONTROL_PLANE_URL", "http://ai-control-plane:8000")

async def request_sovereign_auth(action: str, task_id: str):
    """
    Gửi yêu cầu xác thực Chủ quyền tới Control Plane để mở Pad trên Frontend.
    """
    try:
        async with httpx.AsyncClient() as client:
            # Tạo một yêu cầu HITL đặc biệt
            payload = {
                "task_id": f"SOV_{action}_{task_id}",
                "message": f"Yêu cầu xác thực chủ quyền cho hành động: {action}",
                "type": "SOVEREIGN_AUTH",
                "action": action
            }
            # Gửi tới endpoint tạo HITL (giả sử có endpoint này hoặc dùng redis)
            # Ở đây chúng ta đẩy trực tiếp vào Redis hitl_pending để Frontend thấy
            from redis_client import redis_safe
            def _push_hitl(r):
                r.hset("hitl_pending", payload["task_id"], json.dumps(payload, ensure_ascii=False))
                r.publish("monitor:log_channel", json.dumps({
                    "tag": "STEWARD", "msg": f"⚠️ [SECURITY]: Đang chờ Master nhập Mật mã cho {action}...", "task_id": task_id
                }))
            redis_safe(_push_hitl)
            
        return f"Đã gửi yêu cầu xác thực cho {action}. Chờ Master phê duyệt trên bảng điều khiển."
    except Exception as e:
        return f"Lỗi yêu cầu xác thực: {e}"
