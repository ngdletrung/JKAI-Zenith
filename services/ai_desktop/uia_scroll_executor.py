# -*- coding: utf-8 -*-
"""
services/ai_desktop/uia_scroll_executor.py
[FAIL-CLOSED UIA SCROLL EXECUTOR - D12]

Scrolls one allowlisted element through UIA3 ScrollPattern. It reuses the
resolution/identity machinery of UIAClickExecutor (allowlist gate, fresh tree,
exactly-one-match, identity signature, watchdog gates) and adds the pattern
specifics:

  1. The element must expose ScrollPattern (10004); otherwise
     SCROLL_PATTERN_UNSUPPORTED, never a coordinate fallback.
  2. The requested axis must be scrollable, otherwise ELEMENT_NOT_SCROLLABLE.
  3. direction ∈ {"up", "down"}, unit ∈ {"page", "line"}, steps ∈ [1, 5].
  4. A watchdog stop before the first step raises SCROLL_BLOCKED_WATCHDOG.
     A stop after n >= 1 steps returns watchdog_stopped=True so the worker can
     report CLAIMED_PARTIALLY_DELIVERED instead of pretending nothing happened.

Nothing here writes a lease, consumes a nonce, or decides authorization.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from .actionability import evaluate_actionability
from .uia_click_executor import (
    ResolvedElement,
    UIAClickError,
    UIAClickExecutor,
    element_identity_signature,
)

PATTERN_SCROLL = 10004
SCROLL_AMOUNT_NO_AMOUNT = 2
SCROLL_AMOUNT_LARGE_DECREMENT = 0
SCROLL_AMOUNT_SMALL_DECREMENT = 1
SCROLL_AMOUNT_LARGE_INCREMENT = 3
SCROLL_AMOUNT_SMALL_INCREMENT = 4

MAX_SCROLL_STEPS = 5

# direction + unit -> UIA ScrollAmount for the vertical axis.
_VERTICAL_AMOUNT = {
    ("up", "page"): SCROLL_AMOUNT_LARGE_DECREMENT,
    ("up", "line"): SCROLL_AMOUNT_SMALL_DECREMENT,
    ("down", "page"): SCROLL_AMOUNT_LARGE_INCREMENT,
    ("down", "line"): SCROLL_AMOUNT_SMALL_INCREMENT,
}


class UIAScrollError(UIAClickError):
    """Same typed fail-closed contract as UIAClickError."""


class UIAScrollExecutor(UIAClickExecutor):
    """Resolve and scroll a single allowlisted element on one HWND."""

    @staticmethod
    def _scroll_interface() -> Any:
        from comtypes.gen.UIAutomationClient import IUIAutomationScrollPattern

        return IUIAutomationScrollPattern

    @staticmethod
    def _validate_request(direction: str, unit: str, steps: int) -> tuple:
        clean_direction = str(direction or "").strip().lower()
        clean_unit = str(unit or "").strip().lower()
        if clean_direction not in ("up", "down"):
            raise UIAScrollError("SCROLL_DIRECTION_INVALID", str(direction))
        if clean_unit not in ("page", "line"):
            raise UIAScrollError("SCROLL_UNIT_INVALID", str(unit))
        if type(steps) is not int or isinstance(steps, bool) or not 1 <= steps <= MAX_SCROLL_STEPS:
            raise UIAScrollError("SCROLL_STEPS_INVALID", str(steps))
        return clean_direction, clean_unit, steps

    def _scroll_pattern(self, element: Any):
        try:
            pointer = element.GetCurrentPattern(PATTERN_SCROLL)
        except Exception:
            pointer = None
        if not pointer:
            raise UIAScrollError("SCROLL_PATTERN_UNSUPPORTED", "ScrollPattern unavailable")
        try:
            return pointer.QueryInterface(self._scroll_interface())
        except Exception as exc:
            raise UIAScrollError("SCROLL_PATTERN_UNSUPPORTED", str(exc)) from exc

    def inspect(self, hwnd: int, identifier: str, rule: Optional[Any]) -> Dict[str, Any]:
        """Read-only preflight: resolve, bind identity, prove the element scrolls."""
        clean = self._require_allowed(rule, identifier)
        rows = []
        node = element = pattern = None
        com_open = False
        try:
            rows, snapshot_hash, pid, process_name, unreadable = self._scan(hwnd)
            com_open = True
            node, element = self._match(rows, clean, unreadable)
            report = evaluate_actionability(node, "scroll")
            self._raise_if_blocked(report, UIAScrollError)
            pattern = self._scroll_pattern(element)
            if not bool(pattern.CurrentVerticallyScrollable):
                raise UIAScrollError("ELEMENT_NOT_SCROLLABLE", clean)
            resolved = ResolvedElement(
                identifier=clean,
                name=node.name,
                automation_id=node.automation_id,
                control_type=node.control_type,
                class_name=node.class_name,
                signature=element_identity_signature(
                    node.name, node.automation_id, node.control_type, node.class_name
                ),
                element_hash=node.element_hash,
                rect=tuple(node.rect),
                supported_patterns=tuple(node.supported_patterns),
                snapshot_hash=snapshot_hash,
                actionability=report.as_dict(),
            )
            payload = resolved.as_dict()
            payload.update({
                "vertically_scrollable": True,
                "vertical_percent": float(pattern.CurrentVerticalScrollPercent),
                "pid": pid,
                "process_name": process_name,
            })
            return payload
        finally:
            pattern = element = node = None
            rows.clear()
            if com_open:
                self._close_com()

    def execute(
        self,
        hwnd: int,
        identifier: str,
        rule: Optional[Any],
        direction: str,
        unit: str,
        steps: int,
        expected_signature: Optional[str] = None,
        watchdog: Optional[Any] = None,
        expected_element_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        clean = self._require_allowed(rule, identifier)
        clean_direction, clean_unit, clean_steps = self._validate_request(direction, unit, steps)
        vertical_amount = _VERTICAL_AMOUNT[(clean_direction, clean_unit)]

        if watchdog is not None and getattr(watchdog, "is_stopped", False):
            raise UIAScrollError("SCROLL_BLOCKED_WATCHDOG", getattr(watchdog, "_stop_reason", ""))

        with self._lock:
            rows = []
            node = element = pattern = None
            com_open = False
            try:
                rows, snapshot_hash, pid, process_name, unreadable = self._scan(hwnd)
                com_open = True
                node, element = self._match(rows, clean, unreadable, expected_element_hash)

                report = evaluate_actionability(node, "scroll")
                self._raise_if_blocked(report, UIAScrollError)

                signature = element_identity_signature(
                    node.name, node.automation_id, node.control_type, node.class_name
                )
                if expected_signature and signature != expected_signature:
                    raise UIAScrollError(
                        "ELEMENT_IDENTITY_DRIFT",
                        f"expected {expected_signature[:16]} got {signature[:16]}",
                    )

                pattern = self._scroll_pattern(element)
                if not bool(pattern.CurrentVerticallyScrollable):
                    raise UIAScrollError("ELEMENT_NOT_SCROLLABLE", clean)

                percent_before = float(pattern.CurrentVerticalScrollPercent)
                applied = 0
                watchdog_stopped = False
                for _ in range(clean_steps):
                    if watchdog is not None and getattr(watchdog, "is_stopped", False):
                        if applied == 0:
                            raise UIAScrollError(
                                "SCROLL_BLOCKED_WATCHDOG", getattr(watchdog, "_stop_reason", "")
                            )
                        watchdog_stopped = True
                        break
                    try:
                        pattern.Scroll(SCROLL_AMOUNT_NO_AMOUNT, vertical_amount)
                    except Exception as exc:
                        # Applied steps are already on screen: never report NOT_DELIVERED.
                        raise UIAScrollError(
                            "SCROLL_FAILED",
                            f"after {applied} step(s): {exc}",
                            delivery_state=(
                                UIAScrollError.PARTIAL if applied else UIAScrollError.NOT_DELIVERED
                            ),
                            details={
                                "scroll_steps_applied": applied,
                                "vertical_percent_before": percent_before,
                            },
                        ) from exc
                    applied += 1
                try:
                    percent_after = float(pattern.CurrentVerticalScrollPercent)
                except Exception as exc:
                    raise UIAScrollError(
                        "SCROLL_STATE_READ_FAILED",
                        str(exc),
                        delivery_state=(
                            UIAScrollError.UNCERTAIN if applied else UIAScrollError.NOT_DELIVERED
                        ),
                        details={"scroll_steps_applied": applied},
                    ) from exc

                return {
                    "status": "EXECUTED",
                    "scrolled": True,
                    "pattern_used": "ScrollPattern",
                    "element_identifier": clean,
                    "element_name": node.name,
                    "element_automation_id": node.automation_id,
                    "element_control_type": node.control_type,
                    "element_class_name": node.class_name,
                    "element_signature": signature,
                    "element_hash": node.element_hash,
                    "rect": list(node.rect),
                    "scroll_direction": clean_direction,
                    "scroll_unit": clean_unit,
                    "scroll_steps_requested": clean_steps,
                    "scroll_steps_applied": applied,
                    "watchdog_stopped": watchdog_stopped,
                    "vertical_percent_before": percent_before,
                    "vertical_percent_after": percent_after,
                    "snapshot_hash": snapshot_hash,
                    "actionability": report.as_dict(),
                    "pid": pid,
                    "process_name": process_name,
                }
            finally:
                pattern = element = node = None
                rows.clear()
                if com_open:
                    self._close_com()
