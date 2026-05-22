import os
import json
import re
from pathlib import Path

# Cấu hình đường dẫn thưa Master
RUFLO_SKILLS_DIR = Path(r"d:\Docker\N8N\files\ruflo-main\.agents\skills")
JKAI_SKILLS_DIR = Path(r"d:\Docker\N8N\intelligence\skills")

def assimilate():
    print("[ASSIMILATION]: Bat dau can quet di san Ruflo theo quy tac 4 file thua Master...")
    
    if not RUFLO_SKILLS_DIR.exists():
        print(f"Error: Path {RUFLO_SKILLS_DIR} not found.")
        return

    count = 0
    for skill_folder in RUFLO_SKILLS_DIR.iterdir():
        if not skill_folder.is_dir(): continue
        
        skill_md = skill_folder / "SKILL.md"
        if not skill_md.exists(): continue
        
        try:
            content = skill_md.read_text(encoding="utf-8")
            
            # Trích xuất metadata
            name_match = re.search(r"name:\s*(.*)", content)
            desc_match = re.search(r"description:\s*(.*)", content)
            
            skill_id = skill_folder.name
            skill_name = name_match.group(1).strip() if name_match else skill_id
            skill_desc = desc_match.group(1).strip() if desc_match else "Elite skill assimilated from Ruflo"
            
            # Tạo thư mục JKAI
            jkai_folder = JKAI_SKILLS_DIR / skill_id
            jkai_folder.mkdir(parents=True, exist_ok=True)
            
            # 1. [META.JSON]
            meta = {
                "id": skill_id,
                "name": skill_name,
                "description": skill_desc,
                "type": "assimilated",
                "origin": "ruflo-main",
                "tags": ["ruflo", "elite", "v3"]
            }
            with open(jkai_folder / "meta.json", "w", encoding="utf-8") as f:
                json.dump(meta, f, indent=4, ensure_ascii=False)
            
            # 2. [LOGIC.PY]
            func_name = skill_id.replace("-", "_")
            logic_code = f'"""\n🧬 [ZENITH-LOGIC]: {skill_name}\n"""\nimport asyncio\n\nasync def {func_name}(**kwargs):\n    """Thuc thi ky nang dong hoa tu Ruflo thua Master."""\n    from core.utils.knowledge_brain import knowledge_brain\n    task_id = kwargs.get("task_id", "manual")\n    prompt = f"Executing {skill_name} with params: {{kwargs}}"\n    return await knowledge_brain.ask(prompt, tier=2, task_id=task_id)\n'
            with open(jkai_folder / "logic.py", "w", encoding="utf-8") as f:
                f.write(logic_code)
                
            # 3. [MANIFEST.MD]
            with open(jkai_folder / "manifest.md", "w", encoding="utf-8") as f:
                f.write(content)
                
            # 4. [TEST.PY]
            test_code = f'"""\n🧪 [ZENITH-TEST]: {skill_name}\n"""\nimport asyncio\nfrom logic import {func_name}\n\nasync def test_skill():\n    print(f"Testing {skill_id}...")\n    res = await {func_name}(test_mode=True)\n    print(f"Result: {{res}}")\n\nif __name__ == "__main__":\n    asyncio.run(test_skill())\n'
            with open(jkai_folder / "test.py", "w", encoding="utf-8") as f:
                f.write(test_code)
                
            count += 1
            if count % 20 == 0: print(f"Done: {count} skills...")
            
        except Exception as e:
            print(f"Fail: {skill_folder.name} -> {e}")

    print(f"SUCCESS: Assimilated {count} skills with 4-file rule thua Master!")

if __name__ == "__main__":
    assimilate()
