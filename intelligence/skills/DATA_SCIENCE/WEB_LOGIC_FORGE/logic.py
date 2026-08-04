import os
import json
import logging
from pathlib import Path

logger = logging.getLogger("jkai.neural_eye.logic")

async def forge_web_skill(domain: str, skill_name: str, code: str, capability: str, **kwargs):
    """
    💎 GIAO THỨC ĐÚC KỸ NĂNG THỊ GIÁC (NEURAL EYE FORGE)
    Tự động tạo bộ hồ sơ 5 file cho kỹ năng web mới.
    """
    base_path = Path("d:/Docker/JKAI/intelligence/skills/neural_eye")
    target_dir = base_path / "domains" / domain / skill_name
    target_dir.mkdir(parents=True, exist_ok=True)
    registry_path = base_path / "registry.json"
    
    try:
        # 1. Ghi bộ hồ sơ 5 file (Nhất thể Standard)
        (target_dir / "logic.py").write_text(code, encoding="utf-8")
        (target_dir / "SKILL.md").write_text(f"---\nid: web_{domain}_{skill_name}\nname_vn: {skill_name}\ndomain: {domain}\n---\n# {skill_name}\n## 📖 TỔNG QUAN\n{capability}", encoding="utf-8")
        (target_dir / "dossier.md").write_text(f"# Hồ sơ Năng lực: {skill_name}\n## 🎯 Capability Overview\n{capability}\n## 🛠️ Detailed Features\n- Tự động hóa trích xuất dữ liệu từ web cho domain {domain}.", encoding="utf-8")
        
        manifest_content = {
            "id": f"web_{domain}_{skill_name}",
            "name_vn": skill_name,
            "domain": domain,
            "rel_path": f"skills/neural_eye/domains/{domain}/{skill_name}/SKILL.md",
            "capability": capability
        }
        (target_dir / "manifest.json").write_text(json.dumps(manifest_content, indent=4, ensure_ascii=False), encoding="utf-8")
        (target_dir / "__init__.py").write_text("# Web Logic Skill\n", encoding="utf-8")
            
        # 2. Cập nhật Registry (vẫn giữ logic cũ cho file registry.json riêng của neural_eye)
        if registry_path.exists():
            with open(registry_path, "r", encoding="utf-8") as f:
                registry = json.load(f)
        else:
            registry = {"skills": {}}
            
        skill_id = f"web_{domain}_{skill_name}"
        registry["skills"][skill_id] = manifest_content
        registry["skills"][skill_id]["learned_at"] = os.path.getmtime(str(target_dir / "logic.py"))
        
        with open(registry_path, "w", encoding="utf-8") as f:
            json.dump(registry, f, ensure_ascii=False, indent=4)
            
        return {
            "status": "success",
            "msg": f"✅ Bộ hồ sơ 5 file của kỹ năng `{skill_name}` đã được đúc thành công!",
            "skill_id": skill_id
        }
    except Exception as e:
        logger.error("[NEURAL-EYE-FORGE-ERR] %s", e)
        return {"status": "error", "msg": str(e)}
