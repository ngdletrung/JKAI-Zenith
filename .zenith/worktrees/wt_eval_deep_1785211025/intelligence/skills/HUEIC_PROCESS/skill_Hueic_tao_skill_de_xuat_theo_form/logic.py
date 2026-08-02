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
        skill_dir = Path(os.path.join(self.skills_root, skill_id))
        os.makedirs(skill_dir, exist_ok=True)

        engine.publish_mission_log("HUEIC_FORGE", f"🛠️ [FORGE]: Đang đúc kết Skill `{skill_id}` tại Tầng 0...", task_id)

        # 1. Tạo bộ hồ sơ 5 file (HUEIC Standard)
        (skill_dir / "logic.py").write_text("# Logic thực thi HUEIC\n", encoding="utf-8")
        (skill_dir / "SKILL.md").write_text(f"---\nid: {skill_id.upper()}\nname_vn: {skill_name_raw}\ndomain: HUEIC_PROCESS\n---\n# {skill_name_raw}\n## 📖 TỔNG QUAN\nKỹ năng HUEIC được đúc từ mẫu.", encoding="utf-8")
        
        dossier_content = f"""# 🏛️ DOSSIER: {skill_id}
## 🎯 Capability Overview
Kỹ năng văn phòng HUEIC chuyên biệt.

## 🛠️ Detailed Features
- Deep Document Analysis: Phân tích tài liệu mẫu dựa trên biến số: {json.dumps(confirmed_vars)}.
- HUEIC Template Forging: Đúc văn bản chuẩn quy trình.

## 🌌 Strategic Value
Tự động hóa hoàn toàn luồng văn thư HUEIC.
"""
        (skill_dir / "dossier.md").write_text(dossier_content, encoding="utf-8")
        
        manifest_content = {
            "id": skill_id.upper(),
            "name_vn": skill_name_raw,
            "domain": "HUEIC_PROCESS",
            "rel_path": f"skills/HUEIC_PROCESS/{skill_id}/SKILL.md",
            "version": "1.0.0"
        }
        (skill_dir / "manifest.json").write_text(json.dumps(manifest_content, indent=4, ensure_ascii=False), encoding="utf-8")
        (skill_dir / "__init__.py").write_text("# HUEIC Skill Initialization\n", encoding="utf-8")
        
        # 3. Đăng ký vào registry.json
        if os.path.exists(self.registry_path):
            with open(self.registry_path, "r", encoding="utf-8") as f:
                reg = json.load(f)
            reg["skills"][skill_id.upper()] = manifest_content
            with open(self.registry_path, "w", encoding="utf-8") as f:
                json.dump(reg, f, indent=4, ensure_ascii=False)

        return f"✅ [FORGE-SUCCESS]: Bộ hồ sơ 5 file của Skill HUEIC `{skill_id}` đã được niêm yết tại Tầng 0!"

_instance = HueicSkillForge()
async def execute(**kwargs):
    return await _instance.execute(**kwargs)
