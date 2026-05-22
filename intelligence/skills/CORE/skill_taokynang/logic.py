import os
import json
from core.utils.engine import engine

class ZenithSkillFactory:
    """
    🏭 JKAI ZENITH: ULTIMATE SKILL FACTORY (Lõi Tạo tác v2.0)
    Nhiệm vụ: Tự động hóa việc kiến tạo Siêu kỹ năng chuẩn "Bộ Tứ Elite".
    """
    def __init__(self):
        from core.config import settings
        self.skills_root = os.path.join(settings.INTELLIGENCE_DIR, "skills")

    async def tao_ky_nang_elite(self, skill_id, skill_name, description="", task_id="sys"):
        """Giao thức kiến tạo 4 tệp tin chuẩn Corporate!"""
        engine.publish_mission_log("FACTORY_INIT", f"🏭 [FACTORY]: Khởi động dây chuyền đúc kỹ năng mới: `{skill_name}` (#{skill_id})", task_id)
        
        path = os.path.join(self.skills_root, skill_id)
        os.makedirs(path, exist_ok=True)
        
        # 1. logic.py (Mã nguồn thực thi)
        engine.publish_mission_log("FACTORY_CODE", f"🛠️ [FACTORY]: Đang phẫu thuật mã nguồn logic cho `{skill_id}`...", task_id)
        logic_template = f'''"""
🔬 JKAI ZENITH: {skill_name} LOGIC
Thực thi chuyên sâu chuẩn Elite.
"""
import os
import json
import asyncio
from core.utils.engine import engine

class SkillLogic:
    def __init__(self):
        pass

    async def execute(self, **kwargs):
        task_id = kwargs.get("task_id", "sys")
        engine.publish_mission_log("{skill_id.upper()}", "🚀 [EXECUTING]: {skill_name} đang được triển khai...", task_id)
        
        # Logic thực thi của Master tại đây
        
        result = "✅ [SUCCESS]: {skill_name} đã hoàn tất!"
        engine.publish_mission_log("{skill_id.upper()}", result, task_id)
        return result

_instance = SkillLogic()

async def execute(**kwargs):
    return await _instance.execute(**kwargs)
'''
        with open(os.path.join(path, "logic.py"), "w", encoding="utf-8") as f:
            f.write(logic_template)

        # 2. schema.json (Giao thức kết nối)
        schema = {
            "name": skill_id,
            "description": f"{skill_name}. {description}",
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "string", "description": "ID nhiệm vụ hệ thống"}
                }
            }
        }
        with open(os.path.join(path, "schema.json"), "w", encoding="utf-8") as f:
            json.dump(schema, f, indent=2, ensure_ascii=False)

        # 3. manual.md (Linh hồn vận hành)
        with open(os.path.join(path, "manual.md"), "w", encoding="utf-8") as f:
            f.write(f"# 📖 CẨM NĂNG: {skill_name.upper()}\n\nKỹ năng này cung cấp năng lực {skill_name} đẳng cấp cho Tập đoàn.\n\n--- \n*ZENITH ELITE* 💎🫡")

        # 4. workflow.md (Kỷ luật tác chiến)
        with open(os.path.join(path, "workflow.md"), "w", encoding="utf-8") as f:
            f.write(f"# 📑 QUY TRÌNH: {skill_name.upper()}\n\n1. Tiếp nhận chỉ thị từ Master.\n2. Phân tích bối cảnh vĩ mô.\n3. Gọi công cụ thực thi.\n4. Báo cáo kết quả.")

        msg = f"✅ [FACTORY]: Đã xuất xưởng bộ tứ kỹ năng {skill_id} thành công!"
        engine.publish_mission_log("FACTORY_DONE", msg, task_id)
        return msg

_instance = ZenithSkillFactory()

# 🚀 GIAO THỨC NHẤT THỂ HÓA: Wrapper cấp module để ToolRouter nhận diện
async def tao_ky_nang_elite(**kwargs):
    return await _instance.tao_ky_nang_elite(**kwargs)
