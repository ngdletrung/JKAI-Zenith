# -*- coding: utf-8 -*-
"""
tests/test_uia_click_executor.py
[NEGATIVE & POSITIVE UNIT TESTS FOR D11 UIA CLICK EXECUTOR]

COM is replaced by strict fakes through UIAClickExecutor._open_uia, so these
tests exercise the real allowlist gate, fresh-tree resolution, ambiguity
handling, identity binding, pattern discipline, and watchdog ordering without
touching a live desktop.
"""

import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, ".")

from services.ai_desktop.app_policy import AppRule
from services.ai_desktop.uia_click_executor import (
    ResolvedElement,
    UIAClickError,
    UIAClickExecutor,
    element_identity_signature,
)

CONTROL_TYPE_BUTTON = 50000
CONTROL_TYPE_MENUITEM = 50011

RULE = AppRule(
    process_name="notepad.exe",
    app_name="Notepad Scratch",
    allowed_actions=frozenset({"type_text", "click"}),
    element_allowlist=frozenset({"text editor", "line down", "line up"}),
    max_text_length=500,
    allow_raw_xy=False,
)

RULE_AUTOMATION_ID = AppRule(
    process_name="notepad.exe",
    app_name="Notepad Scratch",
    allowed_actions=frozenset({"click"}),
    element_allowlist=frozenset({"scrolldownbutton"}),
    max_text_length=500,
    allow_raw_xy=False,
)


class _Rect:
    def __init__(self, left=0, top=0, right=10, bottom=10):
        self.left, self.top, self.right, self.bottom = left, top, right, bottom


class _FakePattern:
    def __init__(self, expand_state=0):
        self.calls = []
        self.expand_state = expand_state

    def QueryInterface(self, interface):
        return self

    def Invoke(self):
        self.calls.append("invoke")

    def Expand(self):
        self.calls.append("expand")

    def Collapse(self):
        self.calls.append("collapse")

    @property
    def CurrentExpandCollapseState(self):
        return self.expand_state


class _FakeElement:
    def __init__(
        self,
        name,
        automation_id,
        control_type=CONTROL_TYPE_BUTTON,
        class_name="Button",
        enabled=True,
        offscreen=False,
        patterns=None,
    ):
        self.CurrentName = name
        self.CurrentAutomationId = automation_id
        self.CurrentControlType = control_type
        self.CurrentClassName = class_name
        self.CurrentIsEnabled = enabled
        self.CurrentIsOffscreen = offscreen
        self.CurrentBoundingRectangle = _Rect()
        self.patterns = patterns or {}

    def GetCurrentPattern(self, pattern_id):
        if pattern_id in self.patterns:
            return self.patterns[pattern_id]
        raise ValueError(f"pattern {pattern_id} unavailable")


class _FakeDescendants:
    def __init__(self, elements):
        self.elements = list(elements)
        self.Length = len(self.elements)

    def GetElement(self, index):
        return self.elements[index]


class _FakeUIA:
    def CreateTrueCondition(self):
        return object()


class _FakeRoot:
    def __init__(self, elements):
        self._descendants = _FakeDescendants(elements)

    def FindAll(self, scope, condition):
        return self._descendants


def _patched(elements):
    return (
        patch.object(UIAClickExecutor, "_open_uia", return_value=(_FakeUIA(), _FakeRoot(elements))),
        patch.object(
            UIAClickExecutor,
            "_pattern_interfaces",
            return_value={"invoke": "INVOKE_IFACE", "expand_collapse": "EXPAND_IFACE"},
        ),
        patch("services.ai_desktop.uia_click_executor.win32gui.IsWindow", return_value=True),
        patch(
            "services.ai_desktop.uia_click_executor.win32process.GetWindowThreadProcessId",
            return_value=(1, 4242),
        ),
        patch(
            "services.ai_desktop.uia_click_executor.UIATreeInspector._resolve_process_name",
            return_value="notepad.exe",
        ),
    )


