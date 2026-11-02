# -*- coding: utf-8 -*-
"""
services/ai_desktop/app_policy.py
Single-source-of-truth loader for the desktop mutation policy.

The policy lives in config/security/desktop_app_allowlist.json. Any missing or
malformed field fails closed (DesktopPolicyError) instead of falling back to a
hard-coded default, so a broken policy file can never silently widen scope.
"""

import json
import os
import threading
from dataclasses import dataclass
from typing import Any, Dict, FrozenSet, Optional, Tuple

DEFAULT_POLICY_PATH = os.path.abspath(
    os.path.join(os.path.dirname(__file__), "..", "..", "config", "security", "desktop_app_allowlist.json")
)
POLICY_PATH_ENV = "JKAI_DESKTOP_POLICY_PATH"

KNOWN_ACTIONS = frozenset({"click", "type_text", "focus", "key_combo", "scroll"})


class DesktopPolicyError(RuntimeError):
    """Raised when the desktop policy is missing, malformed, or self-inconsistent."""


def _as_frozenset(value: Any, field: str, allow_empty: bool) -> FrozenSet[str]:
    if type(value) is not list:
        raise DesktopPolicyError(f"POLICY_FIELD_NOT_LIST: {field}")
    items = []
    for item in value:
        if type(item) is not str or not item.strip():
            raise DesktopPolicyError(f"POLICY_FIELD_INVALID_ITEM: {field}")
        items.append(item.strip().casefold())
    if not items and not allow_empty:
        raise DesktopPolicyError(f"POLICY_FIELD_EMPTY: {field}")
    return frozenset(items)


@dataclass(frozen=True)
class AppRule:
    """Per-process scope: which actions and which elements are permitted."""

    process_name: str
    app_name: str
    allowed_actions: FrozenSet[str]
    element_allowlist: FrozenSet[str]
    max_text_length: Optional[int]
    allow_raw_xy: bool

    def allows_action(self, action_type: str) -> bool:
        return str(action_type).casefold() in self.allowed_actions

    def allows_element_identifier(self, identifier: str) -> bool:
        """True only for a non-empty identifier present in the element allowlist."""
        key = str(identifier or "").strip().casefold()
        return bool(key) and key in self.element_allowlist

    def allows_element(self, name: str, automation_id: str, class_name: str, control_type: str) -> Tuple[bool, str]:
        """
        Match an element against the configured allowlist.

        Only identity fields (element Name and AutomationId) are matched. Generic
        ClassName/ControlType values like "Edit" or "Button" would otherwise
        allowlist every control of that class in the process, including password
        fields, so they are deliberately ignored. An empty allowlist denies every
        element (fail closed), it never means "anything goes".
        """
        if not self.element_allowlist:
            return False, "ELEMENT_ALLOWLIST_EMPTY"

        candidates = {
            str(value).strip().casefold()
            for value in (name, automation_id)
            if value and str(value).strip()
        }
        if candidates & self.element_allowlist:
            return True, "ELEMENT_ALLOWLISTED"
        return False, f"ELEMENT_NOT_ALLOWLISTED: {sorted(candidates)}"


