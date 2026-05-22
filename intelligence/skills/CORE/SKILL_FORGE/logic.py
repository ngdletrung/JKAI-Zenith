import os
import json
import asyncio
import logging
import re
from pathlib import Path
from core.utils.engine import engine
from core.utils.json_repair import repair_json

logger = logging.getLogger("jkai.skill_forge")

class SkillForge:
    """
    🏛️ [ZENITH-MASTER-FORGE v50.1]: Lò đúc Chủ quyền Tối thượng.
    Kiến tạo, Cấu hình và Đồng hóa mọi năng lực vào AI-OS.
    """
    def __init__(self):
        from core.utils import path_manager
        self.workspace = Path(path_manager.get_root())
        self.skills_dir = self.workspace / "intelligence" / "skills"
        self.registry_path = Path(path_manager.get("SKILLS_REGISTRY", str(self.workspace / "intelligence" / "registry_Map_skills.json")))
        self.map_path = self.workspace / "intelligence" / "MAP_SKILLS.md"

    async def forge_new_skill(self, description: str, task_id: str = "forge", trace_id: str = "sys"):
        engine.publish_mission_log("FORGE", f"🛠️ [MASTER-FORGE]: Bắt đầu tiến trình đúc kết năng lực mới: '{description[:60]}...'", task_id, trace_id)
        
        try:
            # 🧠 Phase 1: Neural Design & Validation
            validate_prompt = f"""
            [VALIDATOR v1.0] - Kiểm tra độ minh bạch của yêu cầu: "{description}"
            Nếu yêu cầu quá mơ hồ để viết code (thiếu Input/Output/Logic cụ thể), hãy trả về JSON: {{"status": "vague", "reason": "Câu hỏi gợi ý Master..."}}
            Nếu đã đủ rõ ràng, trả về JSON: {{"status": "clear"}}
            """
            val_res = await engine.chat_completion(messages=[{"role": "system", "content": validate_prompt}], role="PLANNER", format="json")
            val_data = json.loads(repair_json(val_res))
            
            if val_data.get("status") == "vague":
                return {"status": "clarification_needed", "output": f", yêu cầu này còn hơi mơ hồ để tôi có thể đúc một kỹ năng Elite. {val_data.get('reason')}"}

            # 🧠 Phase 1: Neural Design & Validation
            prompt = f"""
            [GRAND ARCHITECT v50.2 - SOVEREIGN v2.0]
            YÊU CẦU CỦA MASTER: {description}
            
            TIÊU CHUẨN KIẾN TRÚC ELITE:
            1. THẨM ĐỊNH (Validation): Nếu yêu cầu thiếu Input/Output rõ ràng, PHẢI trả về câu hỏi làm rõ.
            2. KHÁM PHÁ (Discovery): Tích hợp `await engine.get_experience()` để tự tìm dữ liệu trong Workspace.
            3. THỊ GIÁC & EXCEL: Phải hỗ trợ Phân tích ảnh và Excel Đa Sheet (pandas sheet_name=None).
            4. KỶ LUẬT & PHẢN HỒI: Sử dụng `path_manager` và trả về `attachments` để gửi tệp trực tiếp.
            
            TRẢ VỀ JSON:
            {{
                "skill_id": "SKILL_NAME_SNAKE_CASE",
                "name_vn": "Tên tiếng Việt trang trọng",
                "domain": "CORE/BUSINESS/HUEIC_PROCESS/AI_AGENT/TOOLS",
                "logic_code": "...",
                "skill_md": "..."
            }}
            """
            
            engine.publish_progress(30, "Đang đúc kết bản vẽ kiến trúc Trí tuệ...", "forge", task_id, trace_id)
            raw_response = await engine.chat_completion(
                messages=[{"role": "system", "content": "Ngài là Kiến trúc sư Trưởng của Zenith AI-OS."}, {"role": "user", "content": prompt}],
                role="PLANNER",
                format="json",
                task_id=task_id,
                trace_id=trace_id
            )
            
            data = json.loads(repair_json(raw_response))
            skill_id = data["skill_id"]
            domain = data["domain"]
            
            # 📁 Phase 2: Physical Sealing (Niêm phong Thực địa)
            target_dir = self.skills_dir / domain / skill_id
            target_dir.mkdir(parents=True, exist_ok=True)
            
            (target_dir / "logic.py").write_text(data["logic_code"], encoding="utf-8")
            (target_dir / "SKILL.md").write_text(data["skill_md"], encoding="utf-8")
            
            engine.publish_progress(70, f"Đã niêm phong kỹ năng `{skill_id}` vào thực địa `{domain}`.", "forge", task_id, trace_id)
            
            # 🗺️ Phase 3: Sovereign Integration (Nhất thể hóa Chủ quyền)
            await self._sync_to_system(data, target_dir)
            
            engine.publish_mission_log("FORGE", f"✅ [FORGE-SUCCESS]: Kỹ năng Elite `{skill_id}` đã sẵn sàng thực thi!", task_id, trace_id)
            return {"status": "success", "skill_id": skill_id, "path": str(target_dir)}

        except Exception as e:
            engine.publish_mission_log("ERROR", f"🚨 [FORGE-FAULT]: {str(e)}", task_id, trace_id)
            return {"status": "error", "msg": str(e)}

    async def _sync_to_system(self, data, target_dir):
        """Đồng bộ hóa nhất thể vào Registry và Bản đồ."""
        skill_id = data["skill_id"]
        domain = data["domain"]
        name_vn = data["name_vn"]

        # 1. Cập nhật Registry
        if self.registry_path.exists():
            reg = json.loads(self.registry_path.read_text(encoding="utf-8"))
            reg["skills"][skill_id.upper()] = {
                "id": skill_id.upper(),
                "name_vn": name_vn,
                "domain": domain,
                "rel_path": f"skills\\{domain}\\{skill_id}\\SKILL.md",
                "version": "1.0.0",
                "author": "Zenith Forge Auto"
            }
            self.registry_path.write_text(json.dumps(reg, indent=4, ensure_ascii=False), encoding="utf-8")

        # 2. Cập nhật Bản đồ MAP_SKILLS.md
        if self.map_path.exists():
            content = self.map_path.read_text(encoding="utf-8")
            # Heuristic: Tìm vị trí MUC dựa trên Domain
            domain_to_muc = {
                "CORE": "MUC 1", "AI_AGENT": "MUC 3", "BUSINESS": "MUC 4", 
                "HUEIC_PROCESS": "MUC 5", "QA_SECURITY": "MUC 6", "TOOLS": "MUC 7"
            }
            muc_tag = domain_to_muc.get(domain, "MUC 4")
            
            if muc_tag in content:
                parts = content.split(f"## {muc_tag}")
                sub_parts = parts[1].split("---")
                new_entry = f"- **#{skill_id.split('_')[-1]}. {skill_id}**: {name_vn}. [PLUGIN]\n"
                if new_entry not in parts[1]:
                    sub_parts[0] += new_entry
                    updated_content = parts[0] + f"## {muc_tag}" + "---".join(sub_parts)
                    self.map_path.write_text(updated_content, encoding="utf-8")

async def execute(params: dict, task_id: str = "system", trace_id: str = "system"):
    """Entry point cho Đặc vụ Dispatcher triệu hồi Lò đúc."""
    description = params.get("skill_description") or params.get("description")
    if not description:
        return {"status": "error", "output": "Master chưa cung cấp mô tả kỹ năng cần đúc."}
    
    forge = SkillForge()
    result = await forge.forge_new_skill(description, task_id, trace_id)
    return {"status": result["status"], "output": f"Đã đúc thành công kỹ năng tại: {result.get('path')}"}
