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
        engine.publish_mission_log("FORGE", f"[MASTER-FORGE]: Bắt đầu tiến trình đúc kết năng lực mới: '{description[:60]}...'", task_id, trace_id)
        
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
            [GRAND ARCHITECT v50.3 - SOVEREIGN v2.0]
            YÊU CẦU CỦA MASTER: {description}
            
            [WORKING PRINCIPLES]:
            1. [5-FILE-STANDARD]: Luôn duy trì bộ hồ sơ 5 file (logic, SKILL, dossier, manifest, __init__).
            2. [ID-GOVERNANCE]: Tự động phân bổ ID theo dải 10xx, 20xx... dựa trên Domain.
            3. [DIRECTORY-MAPPING]: Kỹ năng mới phải nằm đúng thư mục domain vật lý.
            4. [SSoT-SYNC]: Đồng bộ hóa tức thời vào registry_Map_skills.json và MAP_SKILLS.md.
            
            TIÊU CHUẨN KIẾN TRÚC ELITE (5-FILE):
            1. logic.py: Mã nguồn Python thực thi.
            2. SKILL.md: Manifest YAML v2.0 (id, name_vn, domain, intent_pairs, schema).
            3. dossier.md: Hồ sơ năng lực chi tiết. Bắt buộc có các mục: ## 🛠️ Detailed Features, ## 🎯 Capability Overview, ## 🌌 Strategic Value.
            4. manifest.json: Cấu hình registry tương thích.
            
            TRẢ VỀ JSON:
            {{
                "skill_id": "SKILL_NAME_SNAKE_CASE",
                "name_vn": "Tên tiếng Việt trang trọng",
                "domain": "CORE/BUSINESS/HUEIC_PROCESS/AI_AGENT/TOOLS",
                "logic_code": "...",
                "skill_md": "...",
                "dossier_md": "...",
                "manifest_json_content": {{ ... }}
            }}
            """
            
            engine.publish_progress(30, "Đang đúc kết bản vẽ kiến trúc Trí tuệ (5-File Standard)...", "forge", task_id, trace_id)
            raw_response = await engine.chat_completion(
                messages=[{"role": "system", "content": "Ngài là Kiến trúc sư Trưởng của Zenith AI-OS. Luôn tạo ra bộ hồ sơ 5 file chuẩn Elite."}, {"role": "user", "content": prompt}],
                role="PLANNER",
                format="json",
                task_id=task_id,
                trace_id=trace_id
            )
            
            data = json.loads(repair_json(raw_response))
            skill_id = data["skill_id"]
            domain = data["domain"]
            
            # 📁 Phase 2: Physical Sealing (Niêm phong Thực địa - 5 Files)
            target_dir = self.skills_dir / domain / skill_id
            target_dir.mkdir(parents=True, exist_ok=True)
            
            (target_dir / "logic.py").write_text(data["logic_code"], encoding="utf-8")
            (target_dir / "SKILL.md").write_text(data["skill_md"], encoding="utf-8")
            (target_dir / "dossier.md").write_text(data["dossier_md"], encoding="utf-8")
            (target_dir / "manifest.json").write_text(json.dumps(data["manifest_json_content"], indent=4, ensure_ascii=False), encoding="utf-8")
            (target_dir / "__init__.py").write_text("# Zenith Skill Initialization\n", encoding="utf-8")
            
            engine.publish_progress(70, f"Đã niêm phong bộ hồ sơ 5 file cho `{skill_id}` vào thực địa `{domain}`.", "forge", task_id, trace_id)
            
            # 🗺️ Phase 3: Sovereign Integration (Nhất thể hóa Chủ quyền)
            await self._sync_to_system(data, target_dir)
            
            engine.publish_mission_log("FORGE", f"[FORGE-SUCCESS]: Kỹ năng Elite `{skill_id}` đã sẵn sàng thực thi!", task_id, trace_id)
            return {"status": "success", "skill_id": skill_id, "path": str(target_dir)}

        except Exception as e:
            engine.publish_mission_log("ERROR", f"[FORGE-FAULT]: {str(e)}", task_id, trace_id)
            return {"status": "error", "msg": str(e)}

    def _get_next_global_id(self, domain):
        """Phân bổ ID toàn cầu dựa trên phân khu (Domain) từ MAP_SKILLS.md."""
        ranges = {
            "CORE": 1000, "DATA": 2000, "DEV": 3000, "RESEARCH": 4000,
            "BUSINESS": 5000, "SECURITY": 6000, "HUEIC": 7000, "TOOLS": 8000
        }
        base = ranges.get(domain, 9000)
        
        if not self.map_skills_path.exists():
            return f"#{base + 1}"
            
        content = self.map_skills_path.read_text(encoding="utf-8")
        import re
        ids = re.findall(r'\|\s*\*\*#(\d+)\*\*', content)
        
        # Lọc các ID thuộc dải của domain
        domain_ids = [int(i) for i in ids if base <= int(i) < base + 1000]
        
        if not domain_ids:
            return f"#{base + 1}"
        return f"#{max(domain_ids) + 1}"

    async def _sync_to_system(self, data, target_dir):
        """Đồng bộ hóa nhất thể vào Registry và Bản đồ với ID tự động."""
        skill_id = data["skill_id"]
        domain = data["domain"]
        name_vn = data["name_vn"]
        
        global_id = self._get_next_global_id(domain)
        rel_path = f"skills/{domain}/{skill_id}/SKILL.md"

        # 1. Cập nhật Registry
        if self.registry_path.exists():
            reg = json.loads(self.registry_path.read_text(encoding="utf-8"))
            reg["skills"][skill_id.upper()] = {
                "id": skill_id.upper(),
                "global_id": global_id,
                "name_vn": name_vn,
                "domain": domain,
                "rel_path": rel_path,
                "version": "1.0.0",
                "author": "Zenith Forge Auto",
                "learned_at": os.path.getmtime(str(target_dir / "logic.py"))
            }
            self.registry_path.write_text(json.dumps(reg, indent=4, ensure_ascii=False), encoding="utf-8")

        # 2. Cập nhật Bản đồ MAP_SKILLS.md (Chèn vào cuối phân khu tương ứng)
        if self.map_skills_path.exists():
            content = self.map_skills_path.read_text(encoding="utf-8")
            # Tìm vị trí phân khu
            section_markers = {
                "CORE": "## MỤC I:", "DATA": "## MỤC II:", "DEV": "## MỤC III:",
                "RESEARCH": "## MỤC IV:", "BUSINESS": "## MỤC V:", "SECURITY": "## MỤC VI:",
                "HUEIC": "## MỤC VII:", "TOOLS": "## MỤC VIII:"
            }
            marker = section_markers.get(domain, "## MỤC I:")
            
            # Tạo dòng mới
            features = data.get("dossier_md", "").split("## 🛠️ Detailed Features")[-1].split("##")[0].strip()
            # Dọn dẹp features để bỏ qua các ký tự xuống dòng gây hỏng bảng
            features_clean = features.replace("\n", "; ").strip("- ")
            new_row = f"| **{global_id}** | **{name_vn}**: {features_clean[:200]}... | {name_vn.lower().replace(' ', ', ')} | {skill_id.upper()} | Plugin |"
            
            # Chèn dòng vào file
            lines = content.splitlines()
            target_idx = -1
            for i, line in enumerate(lines):
                if marker in line:
                    target_idx = i
                    break
            
            if target_idx != -1:
                # Tìm cuối bảng hiện tại (dòng trống sau bảng)
                inserted = False
                for i in range(target_idx + 1, len(lines)):
                    if lines[i].strip() == "" and i > target_idx + 3:
                        lines.insert(i, new_row)
                        inserted = True
                        break
                if not inserted:
                    lines.append(new_row)
            else:
                lines.append(f"\n{marker}\n| STT | Tên Kỹ Năng | Keywords | ID | Loại |\n| :--- | :--- | :--- | :--- | :--- |\n{new_row}")
                    
            self.map_skills_path.write_text("\n".join(lines), encoding="utf-8")

async def execute(params: dict, task_id: str = "system", trace_id: str = "system"):
    """Entry point cho Đặc vụ Dispatcher triệu hồi Lò đúc."""
    description = params.get("skill_description") or params.get("description")
    if not description:
        return {"status": "error", "output": "Master chưa cung cấp mô tả kỹ năng cần đúc."}
    
    forge = SkillForge()
    result = await forge.forge_new_skill(description, task_id, trace_id)
    return {"status": result["status"], "output": f"Đã đúc thành công kỹ năng tại: {result.get('path')}"}
