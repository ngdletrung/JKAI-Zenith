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
            logger.error(f"❌ Execution error in plugin {plugin_id}: {e}")
            return {"status": "error", "message": str(e)}

# Singleton
plugin_manager = PluginManager(
    plugins_root="d:/Docker/JKAI/intelligence/skills/plugins",
    registry_path="d:/Docker/JKAI/intelligence/kernel_registry.json"
)
