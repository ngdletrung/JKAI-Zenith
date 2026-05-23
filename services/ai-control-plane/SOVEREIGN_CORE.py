# =================================================================
# 🏛️ JKAI ZENITH: SOVEREIGN CORE v1.0 (IMMUTABLE DIRECTIVE)
# =================================================================
# ĐỊNH LUẬT SẮT: TỆP TIN NÀY KHÔNG THỂ BỊ CHỈNH SỬA BỞI AI.
# CHỈ MASTER LEETRUNG MỚI CÓ QUYỀN THAY ĐỔI GIAO THỨC NÀY.

import os
import subprocess
import logging
import hashlib
import time

logger = logging.getLogger("jkai.sovereign")

# 🕵️ MÃ BĂM CHỦ QUYỀN (PROTECTED)
MASTER_HASH = "0e94b3de1477fd760e485cf448efbbe3471497d807861eed47ae8295c2f446a2"
# ⛓️ DẤU VÂN TAY PHẦN CỨNG (Sẽ được ghi đè ở lần đầu xác thực)
AUTHORIZED_HWID = "9eff57f30379e3c5b99200d70246cf7a6a0ece5b69e60c614893fde0accb3011"

class SovereignCore:
    def __init__(self, task_manager):
        self.task_manager = task_manager
        self.is_boot_locked = False

    def verify_key(self, provided_key):
        """Xác thực mật mã thông qua cơ chế Băm."""
        return hashlib.sha256(provided_key.encode()).hexdigest() == MASTER_HASH

    def check_hardware_integrity(self):
        """Kiểm tra xem phần cứng hiện tại có khớp với thiết bị đã đăng ký không."""
        from hardware_identity import get_hwid
        if AUTHORIZED_HWID == "INITIAL_UNSET_IDENTITY":
            return "UNREGISTERED"
        current = get_hwid()
        return "MATCH" if current == AUTHORIZED_HWID else "MISMATCH"

    async def register_current_device(self, provided_key):
        """Đăng ký phần cứng hiện tại làm thiết bị chính chủ."""
        if not self.verify_key(provided_key):
            return {"ok": False, "msg": "❌ Mật mã xác thực thiết bị không chính xác!"}
        
        from hardware_identity import get_hwid
        new_hwid = get_hwid()
        try:
            with open(__file__, "r", encoding="utf-8") as f:
                content = f.read()
            new_content = content.replace(f'AUTHORIZED_HWID = "{AUTHORIZED_HWID}"', f'AUTHORIZED_HWID = "{new_hwid}"')
            with open(__file__, "w", encoding="utf-8") as f:
                f.write(new_content)
            return {"ok": True, "msg": f"✅ THIẾT BỊ ĐÃ ĐƯỢC ĐĂNG KÝ CHÍNH CHỦ! HWID: {new_hwid[:8]}..."}
        except Exception as e:
            return {"ok": False, "msg": f"❌ Lỗi ghi danh thiết bị: {e}"}

    async def emergency_cancel(self):
        """🏛️ GIAO THỨC CHỦ QUYỀN: Kích hoạt lệnh dừng khẩn cấp toàn hệ thống."""
        logger.warning("🚨 [SOVEREIGN]: KÍCH HOẠT LỆNH DỪNG KHẨN CẤP THEO MỆNH LỆNH MASTER!")
        
        try:
            # 1. Phát tín hiệu Dừng toàn cầu
            def _set_stop(r):
                r.set("agent:stop_signal", "true", ex=3) # Hiệu lực trong 3 giây để ngắt mạch, sau đó tự reset
                r.delete("ai_task_queue", "user_request_queue", "exec_queue")
                r.set("agent_status", "IDLE")
            
            from redis_client import redis_safe
            redis_safe(_set_stop)
            
            # 2. Xóa hàng chờ HITL
            if self.task_manager and hasattr(self.task_manager, 'async_redis'):
                await self.task_manager.async_redis.delete("hitl_pending")
            
            return {"ok": True, "msg": "✅ Toàn bộ tác vụ đã bị hủy bỏ. Hệ thống đã trở về trạng thái sẵn sàng!"}
        except Exception as e:
            return {"ok": False, "msg": f"❌ Lỗi thực thi lệnh dừng: {e}"}
        except Exception as e:
            return {"ok": False, "msg": f"❌ Lỗi kích hoạt lệnh dừng: {e}"}

    def _flush_all_history(self):
        """🧹 [NEURAL-FLUSH]: Khởi tạo lại trạng thái hệ thống để Master luôn thấy giao diện sạch sẽ."""
        try:
            from redis_client import redis_safe
            def _flush(r):
                # Xóa lịch sử chat, process logs, và các monitor logs
                p_keys = r.keys("chat_history:*") + r.keys("chat_title:*") + r.keys("process_logs:*") + r.keys("monitor:logs:*") + r.keys("monitor:log_history*")
                if p_keys:
                    r.delete(*p_keys)
                r.set("agent_status", "IDLE")
                # Đặt tín hiệu dừng ngắt mạch 3 giây thay vì xóa, để giết các luồng ngầm thưa Master
                r.set("agent:stop_signal", "true", ex=3)
                r.delete("hitl_pending")
            redis_safe(_flush)
            logger.info("🧹 [SOVEREIGN]: Đã hoàn tất Giao thức Khởi tạo hệ thống.")
        except: pass

    async def supreme_shutdown(self, provided_key):
        """🔌 GIAO THỨC /SHUTDOWN: Tắt toàn bộ hệ sinh thái."""
        if not self.verify_key(provided_key):
            return {"ok": False, "msg": "❌ Mật mã tối thượng không chính xác!"}
            
        logger.warning("🔌 [SOVEREIGN]: KÍCH HOẠT LỆNH TẮT HỆ THỐNG TỪ MASTER!")
        
        # 🧹 [PRE-SHUTDOWN-CLEANUP]: Chuẩn bị hạ tầng trước khi đóng máy
        self._flush_all_history()

        try:
            subprocess.Popen(["sh", "-c", "sleep 2 && docker-compose down"], start_new_session=True)
            subprocess.Popen(["sh", "-c", "pkill ollama"], start_new_session=True)
        except: pass
        return {"ok": True, "msg": "🔌 Hệ thống đang tiến hành chuẩn bị và tắt toàn bộ. Tạm biệt Master!"}

    async def change_master_key(self, old_key, new_key):
        """🔄 GIAO THỨC ĐỔI MẬT MÃ CHỦ QUYỀN."""
        if not self.verify_key(old_key):
            return {"ok": False, "msg": "❌ Mật mã cũ không chính xác!"}
        
        new_hash = hashlib.sha256(new_key.encode()).hexdigest()
        try:
            with open(__file__, "r", encoding="utf-8") as f:
                content = f.read()
            new_content = content.replace(MASTER_HASH, new_hash)
            with open(__file__, "w", encoding="utf-8") as f:
                f.write(new_content)
            return {"ok": True, "msg": "✅ MẬT MÃ CHỦ QUYỀN ĐÃ ĐƯỢC CẬP NHẬT THÀNH CÔNG!"}
        except Exception as e:
            return {"ok": False, "msg": f"❌ Lỗi cập nhật: {e}"}

    async def initiate_self_destruct(self):
        """🔥 BƯỚC 1: Khởi động ngòi nổ tự hủy."""
        return {
            "status": "pending_approval", 
            "msg": "⚠️ CẢNH BÁO: Master đang kích hoạt GIAO THỨC TỰ HỦY. Nhấn APPROVE để tiếp tục."
        }

    async def confirm_self_destruct(self, provided_key):
        """🔥 BƯỚC 2: Xác thực và THIÊU RỤI."""
        if not self.verify_key(provided_key):
            return {"ok": False, "msg": "❌ Mật mã tối thượng không chính xác!"}

        logger.critical("🔥 [SOVEREIGN]: KHỞI ĐỘNG THIÊU RỤI TOÀN PHẦN!")
        try:
            destruct_cmd = 'timeout 3 && rmdir /s /q D:\\Docker\\N8N'
            subprocess.Popen(["cmd", "/c", destruct_cmd], start_new_session=True)
        except: pass
        return {"ok": True, "msg": "🔥 DỮ LIỆU ĐANG ĐƯỢC THIÊU RỤI. TẠM BIỆT MASTER."}

    def validate_outbound(self, url):
        """🛡️ GIAO THỨC GIÁM SÁT KẾT NỐI."""
        ALLOWED = ["localhost", "ai-brain", "ai-executor", "ai-browser", "127.0.0.1"]
        return any(domain in url for domain in ALLOWED)
