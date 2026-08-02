import os
import json
import logging
import asyncio
import importlib.util
from pathlib import Path
from typing import Dict, Any, List, Optional

logger = logging.getLogger("Z-SOS.Kernel")

class PluginManager:
    """
    🏗️ Z-SOS Plugin Manager
    Handles discovery, registration, and execution of Z-SOS plugins.
    """
    def __init__(self, plugins_root: str, registry_path: str):
        self.skills_root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..", "intelligence", "skills"))
        self.registry_path = Path(registry_path)
        self._plugin_registry = {} # {id: {manifest, path, dossier_path, logic_path}}
        self.plugins: Dict[str, Dict[str, Any]] = {}
        self.registry: Dict[str, Any] = {"plugins": {}, "system": {}}

    def load_registry(self):
        if self.registry_path.exists():
            try:
                self.registry = json.loads(self.registry_path.read_text(encoding="utf-8"))
            except Exception as e:
                logger.error(f"Failed to load registry: {e}")

    def save_registry(self):
        try:
            self.registry_path.write_text(json.dumps(self.registry, indent=2, ensure_ascii=False), encoding="utf-8")
        except Exception as e:
            logger.error(f"Failed to save registry: {e}")

    async def scan_plugins(self):
        """🛡️ Quét toàn bộ thư mục skills để tìm các Plugin có 'Passport' (manifest.json)."""
        logger.info(f"🚀 [Z-SOS] Scanning all skills for Z-SOS manifests in {self.skills_root}")
        
        if not os.path.exists(self.skills_root):
            logger.error("❌ Skills directory not found!")
            return

        found_plugins = {}
        
        # Duyệt qua các thư mục con để tìm manifest.json thưa Master
        for root, dirs, files in os.walk(self.skills_root):
            if "manifest.json" in files:
                manifest_path = Path(root) / "manifest.json"
                plugin_dir = Path(root)
                plugin_id = plugin_dir.name
                
                try:
                    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                    logic_path = plugin_dir / "logic.py"
                    dossier_path = plugin_dir / "dossier.md"
                    
                    found_plugins[plugin_id] = {
                        "manifest": manifest,
                        "path": str(plugin_dir),
                        "logic_path": str(logic_path) if logic_path.exists() else None,
                        "dossier_path": str(dossier_path) if dossier_path.exists() else None
                    }
                    logger.info(f"✅ Discovered plugin: {plugin_id} (v{manifest.get('version')})")
                except Exception as e:
                    logger.error(f"❌ Error loading manifest at {manifest_path}: {e}")

        self.registry["plugins"] = found_plugins
        import datetime
        self.registry["system"]["last_scan"] = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self.save_registry()
        self.plugins = found_plugins

    def get_plugin(self, plugin_id: str) -> Optional[Dict[str, Any]]:
        return self.plugins.get(plugin_id)

    def get_dossier(self, plugin_id: str) -> Optional[str]:
        plugin = self.get_plugin(plugin_id)
        if plugin and plugin.get("dossier_path"):
            try:
                return Path(plugin["dossier_path"]).read_text(encoding="utf-8")
            except Exception:
                return None
        return None

    def validate_params(self, plugin_id: str, params: Dict[str, Any]) -> Optional[str]:
        plugin = self.get_plugin(plugin_id)
        if not plugin: return "Plugin not found."
        
        manifest = plugin.get("manifest", {})
        schema = manifest.get("schema", {}).get("input", {})
        if not schema: return None # No schema, skip validation
        
        required = schema.get("required", [])
        for req in required:
            if req not in params:
                return f"Missing required parameter: {req}"
        
        properties = schema.get("properties", {})
        for key, val in params.items():
            if key in properties:
                expected_type = properties[key].get("type")
                if expected_type == "string" and not isinstance(val, str):
                    return f"Parameter {key} must be a string."
                elif expected_type == "boolean" and not isinstance(val, bool):
                    return f"Parameter {key} must be a boolean."
                elif expected_type == "integer" and not isinstance(val, int):
                    return f"Parameter {key} must be an integer."
        
        return None

    async def execute_plugin(self, plugin_id: str, params: Dict[str, Any]) -> Dict[str, Any]:
        # Validate before execution
        error = self.validate_params(plugin_id, params)
        if error:
            return {"status": "error", "message": f"Schema Validation Error: {error}"}

        plugin = self.get_plugin(plugin_id)
        if not plugin or not plugin.get("logic_path"):
            return {"status": "error", "message": f"Plugin {plugin_id} not found or has no logic."}
        
        try:
            # For local tests, we use importlib. 
            # In production, Dispatcher calls Receptionist -> ExecutorGateway -> ai-executor ToolRouter.
            # This execute_plugin is mainly for internal brain tests or direct calls.
            spec = importlib.util.spec_from_file_location(f"z_plugin_{plugin_id}", plugin["logic_path"])
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            if hasattr(module, "execute"):
                return await module.execute(params)
            else:
                return {"status": "error", "message": f"Plugin {plugin_id} logic.py has no execute() function."}
        except Exception as e:
            logger.error(f"Execution error in plugin {plugin_id}: {e}")
            return {"status": "error", "message": str(e)}

    def match_and_load_skills(self, query: str, max_skills: int = 2) -> Dict[str, Any]:
        """
        Bộ nạp kỹ năng động (Dynamic Skill Loader):
        Quét từ khóa trong yêu cầu (goal/query), đối chiếu với tên, mô tả, tags của các kỹ năng và SKILL.md.
        Chỉ trả về các cẩm nang phù hợp nhất để tối ưu hóa token và VRAM cho Qwen3-30B trên RX6600.
        """
        query_words = set(w.lower() for w in query.split() if len(w) >= 3)
        matched_skills = []
        
        # 1. Quét trong plugins đã load từ registry
        for plugin_id, info in self.plugins.items():
            manifest = info.get("manifest", {})
            name = str(manifest.get("name", plugin_id)).lower()
            desc = str(manifest.get("description", "")).lower()
            tags = set(w.lower() for w in manifest.get("tags", []))
            
            score = 0
            for qw in query_words:
                if qw in name: score += 3
                if qw in desc: score += 2
                if qw in tags: score += 4
            
            if score > 0 or "core" in tags:
                dossier_content = ""
                if info.get("dossier_path"):
                    try:
                        dossier_content = Path(info["dossier_path"]).read_text(encoding="utf-8")
                    except Exception:
                        pass
                matched_skills.append({
                    "skill_id": plugin_id,
                    "name": manifest.get("name", plugin_id),
                    "score": score,
                    "content": dossier_content or str(manifest.get("description", ""))
                })
        
        # 2. Quét trực tiếp các file SKILL.md hoặc tệp cẩm nang trong skills_root
        if os.path.exists(self.skills_root):
            for root, _, files in os.walk(self.skills_root):
                for f_name in files:
                    if f_name.upper() in ("SKILL.MD", "DOSSIER.MD"):
                        f_path = Path(root) / f_name
                        skill_name = Path(root).name
                        if any(s["skill_id"] == skill_name for s in matched_skills):
                            continue
                        try:
                            text_preview = f_path.read_text(encoding="utf-8")[:1000].lower()
                            score = 0
                            for qw in query_words:
                                if qw in skill_name.lower(): score += 4
                                if qw in text_preview: score += 1
                            if score > 0 or "general" in skill_name.lower() or "standard" in skill_name.lower():
                                full_text = f_path.read_text(encoding="utf-8")
                                matched_skills.append({
                                    "skill_id": skill_name,
                                    "name": skill_name,
                                    "score": score,
                                    "content": full_text[:3000] # Giả lập truncation an toàn cho RAM/KV cache
                                })
                        except Exception:
                            pass

        matched_skills.sort(key=lambda x: x["score"], reverse=True)
        selected = matched_skills[:max_skills]
        
        summary_text = "\n\n".join([f"### [SKILL: {s['name']}]\n{s['content']}" for s in selected]) if selected else "Không có kỹ năng đặc biệt, áp dụng tri thức cốt lõi mặc định."
        return {
            "status": "success",
            "count": len(selected),
            "skills": [s["skill_id"] for s in selected],
            "payload": summary_text
        }

# Singleton
_AI_BRAIN_ROOT = os.path.dirname(os.path.abspath(__file__))
_REPO_ROOT = os.path.dirname(os.path.dirname(_AI_BRAIN_ROOT))
plugin_manager = PluginManager(
    plugins_root=os.getenv("JKAI_PLUGINS_ROOT", os.path.join(_REPO_ROOT, "intelligence", "skills", "plugins")),
    registry_path=os.getenv("JKAI_KERNEL_REGISTRY", os.path.join(_REPO_ROOT, "intelligence", "kernel_registry.json"))
)

