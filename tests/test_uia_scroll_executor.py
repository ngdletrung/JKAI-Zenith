# -*- coding: utf-8 -*-
"""
tests/test_uia_scroll_executor.py
[NEGATIVE & POSITIVE UNIT TESTS FOR D12 UIA SCROLL EXECUTOR]

COM is replaced by strict fakes; these tests exercise the inherited allowlist
gate, ambiguity handling, identity binding, ScrollPattern discipline, the
direction/unit/steps mapping, and watchdog ordering without a live desktop.
"""

import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, ".")

from services.ai_desktop.app_policy import AppRule
from services.ai_desktop.uia_click_executor import (
    UIAClickError,
    element_identity_signature,
)
from services.ai_desktop.uia_scroll_executor import (
    UIAScrollError,
    UIAScrollExecutor,
)

PATTERN_SCROLL = 10004

RULE = AppRule(
    process_name="notepad.exe",
    app_name="Notepad Scratch",
    allowed_actions=frozenset({"type_text", "click", "scroll"}),
    element_allowlist=frozenset({"text editor", "line down"}),
    max_text_length=500,
    allow_raw_xy=False,
)


class _Rect:
    def __init__(self, left=0, top=0, right=100, bottom=100):
        self.left, self.top, self.right, self.bottom = left, top, right, bottom


class _FakeScrollPattern:
    def __init__(self, scrollable=True, percent=0.0):
        self.calls = []
        self.scrollable = scrollable
        self.percent = percent

    def QueryInterface(self, interface):
        return self

    def Scroll(self, horizontal_amount, vertical_amount):
        self.calls.append((horizontal_amount, vertical_amount))
        self.percent = min(100.0, self.percent + 0.5)

    @property
    def CurrentVerticallyScrollable(self):
        return self.scrollable

    @property
    def CurrentVerticalScrollPercent(self):
        return self.percent


class _FakeElement:
    def __init__(
        self,
        name="Text Editor",
        automation_id="15",
        class_name="Edit",
        enabled=True,
        offscreen=False,
        patterns=None,
    ):
        self.CurrentName = name
        self.CurrentAutomationId = automation_id
        self.CurrentControlType = 50004
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
        patch("services.ai_desktop.uia_click_executor.win32gui.IsWindow", return_value=True),
        patch(
            "services.ai_desktop.uia_click_executor.win32process.GetWindowThreadProcessId",
            return_value=(1, 4242),
        ),
        patch(
            "services.ai_desktop.uia_click_executor.UIATreeInspector._resolve_process_name",
            return_value="notepad.exe",
        ),
        patch.object(UIAScrollExecutor, "_open_uia", return_value=(_FakeUIA(), _FakeRoot(elements))),
        patch.object(UIAScrollExecutor, "_scroll_interface", return_value="SCROLL_IFACE"),
    )


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


