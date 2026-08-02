import os
import json
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("Guardrails.RulesLoader")

_RULES_CACHE: Optional[Dict[str, Any]] = None


def load_rules(path: Optional[str] = None) -> Dict[str, Any]:
    global _RULES_CACHE
    if _RULES_CACHE is not None:
        return _RULES_CACHE

    path = path or os.path.join(os.path.dirname(__file__), "..", "..", ".jkairules.json")
    path = os.path.abspath(path)

    if not os.path.exists(path):
        logger.warning(f"[RULES] .jkairules.json not found at {path}")
        _RULES_CACHE = {}
        return _RULES_CACHE

    try:
        with open(path, "r", encoding="utf-8") as f:
            _RULES_CACHE = json.load(f)
        logger.info(f"[RULES] Loaded rules from {path}")
    except Exception as e:
        logger.error(f"[RULES] Failed to load {path}: {e}")
        _RULES_CACHE = {}

    return _RULES_CACHE


def get_behavioral_rules() -> list:
    data = load_rules()
    return data.get("behavioral_rules", [])


def get_guardrails() -> dict:
    data = load_rules()
    return data.get("infrastructure_guardrails", {})


def get_agent_defaults() -> dict:
    data = load_rules()
    return data.get("agent_defaults", {})


def invalidate_cache():
    global _RULES_CACHE
    _RULES_CACHE = None
