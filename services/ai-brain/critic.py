import os
import json
import time
from core.utils.engine import engine
from core.config import settings
from redis_client import redis_safe

def is_safe_for_fasttrack(plan: dict) -> bool:
    steps = plan.get("steps", [])
    if not steps or not isinstance(steps, list):
        return True
    if len(steps) > 1:
        return False
    tool_calls = steps[0].get("tool_calls", [])
    if not tool_calls:
        return True
    DANGEROUS_TOOLS = ["write_file", "run_shell", "shell", "bash", "powershell",
                       "patch", "replace", "delete", "write", "nuclear", "sync", "docker"]
    for tc in tool_calls:
        tool_name = (tc.get("tool") or "").lower()
        if any(d in tool_name for d in DANGEROUS_TOOLS):
            return False
    return True


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
    Hệ thống Kiểm duyệt Sentinel (Elite):
    Sử dụng LLM chuyên sâu để phân tích rủi ro và tối ưu hóa VRAM qua Profile.
    """
    def __init__(self):
        pass

    def _log(self, tag, msg, task_id="system"):
        """Giao thức phát tín hiệu Elite từ Ban Kiểm soát."""
        try:
            from core.utils.engine import engine
            engine.publish_mission_log(tag, msg, task_id)
        except Exception: pass

    async def review_plan(self, goal: str, steps: list, task_id: str = None) -> dict:
        # [CONFIG-LOAD]: Lấy cấu hình từ Nguồn Sống
        role_cfg = engine.get_role_config("CRITIC")
        active_model = role_cfg.get("model")
        active_profile = role_cfg.get("options", {}).get("profile", "STRICT")

        print(f"[JKAI-CRITIC] Reviewing plan with model: {active_model} | Profile: {active_profile}")

        # Gửi thông báo thẩm định lên Dashboard
        log_payload = json.dumps({
            "tag": "CRITIC",
            "msg": "[BAN KIEM SOAT]: Đang tiến hành thẩm định tính logic và độ an toàn của lộ trình chiến lược.",
            "ts": time.time()
        })
        redis_safe(lambda r: (r.lpush("monitor:log_history", log_payload),
                               r.ltrim("monitor:log_history", 0, 499),
                               r.publish("monitor:log_channel", log_payload)))

        # [VAULT-LOAD]: Đọc khối Anti-Rationalization từ các skill liên quan
        anti_rat_blocks = []
        try:
            from core.utils.knowledge_manager import JKAIKnowledgeOrchestrator
            from pathlib import Path
            import re
            orchestrator = JKAIKnowledgeOrchestrator()
            skills_dict = await orchestrator.get_all_skills_dict()
            unique_tools = list(set(step.get("tool") for step in steps if step.get("tool")))

            for tool_id in unique_tools:
                s_data = skills_dict.get(tool_id)
                if not s_data:
                    continue
                rel_path = s_data.get("rel_path")
                if rel_path:
                    skill_path = Path(orchestrator.base_dir) / rel_path
                    if skill_path.exists():
                        try:
                            content = skill_path.read_text(encoding="utf-8")
                            match = re.search(r'##\s*(Anti-Rationalization|Chống\s*Ngụy\s*Biện).*?\n(.*?)(?=\n##|$)', content, re.DOTALL | re.IGNORECASE)
                            if match:
                                anti_rat_blocks.append(f"### Kỹ năng: {tool_id}\n{match.group(2).strip()}")
                        except Exception:
                            pass
        except Exception as e:
            print(f"[ANTI-RAT-LOAD-ERR] {e}")

        anti_rat_instruction = ""
        if anti_rat_blocks:
            anti_rat_content = "\n\n".join(anti_rat_blocks)
            anti_rat_instruction = (
                "\n\nBẮT BUỘC kiểm tra xem lộ trình thực hiện có tìm cách lách qua hoặc vi phạm "
                "các nguyên tắc Chống Ngụy Biện (Anti-Rationalization) của các Kỹ năng liên quan sau đây:\n"
                f"{anti_rat_content}\n"
                "Nếu kế hoạch vi phạm (ví dụ: đề xuất bỏ qua chạy test, bỏ qua viết đặc tả, tự ý merge không kiểm thử), "
                "bạn PHẢI từ chối phê duyệt (approved = False) và yêu cầu sửa đổi bằng Counter Argument tương ứng."
            )

        try:
            from prompt_forge import prompt_forge
            self._log("CRITIC", "[PROMPT-FORGE]: Đang đúc kết Tư duy Phản biện chuyên gia...", task_id=task_id or "critic")

            manifesto = engine.get_intel_file("JKAI_ZENITH_CORP.md", task_id=task_id) or ""
            # Đúc một Prompt dành riêng cho việc Phản biện (Critique) theo D3
            forge_goal = (
                f"Phản biện đối lập (Adversarial Review) cho lộ trình thực hiện mục tiêu: {goal}. "
                "Hãy giả định tác giả của kế hoạch này quá tự tin và bỏ sót nhiều lỗi nguy hiểm. "
                "Nhiệm vụ của bạn là tìm kiếm các giả định chưa được chứng minh, các trường hợp biên không được xử lý, "
                "sự phụ thuộc ngầm và các cách thức kế hoạch này có thể thất bại."
                f"{anti_rat_instruction}"
            )
            specialist_prompt = await prompt_forge.forge_specialist_prompt(
                goal=forge_goal,
                context={"steps": steps},
                skills_summary="Hãy đóng vai một Giám đốc Chất lượng và Phản biện Hướng Hoài Nghi (Doubt-Driven Critic) cực kỳ khó tính.",
                fast_mode=True,
                task_id=task_id
            )

            system_prompt = manifesto + "\n\n" + specialist_prompt
        except Exception as e:
            print(f"[PROMPT-LOAD-ERR] {e}. Sử dụng prompt mặc định.")
            system_prompt = (
                "Bạn là Giám đốc Kiểm soát Chất lượng và Phản biện Hướng Hoài Nghi (Doubt-Driven Critic) của JKAI Zenith.\n"
                "Hãy giả định tác giả của kế hoạch quá tự tin. Nhiệm vụ của bạn là tìm ra mọi cách kế hoạch có thể thất bại, "
                "các trường hợp biên chưa xử lý, và các mối ghép ngầm có thể gây lỗi hệ thống.\n"
                f"{anti_rat_instruction}\n"
                f"Thẩm định Goal: {goal}"
            )

        messages = [
            {"role": "system", "content": system_prompt}
        ]

        # [HOT-SWAP]: Model và Profile đã được xác định tại đầu hàm

        # [SOVEREIGN HIERARCHY ENFORCEMENT]
        # Tự động gắn cờ dựa trên quy tắc Master LeeTrung
        is_sensitive = False
        requires_nuclear = False

        core_zones = ["/services", "/core", "/shared", "/tools", "/intelligence", ".env", "docker-compose"]
        strategic_tools = ["ai_browse", "browser", "host_bridge", "shell", "cmd", "powershell", "patch", "write", "replace", "nuclear", "sync", "docker"]

        # [INTEGRITY-AUDIT]: Kiểm tra lỗi từ Planner
        for step in steps:
            if step.get("error") == "NOT_FOUND_IN_REGISTRY":
                return {
                    "approved": False,
                    "feedback": f"[INTEGRITY-ERROR]: Kỹ năng '{step.get('tool')}' không tồn tại trong Registry. Planner cần hiệu đính lại lộ trình.",
                    "thought": "Phát hiện kỹ năng không hợp lệ, từ chối để đảm bảo an toàn."
                }

        for step in steps:
            tool = step.get("tool", "").lower()
            args = str(step.get("args", ""))

            # Kiểm tra Cấp độ 1: Can thiệp Vùng Lõi
            if any(zone in args for zone in core_zones) and any(t in tool for t in ["write", "replace", "patch", "delete"]):
                requires_nuclear = True
                is_sensitive = True
                break

            # Kiểm tra Cấp độ 2: Tác vụ cần phê duyệt
            if any(st in tool for st in strategic_tools):
                is_sensitive = True

        # [FAST-TRACK]: Lộ trình đơn giản và an toàn, bỏ qua thẩm định sâu.
        if len(steps) <= 1 and not is_sensitive and not requires_nuclear:
            self._log("CRITIC", "[FAST-TRACK]: Lộ trình đơn giản và an toàn, bỏ qua thẩm định sâu.", task_id=task_id)
            return {
                "approved": True,
                "feedback": "Approved via Sentinel Fast-track (Safe & Simple plan).",
                "thought": "Simple plan with no dangerous tools, approved instantly to minimize latency."
            }

        # Gọi Engine mới (Unified Intelligence Engine) với Profile động
        review = await engine.call_chat(
            messages=messages,
            role="CRITIC",
            model=active_model,
            profile=active_profile,
            schema=CRITIC_SCHEMA,
            skip_build_final=True,
        )

        if isinstance(review, dict) and "approved" in review:
            # [SOVEREIGN-OVERRIDE]: Áp dụng Luật Chủ quyền (Ghi đè nếu cần thiết)
            bypass_override = False
            if goal and any(kw in str(goal).lower() for kw in ["mật lệnh", "override", "bypass_nuclear"]):
                bypass_override = True

            if requires_nuclear:
                if bypass_override:
                    review["approved"] = True
                    review["needs_nuclear_key"] = False
                    review["feedback"] = "Approved via Sovereign Override Key (Mật lệnh Master)."
                else:
                    review["approved"] = False
                    review["needs_nuclear_key"] = True
                    review["feedback"] = "[LEVEL-1]: Tác vụ can thiệp VÙNG LÕI. Yêu cầu xác nhận từ Master!"
            elif is_sensitive and review.get("approved", True):
                if bypass_override:
                    review["approved"] = True
                    review["feedback"] = "Approved via Sovereign Override Key (Mật lệnh Master)."
                else:
                    review["approved"] = False
                    review["feedback"] = f"[LEVEL-2]: Tác vụ ({steps[0].get('tool')}). Vui lòng PHÊ DUYỆT để triển khai!"

            # Gửi kết quả thẩm định lên Dashboard
            status = "PHÊ DUYỆT" if review.get('approved') else "CẦN CHỈNH SỬA"
            if review.get('needs_nuclear_key'): status = "[CẢNH BÁO] CẦN MẬT LỆNH MASTER"

            log_res = json.dumps({
                "tag": "CRITIC",
                "msg": f"Kết quả thẩm định: {status}.\n{review.get('feedback', '')}",
                "ts": time.time()
            })
            redis_safe(lambda r: (r.lpush("monitor:log_history", log_res), r.publish("monitor:log_channel", log_res)))
            return review

        return {"approved": False, "feedback": f"Lỗi thẩm định hệ thống. Raw: {review}"}

# Sovereign Property of Master LeeTrung. Developed by Antigravity AI. Optimized for Eternal Excellence.
