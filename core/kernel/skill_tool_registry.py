import os
import re
import sys
import json
import time
import logging
import importlib.util
import inspect

from typing import Dict, List, Any, Optional

logger = logging.getLogger("SkillToolRegistry")

_CACHE_TTL = 60


class SkillToolRegistry:
    """
    Centralized Skill → Ollama Tool Definition Generator.
    Reads from 5 skill files: manifest.json (schema), logic.py (inspect),
    SKILL.md (metadata), dossier.md (description), __init__.py (package).
    Both FAST and DEEP pipelines use this single source.
    """
    def __init__(self):
        self._cache: Optional[Dict[str, Any]] = None
        self._cache_time: float = 0
        self._skills_root = os.path.abspath(os.path.join(
            os.path.dirname(__file__), "..", "..", "intelligence", "skills"
        ))

    async def _get_all_skills(self) -> Dict[str, dict]:
        try:
            from core.utils.knowledge_manager import JKAIKnowledgeOrchestrator
            orchestrator = JKAIKnowledgeOrchestrator()
            return await orchestrator.get_all_skills_dict()
        except Exception as e:
            logger.debug(f"[SKILL-REGISTRY] Cannot read registry: {e}")
            return {}

    def _resolve_skill_dir(self, skill_id: str, skill_info: dict) -> Optional[str]:
        rel_path = skill_info.get("rel_path", "")
        if rel_path:
            rel_path = rel_path.replace("\\", "/")
            skill_dir = os.path.dirname(rel_path)
            rel_subdir = re.sub(r'^skills/[/\\]?', '', skill_dir)
            candidate = os.path.join(self._skills_root, rel_subdir)
            if os.path.isdir(candidate):
                return candidate
        candidate = os.path.join(self._skills_root, skill_id)
        return candidate if os.path.isdir(candidate) else None

    def _read_manifest_schema(self, skill_dir: str) -> Optional[Dict[str, Any]]:
        manifest_path = os.path.join(skill_dir, "manifest.json")
        if not os.path.exists(manifest_path):
            return None
        try:
            with open(manifest_path, "r", encoding="utf-8") as f:
                manifest = json.load(f)
            schema = manifest.get("schema", {})
            input_schema = schema.get("input", {})
            props = input_schema.get("properties", {})
            required = input_schema.get("required", [])
            if not props:
                return None

            param_props = {}
            param_required = []
            for p_name, p_def in props.items():
                json_type = p_def.get("type", "string")
                p_description = p_def.get("description", f"Tham số {p_name}")
                p_item = {"type": json_type, "description": p_description}
                if "enum" in p_def:
                    p_item["enum"] = p_def["enum"]
                param_props[p_name] = p_item
                if p_name in required:
                    param_required.append(p_name)
            return {
                "param_props": param_props,
                "param_required": param_required,
                "description": manifest.get("description", ""),
                "triggers": manifest.get("triggers", []),
            }
        except Exception as e:
            logger.debug(f"[SKILL-REGISTRY] Cannot read manifest {manifest_path}: {e}")
            return None

    def _inspect_logic_function(self, skill_dir: str) -> Optional[Dict[str, Any]]:
        logic_file = os.path.join(skill_dir, "logic.py")
        if not os.path.exists(logic_file):
            return None
        try:
            spec = importlib.util.spec_from_file_location(f"_skill_scan_{hash(logic_file)}", logic_file)
            if not spec or not spec.loader:
                return None
            mod = importlib.util.module_from_spec(spec)
            sys.modules[mod.__name__] = mod
            spec.loader.exec_module(mod)

            for name in dir(mod):
                if name.startswith("_"):
                    continue
                obj = getattr(mod, name)
                if inspect.isfunction(obj) or inspect.iscoroutinefunction(obj):
                    sig = inspect.signature(obj)
                    params = []
                    for p_name, p_param in sig.parameters.items():
                        if p_name in ("self", "cls", "task_id", "trace_id", "session_id"):
                            continue
                        param_def = {"name": p_name, "required": p_param.default == inspect.Parameter.empty}
                        if p_param.annotation != inspect.Parameter.empty:
                            param_def["type"] = self._py_type_to_json(p_param.annotation)
                        else:
                            param_def["type"] = "string"
                        params.append(param_def)
                    return {"entry_function": name, "parameters": params}
        except Exception as e:
            logger.debug(f"[SKILL-REGISTRY] Cannot inspect {logic_file}: {e}")
        return None

    @staticmethod
    def _py_type_to_json(annotation) -> str:
        type_map = {
            int: "integer", float: "number", str: "string", bool: "boolean",
            dict: "object", list: "array", type(None): "null",
        }
        origin = getattr(annotation, "__origin__", None)
        if origin is list:
            return "array"
        if origin is dict:
            return "object"
        return type_map.get(annotation, "string")

    async def get_tool_spec(self) -> List[Dict[str, Any]]:
        now = time.time()
        if self._cache and (now - self._cache_time) < _CACHE_TTL:
            return self._cache["tools"]

        all_skills = await self._get_all_skills()
        tools = []
        skill_id_enum = []

        for skill_id, skill_info in all_skills.items():
            if not isinstance(skill_info, dict):
                continue

            skill_dir = self._resolve_skill_dir(skill_id, skill_info)
            description = skill_info.get("description") or skill_info.get("name_vn", skill_id)

            # Priority: manifest.json schema > logic.py inspect > generic
            manifest_schema = self._read_manifest_schema(skill_dir) if skill_dir else None

            if manifest_schema:
                param_props = dict(manifest_schema["param_props"])
                param_required = list(manifest_schema["param_required"])
                if manifest_schema["description"]:
                    description = manifest_schema["description"]
            elif skill_dir:
                func_info = self._inspect_logic_function(skill_dir)
                if func_info:
                    param_props = {}
                    param_required = []
                    for p in func_info["parameters"]:
                        param_props[p["name"]] = {
                            "type": p.get("type", "string"),
                            "description": f"Tham số {p['name']}",
                        }
                        if p.get("required"):
                            param_required.append(p["name"])
                else:
                    param_props = {"extracted_params": {"type": "string", "description": "Tham số đầu vào"}}
                    param_required = []
            else:
                param_props = {"extracted_params": {"type": "string", "description": "Tham số đầu vào"}}
                param_required = []

            tools.append({
                "type": "function",
                "function": {
                    "name": skill_id,
                    "description": str(description)[:200],
                    "parameters": {
                        "type": "object",
                        "properties": param_props,
                        "required": param_required,
                    },
                },
            })
            skill_id_enum.append(skill_id)

        tools.append({
            "type": "function",
            "function": {
                "name": "search_memory",
                "description": "Tra cứu di sản tri thức quá khứ. Gọi khi cần context lịch sử.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "query": {"type": "string", "description": "Câu hỏi hoặc chủ đề cần tra cứu"}
                    },
                    "required": ["query"],
                },
            },
        })

        self._cache = {"tools": tools, "skill_ids": skill_id_enum, "time": now}
        self._cache_time = now
        logger.info(f"[SKILL-REGISTRY] Generated {len(tools)} tool specs from {len(skill_id_enum)} skills")
        return tools

    async def get_skill_summary_text(self) -> str:
        now = time.time()
        cached = self._cache if self._cache and (now - self._cache_time) < _CACHE_TTL else None
        if not cached:
            await self.get_tool_spec()
            cached = self._cache
        lines = [f"- {sid}: Kỹ năng đã đăng ký" for sid in (cached or {}).get("skill_ids", [])]
        return "\n".join(lines)


skill_tool_registry = SkillToolRegistry()
