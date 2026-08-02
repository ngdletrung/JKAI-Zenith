import os
import json
import time
import asyncio
from .redis_client import redis_safe

class SovereignGuard:
    """
    🏛️ JKAI ZENITH: VỆ BINH CHỦ QUYỀN (SOVEREIGN GUARD v2.0)
    Giao thức Chuẩn hóa Nhất thể: Nguồn sự thật duy nhất cho mọi tiến trình dừng và thỉnh lệnh.
    
    Hai chế độ phê duyệt:
    - ensure_approval(): HITL real-time — block và chờ Master phê duyệt ngay (cho tác vụ đang chạy)
    - submit_proposal(): Async proposal — lưu vào Tab Kế Hoạch, không block (cho module chạy ngầm)
    """
    
    def __init__(self, service_name: str):
        self.service_name = service_name
        self.redis_host = os.getenv("REDIS_HOST", "redis-ai")

    def _log(self, tag: str, msg: str, task_id: str = "system"):
        """Phát tín hiệu chuẩn hóa."""
        try:
            log_payload = json.dumps({
                "tag": tag, 
                "msg": msg, 
                "ts": time.time(),
                "task_id": task_id
            }, ensure_ascii=False)
            redis_safe(lambda r: r.publish("monitor:log_channel", log_payload))
        except Exception: pass

    def _remove_proposal_from_redis(self, proposal_id: str):
        """Xóa proposal khỏi Redis list zenith:proposals khi đã resolved."""
        try:
            raw = redis_safe(lambda r: r.lrange("zenith:proposals", 0, 99), [])
            updated = []
            for item in raw:
                try:
                    p = json.loads(item)
                    if p.get("id") != proposal_id:
                        updated.append(item)
                except Exception:
                    pass
            redis_safe(lambda r: r.delete("zenith:proposals"))
            for item in updated:
                redis_safe(lambda r: r.rpush("zenith:proposals", item))
            # Thông báo frontend xóa proposal khỏi UI
            redis_safe(lambda r: r.publish(
                "monitor:proposal_channel",
                json.dumps({"event": "proposal_resolved", "proposal_id": proposal_id})
            ))
        except Exception:
            pass

    async def ensure_approval(self, task_id: str, action_desc: str, is_core: bool = False, req_type: str = None) -> bool:
        """
        🛡️ GIAO THỨC PHÊ DUYỆT NHẤT THỂ:
        Dừng mọi tiến trình và đợi lệnh từ Master.
        ĐỒNG THỜI niêm yết lên Tab Kế Hoạch để Master thấy badge thông báo.
        """
        if not task_id or task_id == "unknown":
            return False

        proposal_id = f"hitl_{task_id}_{int(time.time()*1000)}"
        approval_key = f"hitl_approve:{proposal_id}"
        reject_key = f"hitl_reject:{proposal_id}"
        
        # 📜 1. ĐỊNH NGHĨA LOẠI PHÊ DUYỆT CHUẨN HÓA
        if not req_type:
            final_type = "AUTH_REQUIRED" if is_core else "APPROVE_REQUIRED"
        else:
            final_type = req_type
            
        try:
            payload = {
                "task_id": task_id,
                "proposal_id": proposal_id,
                "service": self.service_name,
                "message": f"[{self.service_name.upper()}]: Master co phe duyet hanh dong: {action_desc} khong a?",
                "is_core": is_core,
                "type": final_type,
                "ts": time.time()
            }
            
            # Đẩy vào hàng chờ HITL popup và phát sóng PubSub
            redis_safe(lambda r: r.hset("hitl_pending", proposal_id, json.dumps(payload, ensure_ascii=False)))
            redis_safe(lambda r: r.publish("monitor:hitl_channel", json.dumps({"event": "hitl_created", "payload": payload}, ensure_ascii=False)))
            
            # 📋 [PLAN BOARD SYNC]: Đồng thời niêm yết lên Tab Kế Hoạch để Master thấy badge
            proposal_payload = {
                "id": proposal_id,
                "task_id": task_id,
                "title": f"[HITL] {action_desc[:80]}",
                "description": f"**Loai:** {final_type}\n**Dich vu:** {self.service_name}\n\n{action_desc}",
                "source_module": self.service_name,
                "proposal_type": "HITL_REALTIME",
                "is_red_zone": is_core or "AUTH" in final_type,
                "execute_goal": action_desc,
                "metadata": {"hitl_proposal_id": proposal_id, "hitl_type": final_type},
                "status": "pending",
                "created_at": time.time()
            }
            redis_safe(lambda r: r.lpush("zenith:proposals", json.dumps(proposal_payload, ensure_ascii=False)))
            redis_safe(lambda r: r.ltrim("zenith:proposals", 0, 99))
            redis_safe(lambda r: r.publish(
                "monitor:proposal_channel",
                json.dumps({"event": "proposal_created", "payload": proposal_payload}, ensure_ascii=False)
            ))
            
            status_msg = f"[{final_type}]: Dang doi Master phe chuan hanh dong tai {self.service_name}..."
            if is_core or "AUTH" in final_type:
                status_msg = f"[CORE-AUTH]: Hanh dong can thiep HAT NHAN. Master vui long nhap MAT MA CHU QUYEN!"
            
            self._log("SECURITY", status_msg, task_id)

            # ⏳ 2. VÒNG LẶP CHỜ ĐỢI NHẤT THỂ
            start_wait = time.time()
            timeout = 1800 # 30 phút chuẩn hóa
            
            while time.time() - start_wait < timeout:
                
                if redis_safe(lambda r: r.get(approval_key) == b'true', False):
                    redis_safe(lambda r: (r.delete(approval_key), r.hdel("hitl_pending", proposal_id)))
                    redis_safe(lambda r: r.publish("monitor:hitl_channel", json.dumps({"event": "hitl_resolved", "proposal_id": proposal_id})))
                    # 📋 Xóa khỏi proposals khi đã approved qua HITL
                    self._remove_proposal_from_redis(proposal_id)
                    self._log("SECURITY", f"[APPROVED]: Y chi cua Master da duoc tiep nhan. Tiep tuc thuc thi...", task_id)
                    return True
                
                # Kiểm tra reject
                if redis_safe(lambda r: r.get(reject_key) == b'true', False):
                    redis_safe(lambda r: (r.delete(reject_key), r.hdel("hitl_pending", proposal_id)))
                    redis_safe(lambda r: r.publish("monitor:hitl_channel", json.dumps({"event": "hitl_resolved", "proposal_id": proposal_id})))
                    self._remove_proposal_from_redis(proposal_id)
                    self._log("SECURITY", f"[REJECTED]: Master da tu choi hanh dong nay.", task_id)
                    return False
                
                await asyncio.sleep(2)
            
            self._log("SECURITY", "[TIMEOUT]: Da qua thoi gian cho phe duyet. Hanh dong bi huy.", task_id)
            redis_safe(lambda r: r.hdel("hitl_pending", proposal_id))
            redis_safe(lambda r: r.publish("monitor:hitl_channel", json.dumps({"event": "hitl_resolved", "proposal_id": proposal_id})))
            # Xóa khỏi proposals khi timeout
            self._remove_proposal_from_redis(proposal_id)
            return False

        except Exception as e:
            self._log("ERROR", f"❌ [GUARD-ERR]: Sự cố tại Vệ binh: {str(e)}", task_id)
            return False

    async def submit_proposal(
        self,
        task_id: str,
        title: str,
        description: str,
        proposal_type: str = "KNOWLEDGE_DISTILL",
        is_red_zone: bool = False,
        execute_goal: str = None,
        metadata: dict = None
    ) -> str:
        """
        📋 [AUTONOMOUS PLAN BOARD]: Gửi đề xuất lên Tab Kế Hoạch để Master xem xét khi rảnh.
        KHÔNG block — trả về ngay sau khi lưu. Master tự quyết định sau.
        
        is_red_zone=True: Can thiệp vào mã nguồn/cấu hình → cần mật khẩu lệnh khi phê duyệt
        execute_goal: Nếu có, khi phê duyệt sẽ chạy goal này qua pipeline chuẩn
        """
        proposal_id = f"prop_{task_id}_{int(time.time()*1000)}"
        
        payload = {
            "id": proposal_id,
            "task_id": task_id,
            "title": title,
            "description": description,
            "source_module": self.service_name,
            "proposal_type": proposal_type,
            "is_red_zone": is_red_zone,
            "execute_goal": execute_goal or description,
            "metadata": metadata or {},
            "status": "pending",
            "created_at": time.time()
        }
        
        try:
            # 💾 Lưu vào Redis list — tồn tại cho đến khi Master xử lý
            redis_safe(lambda r: r.lpush("zenith:proposals", json.dumps(payload, ensure_ascii=False)))
            redis_safe(lambda r: r.ltrim("zenith:proposals", 0, 99))  # Giữ tối đa 100 proposals
            
            # 📡 Phát SocketIO event để frontend cập nhật Tab Kế Hoạch ngay lập tức
            redis_safe(lambda r: r.publish(
                "monitor:proposal_channel",
                json.dumps({"event": "proposal_created", "payload": payload}, ensure_ascii=False)
            ))
            
            self._log(
                "ZENITH",
                f"📋 [PLAN BOARD]: Đề xuất «{title}» đã được niêm yết tại Tab Kế Hoạch. Master xem xét khi rảnh thưa Ngài.",
                task_id
            )
            return proposal_id
        except Exception as e:
            self._log("ERROR", f"❌ [PROPOSAL-ERR]: Không thể lưu đề xuất: {str(e)}", task_id)
            return ""

# 💎 Khởi tạo Vệ binh mặc định
guard = SovereignGuard("Zenith Core")