def _execute(elements, identifier="Line down", expected_signature=None, watchdog=None, rule=RULE):
    executor = UIAClickExecutor()
    patches = _patched(elements)
    for item in patches:
        item.start()
    try:
        return executor, executor.execute(
            12345,
            identifier,
            rule,
            expected_signature=expected_signature,
            watchdog=watchdog,
        )
    finally:
        for item in patches:
            item.stop()


class _Watchdog:
    def __init__(self, stop_after_checks=99):
        self.is_stopped = False
        self._stop_reason = "TEST_STOP"
        self.stop_after = stop_after_checks
        self.checks = 0

    def __getattribute__(self, name):
        if name == "is_stopped":
            checks = object.__getattribute__(self, "checks")
            object.__setattr__(self, "checks", checks + 1)
            if checks >= object.__getattribute__(self, "stop_after"):
                return True
            return False
        return object.__getattribute__(self, name)


class TestUIAClickExecutor(unittest.TestCase):
    def _button(self, patterns=None):
        return _FakeElement("Line down", "ScrollDownButton", patterns=patterns or {})

    def test_01_resolve_by_name(self):
        executor = UIAClickExecutor()
        patches = _patched([self._button()])
        for item in patches:
            item.start()
        try:
            resolved = executor.resolve(12345, "Line down", RULE)
        finally:
            for item in patches:
                item.stop()
        self.assertIsInstance(resolved, ResolvedElement)
        self.assertEqual(resolved.automation_id, "ScrollDownButton")
        self.assertEqual(
            resolved.signature,
            element_identity_signature("Line down", "ScrollDownButton", "Button", "Button"),
        )

    def test_02_resolve_by_automation_id(self):
        executor = UIAClickExecutor()
        patches = _patched([self._button()])
        for item in patches:
            item.start()
        try:
            resolved = executor.resolve(12345, "ScrollDownButton", RULE_AUTOMATION_ID)
        finally:
            for item in patches:
                item.stop()
        self.assertEqual(resolved.name, "Line down")

    def test_03_resolve_missing_fails_closed(self):
        executor = UIAClickExecutor()
        patches = _patched([self._button()])
        for item in patches:
            item.start()
        try:
            with self.assertRaises(UIAClickError) as ctx:
                executor.resolve(12345, "Line up", RULE)
        finally:
            for item in patches:
                item.stop()
        self.assertEqual(ctx.exception.code, "ELEMENT_NOT_FOUND")

    def test_04_resolve_ambiguous_fails_closed(self):
        executor = UIAClickExecutor()
        patches = _patched([self._button(), self._button()])
        for item in patches:
            item.start()
        try:
            with self.assertRaises(UIAClickError) as ctx:
                executor.resolve(12345, "Line down", RULE)
        finally:
            for item in patches:
                item.stop()
        self.assertEqual(ctx.exception.code, "ELEMENT_AMBIGUOUS")

    def test_05_not_allowlisted_never_scans(self):
        executor = UIAClickExecutor()
        with patch.object(UIAClickExecutor, "_open_uia") as open_uia:
            with self.assertRaises(UIAClickError) as ctx:
                executor.execute(12345, "Close", RULE)
        self.assertEqual(ctx.exception.code, "ELEMENT_NOT_ALLOWLISTED")
        open_uia.assert_not_called()

    def test_06_empty_allowlist_denies_everything(self):
        locked_rule = AppRule(
            process_name="notepad.exe", app_name="x",
            allowed_actions=frozenset({"click"}),
            element_allowlist=frozenset(), max_text_length=None, allow_raw_xy=False,
        )
        with self.assertRaises(UIAClickError) as ctx:
            UIAClickExecutor().execute(12345, "Line down", locked_rule)
        self.assertEqual(ctx.exception.code, "ELEMENT_NOT_ALLOWLISTED")

    def test_07_execute_invokes_invoke_pattern(self):
        invoke = _FakePattern()
        _executor, result = _execute([self._button({10000: invoke})])
        self.assertEqual(result["status"], "EXECUTED")
        self.assertEqual(result["pattern_used"], "InvokePattern")
        self.assertTrue(result["invoked"])
        self.assertEqual(invoke.calls, ["invoke"])

    def test_08_identity_drift_blocks_before_invoke(self):
        invoke = _FakePattern()
        executor = UIAClickExecutor()
        patches = _patched([self._button({10000: invoke})])
        for item in patches:
            item.start()
        try:
            with self.assertRaises(UIAClickError) as ctx:
                executor.execute(12345, "Line down", RULE, expected_signature="deadbeef")
        finally:
            for item in patches:
                item.stop()
        self.assertEqual(ctx.exception.code, "ELEMENT_IDENTITY_DRIFT")
        self.assertEqual(invoke.calls, [])

    def test_09_unsupported_pattern_fails_closed(self):
        with self.assertRaises(UIAClickError) as ctx:
            _execute([self._button()])
        self.assertEqual(ctx.exception.code, "PATTERN_UNSUPPORTED")

    def test_10_disabled_element_fails_closed(self):
        disabled = _FakeElement(
            "Line down", "ScrollDownButton", enabled=False,
            patterns={10000: _FakePattern()},
        )
        with self.assertRaises(UIAClickError) as ctx:
            _execute([disabled])
        self.assertEqual(ctx.exception.code, "ELEMENT_DISABLED")

    def test_11_offscreen_element_fails_closed(self):
        offscreen = _FakeElement(
            "Line down", "ScrollDownButton", offscreen=True,
            patterns={10000: _FakePattern()},
        )
        with self.assertRaises(UIAClickError) as ctx:
            _execute([offscreen])
        self.assertEqual(ctx.exception.code, "ELEMENT_OFFSCREEN")

    def test_12_watchdog_stop_before_scan(self):
        with self.assertRaises(UIAClickError) as ctx:
            _execute([self._button({10000: _FakePattern()})], watchdog=_Watchdog(stop_after_checks=0))
        self.assertEqual(ctx.exception.code, "CLICK_BLOCKED_WATCHDOG")

    def test_13_watchdog_stop_between_scan_and_invoke(self):
        invoke = _FakePattern()
        element = self._button({10000: invoke})
        executor = UIAClickExecutor()
        patches = _patched([element])
        for item in patches:
            item.start()
        try:
            with self.assertRaises(UIAClickError) as ctx:
                executor.execute(12345, "Line down", RULE, watchdog=_Watchdog(stop_after_checks=1))
        finally:
            for item in patches:
                item.stop()
        self.assertEqual(ctx.exception.code, "CLICK_BLOCKED_WATCHDOG")
        self.assertEqual(invoke.calls, [])

    def test_14_menuitem_uses_expand_collapse(self):
        menu_item = _FakeElement(
            "File", "FileMenu", control_type=CONTROL_TYPE_MENUITEM,
            class_name="MenuItem", patterns={10005: _FakePattern(expand_state=0)},
        )
        rule = AppRule(
            process_name="notepad.exe", app_name="x",
            allowed_actions=frozenset({"click"}),
            element_allowlist=frozenset({"file"}), max_text_length=None, allow_raw_xy=False,
        )
        _executor, _ = _execute([menu_item], identifier="File", rule=rule)

    def test_14b_menuitem_expand_is_reported(self):
        pattern = _FakePattern(expand_state=0)
        menu_item = _FakeElement(
            "File", "FileMenu", control_type=CONTROL_TYPE_MENUITEM,
            class_name="MenuItem", patterns={10005: pattern},
        )
        rule = AppRule(
            process_name="notepad.exe", app_name="x",
            allowed_actions=frozenset({"click"}),
            element_allowlist=frozenset({"file"}), max_text_length=None, allow_raw_xy=False,
        )
        executor = UIAClickExecutor()
        patches = _patched([menu_item])
        for item in patches:
            item.start()
        try:
            result = executor.execute(12345, "File", rule)
        finally:
            for item in patches:
                item.stop()
        self.assertEqual(result["pattern_used"], "ExpandCollapsePattern")
        self.assertEqual(pattern.calls, ["expand"])

    def test_15_missing_identifier_fails_closed(self):
        with self.assertRaises(UIAClickError) as ctx:
            UIAClickExecutor().execute(12345, "   ", RULE)
        self.assertEqual(ctx.exception.code, "ELEMENT_IDENTIFIER_REQUIRED")

    def test_16_invoke_failure_is_delivery_uncertain(self):
        """An Invoke() that raises may still have reached the provider."""
        class _RaisingPattern(_FakePattern):
            def Invoke(self):
                self.calls.append("invoke")
                raise RuntimeError("provider rejected after dispatch")

        with self.assertRaises(UIAClickError) as ctx:
            _execute([self._button({10000: _RaisingPattern()})])
        self.assertEqual(ctx.exception.code, "INVOKE_FAILED")
        self.assertEqual(ctx.exception.delivery_state, UIAClickError.UNCERTAIN)

    def test_17_expand_failure_is_delivery_uncertain(self):
        class _RaisingExpand(_FakePattern):
            def Expand(self):
                self.calls.append("expand")
                raise RuntimeError("provider rejected after expand")

        menu_item = _FakeElement(
            "File", "FileMenu", control_type=CONTROL_TYPE_MENUITEM,
            class_name="MenuItem", patterns={10005: _RaisingExpand(expand_state=0)},
        )
        rule = AppRule(
            process_name="notepad.exe", app_name="x",
            allowed_actions=frozenset({"click"}),
            element_allowlist=frozenset({"file"}), max_text_length=None, allow_raw_xy=False,
        )
        with self.assertRaises(UIAClickError) as ctx:
            _execute([menu_item], identifier="File", rule=rule)
        self.assertEqual(ctx.exception.code, "EXPAND_FAILED")
        self.assertEqual(ctx.exception.delivery_state, UIAClickError.UNCERTAIN)

    def test_18_pre_dispatch_failure_stays_not_delivered(self):
        with self.assertRaises(UIAClickError) as ctx:
            _execute([self._button()])
        self.assertEqual(ctx.exception.delivery_state, UIAClickError.NOT_DELIVERED)

    def test_19_unreadable_candidate_is_incomplete_not_missing(self):
        class _Unreadable:
            @property
            def CurrentName(self):
                raise RuntimeError("UIA identity read failed")

        with self.assertRaises(UIAClickError) as ctx:
            _execute([_Unreadable()])
        self.assertEqual(ctx.exception.code, "ELEMENT_UNREADABLE")
        self.assertEqual(ctx.exception.details["verdict"], "INCOMPLETE")
        self.assertEqual(ctx.exception.delivery_state, UIAClickError.NOT_DELIVERED)

    def test_20_stored_hash_breaks_a_duplicate_tie(self):
        from services.ai_desktop.semantic_action_ir import compute_canonical_element_hash

        invoke = _FakePattern()
        first = _FakeElement("Line down", "A", patterns={10000: _FakePattern()})
        second = _FakeElement("Line down", "B", patterns={10000: invoke})
        second.CurrentBoundingRectangle = _Rect(0, 0, 20, 20)
        expected_hash = compute_canonical_element_hash(
            name="Line down",
            control_type="Button",
            automation_id="B",
            class_name="Button",
            rect=(0, 0, 20, 20),
        )

        executor = UIAClickExecutor()
        patches = _patched([first, second])
        for item in patches:
            item.start()
        try:
            result = executor.execute(
                12345, "Line down", RULE, expected_element_hash=expected_hash
            )
        finally:
            for item in patches:
                item.stop()

        self.assertEqual(result["element_automation_id"], "B")
        self.assertEqual(invoke.calls, ["invoke"])

    def test_21_duplicate_tie_without_stored_hash_stays_ambiguous(self):
        first = _FakeElement("Line down", "A", patterns={10000: _FakePattern()})
        second = _FakeElement("Line down", "B", patterns={10000: _FakePattern()})
        second.CurrentBoundingRectangle = _Rect(0, 0, 20, 20)
        with self.assertRaises(UIAClickError) as ctx:
            _execute([first, second])
        self.assertEqual(ctx.exception.code, "ELEMENT_AMBIGUOUS")


if __name__ == "__main__":
    unittest.main()
