# -*- coding: utf-8 -*-
"""
services/ai_desktop/uia_cache.py
[UIA CACHEREQUEST ADAPTER - ADAPTED FROM WINDOWS-USE]

Portions adapted from CursorTouch/Windows-Use
(https://github.com/CursorTouch/Windows-Use), `windows_use/agent/tree/cache_utils.py`
(MIT License, Copyright (c) 2025 CursorTouch). The vendored `windows_use/uia`
fork that file builds on is Apache-2.0. See NOTICE.md, CREDITS.md,
LICENSES/MIT.txt and LICENSES/Apache-2.0.txt.

Why this exists: `FindAllBuildCache` returns a whole subtree from one
cross-process COM call with exactly the properties the inspector reads.
The previous path issued several COM calls per element, which is slow on
large trees and mixes values captured at different moments, weakening the
snapshot hash used for TOCTOU checks.

The adapter is deliberately read-only and side-effect free: it only builds a
cache request and reads element properties. Every helper returns a safe
fallback instead of raising, so a host without full UIA support keeps the
existing non-cached path.
"""

from __future__ import annotations

from typing import Any, Dict, Optional, Tuple

# UIA property/pattern ids are stable. Prefer the comtypes-generated names and
# fall back to the documented numeric ids when an older typelib lacks them.
_PROPERTY_IDS: Tuple[Tuple[str, int], ...] = (
    ("UIA_NamePropertyId", 30005),
    ("UIA_AutomationIdPropertyId", 30011),
    ("UIA_ClassNamePropertyId", 30012),
    ("UIA_ControlTypePropertyId", 30003),
    ("UIA_IsEnabledPropertyId", 30010),
    ("UIA_IsOffscreenPropertyId", 30022),
    ("UIA_BoundingRectanglePropertyId", 30001),
    ("UIA_HelpTextPropertyId", 30013),
    ("UIA_HasKeyboardFocusPropertyId", 30008),
    ("UIA_IsKeyboardFocusablePropertyId", 30009),
    ("UIA_IsPasswordPropertyId", 30019),
    ("UIA_LocalizedControlTypePropertyId", 30004),
    ("UIA_AcceleratorKeyPropertyId", 30006),
    ("UIA_IsControlElementPropertyId", 30016),
)

_PATTERN_IDS: Tuple[Tuple[str, int], ...] = (
    ("UIA_ScrollPatternId", 10004),
    ("UIA_WindowPatternId", 10001),
    ("UIA_LegacyIAccessiblePatternId", 10018),
)


def _constant(module: Any, name: str, fallback: int) -> int:
    value = getattr(module, name, fallback)
    return value if isinstance(value, int) else fallback


def build_tree_cache_request(uia: Any, module: Any = None) -> Any:
    """Build a CacheRequest covering the properties the inspector reads.

    `module` defaults to `comtypes.gen.UIAutomationClient`; tests inject a
    stand-in. Raises only if `uia.CreateCacheRequest()` itself fails.
    """
    if module is None:
        from comtypes.gen import UIAutomationClient as module  # type: ignore[no-redef]

    request = uia.CreateCacheRequest()
    element_scope = _constant(module, "TreeScope_Element", 1)
    children_scope = _constant(module, "TreeScope_Children", 2)
    request.TreeScope = element_scope | children_scope
    for name, fallback in _PROPERTY_IDS:
        request.AddProperty(_constant(module, name, fallback))
    for name, fallback in _PATTERN_IDS:
        request.AddPattern(_constant(module, name, fallback))
    return request


def find_all_cached(
    uia: Any,
    root: Any,
    scope: int,
    condition: Any,
    cache_request: Any,
) -> Optional[Any]:
    """Return a cached element array, or None when the host cannot cache.

    Tries the automation object first, then the root element, then gives the
    caller a clean fallback to plain `FindAll`.
    """
    for owner in (uia, root):
        finder = getattr(owner, "FindAllBuildCache", None)
        if not callable(finder):
            continue
        try:
            result = finder(scope, condition, cache_request)
        except Exception:
            continue
        if result is not None:
            return result
    return None


def _first(element: Any, names: Tuple[str, ...]) -> Tuple[Any, bool]:
    for name in names:
        try:
            value = getattr(element, name)
        except Exception:
            continue
        if value is not None:
            return value, name.startswith("Cached")
    return None, False


def _rect(value: Any) -> Optional[Tuple[int, int, int, int]]:
    if value is None:
        return None
    try:
        return (int(value.left), int(value.top), int(value.right), int(value.bottom))
    except Exception:
        return None


def read_element(element: Any) -> Dict[str, Any]:
    """Read cached properties with a Current* fallback; never raises."""
    name, from_cache = _first(element, ("CachedName", "CurrentName"))
    automation_id, _ = _first(element, ("CachedAutomationId", "CurrentAutomationId"))
    class_name, _ = _first(element, ("CachedClassName", "CurrentClassName"))
    control_type, _ = _first(element, ("CachedControlType", "CurrentControlType"))
    rect, _ = _first(element, ("CachedBoundingRectangle", "CurrentBoundingRectangle"))
    is_enabled, _ = _first(element, ("CachedIsEnabled", "CurrentIsEnabled"))
    is_offscreen, _ = _first(element, ("CachedIsOffscreen", "CurrentIsOffscreen"))

    try:
        control_type_id = int(control_type)
    except Exception:
        control_type_id = 0

    return {
        "name": str(name or ""),
        "automation_id": str(automation_id or ""),
        "class_name": str(class_name or ""),
        "control_type_id": control_type_id,
        "rect": _rect(rect),
        "is_enabled": True if is_enabled is None else bool(is_enabled),
        "is_offscreen": False if is_offscreen is None else bool(is_offscreen),
        "from_cache": bool(from_cache),
    }
