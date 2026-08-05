#!/usr/bin/env python3
"""
🤖 Agent Metadata Parser & Dynamic Router for JKAI Zenith.
Parses YAML frontmatter from agent definition files (.md) in intelligence/agents/
and dynamically selects the optimal Agent based on task requirements.
"""

import os
import re
import json
import logging
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger("AgentRouter")

try:
    import yaml
    HAS_YAML = True
except ImportError:
    HAS_YAML = False


class AgentRouter:
    """
    Dispatcher & Schema Resolver for JKAI Zenith Agents.
    Scans agent markdown files, extracts YAML frontmatter, and routes incoming tasks.
    """
    def __init__(self, agents_dir: Optional[str] = None):
        default_dir = os.path.join(os.getenv("WORKSPACE_ROOT", r"D:\Docker\JKAI"), "intelligence", "agents")
        self.agents_dir = Path(agents_dir or default_dir)
        self._agent_cache: Dict[str, Dict[str, Any]] = {}
        self.reload_agents()

    def _extract_frontmatter(self, file_path: Path) -> Dict[str, Any]:
        """Extracts and parses YAML frontmatter from markdown file."""
        try:
            content = file_path.read_text(encoding="utf-8")
            # Look for frontmatter enclosed by --- at the top of file
            match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", content, re.DOTALL)
            if not match:
                # Fallback: Extract basic metadata from Markdown headings if YAML frontmatter missing
                from core.utils.engine import engine
                def_cfg = engine.get_role_config("EXECUTOR") or engine.get_role_config("RECEPTIONIST")
                def_model = def_cfg.get("model") if isinstance(def_cfg, dict) else getattr(def_cfg, "model", "auto")
                return {
                    "name": name,
                    "file_path": str(file_path),
                    "description": f"Agent auto-derived from {file_path.name}",
                    "capabilities": [name],
                    "tools": [],
                    "model_preference": def_model,
                    "system_prompt": content.strip()
                }

            yaml_text = match.group(1)
            prompt_text = match.group(2).strip()

            metadata = yaml.safe_load(yaml_text) if HAS_YAML else self._fallback_yaml_parse(yaml_text)
            metadata["file_path"] = str(file_path)
            metadata["system_prompt"] = prompt_text
            if "name" not in metadata:
                metadata["name"] = file_path.stem.replace("agent_", "")
            return metadata
        except Exception as e:
            logger.warning(f"[AGENT-ROUTER] Failed to parse frontmatter from {file_path.name}: {e}")
            from core.utils.engine import engine
            def_cfg = engine.get_role_config("EXECUTOR") or engine.get_role_config("RECEPTIONIST")
            def_model = def_cfg.get("model") if isinstance(def_cfg, dict) else getattr(def_cfg, "model", "auto")
            return {
                "name": file_path.stem.replace("agent_", ""),
                "file_path": str(file_path),
                "description": file_path.stem,
                "capabilities": [],
                "tools": [],
                "model_preference": def_model,
                "system_prompt": ""
            }

    @staticmethod
    def _fallback_yaml_parse(yaml_text: str) -> Dict[str, Any]:
        """Minimal regex-based YAML parser if PyYAML is not installed."""
        result = {}
        for line in yaml_text.splitlines():
            line = line.strip()
            if ":" in line and not line.startswith("#"):
                key, val = line.split(":", 1)
                key = key.strip()
                val = val.strip().strip("'\"")
                if val.startswith("[") and val.endswith("]"):
                    items = [i.strip().strip("'\"") for i in val[1:-1].split(",") if i.strip()]
                    result[key] = items
                else:
                    result[key] = val
        return result

    def reload_agents(self) -> int:
        """Rescans directory and caches all available agents."""
        self._agent_cache.clear()
        if not self.agents_dir.exists():
            logger.warning(f"[AGENT-ROUTER] Agents directory not found: {self.agents_dir}")
            return 0

        for md_file in self.agents_dir.glob("*.md"):
            agent_data = self._extract_frontmatter(md_file)
            agent_name = str(agent_data["name"]).lower()
            self._agent_cache[agent_name] = agent_data
            self._agent_cache[agent_name.replace("-", "_")] = agent_data

        logger.info("[AGENT-ROUTER] Successfully loaded %s agents.", len(self._agent_cache))
        return len(self._agent_cache)

    def list_agents(self) -> List[Dict[str, Any]]:
        """Returns a list of all registered agents and their capabilities."""
        return [
            {
                "name": data["name"],
                "description": data.get("description", ""),
                "capabilities": data.get("capabilities", []),
                "model": data.get("model_preference", "qwen3.5:4b")
            }
            for data in self._agent_cache.values()
        ]

    def route_task(self, prompt: str, forced_agent: Optional[str] = None) -> Dict[str, Any]:
        """
        Determines the most suitable Agent for a given prompt based on keywords & capabilities.
        """
        if forced_agent and forced_agent.lower() in self._agent_cache:
            return self._agent_cache[forced_agent.lower()]

        prompt_lower = prompt.lower()
        
        # Keyword-based capability routing matrix (supports both accented & unaccented Vietnamese)
        routing_rules = [
            ("planner", ["kế hoạch", "ke hoach", "plan", "roadmap", "phân rã", "chiến lược", "strategy"]),
            ("critic", ["đánh giá", "danh gia", "review", "audit", "critic", "pháp lý", "phap ly", "kiểm tra", "kiem tra"]),
            ("security_architect", ["bảo mật", "bao mat", "security", "guardrail", "vulnerability", "lỗ hổng", "auth"]),
            ("performance_engineer", ["benchmark", "tiết kiệm", "tiet kiem", "hiệu năng", "hieu nang", "tối ưu", "speed", "opt"]),
            ("scholar", ["nghiên cứu", "nghien cuu", "paper", "đọc", "doc", "tra cứu", "tra cuu", "literature"]),
            ("executor", ["code", "viết code", "chạy", "chay", "sửa", "sua", "run", "execute", "build", "script"]),
        ]

        for agent_name, keywords in routing_rules:
            for kw in keywords:
                # Use word boundary search for short/ascii keywords to prevent partial substring matches
                pattern = r'\b' + re.escape(kw) + r'\b'
                if re.search(pattern, prompt_lower):
                    agent_key = agent_name.replace("-", "_")
                    cached_agent = self._agent_cache.get(agent_key) or self._agent_cache.get(agent_name)
                    if cached_agent:
                        logger.info("[AGENT-ROUTER] Routed prompt to agent: `%s` (matched '%s')", agent_name, kw)
                        return cached_agent

        # Default fallback to executor or coordinator
        fallback = self._agent_cache.get("executor") or self._agent_cache.get("coordinator")
        if not fallback and self._agent_cache:
            fallback = next(iter(self._agent_cache.values()))

        return fallback or {
            "name": "default_executor",
            "system_prompt": "You are the primary execution agent.",
            "model_preference": "qwen3.5:4b"
        }


agent_router = AgentRouter()
