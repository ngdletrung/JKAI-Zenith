# -*- coding: utf-8 -*-
"""
services/ai_desktop/uia_click_executor.py
[FAIL-CLOSED UIA CLICK EXECUTOR - D11]

Single implementation of "click an allowlisted element" for the desktop
mutation owner. It never clicks coordinates: the only accepted target is an
allowlisted element identifier (UIA Name or AutomationId) evaluated against a
fresh UIA3 tree of the leased HWND.

Safety invariants:
  1. Policy first: the identifier must be in the app rule's element allowlist
     (empty allowlist denies everything).
  2. Fresh resolution: every resolve/execute enumerates the live tree and
     requires exactly one match. Zero matches is ELEMENT_NOT_FOUND, more than
     one is ELEMENT_AMBIGUOUS; both fail closed.
  3. Identity binding: callers can pass the signature captured at preflight.
     execute() refuses ELEMENT_IDENTITY_DRIFT when name/automation_id/
     control_type/class_name changed between preflight and dispatch.
  4. Pattern discipline: InvokePattern is preferred; MenuItem falls back to
     ExpandCollapsePattern; any other element without InvokePattern fails with
     PATTERN_UNSUPPORTED instead of guessing a click point.
  5. Watchdog gate: checked before enumeration and immediately before the
     pattern call.

Nothing here writes a lease, consumes a nonce, or decides authorization. The
HostMutationWorker owns those gates and calls this module only after a
Master-signed approval has been verified.
"""

from __future__ import annotations

import hashlib
import json
import threading
from dataclasses import dataclass, asdict
from typing import Any, Dict, List, Optional, Tuple

import win32gui
import win32process

from .actionability import ActionabilityReport, evaluate_actionability
from .ref_resolution import AMBIGUOUS, INCOMPLETE, MATCHED, resolve_identifier
from .uia_tree_inspector import UIAElementNode, UIA_CONTROL_TYPE_MAP, UIATreeInspector
from .semantic_action_ir import compute_canonical_snapshot_hash
from .app_policy import AppRule

TREE_SCOPE_DESCENDANTS = 0x4
PATTERN_INVOKE = 10000
PATTERN_EXPAND_COLLAPSE = 10005


class UIAClickError(RuntimeError):
    """Typed fail-closed error; `code` is stable for receipts and tests.

    `delivery_state` separates "nothing was sent" from "the provider may have
    acted before failing" (UNCERTAIN) and "part of the sequence landed"
    (PARTIAL). Callers must not report UNCERTAIN/PARTIAL as NOT_DELIVERED.
    """

    NOT_DELIVERED = "NOT_DELIVERED"
    UNCERTAIN = "UNCERTAIN"
    PARTIAL = "PARTIAL"

    def __init__(
        self,
        code: str,
        detail: str = "",
        delivery_state: str = NOT_DELIVERED,
        details: Optional[Dict[str, Any]] = None,
    ) -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail
        self.delivery_state = delivery_state
        self.details = dict(details or {})


@dataclass(frozen=True)
class ResolvedElement:
    identifier: str
    name: str
    automation_id: str
    control_type: str
    class_name: str
    signature: str
    element_hash: str
    rect: Tuple[int, int, int, int]
    supported_patterns: Tuple[str, ...]
    snapshot_hash: str
    actionability: Optional[Dict[str, Any]] = None

    def as_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["rect"] = list(self.rect)
        payload["supported_patterns"] = list(self.supported_patterns)
        return payload


def element_identity_signature(
    name: str, automation_id: str, control_type: str, class_name: str
) -> str:
    """Stable identity hash that ignores rect (window moves are not identity drift)."""
    payload = {
        "automation_id": str(automation_id),
        "class_name": str(class_name),
        "control_type": str(control_type),
        "name": str(name),
    }
    canonical = json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("utf-8")
    return hashlib.sha256(canonical).hexdigest()


