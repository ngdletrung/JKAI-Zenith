import os
import yaml
import json
import re

# =================================================================
# 🌐 JKAI ZENITH: LOGIC THẤU THỊ KIẾN TRÚC (DEEP PROJECT CONTEXT)
# =================================================================

def scan_system_architecture(root_path: str = os.getenv("WORKSPACE_ROOT", "D:/Docker/N8N")):
    """
    Phân tích toàn diện kiến trúc hệ thống: Docker, Network, Volumes và Logic.
    """
    print(f"[JKAI-DEEP-CONTEXT] Scanning system architecture at: {root_path}")
    
    context_map = {
        "services": {},
        "networks": [],
        "volumes": [],
        "environment_vars": [],
        "agent_roles": {},
        "status": "partial"
    }

    try:
        # 1. Phân tích Docker Compose
        compose_path = os.path.join(root_path, "docker-compose.yml")
        if os.path.exists(compose_path):
            with open(compose_path, "r", encoding="utf-8") as f:
                compose_data = yaml.safe_load(f)
                services = compose_data.get("services", {})
                for name, cfg in services.items():
                    context_map["services"][name] = {
                        "image": cfg.get("image"),
                        "ports": cfg.get("ports", []),
                        "volumes": cfg.get("volumes", []),
                        "depends_on": cfg.get("depends_on", []),
                        "networks": cfg.get("networks", [])
                    }
                context_map["networks"] = list(compose_data.get("networks", {}).keys())
                context_map["volumes"] = list(compose_data.get("volumes", {}).keys())

        # 2. Phân tích .env (Anonymized)
        env_path = os.path.join(root_path, ".env")
        if os.path.exists(env_path):
            with open(env_path, "r", encoding="utf-8") as f:
                for line in f:
                    if "=" in line and not line.startswith("#"):
                        key = line.split("=")[0].strip()
                        context_map["environment_vars"].append(key)

        # 3. Phân tích Vai trò Đặc vụ (Agents)
        agents_map_path = os.path.join(root_path, "intelligence", "MAP_AGENTS.md")
        if os.path.exists(agents_map_path):
            with open(agents_map_path, "r", encoding="utf-8") as f:
                content = f.read()
                # Regex hỗ trợ định dạng bảng (Markdown Table)
                matches = re.findall(r'\|.*?\|.*?\*\*(.*?)\*\*.*?\|.*?`(.*?)`', content)
                for name, soul in matches:
                    context_map["agent_roles"][name.strip()] = soul.strip()

        context_map["status"] = "complete"
        
        # 4. Xuất file kết quả vào Vault để RAG có thể truy cập
        output_path = os.path.join(root_path, "intelligence", "vault", "SYSTEM_DEEP_MAP.json")
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(context_map, f, indent=4, ensure_ascii=False)

        return {
            "status": "success",
            "msg": "Đã hoàn thành Thấu thị Kiến trúc. Bản đồ hệ thống đã được lưu vào Vault.",
            "summary": f"Phát hiện {len(context_map['services'])} services, {len(context_map['agent_roles'])} agents."
        }

    except Exception as e:
        return {"status": "error", "msg": f"Lỗi thấu thị: {str(e)}"}

if __name__ == "__main__":
    res = scan_system_architecture()
    print(json.dumps(res, indent=2, ensure_ascii=True))