@dataclass(frozen=True)
class DesktopActionPolicy:
    """Validated, immutable view of config/security/desktop_app_allowlist.json."""

    version: str
    policy_name: str
    destructive_keywords: FrozenSet[str]
    read_only_sampler_port: int
    apps: Dict[str, AppRule]

    def app_rule(self, process_name: str) -> Optional[AppRule]:
        if not process_name:
            return None
        return self.apps.get(str(process_name).strip().casefold())

    @property
    def allowed_processes(self) -> FrozenSet[str]:
        return frozenset(self.apps.keys())

    @classmethod
    def load(cls, path: Optional[str] = None) -> "DesktopActionPolicy":
        resolved = os.path.abspath(path or os.getenv(POLICY_PATH_ENV) or DEFAULT_POLICY_PATH)
        if not os.path.isfile(resolved):
            raise DesktopPolicyError(f"POLICY_FILE_MISSING: {resolved}")

        try:
            with open(resolved, "r", encoding="utf-8") as handle:
                data = json.load(handle)
        except Exception as exc:  # noqa: BLE001 - surfaced as a typed policy error
            raise DesktopPolicyError(f"POLICY_FILE_UNREADABLE: {exc}") from exc

        if type(data) is not dict:
            raise DesktopPolicyError("POLICY_ROOT_NOT_OBJECT")

        version = data.get("version")
        if type(version) is not str or not version.strip():
            raise DesktopPolicyError("POLICY_VERSION_INVALID")

        policy_name = data.get("policy_name", "JKAI_DESKTOP_POLICY")
        if type(policy_name) is not str or not policy_name.strip():
            raise DesktopPolicyError("POLICY_NAME_INVALID")

        destructive = _as_frozenset(data.get("destructive_keywords"), "destructive_keywords", allow_empty=True)

        invariants = data.get("global_invariants") or {}
        if type(invariants) is not dict:
            raise DesktopPolicyError("POLICY_GLOBAL_INVARIANTS_INVALID")
        sampler_port = invariants.get("pure_read_only_sampler_port", 9997)
        if type(sampler_port) is not int or sampler_port <= 0 or sampler_port > 65535:
            raise DesktopPolicyError("POLICY_SAMPLER_PORT_INVALID")

        raw_apps = data.get("allowed_applications")
        if type(raw_apps) is not dict or not raw_apps:
            raise DesktopPolicyError("POLICY_ALLOWED_APPLICATIONS_EMPTY")

        apps: Dict[str, AppRule] = {}
        for raw_process, raw_rule in raw_apps.items():
            if type(raw_process) is not str or not raw_process.strip():
                raise DesktopPolicyError("POLICY_PROCESS_NAME_INVALID")
            if type(raw_rule) is not dict:
                raise DesktopPolicyError(f"POLICY_APP_RULE_NOT_OBJECT: {raw_process}")

            actions = _as_frozenset(raw_rule.get("allowed_actions"), f"{raw_process}.allowed_actions", allow_empty=False)
            unknown = actions - KNOWN_ACTIONS
            if unknown:
                raise DesktopPolicyError(f"POLICY_UNKNOWN_ACTIONS: {raw_process}: {sorted(unknown)}")

            elements = _as_frozenset(
                raw_rule.get("element_allowlist", []), f"{raw_process}.element_allowlist", allow_empty=True
            )

            max_text_length = raw_rule.get("max_text_length")
            if max_text_length is not None:
                if type(max_text_length) is not int or max_text_length <= 0 or max_text_length > 5000:
                    raise DesktopPolicyError(f"POLICY_MAX_TEXT_LENGTH_INVALID: {raw_process}")

            allow_raw_xy = raw_rule.get("allow_raw_xy", False)
            if type(allow_raw_xy) is not bool:
                raise DesktopPolicyError(f"POLICY_ALLOW_RAW_XY_INVALID: {raw_process}")

            app_name = raw_rule.get("app_name", raw_process)
            if type(app_name) is not str:
                raise DesktopPolicyError(f"POLICY_APP_NAME_INVALID: {raw_process}")

            apps[raw_process.strip().casefold()] = AppRule(
                process_name=raw_process.strip().casefold(),
                app_name=app_name,
                allowed_actions=actions,
                element_allowlist=elements,
                max_text_length=max_text_length,
                allow_raw_xy=allow_raw_xy,
            )

        return cls(
            version=version.strip(),
            policy_name=policy_name.strip(),
            destructive_keywords=destructive,
            read_only_sampler_port=sampler_port,
            apps=apps,
        )


_POLICY_LOCK = threading.Lock()
_POLICY_CACHE: Dict[Tuple[str, float, int], DesktopActionPolicy] = {}


def get_policy(path: Optional[str] = None) -> DesktopActionPolicy:
    """Load (and cache by path + mtime + size) the desktop action policy."""
    resolved = os.path.abspath(path or os.getenv(POLICY_PATH_ENV) or DEFAULT_POLICY_PATH)
    try:
        stat = os.stat(resolved)
    except OSError as exc:
        raise DesktopPolicyError(f"POLICY_FILE_MISSING: {resolved}") from exc

    key = (resolved, stat.st_mtime, stat.st_size)
    with _POLICY_LOCK:
        cached = _POLICY_CACHE.get(key)
        if cached is None:
            cached = DesktopActionPolicy.load(resolved)
            _POLICY_CACHE.clear()
            _POLICY_CACHE[key] = cached
        return cached
