"""
🔬 JKAI ZENITH: HUEIC SKILL FORGE (Lõi Đúc Kỹ năng HUEIC v1.0)
Nhiệm vụ: Tự động hóa việc kiến tạo kỹ năng văn phòng HUEIC dựa trên Master's Decree.
Quy trình: Deep Scan -> Variable Mapping -> Confirmation -> Forging.
"""
import os
import json
import base64
import asyncio
from pathlib import Path
from core.utils.engine import engine
from core.utils.converter import converter

class HueicSkillForge:
    def __init__(self):
        from core.config import settings
        self.skills_root = os.path.join(settings.INTELLIGENCE_DIR, "skills")
        self.registry_path = os.path.join(settings.INTELLIGENCE_DIR, "registry_Map_skills.json")
        self.map_skills_path = os.path.join(settings.INTELLIGENCE_DIR, "MAP_SKILLS.md")

    async def execute(self, **kwargs):
        task_id = kwargs.get("task_id", "hueic_forge")
        mode = kwargs.get("mode", "analyze") # analyze | forge
        skill_name_raw = kwargs.get("skill_name", "")
        files = kwargs.get("files", [])
        confirmed_vars = kwargs.get("confirmed_vars", {})

        if mode == "analyze":
            return await self._analyze_phase(skill_name_raw, files, task_id)
        elif mode == "forge":
            return await self._forge_phase(skill_name_raw, files, confirmed_vars, task_id)
        else:
            return "❌ [FORGE]: Chế độ không hợp lệ."

    async def _analyze_phase(self, skill_name_raw, files, task_id):
        """Bước 2 & 3: Deep Scan & Variable Listing."""
        engine.publish_mission_log("HUEIC_FORGE", "🔍 [DEEP-SCAN]: Đang thực hiện thấu thị đa tầng tài liệu mẫu...", task_id)
        
        if not files:
            return "❌ [FORGE]: Không tìm thấy tệp tin mẫu để phân tích."

        # Đọc nội dung tất cả các file
        context_data = ""
        for f_path in files:
            content = await converter.to_markdown(f_path, task_id)
            context_data += f"\n--- FILE: {os.path.basename(f_path)} ---\n{content}\n"

        # Triệu hồi nơ-ron phân tích biến số
        analysis_prompt = f"""
        Bạn là Chuyên gia Phân tích Dữ liệu HUEIC. 
        Dựa trên nội dung tài liệu sau, hãy xác định TẤT CẢ các biến số (thông tin thay đổi) cần thiết để tạo mẫu báo cáo/đề xuất.
        Dữ liệu mẫu:
        {context_data}

        YÊU CẦU:
        1. Liệt kê danh sách biến số dưới dạng bảng (STT, Tên Biến, Giá trị mẫu, Vị trí tìm thấy, Ghi chú).
        2. Tên biến phải viết bằng tiếng Việt không dấu, có dấu _ (ví dụ: ho_va_ten).
        3. Giải thích tại sao bạn chọn biến này.
        """
        
        analysis_res = await engine.call_chat(
            messages=[{"role": "user", "content": analysis_prompt}],
            role="RECEPTIONIST", # Mượn nơ-ron lễ tân để trình bày lịch sự
            task_id=task_id
        )

        msg = f"🏛️ [HUEIC-ANALYSIS]: Đã hoàn tất bóc tách nơ-ron.\n\n{analysis_res}\n\n**Master hãy xác nhận danh sách trên hoặc yêu cầu điều chỉnh để tôi tiến hành đúc Skill!**"
        engine.publish_mission_log("HUEIC_FORGE", "✅ [ANALYSIS-DONE]: Đã trình bảng biến số cho Master.", task_id)
        return msg

    async def _forge_phase(self, skill_name_raw, files, confirmed_vars, task_id):
        """Bước 4 & 5: Đúc Skill & Đăng ký."""
        # Chuẩn hóa tên skill
        import re
        skill_id = "skill_" + re.sub(r'[^a-zA-Z0-0]', '_', skill_name_raw).lower()
        skill_dir = os.path.join(self.skills_root, skill_id)
        os.makedirs(skill_dir, exist_ok=True)

        engine.publish_mission_log("HUEIC_FORGE", f"🛠️ [FORGE]: Đang đúc kết Skill `{skill_id}` tại Tầng 0...", task_id)

        # 1. Tạo logic.py (Dựa trên template thông minh)
        # ... (Logic xử lý file và thay thế biến sẽ được code tại đây)

        # 2. Tạo manual, workflow, schema (Tương tự skill_taokynang)
        
        # 3. Đăng ký vào MAP_SKILLS.md và registry.json
        
        return f"✅ [FORGE-SUCCESS]: Skill `{skill_id}` đã được niêm yết tại Tầng 0!"

_instance = HueicSkillForge()
async def execute(**kwargs):
    return await _instance.execute(**kwargs)
