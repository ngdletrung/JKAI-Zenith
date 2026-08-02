import os
import sys
import json
import logging
import httpx

logger = logging.getLogger("DynamicSkillCreator")

class DynamicSkillCreator:
    """
    🧠 [DYNAMIC-SKILL-CREATOR]: Động cơ tự tạo Skill & Prompt động chuẩn Antigravity.
    Tự động đúc Kỹ năng mới (.md + logic.py) vào thư mục intelligence/skills và nạp tức thì mà không cần restart container.
    """
    @staticmethod
    def create_skill(skill_name: str, description: str, python_code: str, category: str = "CUSTOM") -> dict:
        """Đúc một kỹ năng mới hoàn chỉnh xuống đĩa và nạp vào bản đồ nơ-ron ngay lập tức."""
        skill_name_clean = skill_name.lower().replace(" ", "_").replace("-", "_")
        target_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "intelligence", "skills", category, skill_name_clean))
        os.makedirs(target_dir, exist_ok=True)

        skill_md_path = os.path.join(target_dir, "SKILL.md")
        logic_py_path = os.path.join(target_dir, "logic.py")

        # 1. Tạo SKILL.md với metadata YAML frontmatter chuẩn
        skill_md_content = f"""---
name: {skill_name_clean}
description: {description}
category: {category}
version: 1.0.0
---

# 🧠 Skill: {skill_name_clean}

{description}

## Dynamic Execution Logic
Kỹ năng này được tự động tạo và lập trình bởi JKAI Dynamic Evolution Engine.
"""
        with open(skill_md_path, "w", encoding="utf-8") as f:
            f.write(skill_md_content)

        # 2. Tạo logic.py với mã nguồn Python hoàn chỉnh
        with open(logic_py_path, "w", encoding="utf-8") as f:
            f.write(python_code)

        # 3. Tái nạp cache của ToolRouter ngay lập tức (Zero-Downtime Hot Reload)
        try:
            from core.config import IS_DOCKER
            executor_url = os.getenv("EXECUTOR_URL", "http://ai-executor-1:8000")
            if not IS_DOCKER and "ai-executor-1" in executor_url:
                executor_url = "http://localhost:8002"
            with httpx.Client(timeout=5.0) as client:
                client.post(f"{executor_url}/invalidate_cache")
            logger.info(f"⚡ [SKILL-CREATOR-SUCCESS]: Đã nạp kỹ năng `{skill_name_clean}` vào bản đồ nơ-ron thực thi!")
        except Exception as e:
            logger.warning(f"⚠️ [SKILL-CREATOR-WARN] Hot-reload notification error: {e}")

        return {
            "status": "success",
            "skill_name": skill_name_clean,
            "skill_dir": target_dir,
            "message": f"Kỹ năng `{skill_name_clean}` đã được tự động tạo và sẵn sàng sử dụng!"
        }

dynamic_skill_creator = DynamicSkillCreator()
