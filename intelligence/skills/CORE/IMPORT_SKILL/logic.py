import os
import shutil
from pathlib import Path
from core.utils.skill_forge import skill_forge
from core.utils.knowledge_manager import knowledge_orchestrator
from core.utils.engine import engine

class SyncKnowledgeElite:
    """
    🏛️ SYNC_KNOWLEDGE ELITE v2.0
    Đặc vụ đồng hóa tri thức chuẩn Sovereign.
    Gọn nhẹ - An toàn - Tự trị.
    """
    def __init__(self):
        self.incoming_dir = Path("D:/Docker/N8N/intelligence/archive/import_dump")
        self.skills_base = Path("D:/Docker/N8N/intelligence/skills")

    async def sync_all(self, task_id: str = "sys"):
        engine.publish_mission_log("SYNC", "🚀 [ELITE-SYNC]: Bắt đầu chiến dịch đồng hóa tri thức mới...", task_id)
        
        if not self.incoming_dir.exists():
            return {"status": "idle", "msg": "Kho lưu trữ import_dump trống."}

        count = 0
        for item in self.incoming_dir.iterdir():
            if item.is_dir():
                # [SOVEREIGN-FORGE-LOGIC]: Sử dụng Lò đúc để đúc kỹ năng mới
                skill_id = item.name
                logic_file = item / "logic.py"
                
                if logic_file.exists():
                    # 1. Thẩm định an ninh
                    code = logic_file.read_text(encoding="utf-8")
                    is_safe, msg = skill_forge.security_scan(code)
                    if not is_safe:
                        engine.publish_mission_log("SECURITY", f"🚨 [BLOCKED]: {skill_id} bị chặn do {msg}", task_id)
                        continue
                    
                    # 2. Tự động soạn thảo SKILL.md
                    manifest = skill_forge.auto_author_manifest(skill_id, logic_file)
                    with open(item / "SKILL.md", "w", encoding="utf-8") as f:
                        f.write(manifest)
                    
                    # 3. Phân loại Domain (Sử dụng cơ chế gợi ý của Sanitizer)
                    target_domain = "CORE" # Default cho tri thức mới
                    dest_path = self.skills_base / target_domain / skill_id
                    
                    if not dest_path.parent.exists(): os.makedirs(dest_path.parent)
                    shutil.move(str(item), str(dest_path))
                    count += 1
                    engine.publish_mission_log("SYNC", f"✅ [ASSIMILATED]: {skill_id} -> {target_domain}", task_id)

        # Cập nhật Registry toàn cục
        await knowledge_orchestrator.sync_sovereign_registry()
        return {"status": "success", "synced_count": count}

async def run_sync(**kwargs):
    sync_agent = SyncKnowledgeElite()
    return await sync_agent.sync_all(**kwargs)
