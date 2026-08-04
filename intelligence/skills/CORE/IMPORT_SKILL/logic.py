import os
import shutil
from pathlib import Path
from core.utils.skill_forge import skill_forge
from core.utils.knowledge_manager import knowledge_orchestrator
from core.utils.engine import engine
from core.utils import path_manager

class SyncKnowledgeElite:
    """
    🏛️ SYNC_KNOWLEDGE ELITE v2.0
    Đặc vụ đồng hóa tri thức chuẩn Sovereign.
    Gọn nhẹ - An toàn - Tự trị.
    """
    def __init__(self):
        incoming_path = path_manager.get("IMPORT_DUMP_DIR") or os.path.join(path_manager.get_root(), "intelligence", "archive", "import_dump")
        skills_path = path_manager.get("SKILLS_DIR") or os.path.join(path_manager.get_root(), "intelligence", "skills")
        self.incoming_dir = Path(incoming_path)
        self.skills_base = Path(skills_path)

    async def sync_all(self, task_id: str = "sys"):
        engine.publish_mission_log("SYNC", "[ELITE-SYNC]: Bắt đầu chiến dịch đồng hóa tri thức mới...", task_id)
        
        if not self.incoming_dir.exists():
            return {"status": "idle", "msg": "Kho lưu trữ import_dump trống."}

        # Load Map Skills for ID calculation
        map_path = Path(path_manager.get_root()) / "intelligence" / "MAP_SKILLS.md"
        content = map_path.read_text(encoding="utf-8") if map_path.exists() else ""
        
        def get_next_id(domain):
            ranges = {"CORE": 1000, "DATA": 2000, "DEV": 3000, "RESEARCH": 4000, "BUSINESS": 5000, "SECURITY": 6000, "HUEIC": 7000, "TOOLS": 8000}
            base = ranges.get(domain, 9000)
            import re
            ids = [int(i) for i in re.findall(r'\|\s*\*\*#(\d+)\*\*', content) if base <= int(i) < base + 1000]
            return f"#{max(ids) + 1}" if ids else f"#{base + 1}"

        count = 0
        for item in self.incoming_dir.iterdir():
            if item.is_dir():
                skill_id = item.name
                logic_file = item / "logic.py"
                
                if logic_file.exists():
                    # 1. Thẩm định an ninh
                    code = logic_file.read_text(encoding="utf-8")
                    is_safe, msg = skill_forge.security_scan(code)
                    if not is_safe:
                        engine.publish_mission_log("SECURITY", f"[BLOCKED]: {skill_id} bị chặn do {msg}", task_id)
                        continue
                    
                    # 2. Phân loại Domain (Dựa trên tên hoặc mặc định)
                    target_domain = "CORE"
                    if "sec" in skill_id.lower() or "security" in skill_id.lower(): target_domain = "SECURITY"
                    elif "data" in skill_id.lower() or "ai" in skill_id.lower(): target_domain = "DATA"
                    elif "dev" in skill_id.lower(): target_domain = "DEV"
                    elif "hueic" in skill_id.lower(): target_domain = "HUEIC"
                    
                    global_id = get_next_id(target_domain)
                    
                    # 3. Tự động soạn thảo 5 file
                    manifest_md = skill_forge.auto_author_manifest(skill_id, logic_file)
                    (item / "SKILL.md").write_text(manifest_md, encoding="utf-8")
                    
                    z_manifest = {
                        "id": skill_id.upper(),
                        "global_id": global_id,
                        "name_vn": skill_id.replace("_", " ").title(),
                        "domain": target_domain,
                        "rel_path": f"skills/{target_domain}/{skill_id}/SKILL.md",
                        "version": "1.0.0",
                        "author": "Zenith Importer"
                    }
                    (item / "manifest.json").write_text(json.dumps(z_manifest, indent=4, ensure_ascii=False), encoding="utf-8")
                    
                    dossier_content = f"# 🏛️ DOSSIER: {skill_id}\n## 🎯 Capability Overview\nKỹ năng được nhập khẩu tự động vào hệ thống Zenith.\n\n## 🛠️ Detailed Features\n- ID Toàn cầu: {global_id}\n- Phân khu: {target_domain}\n- Logic thực thi từ file `logic.py` đã qua thẩm định.\n\n## 🌌 Strategic Value\nGia tăng mật độ nơ-ron chuyên biệt cho phân khu {target_domain}.\n"
                    (item / "dossier.md").write_text(dossier_content, encoding="utf-8")
                    (item / "__init__.py").write_text("# Imported Skill Initialization\n", encoding="utf-8")
                    
                    # 4. Di chuyển vào thực địa
                    dest_path = self.skills_base / target_domain / skill_id
                    dest_path.parent.mkdir(parents=True, exist_ok=True)
                    shutil.move(str(item), str(dest_path))
                    
                    # 5. Cập nhật MAP_SKILLS.md
                    new_row = f"| **{global_id}** | **{skill_id.replace('_', ' ').title()}**: Tự động nhập khẩu. | {skill_id.lower()} | {skill_id.upper()} | Plugin |"
                    # (Logic cập nhật markdown tương tự SKILL_FORGE)
                    lines = content.splitlines()
                    for i, line in enumerate(lines):
                        if f"## MỤC" in line and target_domain in line:
                            for j in range(i+1, len(lines)):
                                if lines[j].strip() == "" and j > i+3:
                                    lines.insert(j, new_row)
                                    break
                            break
                    content = "\n".join(lines)
                    map_path.write_text(content, encoding="utf-8")
                    
                    count += 1
                    engine.publish_mission_log("SYNC", f"[ASSIMILATED]: {skill_id} -> {target_domain} ({global_id})", task_id)

        await knowledge_orchestrator.sync_sovereign_registry()
        return {"status": "success", "synced_count": count}

async def run_sync(**kwargs):
    sync_agent = SyncKnowledgeElite()
    return await sync_agent.sync_all(**kwargs)
