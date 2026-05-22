import os
import re
import json
import asyncio
import sys
import time
import uuid
from pathlib import Path

# [TERMINAL-UNICODE-FIX]
if sys.platform == "win32":
    try: sys.stdout.reconfigure(encoding='utf-8')
    except: pass

script_dir = Path(__file__).parent.absolute()
project_root = script_dir.parent
os.chdir(project_root)

if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from core.utils.engine import engine
from core.qdrant_client import qdrant_client

async def sync_skills_hierarchical(task_id: str = "sys_sync"):
    engine.publish_mission_log("SYNC", "Khởi động Giao thức Blitz-Skill: Đồng bộ năng lực siêu tốc thưa Master...", task_id)
    
    registry_path = project_root / "intelligence" / "registry_Map_skills.json"
    if not registry_path.exists():
        engine.publish_mission_log("SYNC", f"❌ [ERR]: Khong tim thay registry ({registry_path}) thua Master.", task_id)
        return

    with open(registry_path, "r", encoding="utf-8") as f:
        registry = json.load(f)
        skills_db = registry.get("skills", {})

    total_skills = len(skills_db)
    engine.publish_mission_log("SYNC", f"🧠 [NEURAL-SCAN]: Tim thay {total_skills} ky nang thưa Ngài.", task_id)

    # 🚀 [NEURAL-BUFFER]: Buffer de batch upsert thưa Master
    point_buffer = []
    count = 0
    
    # 💎 [PARALLEL-PREPARATION]: Chuan bi du lieu de embedding song song
    skill_list = list(skills_db.items())
    batch_size = 32 # So luong ky nang xu ly song song thưa Master

    for i in range(0, total_skills, batch_size):
        current_batch = skill_list[i:i+batch_size]
        
        # Xay dung input text cho batch
        batch_inputs = []
        batch_metadata = []
        
        for s_name, s_data in current_batch:
            s_desc = s_data.get("description") or s_data.get("notes", "") or s_data.get("name_vn", "")
            s_features = s_data.get("features", [])
            s_rating = s_data.get("rating", 1)
            s_tier = s_data.get("tier", s_data.get("domain", "Unknown Domain"))
            
            if len(s_desc) < 2 and not s_features: continue
            
            features_text = ", ".join(s_features) if s_features else "Standard features"
            input_text = f"Skill Name: {s_name}\nDomain: {s_tier}\nCapability: {s_desc}\nFeatures: {features_text}"
            
            batch_inputs.append(input_text)
            batch_metadata.append({
                "skill_id": s_name, "name": s_name, "description": s_desc,
                "rating": s_rating, "features": s_features, "tier": s_tier
            })

        # ⚡ [PARALLEL-EMBEDDING]: Ma hoa toan bo batch trong mot nhip thưa Master
        embeddings = await asyncio.gather(*[engine.get_embeddings(text) for text in batch_inputs], return_exceptions=True)
        
        for (meta, vector) in zip(batch_metadata, embeddings):
            if isinstance(vector, Exception) or not vector: continue
            
            point_buffer.append({
                "id": str(uuid.uuid5(uuid.NAMESPACE_DNS, meta["skill_id"])),
                "vector": vector,
                "payload": { **meta, "timestamp": time.time() }
            })
            count += 1

        # ⚡ [BATCH-UPSERT]: Phong thich vao Qdrant thưa Master
        if point_buffer:
            await qdrant_client.upsert_batch(point_buffer, "jkai_skills")
            print(f"  Blitz-Skill: Processed {count}/{total_skills} neurons thưa Master...")
            point_buffer.clear()

    if count > 0:
        engine.publish_mission_log("SYNC", f"✅ [SUCCESS]: Đã nạp {count} nơ-ron năng lực vào Vỏ não Thần kinh thưa Master!", task_id)
    else:
        engine.publish_mission_log("SYNC", "⚠️ [IDLE]: Không có nơ-ron năng lực mới nào đủ tiêu chuẩn đồng hóa thưa Master. (Vui lòng kiểm tra mô tả kỹ năng)", task_id)
    
    sync_file = project_root / "intelligence" / "last_sync_skills.json"
    with open(sync_file, "w") as f:
        json.dump({"last_sync_time": time.time(), "skills_count": count}, f)

if __name__ == "__main__":
    t_id = sys.argv[1] if len(sys.argv) > 1 else "sys_sync"
    asyncio.run(sync_skills_hierarchical(t_id))
