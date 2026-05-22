import os
import shutil
import re
import json
import sys

BASE_DIR = "/workspace" if os.path.exists("/workspace") else r"D:\Docker\N8N"
QUARANTINE_DIR = os.path.join(BASE_DIR, "intelligence", "archive", "quarantine")
SKILLS_DIR = os.path.join(BASE_DIR, "intelligence", "skills")
MAP_SKILLS_FILE = os.path.join(BASE_DIR, "intelligence", "MAP_SKILLS.md")
REGISTRY_FILE = os.path.join(BASE_DIR, "intelligence", "registry_Map_skills.json")

def get_domain_from_skill_md(md_path):
    domain = "CORE"
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
            match = re.search(r'^domain:\s*(\w+)', content, re.MULTILINE)
            if match:
                domain = match.group(1).upper()
    except Exception as e:
        pass
    
    # Map to existing folders if possible
    valid_domains = ["BUSINESS", "CODING", "CORE", "DATA_SCIENCE", "DEVOPS", "FINANCE", "HUEIC_PROCESS", "RESEARCH", "SECURITY"]
    if domain not in valid_domains:
        domain = "CORE"
    return domain

def get_skill_info(md_path):
    info = {"id": "", "name": "", "desc": ""}
    try:
        with open(md_path, "r", encoding="utf-8") as f:
            content = f.read()
            # Try to get id
            match_id = re.search(r'^id:\s*(.+)', content, re.MULTILINE)
            if match_id: info["id"] = match_id.group(1).strip()
            
            # Try to get name
            match_name = re.search(r'^name_vn:\s*(.+)', content, re.MULTILINE)
            if match_name: info["name"] = match_name.group(1).strip()
            
            # Try to get desc
            match_desc = re.search(r'## 📖 TỔNG QUAN\n(.*?)\n##', content, re.DOTALL)
            if match_desc: info["desc"] = match_desc.group(1).strip().replace('\n', ' ')
            
    except Exception as e:
        pass
    return info

def refactor_logic_py(logic_path):
    try:
        with open(logic_path, "r", encoding="utf-8") as f:
            content = f.read()
            
        # Fix sys.path.append if exists (Docker uses PYTHONPATH so it's not strictly needed, but let's make it safe)
        content = re.sub(r'sys\.path\.append\(.*?\)', 'try:\n    from core.utils.engine import engine\nexcept ImportError:\n    pass', content)
        
        # Write back
        with open(logic_path, "w", encoding="utf-8") as f:
            f.write(content)
    except Exception as e:
        print(f"Error refactoring {logic_path}: {e}")

def main():
    print("🚀 [ZENITH AUTO-FORGE]: Bắt đầu rà soát và phục hồi toàn bộ quarantine skills...")
    
    restored_skills = []
    
    if not os.path.exists(QUARANTINE_DIR):
        print(f"❌ Không tìm thấy thư mục quarantine: {QUARANTINE_DIR}")
        return

    for item in os.listdir(QUARANTINE_DIR):
        item_path = os.path.join(QUARANTINE_DIR, item)
        if os.path.isdir(item_path):
            md_path = os.path.join(item_path, "SKILL.md")
            logic_path = os.path.join(item_path, "logic.py")
            
            # Only process if it has at least a SKILL.md or logic.py
            if os.path.exists(md_path) or os.path.exists(logic_path):
                domain = "CORE"
                if os.path.exists(md_path):
                    domain = get_domain_from_skill_md(md_path)
                
                target_dir = os.path.join(SKILLS_DIR, domain, item)
                
                # Check if it already exists in the target directory
                if not os.path.exists(target_dir):
                    print(f"📦 Đang phục hồi [{item}] -> {domain}")
                    shutil.copytree(item_path, target_dir)
                    
                    if os.path.exists(os.path.join(target_dir, "logic.py")):
                        refactor_logic_py(os.path.join(target_dir, "logic.py"))
                    
                    if os.path.exists(md_path):
                        info = get_skill_info(md_path)
                        if info["id"] and info["name"]:
                            restored_skills.append({
                                "id": info["id"],
                                "name": info["name"],
                                "desc": info["desc"][:100] + "..." if len(info["desc"]) > 100 else info["desc"],
                                "domain": domain,
                                "folder": item
                            })
                else:
                    print(f"⚠️ [{item}] đã tồn tại ở {target_dir}, bỏ qua.")
                    
    print(f"✅ Đã phục hồi {len(restored_skills)} skills.")
    
    # Update registry.json directly via python
    if restored_skills:
        print("🔄 Đang cập nhật MAP_SKILLS.md...")
        try:
            with open(MAP_SKILLS_FILE, "a", encoding="utf-8") as f:
                f.write("\n\n---")
                f.write("\n\n## QUÂN ĐOÀN ĐÃ PHỤC HỒI TỪ QUARANTINE\n")
                for s in restored_skills:
                    f.write(f"- **{s['id']}**: {s['name']}. {s['desc']} [{s['domain']}]\n")
            print("✅ Cập nhật MAP_SKILLS.md thành công.")
        except Exception as e:
            print(f"❌ Lỗi cập nhật MAP_SKILLS.md: {e}")
            
    print("🔄 Đang đồng bộ registry_Map_skills.json...")
    try:
        # Import engine and knowledge manager directly to sync
        sys.path.append(BASE_DIR)
        import asyncio
        from core.utils.knowledge_manager import knowledge_orchestrator
        asyncio.run(knowledge_orchestrator.sync_sovereign_registry())
        print("✅ Đồng bộ registry thành công.")
    except Exception as e:
        print(f"❌ Lỗi đồng bộ registry: {e}")

if __name__ == "__main__":
    main()
