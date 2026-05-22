import os
import json
from pathlib import Path

JKAI_SKILLS_DIR = Path(r"d:\Docker\N8N\intelligence\skills")
REGISTRY_PATH = Path(r"d:\Docker\N8N\intelligence\registry.json")

def update_registry():
    print("[REGISTRY]: Dang cap nhat danh sach ky nang...")
    
    if not REGISTRY_PATH.exists():
        registry = {"skills": {}}
    else:
        with open(REGISTRY_PATH, "r", encoding="utf-8") as f:
            registry = json.load(f)
    
    count = 0
    for skill_folder in JKAI_SKILLS_DIR.iterdir():
        if not skill_folder.is_dir(): continue
        
        meta_path = skill_folder / "meta.json"
        if not meta_path.exists(): continue
        
        try:
            with open(meta_path, "r", encoding="utf-8") as f:
                meta = json.load(f)
            
            skill_id = meta["id"]
            registry["skills"][skill_id] = {
                "name": meta["name"],
                "description": meta["description"],
                "path": f"skills/{skill_id}/logic.py",
                "type": meta.get("type", "custom")
            }
            count += 1
        except Exception as e:
            print(f"Fail: {skill_folder.name} -> {e}")

    with open(REGISTRY_PATH, "w", encoding="utf-8") as f:
        json.dump(registry, f, indent=4, ensure_ascii=False)
        
    print(f"SUCCESS: Da ghi danh {count} ky nang vao Registry thua Master!")

if __name__ == "__main__":
    update_registry()
