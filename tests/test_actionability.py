# -*- coding: utf-8 -*-
"""
tests/test_actionability.py
[UNIT TESTS FOR THE AGENT-DESKTOP ACTIONABILITY PORT]

Pure evaluation over node-shaped objects; no COM, no live desktop.
"""

import sys
import unittest

sys.path.insert(0, ".")

from services.ai_desktop.actionability import (
    DELIVERY_KEYBOARD,
    DELIVERY_POINTER,
    DELIVERY_SEMANTIC,
    STATUS_FAIL,
    STATUS_SKIP,
    STATUS_UNKNOWN,
    TERMINAL_ACTION_NOT_SUPPORTED,
    TERMINAL_PATTERN_UNSUPPORTED,
    TERMINAL_SCROLL_PATTERN_UNSUPPORTED,
    evaluate_actionability,
    requirements_for,
)


def _node(**overrides):
    base = {
        "name": "Line down",
        "control_type": "Button",
        "is_enabled": True,
        "is_visible": True,
        "rect": (0, 0, 10, 10),
        "supported_patterns": ("InvokePattern",),
    }
    base.update(overrides)
    return base


class TestRequirementsMatrix(unittest.TestCase):
    def test_01_pointer_actions_require_stability_and_text_actions_do_not(self):
        self.assertTrue(requirements_for("click").stable)
        self.assertTrue(requirements_for("click").receives_events)
        self.assertFalse(requirements_for("type_text").stable)
        self.assertTrue(requirements_for("type_text").editable)
        self.assertFalse(requirements_for("focus").visible)
        self.assertFalse(requirements_for("key_combo").enabled)

    def test_02_unknown_action_is_rejected(self):
        with self.assertRaises(ValueError):
            requirements_for("teleport")
        with self.assertRaises(ValueError):
            evaluate_actionability(_node(), "teleport")


class TestClickGates(unittest.TestCase):
    def test_03_invoke_button_is_actionable(self):
        report = evaluate_actionability(_node(), "click")
        self.assertTrue(report.actionable)
        self.assertIsNone(report.terminal_code)
        self.assertEqual(report.failure_reasons(), "")

    def test_04_missing_pattern_is_terminal(self):
        report = evaluate_actionability(_node(supported_patterns=()), "click")
        self.assertFalse(report.actionable)
        self.assertEqual(report.terminal_code, TERMINAL_PATTERN_UNSUPPORTED)

    def test_05_menuitem_expand_collapse_is_accepted(self):
        node = _node(control_type="MenuItem", supported_patterns=("ExpandCollapsePattern",))
        self.assertTrue(evaluate_actionability(node, "click").actionable)
        other = _node(supported_patterns=("ExpandCollapsePattern",))
        self.assertFalse(evaluate_actionability(other, "click").actionable)

    def test_06_disabled_element_is_blocked_without_terminal_code(self):
        report = evaluate_actionability(_node(is_enabled=False), "click")
        self.assertFalse(report.actionable)
        self.assertIsNone(report.terminal_code)
        self.assertEqual(report.blocking_checks[0].check, "enabled")

    def test_07_offscreen_element_is_blocked(self):
        report = evaluate_actionability(_node(is_visible=False), "click")
        self.assertFalse(report.actionable)
        self.assertEqual(report.blocking_checks[0].check, "visible")

    def test_08_unknown_live_state_blocks_as_unknown(self):
        report = evaluate_actionability(_node(is_enabled=None), "click")
        self.assertFalse(report.actionable)
        self.assertEqual(report.blocking_checks[0].status, STATUS_UNKNOWN)

    def test_09_semantic_delivery_ignores_zero_sized_bounds(self):
        report = evaluate_actionability(
            _node(rect=(5, 5, 5, 5)), "click", delivery=DELIVERY_SEMANTIC
        )
        self.assertTrue(report.actionable)

    def test_10_pointer_delivery_rejects_zero_sized_bounds(self):
        report = evaluate_actionability(
            _node(rect=(5, 5, 5, 5)), "click", delivery=DELIVERY_POINTER
        )
        self.assertFalse(report.actionable)
        self.assertEqual(report.blocking_checks[0].reason, "bounds are zero-sized")

    def test_11_pointer_delivery_stability_is_incomplete_without_a_sampler(self):
        report = evaluate_actionability(_node(), "click", delivery=DELIVERY_POINTER)
        self.assertFalse(report.actionable)
        stable = [check for check in report.checks if check.check == "stable"][0]
        self.assertEqual(stable.status, STATUS_UNKNOWN)

    def test_12_semantic_delivery_skips_stability(self):
        report = evaluate_actionability(_node(), "click", delivery=DELIVERY_SEMANTIC)
        stable = [check for check in report.checks if check.check == "stable"][0]
        self.assertEqual(stable.status, STATUS_SKIP)

    def test_13_terminal_code_outranks_an_earlier_transient_failure(self):
        report = evaluate_actionability(
            _node(is_enabled=False, supported_patterns=()), "click"
        )
        self.assertEqual(report.blocking_checks[0].check, "enabled")
        self.assertEqual(report.terminal_code, TERMINAL_PATTERN_UNSUPPORTED)
        self.assertIn("enabled", report.failure_reasons())
        self.assertIn("supported_action", report.failure_reasons())


