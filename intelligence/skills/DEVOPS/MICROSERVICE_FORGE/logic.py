import os
import json
import yaml
import subprocess
from pathlib import Path
from core.utils.engine import engine
from core.utils import path_manager

class InstantForge:
    """
    ⚡ INSTANT FORGE: Giao thức Kiến tạo Dịch vụ Tức thì JKAI Zenith.
    Tự động hóa toàn bộ quy trình: Viết code -> Dockerize -> Deploy.
    """
    def __init__(self):
        self.base_dir = Path(os.getenv("WORKSPACE_ROOT", path_manager.get_root()))
        self.services_dir = self.base_dir / "services"
        self.compose_path = self.base_dir / "docker-compose.yml"

    async def forge_service(self, service_name: str, requirements: str, task_id: str = "sys"):
        """
        Khởi tạo và triển khai một service mới.
        """
        engine.publish_mission_log("FORGE_INIT", f"[FORGE]: Bắt đầu quy trình kiến tạo dịch vụ mới: `{service_name}`", task_id)

        # 1. AI Thiết kế kiến trúc
        engine.publish_mission_log("FORGE_PLAN", f"[FORGE]: Đang triệu tập Kiến trúc sư Hệ thống để thiết kế Blueprint cho `{service_name}`...", task_id)
        prompt = f"""Bạn là Kiến trúc sư Hệ thống của JKAI Zenith. 
        Nhiệm vụ: Thiết kế mã nguồn cho một Microservice Python mới.
        Yêu cầu Master: {requirements}
        Tên service: {service_name}
        
        TRẢ VỀ JSON:
        {{
            "main_py": "mã nguồn chính",
            "requirements_txt": "các thư viện cần thiết",
            "dockerfile": "Dockerfile chuẩn",
            "description": "mô tả ngắn gọn"
        }}
        """
        forge_plan = await engine.call_chat(
            messages=[{"role": "user", "content": prompt}],
            role="PLANNER",
            json_mode=True
        )

        # 2. Tạo bộ hồ sơ 5 file (Nhất thể Standard)
        target_dir = self.services_dir / service_name
        target_dir.mkdir(parents=True, exist_ok=True)
        
        (target_dir / "logic.py").write_text(forge_plan.get("main_py", ""), encoding="utf-8")
        (target_dir / "SKILL.md").write_text(f"---\nid: {service_name.upper()}\nname_vn: {service_name}\ndomain: DEVOPS\n---\n# {service_name}\n## 📖 TỔNG QUAN\n{forge_plan.get('description', '')}", encoding="utf-8")
        (target_dir / "dossier.md").write_text(f"# Hồ sơ Năng lực: {service_name}\n## 🎯 Capability Overview\n{forge_plan.get('description', '')}\n## 🛠️ Detailed Features\n- Microservice tự động được đúc cho hạ tầng Zenith.", encoding="utf-8")
        
        manifest_content = {
            "id": service_name.upper(),
            "name_vn": service_name,
            "domain": "DEVOPS",
            "rel_path": f"services/{service_name}/SKILL.md",
            "description": forge_plan.get("description", "")
        }
        (target_dir / "manifest.json").write_text(json.dumps(manifest_content, indent=4, ensure_ascii=False), encoding="utf-8")
        (target_dir / "__init__.py").write_text("# Microservice Initialization\n", encoding="utf-8")
        
        # Docker files
        (target_dir / "requirements.txt").write_text(forge_plan.get("requirements_txt", ""), encoding="utf-8")
        (target_dir / "Dockerfile").write_text(forge_plan.get("dockerfile", ""), encoding="utf-8")

        engine.publish_mission_log("FORGE_WRITE", f"[FORGE]: Đã phẫu thuật xong bộ hồ sơ 5 file và Docker cho `{service_name}`.", task_id)

        # 3. Cập nhật Docker Compose
        try:
            with open(self.compose_path, 'r', encoding='utf-8') as f:
                compose_data = yaml.safe_load(f) or {"services": {}}
            
            # Thêm service mới
            compose_data["services"][service_name] = {
                "build": f"./services/{service_name}",
                "container_name": f"jkai-{service_name}",
                "restart": "always",
                "networks": ["jkai-network"],
                "environment": ["REDIS_HOST=redis-ai"]
            }
            
            with open(self.compose_path, 'w', encoding='utf-8') as f:
                yaml.dump(compose_data, f, sort_keys=False)
            
            engine.publish_mission_log("FORGE_INFRA", f"[FORGE]: Đã cập nhật `docker-compose.yml`. Service đã sẵn sàng nạp.", task_id)
        except Exception as e:
            engine.publish_mission_log("ERROR", f"[FORGE-ERR] Lỗi cập nhật hạ tầng: {e}", task_id)

        # 📊 [MISSION DEBRIEF] - Báo cáo Lò rèn
        report = f"""# 🔥 [MISSION DEBRIEF] - INSTANT FORGE ONLINE
| Hạng mục | Thông tin |
| :--- | :--- |
| **Dịch vụ** | {service_name} |
| **Mô tả** | {forge_plan.get('description', 'Microservice chuyên biệt')} |
| **Trạng thái** | 🟡 Đã kiến tạo - Chờ Triển khai |
| **Vị trí** | `./services/{service_name}` |

**Hành động tiếp theo**: Master chỉ cần ra lệnh `Triển khai` để tôi kích hoạt Container này.
"""
        engine.publish_mission_log("MISSION_RESULT", report, task_id)

        return {"status": "success", "service": service_name, "report": report}

# 🚀 Giao thức Nhất thể hóa
_instance = InstantForge()

async def initiate_instant_forge(service_name: str, requirements: str, **kwargs):
    return await _instance.forge_service(service_name, requirements)