class UIAClickExecutor:
    """Resolve and invoke a single allowlisted UIA element on one HWND."""

    def __init__(self, scan_ttl_seconds: float = 0.0) -> None:
        # resolve() and execute() must each scan fresh; the TTL exists only for
        # callers that explicitly want one snapshot reused within a request.
        self.scan_ttl_seconds = scan_ttl_seconds
        self._lock = threading.RLock()

    # ------------------------------------------------------------------ COM
    @staticmethod
    def _open_uia(hwnd: int):
        """Create a UIA3 automation object and root element for `hwnd`.

        COM must already be initialized on this thread; `_scan` owns that
        balance so a patched `_open_uia` in tests cannot unbalance the count.
        """
        import comtypes.client
        from comtypes.gen.UIAutomationClient import CUIAutomation, IUIAutomation

        uia = comtypes.client.CreateObject(CUIAutomation, interface=IUIAutomation)
        root = uia.ElementFromHandle(hwnd)
        return uia, root

    @staticmethod
    def _pattern_interfaces() -> Dict[str, Any]:
        from comtypes.gen.UIAutomationClient import (
            IUIAutomationExpandCollapsePattern,
            IUIAutomationInvokePattern,
        )

        return {
            "invoke": IUIAutomationInvokePattern,
            "expand_collapse": IUIAutomationExpandCollapsePattern,
        }

    # ------------------------------------------------------------- scanning
    def _enumerate(self, uia, root) -> Tuple[List[Tuple[UIAElementNode, Any]], int]:
        """Return readable rows plus a count of elements whose identity was unreadable.

        An identity read failure is tracked, never silently treated as a
        non-match: the resolver uses the count to report INCOMPLETE instead of
        REFUTED, which keeps a transient UIA failure from looking like a stale
        ref.
        """
        descendants = root.FindAll(TREE_SCOPE_DESCENDANTS, uia.CreateTrueCondition())
        if descendants is None:
            raise UIAClickError("UIA_TREE_UNAVAILABLE", "FindAll returned None")

        rows: List[Tuple[UIAElementNode, Any]] = []
        unreadable = 0
        for index in range(descendants.Length):
            try:
                element = descendants.GetElement(index)
                name = element.CurrentName or ""
                automation_id = element.CurrentAutomationId or ""
            except Exception:
                unreadable += 1
                continue
            try:
                class_name = element.CurrentClassName or "Unknown"
                control_type = UIA_CONTROL_TYPE_MAP.get(
                    element.CurrentControlType,
                    UIATreeInspector._infer_control_type(class_name, name),
                )
                rect_obj = element.CurrentBoundingRectangle
                rect = (
                    int(rect_obj.left),
                    int(rect_obj.top),
                    int(rect_obj.right),
                    int(rect_obj.bottom),
                )
                patterns, _details = UIATreeInspector._extract_com_pattern_details(element)
                node = UIAElementNode(
                    name=name,
                    control_type=control_type,
                    automation_id=automation_id,
                    class_name=class_name,
                    rect=rect,
                    center=((rect[0] + rect[2]) // 2, (rect[1] + rect[3]) // 2),
                    hwnd=0,
                    is_enabled=bool(element.CurrentIsEnabled),
                    is_visible=not bool(getattr(element, "CurrentIsOffscreen", False)),
                    supported_patterns=patterns,
                    ref=f"e{index + 1}",
                )
                rows.append((node, element))
            except Exception:
                unreadable += 1
                continue
        return rows, unreadable

    @staticmethod
    def _close_com() -> None:
        try:
            import comtypes

            comtypes.CoUninitialize()
        except Exception:
            pass

    def _scan(self, hwnd: int) -> Tuple[List[Tuple[UIAElementNode, Any]], str, int, str, int]:
        """Enumerate the live tree and keep COM initialized for the caller.

        The returned rows hold live COM proxies, so the apartment must stay
        initialized until the caller finishes invoking and drops them. On any
        failure inside this method the apartment is closed here instead.
        """
        if not win32gui.IsWindow(hwnd):
            raise UIAClickError("TARGET_HWND_INVALID", str(hwnd))

        _thread_id, pid = win32process.GetWindowThreadProcessId(hwnd)
        process_name = UIATreeInspector._resolve_process_name(pid)
        import comtypes

        comtypes.CoInitialize()
        try:
            uia, root = self._open_uia(hwnd)
            if not root:
                raise UIAClickError("UIA_ROOT_UNAVAILABLE", str(hwnd))
            rows, unreadable = self._enumerate(uia, root)
            for node, _element in rows:
                node.hwnd = hwnd
            snapshot_hash = compute_canonical_snapshot_hash(
                hwnd=hwnd, pid=pid, process_name=process_name, elements=[n for n, _ in rows]
            )
        except Exception:
            self._close_com()
            raise
        return rows, snapshot_hash, pid, process_name, unreadable

    # ------------------------------------------------------------ resolution
    @staticmethod
    def _require_allowed(rule: Optional[AppRule], identifier: str) -> str:
        clean = str(identifier or "").strip()
        if not clean:
            raise UIAClickError("ELEMENT_IDENTIFIER_REQUIRED")
        if rule is None:
            raise UIAClickError("POLICY_RULE_UNAVAILABLE")
        if not rule.allows_element_identifier(clean):
            raise UIAClickError("ELEMENT_NOT_ALLOWLISTED", clean)
        return clean

    @staticmethod
    def _match(
        rows: List[Tuple[UIAElementNode, Any]],
        identifier: str,
        unreadable: int = 0,
        expected_element_hash: Optional[str] = None,
    ) -> Tuple[UIAElementNode, Any]:
        result = resolve_identifier(
            identifier,
            [node for node, _element in rows],
            range(unreadable),
            expected_element_hash=expected_element_hash,
        )
        if result.verdict == MATCHED:
            return rows[result.index]
        if result.verdict == INCOMPLETE:
            raise UIAClickError(
                "ELEMENT_UNREADABLE", result.reason, details=result.as_dict()
            )
        if result.verdict == AMBIGUOUS:
            raise UIAClickError(
                "ELEMENT_AMBIGUOUS", result.reason, details=result.as_dict()
            )
        raise UIAClickError("ELEMENT_NOT_FOUND", identifier, details=result.as_dict())

    @staticmethod
    def _raise_if_blocked(report: ActionabilityReport, error_cls=None) -> None:
        blocking = report.blocking_checks
        if not blocking:
            return
        first = blocking[0]
        code = first.terminal_code or {
            "visible": "ELEMENT_OFFSCREEN",
            "enabled": "ELEMENT_DISABLED",
        }.get(first.check, "ACTIONABILITY_BLOCKED")
        raise (error_cls or UIAClickError)(code, first.reason or first.check)

    def resolve(self, hwnd: int, identifier: str, rule: Optional[AppRule]) -> ResolvedElement:
        """Resolve the identifier on a fresh tree without invoking anything."""
        clean = self._require_allowed(rule, identifier)
        rows: List[Tuple[UIAElementNode, Any]] = []
        node = element = None
        com_open = False
        try:
            rows, snapshot_hash, _pid, _proc, unreadable = self._scan(hwnd)
            com_open = True
            node, element = self._match(rows, clean, unreadable)
            report = evaluate_actionability(node, "click")
            return ResolvedElement(
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
        finally:
            node = element = None
            rows.clear()
            if com_open:
                self._close_com()

    # -------------------------------------------------------------- dispatch
    def _invoke(self, element: Any, node: UIAElementNode) -> str:
        interfaces = self._pattern_interfaces()

        try:
            invoke_ptr = element.GetCurrentPattern(PATTERN_INVOKE)
        except Exception:
            invoke_ptr = None
        if invoke_ptr:
            try:
                invoke_ptr.QueryInterface(interfaces["invoke"]).Invoke()
            except Exception as exc:
                # The provider may have acted before the call failed: never claim
                # "not delivered" when delivery is genuinely unknown.
                raise UIAClickError(
                    "INVOKE_FAILED", str(exc), delivery_state=UIAClickError.UNCERTAIN
                ) from exc
            return "InvokePattern"

        if node.control_type == "MenuItem":
            try:
                expand_ptr = element.GetCurrentPattern(PATTERN_EXPAND_COLLAPSE)
            except Exception:
                expand_ptr = None
            if expand_ptr:
                try:
                    obj = expand_ptr.QueryInterface(interfaces["expand_collapse"])
                    if int(obj.CurrentExpandCollapseState) == 1:
                        obj.Collapse()
                    else:
                        obj.Expand()
                except Exception as exc:
                    raise UIAClickError(
                        "EXPAND_FAILED", str(exc), delivery_state=UIAClickError.UNCERTAIN
                    ) from exc
                return "ExpandCollapsePattern"

        raise UIAClickError(
            "PATTERN_UNSUPPORTED",
            f"{node.control_type} {node.name!r} supports {list(node.supported_patterns)}",
        )

    def execute(
        self,
        hwnd: int,
        identifier: str,
        rule: Optional[AppRule],
        expected_signature: Optional[str] = None,
        watchdog: Optional[Any] = None,
        expected_element_hash: Optional[str] = None,
    ) -> Dict[str, Any]:
        """Resolve on a fresh tree, verify identity, then invoke exactly once."""
        clean = self._require_allowed(rule, identifier)
        if watchdog is not None and getattr(watchdog, "is_stopped", False):
            raise UIAClickError("CLICK_BLOCKED_WATCHDOG", getattr(watchdog, "_stop_reason", ""))

        with self._lock:
            rows: List[Tuple[UIAElementNode, Any]] = []
            node = element = None
            com_open = False
            try:
                rows, snapshot_hash, pid, process_name, unreadable = self._scan(hwnd)
                com_open = True
                node, element = self._match(rows, clean, unreadable, expected_element_hash)

                report = evaluate_actionability(node, "click")
                self._raise_if_blocked(report)

                signature = element_identity_signature(
                    node.name, node.automation_id, node.control_type, node.class_name
                )
                if expected_signature and signature != expected_signature:
                    raise UIAClickError(
                        "ELEMENT_IDENTITY_DRIFT",
                        f"expected {expected_signature[:16]} got {signature[:16]}",
                    )

                if watchdog is not None and getattr(watchdog, "is_stopped", False):
                    raise UIAClickError("CLICK_BLOCKED_WATCHDOG", getattr(watchdog, "_stop_reason", ""))

                pattern_used = self._invoke(element, node)

                return {
                    "status": "EXECUTED",
                    "invoked": True,
                    "pattern_used": pattern_used,
                    "element_identifier": clean,
                    "element_name": node.name,
                    "element_automation_id": node.automation_id,
                    "element_control_type": node.control_type,
                    "element_class_name": node.class_name,
                    "element_signature": signature,
                    "element_hash": node.element_hash,
                    "rect": list(node.rect),
                    "snapshot_hash": snapshot_hash,
                    "actionability": report.as_dict(),
                    "pid": pid,
                    "process_name": process_name,
                }
            finally:
                node = element = None
                rows.clear()
                if com_open:
                    self._close_com()