class TestScrollAndTextGates(unittest.TestCase):
    def test_14_scroll_requires_scroll_pattern(self):
        report = evaluate_actionability(
            _node(control_type="Edit", supported_patterns=("TextPattern",)), "scroll"
        )
        self.assertFalse(report.actionable)
        self.assertEqual(report.terminal_code, TERMINAL_SCROLL_PATTERN_UNSUPPORTED)

    def test_15_scroll_with_pattern_is_actionable_without_pointer_evidence(self):
        report = evaluate_actionability(
            _node(control_type="Pane", supported_patterns=("ScrollPattern",), rect=(0, 0, 0, 0)),
            "scroll",
        )
        self.assertTrue(report.actionable)

    def test_16_type_text_accepts_editable_control_types(self):
        for control_type in ("Edit", "Document", "ComboBox"):
            report = evaluate_actionability(
                _node(control_type=control_type, supported_patterns=()),
                "type_text",
                delivery=DELIVERY_KEYBOARD,
            )
            self.assertTrue(report.actionable, control_type)

    def test_17_type_text_accepts_value_or_text_pattern(self):
        for pattern in ("ValuePattern", "TextPattern"):
            report = evaluate_actionability(
                _node(control_type="Custom", supported_patterns=(pattern,)),
                "type_text",
                delivery=DELIVERY_KEYBOARD,
            )
            self.assertTrue(report.actionable, pattern)

    def test_18_type_text_rejects_non_editable_elements(self):
        report = evaluate_actionability(
            _node(control_type="Button", supported_patterns=("InvokePattern",)),
            "type_text",
            delivery=DELIVERY_KEYBOARD,
        )
        self.assertFalse(report.actionable)
        self.assertEqual(report.terminal_code, TERMINAL_ACTION_NOT_SUPPORTED)
        self.assertEqual(report.blocking_checks[0].check, "editable")

    def test_19_focus_has_no_requirements(self):
        node = _node(is_enabled=False, is_visible=False, supported_patterns=())
        report = evaluate_actionability(node, "focus")
        self.assertTrue(report.actionable)
        required = {
            check.check: check.status for check in report.checks
        }
        self.assertEqual(required["enabled"], STATUS_SKIP)
        self.assertEqual(required["visible"], STATUS_SKIP)
        self.assertEqual(required["editable"], STATUS_SKIP)


class TestReportShape(unittest.TestCase):
    def test_20_as_dict_is_json_ready(self):
        payload = evaluate_actionability(_node(), "click").as_dict()
        self.assertEqual(payload["action"], "click")
        self.assertTrue(payload["actionable"])
        self.assertIsNone(payload["terminal_code"])
        self.assertEqual(len(payload["checks"]), 5)
        self.assertEqual(
            set(payload["checks"][0]), {"check", "status", "reason", "terminal_code"}
        )

    def test_21_failure_status_is_reported_verbatim(self):
        report = evaluate_actionability(_node(is_visible=False), "click")
        self.assertEqual(report.blocking_checks[0].status, STATUS_FAIL)


if __name__ == "__main__":
    unittest.main()