class TestUIAScrollExecutor(unittest.TestCase):
    def _run(self, elements, direction="down", unit="page", steps=3,
             expected_signature=None, watchdog=None, identifier="Text Editor"):
        executor = UIAScrollExecutor()
        patches = _patched(elements)
        for item in patches:
            item.start()
        try:
            return executor.execute(
                hwnd=12345,
                identifier=identifier,
                rule=RULE,
                direction=direction,
                unit=unit,
                steps=steps,
                expected_signature=expected_signature,
                watchdog=watchdog,
            )
        finally:
            for item in patches:
                item.stop()

    def _element(self, pattern=None, **kwargs):
        pattern = pattern if pattern is not None else _FakeScrollPattern()
        return _FakeElement(patterns={PATTERN_SCROLL: pattern}, **kwargs), pattern

    def test_01_down_page_scrolls_requested_steps(self):
        element, pattern = self._element()
        result = self._run([element], direction="down", unit="page", steps=3)
        self.assertEqual(result["status"], "EXECUTED")
        self.assertTrue(result["scrolled"])
        self.assertEqual(result["pattern_used"], "ScrollPattern")
        self.assertEqual(result["scroll_steps_requested"], 3)
        self.assertEqual(result["scroll_steps_applied"], 3)
        self.assertFalse(result["watchdog_stopped"])
        self.assertEqual(pattern.calls, [(2, 3), (2, 3), (2, 3)])
        self.assertGreater(result["vertical_percent_after"], result["vertical_percent_before"])

    def test_02_direction_unit_mapping(self):
        cases = {
            ("up", "page"): (2, 0),
            ("up", "line"): (2, 1),
            ("down", "page"): (2, 3),
            ("down", "line"): (2, 4),
        }
        for (direction, unit), expected in cases.items():
            element, pattern = self._element()
            result = self._run([element], direction=direction, unit=unit, steps=1)
            self.assertEqual(pattern.calls, [expected], f"{direction}/{unit}")
            self.assertEqual(result["scroll_direction"], direction)
            self.assertEqual(result["scroll_unit"], unit)

    def test_03_invalid_request_params_fail_closed_before_scan(self):
        bad = (
            dict(direction="left", unit="page", steps=1),
            dict(direction="down", unit="screen", steps=1),
            dict(direction="down", unit="page", steps=0),
            dict(direction="down", unit="page", steps=6),
            dict(direction="down", unit="page", steps=True),
            dict(direction="down", unit="page", steps="3"),
        )
        for kwargs in bad:
            with patch.object(UIAScrollExecutor, "_open_uia") as open_uia:
                with self.assertRaises(UIAScrollError) as ctx:
                    UIAScrollExecutor().execute(12345, "Text Editor", RULE, **kwargs)
                open_uia.assert_not_called()
            self.assertIn(ctx.exception.code, {
                "SCROLL_DIRECTION_INVALID", "SCROLL_UNIT_INVALID", "SCROLL_STEPS_INVALID",
            }, kwargs)

    def test_04_scroll_pattern_unsupported_fails_closed(self):
        element = _FakeElement(patterns={})
        with self.assertRaises(UIAScrollError) as ctx:
            self._run([element])
        self.assertEqual(ctx.exception.code, "SCROLL_PATTERN_UNSUPPORTED")

    def test_05_not_vertically_scrollable_fails_closed(self):
        element, pattern = self._element(pattern=_FakeScrollPattern(scrollable=False))
        with self.assertRaises(UIAScrollError) as ctx:
            self._run([element])
        self.assertEqual(ctx.exception.code, "ELEMENT_NOT_SCROLLABLE")
        self.assertEqual(pattern.calls, [])

    def test_06_identity_drift_blocks_before_scroll(self):
        element, pattern = self._element()
        with self.assertRaises(UIAScrollError) as ctx:
            self._run([element], expected_signature="deadbeef")
        self.assertEqual(ctx.exception.code, "ELEMENT_IDENTITY_DRIFT")
        self.assertEqual(pattern.calls, [])

    def test_07_watchdog_before_first_step_blocks(self):
        element, pattern = self._element()
        with self.assertRaises(UIAScrollError) as ctx:
            self._run([element], watchdog=_Watchdog(stop_after_checks=0))
        self.assertEqual(ctx.exception.code, "SCROLL_BLOCKED_WATCHDOG")
        self.assertEqual(pattern.calls, [])

    def test_08_watchdog_mid_stream_reports_partial_delivery(self):
        element, pattern = self._element()
        result = self._run([element], steps=4, watchdog=_Watchdog(stop_after_checks=2))
        self.assertTrue(result["watchdog_stopped"])
        self.assertEqual(result["scroll_steps_requested"], 4)
        self.assertEqual(result["scroll_steps_applied"], 1)
        self.assertEqual(len(pattern.calls), 1)

    def test_09_disabled_and_offscreen_elements_fail_closed(self):
        disabled, _ = self._element(enabled=False)
        with self.assertRaises(UIAScrollError) as ctx:
            self._run([disabled])
        self.assertEqual(ctx.exception.code, "ELEMENT_DISABLED")

        offscreen, _ = self._element(offscreen=True)
        with self.assertRaises(UIAScrollError) as ctx:
            self._run([offscreen])
        self.assertEqual(ctx.exception.code, "ELEMENT_OFFSCREEN")

    def test_10_not_allowlisted_never_scans(self):
        with patch.object(UIAScrollExecutor, "_open_uia") as open_uia:
            with self.assertRaises(UIAClickError) as ctx:
                UIAScrollExecutor().execute(
                    12345, "Close", RULE, direction="down", unit="page", steps=1)
        self.assertEqual(ctx.exception.code, "ELEMENT_NOT_ALLOWLISTED")
        open_uia.assert_not_called()

    def test_11_ambiguous_match_fails_closed(self):
        first, _ = self._element()
        second, _ = self._element()
        with self.assertRaises(UIAClickError) as ctx:
            self._run([first, second])
        self.assertEqual(ctx.exception.code, "ELEMENT_AMBIGUOUS")

    def test_12_inspect_is_read_only_and_binds_identity(self):
        element, pattern = self._element(pattern=_FakeScrollPattern(percent=12.5))
        executor = UIAScrollExecutor()
        patches = _patched([element])
        for item in patches:
            item.start()
        try:
            inspected = executor.inspect(12345, "Text Editor", RULE)
        finally:
            for item in patches:
                item.stop()
        self.assertTrue(inspected["vertically_scrollable"])
        self.assertEqual(inspected["vertical_percent"], 12.5)
        self.assertEqual(inspected["process_name"], "notepad.exe")
        self.assertEqual(
            inspected["signature"],
            element_identity_signature("Text Editor", "15", "Edit", "Edit"),
        )
        self.assertEqual(pattern.calls, [])

    def test_13_inspect_rejects_unsupported_and_not_scrollable(self):
        executor = UIAScrollExecutor()
        patches = _patched([_FakeElement(patterns={})])
        for item in patches:
            item.start()
        try:
            with self.assertRaises(UIAScrollError) as ctx:
                executor.inspect(12345, "Text Editor", RULE)
        finally:
            for item in patches:
                item.stop()
        self.assertEqual(ctx.exception.code, "SCROLL_PATTERN_UNSUPPORTED")

        element, _ = self._element(pattern=_FakeScrollPattern(scrollable=False))
        patches = _patched([element])
        for item in patches:
            item.start()
        try:
            with self.assertRaises(UIAScrollError) as ctx:
                executor.inspect(12345, "Text Editor", RULE)
        finally:
            for item in patches:
                item.stop()
        self.assertEqual(ctx.exception.code, "ELEMENT_NOT_SCROLLABLE")

    def test_14_failure_after_one_step_is_partial(self):
        class _FailingSecond(_FakeScrollPattern):
            def Scroll(self, horizontal_amount, vertical_amount):
                self.calls.append((horizontal_amount, vertical_amount))
                if len(self.calls) == 2:
                    raise RuntimeError("provider failed mid-sequence")
                self.percent = min(100.0, self.percent + 0.5)

        element, _ = self._element(pattern=_FailingSecond())
        with self.assertRaises(UIAScrollError) as ctx:
            self._run([element], steps=3)
        self.assertEqual(ctx.exception.code, "SCROLL_FAILED")
        self.assertEqual(ctx.exception.delivery_state, UIAScrollError.PARTIAL)
        self.assertEqual(ctx.exception.details["scroll_steps_applied"], 1)

    def test_15_failure_on_first_step_is_not_delivered(self):
        class _FailingFirst(_FakeScrollPattern):
            def Scroll(self, horizontal_amount, vertical_amount):
                self.calls.append((horizontal_amount, vertical_amount))
                raise RuntimeError("provider unavailable")

        element, _ = self._element(pattern=_FailingFirst())
        with self.assertRaises(UIAScrollError) as ctx:
            self._run([element], steps=3)
        self.assertEqual(ctx.exception.delivery_state, UIAScrollError.NOT_DELIVERED)
        self.assertEqual(ctx.exception.details["scroll_steps_applied"], 0)

    def test_16_percent_read_failure_after_steps_is_uncertain(self):
        class _BadPercent(_FakeScrollPattern):
            @property
            def CurrentVerticalScrollPercent(self):
                if self.calls:
                    raise RuntimeError("provider stopped answering")
                return self.percent

        element, _ = self._element(pattern=_BadPercent())
        with self.assertRaises(UIAScrollError) as ctx:
            self._run([element], steps=3)
        self.assertEqual(ctx.exception.code, "SCROLL_STATE_READ_FAILED")
        self.assertEqual(ctx.exception.delivery_state, UIAScrollError.UNCERTAIN)
        self.assertEqual(ctx.exception.details["scroll_steps_applied"], 3)


if __name__ == "__main__":
    unittest.main()
