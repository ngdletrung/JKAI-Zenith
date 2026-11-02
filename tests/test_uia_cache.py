# -*- coding: utf-8 -*-
"""Unit tests for the UIA CacheRequest adapter (services/ai_desktop/uia_cache.py)."""

import sys
import unittest
from types import SimpleNamespace

sys.path.insert(0, ".")

from services.ai_desktop.uia_cache import (
    build_tree_cache_request,
    find_all_cached,
    read_element,
)


class _FakeRect:
    def __init__(self, left, top, right, bottom):
        self.left, self.top, self.right, self.bottom = left, top, right, bottom


class _FakeCacheRequest:
    def __init__(self):
        self.TreeScope = None
        self.properties = []
        self.patterns = []

    def AddProperty(self, value):
        self.properties.append(value)

    def AddPattern(self, value):
        self.patterns.append(value)


class _FakeUIA:
    def __init__(self, request):
        self.request = request
        self.BuildRequests = []

    def CreateCacheRequest(self):
        return self.request

    def FindAllBuildCache(self, scope, condition, request):
        self.BuildRequests.append((scope, condition, request))
        return "CACHED_ARRAY"


class _FakeRoot:
    def __init__(self, result=None, raise_error=False):
        self.result = result
        self.raise_error = raise_error
        self.calls = []

    def FindAllBuildCache(self, scope, condition, request):
        self.calls.append((scope, condition, request))
        if self.raise_error:
            raise RuntimeError("no cache support")
        return self.result

    def FindAll(self, scope, condition):
        return "PLAIN_ARRAY"


def _module(**overrides):
    values = {
        "TreeScope_Element": 1,
        "TreeScope_Children": 2,
        "UIA_NamePropertyId": 30005,
        "UIA_ScrollPatternId": 10004,
    }
    values.update(overrides)
    return SimpleNamespace(**values)


class TestBuildRequest(unittest.TestCase):
    def test_sets_element_and_children_scope(self):
        request = _FakeCacheRequest()
        build_tree_cache_request(_FakeUIA(request), module=_module())
        self.assertEqual(request.TreeScope, 3)

    def test_adds_properties_and_patterns(self):
        request = _FakeCacheRequest()
        build_tree_cache_request(_FakeUIA(request), module=_module())
        self.assertEqual(len(request.properties), 14)
        self.assertEqual(len(request.patterns), 3)
        self.assertIn(30005, request.properties)
        self.assertIn(10004, request.patterns)

    def test_uses_numeric_fallbacks_when_typelib_lacks_names(self):
        request = _FakeCacheRequest()
        build_tree_cache_request(_FakeUIA(request), module=SimpleNamespace())
        self.assertEqual(request.TreeScope, 3)
        self.assertIn(30005, request.properties)
        self.assertIn(10004, request.patterns)

    def test_non_int_constant_falls_back(self):
        request = _FakeCacheRequest()
        module = _module(UIA_NamePropertyId="bad")
        build_tree_cache_request(_FakeUIA(request), module=module)
        self.assertIn(30005, request.properties)


class TestFindAllCached(unittest.TestCase):
    def test_prefers_automation_object(self):
        uia = _FakeUIA(_FakeCacheRequest())
        root = _FakeRoot(result="ROOT_ARRAY")
        result = find_all_cached(uia, root, 4, "cond", "req")
        self.assertEqual(result, "CACHED_ARRAY")
        self.assertEqual(uia.BuildRequests, [(4, "cond", "req")])
        self.assertEqual(root.calls, [])

    def test_falls_back_to_root_when_automation_object_fails(self):
        class _FailingUIA:
            def FindAllBuildCache(self, *args):
                raise RuntimeError("boom")

        root = _FakeRoot(result="ROOT_ARRAY")
        result = find_all_cached(_FailingUIA(), root, 4, "cond", "req")
        self.assertEqual(result, "ROOT_ARRAY")

    def test_returns_none_when_no_owner_supports_cache(self):
        result = find_all_cached(object(), object(), 4, "cond", "req")
        self.assertIsNone(result)

    def test_returns_none_when_root_raises(self):
        result = find_all_cached(object(), _FakeRoot(raise_error=True), 4, "cond", "req")
        self.assertIsNone(result)


class _FakeElement:
    def __init__(self, **values):
        for key, value in values.items():
            setattr(self, key, value)


class TestReadElement(unittest.TestCase):
    def test_prefers_cached_values(self):
        element = _FakeElement(
            CachedName="Save",
            CurrentName="LiveSave",
            CachedAutomationId="save-btn",
            CurrentAutomationId="live-save",
            CachedClassName="Button",
            CurrentClassName="LiveButton",
            CachedControlType=50000,
            CurrentControlType=50001,
            CachedBoundingRectangle=_FakeRect(1, 2, 30, 40),
            CurrentBoundingRectangle=_FakeRect(9, 9, 9, 9),
            CachedIsEnabled=False,
            CurrentIsEnabled=True,
            CachedIsOffscreen=True,
            CurrentIsOffscreen=False,
        )
        info = read_element(element)
        self.assertEqual(info["name"], "Save")
        self.assertEqual(info["automation_id"], "save-btn")
        self.assertEqual(info["class_name"], "Button")
        self.assertEqual(info["control_type_id"], 50000)
        self.assertEqual(info["rect"], (1, 2, 30, 40))
        self.assertFalse(info["is_enabled"])
        self.assertTrue(info["is_offscreen"])
        self.assertTrue(info["from_cache"])

    def test_falls_back_to_current_values(self):
        element = _FakeElement(
            CurrentName="Open",
            CurrentAutomationId="open",
            CurrentClassName="Button",
            CurrentControlType=50000,
            CurrentBoundingRectangle=_FakeRect(0, 0, 10, 10),
            CurrentIsEnabled=True,
            CurrentIsOffscreen=False,
        )
        info = read_element(element)
        self.assertEqual(info["name"], "Open")
        self.assertEqual(info["rect"], (0, 0, 10, 10))
        self.assertFalse(info["from_cache"])

    def test_tolerates_raising_properties(self):
        class _Broken:
            @property
            def CachedName(self):
                raise RuntimeError("dead element")

            @property
            def CurrentName(self):
                return "Fallback"

            @property
            def CachedBoundingRectangle(self):
                raise RuntimeError("dead element")

            @property
            def CurrentBoundingRectangle(self):
                return None

        info = read_element(_Broken())
        self.assertEqual(info["name"], "Fallback")
        self.assertIsNone(info["rect"])
        self.assertTrue(info["is_enabled"])
        self.assertFalse(info["is_offscreen"])

    def test_bad_control_type_and_rect_degrade(self):
        element = _FakeElement(
            CachedName="Weird",
            CachedControlType="not-an-int",
            CachedBoundingRectangle=object(),
        )
        info = read_element(element)
        self.assertEqual(info["control_type_id"], 0)
        self.assertIsNone(info["rect"])

    def test_missing_names_are_empty_strings(self):
        info = read_element(_FakeElement())
        self.assertEqual(info["name"], "")
        self.assertEqual(info["automation_id"], "")
        self.assertEqual(info["class_name"], "")
        self.assertFalse(info["from_cache"])


class TestInspectorFallbackContract(unittest.TestCase):
    def test_inspector_imports_adapter(self):
        import services.ai_desktop.uia_tree_inspector as inspector

        self.assertTrue(hasattr(inspector, "read_uia_element"))
        self.assertTrue(hasattr(inspector, "find_all_cached"))


if __name__ == "__main__":
    unittest.main()
