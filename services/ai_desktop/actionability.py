# -*- coding: utf-8 -*-
"""
services/ai_desktop/actionability.py
[ACTIONABILITY PREFLIGHT - D13]

Ported from agent-desktop (crates/core/src/actionability: requirements.rs,
gates.rs, report.rs; Apache-2.0 - see NOTICE.md / CREDITS.md). The port keeps
the two properties that made the original useful:

  1. A per-action requirements matrix decides which gates even run, so a
     semantic UIA pattern call (InvokePattern / ScrollPattern) is never
     blocked by pointer-only evidence such as a zero-sized bounding rect or
     an unsampled stability window.
  2. A terminal code on a blocking check marks a permanent refusal and
     outranks a transient gap. Callers map the terminal code straight onto
     their own fail-closed error; a check without a terminal code is a
     retryable pre-dispatch refusal.

JKAI only reaches elements through semantic UIA patterns or keyboard input,
so `receives_events` (a hit-test/occlusion property) is carried in the matrix
but not gated: an InvokePattern call does not deliver through the pointer.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, Optional, Tuple

STATUS_PASS = "pass"
STATUS_FAIL = "fail"
STATUS_UNKNOWN = "unknown"
STATUS_SKIP = "skip"

DELIVERY_SEMANTIC = "SEMANTIC"
DELIVERY_KEYBOARD = "KEYBOARD"
DELIVERY_POINTER = "POINTER"
DELIVERY_NONE = "NONE"

TERMINAL_PATTERN_UNSUPPORTED = "PATTERN_UNSUPPORTED"
TERMINAL_SCROLL_PATTERN_UNSUPPORTED = "SCROLL_PATTERN_UNSUPPORTED"
TERMINAL_ACTION_NOT_SUPPORTED = "ACTION_NOT_SUPPORTED"

_EDITABLE_CONTROL_TYPES = frozenset({"edit", "document", "combobox"})
_EDITABLE_PATTERNS = ("ValuePattern", "TextPattern")
_CLICK_PATTERNS = ("InvokePattern",)


@dataclass(frozen=True)
class ActionRequirements:
    visible: bool
    stable: bool
    enabled: bool
    editable: bool
    receives_events: bool


_REQUIREMENTS: Dict[str, ActionRequirements] = {
    "click": ActionRequirements(True, True, True, False, True),
    "scroll": ActionRequirements(True, True, True, False, False),
    "type_text": ActionRequirements(True, False, True, True, False),
    "focus": ActionRequirements(False, False, False, False, False),
    "key_combo": ActionRequirements(False, False, False, False, False),
}


@dataclass(frozen=True)
class ActionabilityCheck:
    check: str
    status: str
    reason: str = ""
    terminal_code: Optional[str] = None

    @property
    def blocking(self) -> bool:
        return self.status in (STATUS_FAIL, STATUS_UNKNOWN)

    def as_dict(self) -> Dict[str, Any]:
        return {
            "check": self.check,
            "status": self.status,
            "reason": self.reason,
            "terminal_code": self.terminal_code,
        }


@dataclass(frozen=True)
class ActionabilityReport:
    action: str
    actionable: bool
    checks: Tuple[ActionabilityCheck, ...]

    @property
    def blocking_checks(self) -> Tuple[ActionabilityCheck, ...]:
        return tuple(check for check in self.checks if check.blocking)

    @property
    def terminal_code(self) -> Optional[str]:
        """First blocking check that carries a code; terminal outranks transient."""
        for check in self.checks:
            if check.blocking and check.terminal_code:
                return check.terminal_code
        return None

    def failure_reasons(self) -> str:
        return ", ".join(
            f"{check.check} ({(check.reason or 'failed')})" for check in self.blocking_checks
        )

    def as_dict(self) -> Dict[str, Any]:
        return {
            "action": self.action,
            "actionable": self.actionable,
            "terminal_code": self.terminal_code,
            "failure_reasons": self.failure_reasons(),
            "checks": [check.as_dict() for check in self.checks],
        }


def requirements_for(action: str) -> ActionRequirements:
    try:
        return _REQUIREMENTS[str(action)]
    except KeyError as exc:
        raise ValueError(f"UNKNOWN_ACTION: {action}") from exc


def _field(element: Any, name: str, default: Any = None) -> Any:
    if isinstance(element, dict):
        return element.get(name, default)
    return getattr(element, name, default)


def _pass(check: str) -> ActionabilityCheck:
    return ActionabilityCheck(check=check, status=STATUS_PASS)


def _skip(check: str, reason: str) -> ActionabilityCheck:
    return ActionabilityCheck(check=check, status=STATUS_SKIP, reason=reason)


def _fail(check: str, reason: str, terminal_code: Optional[str] = None) -> ActionabilityCheck:
    return ActionabilityCheck(
        check=check, status=STATUS_FAIL, reason=reason, terminal_code=terminal_code
    )


def _unknown(check: str, reason: str) -> ActionabilityCheck:
    return ActionabilityCheck(check=check, status=STATUS_UNKNOWN, reason=reason)


def _is_editable(element: Any) -> bool:
    control_type = str(_field(element, "control_type", "") or "").strip().casefold()
    if control_type in _EDITABLE_CONTROL_TYPES:
        return True
    patterns = _field(element, "supported_patterns", ()) or ()
    return any(pattern in patterns for pattern in _EDITABLE_PATTERNS)


def _visibility(element: Any, requires_geometry: bool) -> ActionabilityCheck:
    visible = _field(element, "is_visible", None)
    if visible is None:
        return _unknown("visible", "live visibility state unavailable")
    if not bool(visible):
        return _fail("visible", "element is hidden or offscreen")

    if requires_geometry:
        rect = _field(element, "rect", None)
        try:
            left, top, right, bottom = (int(value) for value in rect)
        except (TypeError, ValueError):
            return _unknown("visible", "bounds unavailable")
        if right <= left or bottom <= top:
            return _fail("visible", "bounds are zero-sized")
    return _pass("visible")


def _stability(requirements: ActionRequirements, delivery: str) -> ActionabilityCheck:
    if not requirements.stable:
        return _skip("stable", "action does not require stability")
    if delivery != DELIVERY_POINTER:
        return _skip("stable", "delivery does not use the pointer")
    return _unknown("stable", "pointer delivery needs a stability sampler")


def _enabled(element: Any) -> ActionabilityCheck:
    enabled = _field(element, "is_enabled", None)
    if enabled is None:
        return _unknown("enabled", "live enabled state unavailable")
    if not bool(enabled):
        return _fail("enabled", "live enabled state is false")
    return _pass("enabled")


def _editable(element: Any, requirements: ActionRequirements) -> ActionabilityCheck:
    if not requirements.editable:
        return _skip("editable", "action does not write text")
    if _is_editable(element):
        return _pass("editable")
    return _fail(
        "editable",
        f"control type {_field(element, 'control_type', '')!r} is not editable",
        terminal_code=TERMINAL_ACTION_NOT_SUPPORTED,
    )


def _supported_action(element: Any, action: str) -> ActionabilityCheck:
    patterns = _field(element, "supported_patterns", ()) or ()
    control_type = str(_field(element, "control_type", "") or "")

    if action == "click":
        if any(pattern in patterns for pattern in _CLICK_PATTERNS):
            return _pass("supported_action")
        if control_type == "MenuItem" and "ExpandCollapsePattern" in patterns:
            return _pass("supported_action")
        return _fail(
            "supported_action",
            f"{control_type or 'element'} exposes neither InvokePattern nor ExpandCollapsePattern",
            terminal_code=TERMINAL_PATTERN_UNSUPPORTED,
        )

    if action == "scroll":
        if "ScrollPattern" in patterns:
            return _pass("supported_action")
        return _fail(
            "supported_action",
            f"{control_type or 'element'} does not expose ScrollPattern",
            terminal_code=TERMINAL_SCROLL_PATTERN_UNSUPPORTED,
        )

    if action == "type_text":
        if _is_editable(element):
            return _pass("supported_action")
        return _fail(
            "supported_action",
            f"{control_type or 'element'} exposes no text-editing pattern",
            terminal_code=TERMINAL_ACTION_NOT_SUPPORTED,
        )

    return _pass("supported_action")


def evaluate_actionability(
    element: Any,
    action: str,
    delivery: str = DELIVERY_SEMANTIC,
    requires_geometry: Optional[bool] = None,
) -> ActionabilityReport:
    """Evaluate one element against the requirements of `action`.

    `element` is any object (or dict) exposing `is_visible`, `is_enabled`,
    `rect`, `control_type` and `supported_patterns`. Nothing here invokes a
    pattern; the caller decides what a blocked report means.
    """
    requirements = requirements_for(action)
    if requires_geometry is None:
        requires_geometry = delivery == DELIVERY_POINTER

    checks = [
        _enabled(element) if requirements.enabled else _skip("enabled", "action does not require it"),
        _visibility(element, requires_geometry) if requirements.visible else _skip("visible", "action does not require it"),
        _stability(requirements, delivery),
        _editable(element, requirements),
        _supported_action(element, action),
    ]
    actionable = not any(check.blocking for check in checks)
    return ActionabilityReport(action=action, actionable=actionable, checks=tuple(checks))
