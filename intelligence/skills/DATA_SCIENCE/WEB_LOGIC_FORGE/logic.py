import os
import json
import logging

logger = logging.getLogger("jkai.neural_eye.logic")

async def forge_web_skill(domain: str, skill_name: str, code: str, capability: str, **kwargs):
    """
    💎 GIAO THỨC ĐÚC KỸ NĂNG THỊ GIÁC (NEURAL EYE FORGE)
    Tự động tạo file code và cập nhật Registry cho kỹ năng web mới.
    """
    base_path = "d:/Docker/N8N/intelligence/skills/neural_eye"
    domain_path = os.path.join(base_path, "domains", domain)
    os.makedirs(domain_path, exist_ok=True)
    
    file_path = os.path.join(domain_path, f"{skill_name}.py")
    registry_path = os.path.join(base_path, "registry.json")
    
    try:
        # 1. Ghi file code Python
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(code)
            
        # 2. Cập nhật Registry
        if os.path.exists(registry_path):
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
        else:
            registry = {"skills": {}}
            
        skill_id = f"web_{domain}_{skill_name}"
        registry["skills"][skill_id] = {
            "domain": domain,
            "name": skill_name,
            "capability": capability,
            "path": file_path,
            "learned_at": os.path.getmtime(file_path)
        }
        
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, ensure_ascii=False, indent=4)
            
        return {
            "status": "success",
            "msg": f"✅ Kỹ năng `{skill_name}` cho `{domain}` đã được đúc thành công!",
            "skill_id": skill_id
        }
    except Exception as e:
        logger.error(f"❌ [NEURAL-EYE-FORGE-ERR]: {e}")
        return {"status": "error", "msg": str(e)}
