import os
import json
import time
from core.utils.engine import engine
from core.config import settings
from redis_client import redis_safe

CRITIC_SCHEMA = {
    "type": "object",
    "properties": {
        "thought": {
            "type": "string",
            "description": "Internal reasoning process for the critique"
        },
        "approved": {
            "type": "boolean",
            "description": "Whether the plan is approved"
        },
        "feedback": {
            "type": "string",
            "description": "Constructive feedback or modification requests"
        },
        "needs_nuclear_key": {
            "type": "boolean",
            "description": "True if the plan requires Master's explicit approval decree"
        }
    },
    "required": ["approved", "feedback", "thought"]
}

class Critic:
    """
    HỆ THỐNG KIỂM DUYỆT SENTINEL (Elite): 
    Sử dụng LLM chuyên sâu để phân tích rủi ro và tối ưu hóa VRAM qua Profile.
    """
    def __init__(self):
        pass

    def _log(self, tag, msg, task_id="system"):
        """Giao thức Phát tín hiệu Elite từ Ban Kiểm soát thưa Master! 🛡️💎"""
        try:
            from core.utils.engine import engine
            engine.publish_mission_log(tag, msg, task_id)
        except: pass

    async def review_plan(self, goal: str, steps: list) -> dict:
        # 🛡️ Lấy cấu hình từ Nguồn Sống
        role_cfg = engine.get_role_config("CRITIC")
        active_model = role_cfg.get("model")
        active_profile = role_cfg.get("options", {}).get("profile", "STRICT")

        print(f"🛡️ [JKAI-CRITIC] Reviewing plan with model: {active_model} | Profile: {active_profile}")
        
        # Gửi thông báo Thẩm định lên Dashboard
        log_payload = json.dumps({
            "tag": "CRITIC",
            "msg": "🔬 [BAN KIỂM SOÁT]: Đang tiến hành thẩm định tính logic và độ an toàn của lộ trình chiến lược.",
            "ts": time.time()
        })
        redis_safe(lambda r: (r.lpush("monitor:log_history", log_payload), 
                               r.ltrim("monitor:log_history", 0, 499), 
                               r.publish("monitor:log_channel", log_payload)))

        # 🛡️ [VAULT-LOAD] Đọc "Linh hồn" từ RAM Cache trung tâm
        try:
            from prompt_forge import prompt_forge
            self._log("CRITIC", "🛠️ [PROMPT-FORGE]: Đang đúc kết Tư duy Phản biện chuyên gia...", task_id="critic")
            
            manifesto = engine.get_intel_file("JKAI_ZENITH_CORP.md") or ""
            # Đúc một Prompt dành riêng cho việc Phản biện (Critique) thưa Master
            forge_goal = f"Phản biện và kiểm soát chất lượng cho lộ trình thực hiện mục tiêu: {goal}"
            specialist_prompt = await prompt_forge.forge_specialist_prompt(
                goal=forge_goal,
                context={"steps": steps},
                skills_summary="Hãy đóng vai một Giám đốc Chất lượng cực kỳ khó tính và am tường kỹ thuật."
            )
            
            system_prompt = manifesto + "\n\n" + specialist_prompt
        except Exception as e:
            print(f"⚠️ [PROMPT-LOAD-ERR] {e}. Sử dụng prompt mặc định.")
            system_prompt = f"Bạn là Thẩm định viên Cao cấp của JKAI Zenith. Thẩm định Goal: {goal}"

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # 🚀 HOT-SWAP: Model và Profile đã được xác định tại đầu hàm

        # 🛡️ [SOVEREIGN HIERARCHY ENFORCEMENT]
        # Tự động gắn cờ dựa trên quy tắc Master LeeTrung
        is_sensitive = False
        requires_nuclear = False
        
        core_zones = ["/services", "/core", "/shared", "/tools", "/intelligence", ".env", "docker-compose"]
        strategic_tools = ["ai_browse", "browser", "host_bridge", "shell", "cmd", "powershell", "patch", "write", "replace", "nuclear", "sync", "docker"]
        
        # 🧪 [INTEGRITY-AUDIT]: Kiểm tra lỗi từ Planner thưa Master
        for step in steps:
            if step.get("error") == "NOT_FOUND_IN_REGISTRY":
                return {
                    "approved": False, 
                    "feedback": f"❌ [INTEGRITY-ERROR]: Kỹ năng '{step.get('tool')}' không tồn tại trong Registry thưa Master! Planner cần phải hiệu đính lại lộ trình.",
                    "thought": "Phát hiện kỹ năng không hợp lệ, từ chối để đảm bảo an toàn thưa Ngài."
                }

        for step in steps:
            tool = step.get("tool", "").lower()
            args = str(step.get("args", ""))
            
            # Kiểm tra Cấp độ 1: Can thiệp Vùng Lõi
            if any(zone in args for zone in core_zones) and any(t in tool for t in ["write", "replace", "patch", "delete"]):
                requires_nuclear = True
                is_sensitive = True
                break
                
            # Kiểm tra Cấp độ 2: Tác chiến Chiến lược
            if any(st in tool for st in strategic_tools):
                is_sensitive = True

        # Gọi Engine mới (Unified Intelligence Engine) với Profile động
        review = await engine.call_chat(
            messages=messages,
            role="CRITIC",
            model=active_model,
            profile=active_profile,
            schema=CRITIC_SCHEMA
        )

        if isinstance(review, dict) and "approved" in review:
            # 💎 Áp dụng Luật Chủ quyền (Ghi đè nếu cần thiết)
            if requires_nuclear:
                review["approved"] = False
                review["needs_nuclear_key"] = True
                review["feedback"] = "⚠️ [LEVEL 1]: Tác vụ can thiệp VÙNG LÕI. Yêu cầu MẬT MÃ TỐI THƯỢNG thưa Master!"
            elif is_sensitive and review.get("approved", True):
                review["approved"] = False # Ép buộc phải bấm APPROVE
                review["feedback"] = f"🟡 [LEVEL 2]: Tác vụ Tác chiến Chiến lược ({steps[0].get('tool')}). Vui lòng PHÊ DUYỆT để triển khai thưa Master!"

            # Gửi kết quả thẩm định lên Dashboard
            status = "PHÊ DUYỆT" if review.get('approved') else "CẦN CHỈNH SỬA"
            if review.get('needs_nuclear_key'): status = "⚠️ CẦN MẬT LỆNH MASTER"
            
            log_res = json.dumps({
                "tag": "CRITIC",
                "msg": f"Kết quả thẩm định: {status}.\n{review.get('feedback', '')}",
                "ts": time.time()
            })
            redis_safe(lambda r: (r.lpush("monitor:log_history", log_res), r.publish("monitor:log_channel", log_res)))
            return review

        return {"approved": False, "feedback": f"Lỗi thẩm định hệ thống. Raw: {review}"}

# *Sovereign Property of Master LeeTrung. Developed by Antigravity AI. Optimized for Eternal Excellence. 🌌🏛️🔥🦾👑🔗*
