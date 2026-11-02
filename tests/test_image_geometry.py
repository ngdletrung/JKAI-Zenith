# -*- coding: utf-8 -*-
"""Unit tests for the UI-TARS-derived image geometry helpers and OCR pixel guard."""

import sys
import unittest
from types import SimpleNamespace
from unittest.mock import patch

sys.path.insert(0, ".")

from services.ai_desktop.image_geometry import (
    MAX_PIXELS,
    MIN_PIXELS,
    ceil_by_factor,
    floor_by_factor,
    linear_resize,
    round_by_factor,
    smart_resize,
)
from services.ai_desktop.ocr_observer import MAX_OCR_PIXELS, TesseractBackend


class TestFactorRounding(unittest.TestCase):
    def test_round(self):
        self.assertEqual(round_by_factor(1080, 28), 1092)
        self.assertEqual(round_by_factor(1000, 28), 1008)

    def test_ceil(self):
        self.assertEqual(ceil_by_factor(1081, 28), 1092)
        self.assertEqual(ceil_by_factor(1080, 28), 1092)

    def test_floor(self):
        self.assertEqual(floor_by_factor(1091, 28), 1064)

    def test_invalid_inputs(self):
        for func in (round_by_factor, ceil_by_factor, floor_by_factor):
            with self.assertRaises(ValueError):
                func(100, 0)
            with self.assertRaises(ValueError):
                func(0, 28)
            with self.assertRaises(ValueError):
                func(True, 28)


class TestLinearResize(unittest.TestCase):
    def test_large_image_downscales_within_budget(self):
        height, width = linear_resize(2160, 3840, max_pixels=4_000_000)
        self.assertLessEqual(height * width, 4_000_000)
        self.assertAlmostEqual(width / height, 3840 / 2160, places=1)

    def test_small_image_upscales_to_minimum(self):
        height, width = linear_resize(10, 10, min_pixels=MIN_PIXELS, max_pixels=MAX_PIXELS)
        self.assertGreaterEqual(height * width, MIN_PIXELS)

    def test_within_budget_is_unchanged(self):
        self.assertEqual(linear_resize(1080, 1920), (1080, 1920))

    def test_min_above_max_rejected(self):
        with self.assertRaises(ValueError):
            linear_resize(100, 100, min_pixels=1000, max_pixels=500)


class TestSmartResize(unittest.TestCase):
    def test_sides_are_factor_aligned(self):
        height, width = smart_resize(1080, 1920)
        self.assertEqual(height % 28, 0)
        self.assertEqual(width % 28, 0)

    def test_large_image_fits_budget_and_keeps_ratio(self):
        height, width = smart_resize(4320, 7680, max_pixels=12_000_000)
        self.assertLessEqual(height * width, 12_000_000)
        self.assertAlmostEqual(width / height, 7680 / 4320, delta=0.05)

    def test_extreme_ratio_rejected(self):
        with self.assertRaises(ValueError):
            smart_resize(1, 300)

    def test_invalid_dimensions_rejected(self):
        with self.assertRaises(ValueError):
            smart_resize(0, 100)


class _FakeImage:
    def __init__(self, size, fail_resize=False):
        self.size = size
        self.fail_resize = fail_resize
        self.closed = False
        self.children = []

    def resize(self, size, resample):
        if self.fail_resize:
            raise RuntimeError("resize failed")
        child = _FakeImage(size)
        self.children.append(child)
        return child

    def close(self):
        self.closed = True


class TestOcrPixelGuard(unittest.TestCase):
    def _run(self, image, backend=None):
        captured = {}

        def fake_image_to_string(img, lang, timeout):
            captured["size"] = img.size
            captured["lang"] = lang
            captured["timeout"] = timeout
            return "text"

        fake_module = SimpleNamespace(image_to_string=fake_image_to_string)
        with patch.dict(sys.modules, {"pytesseract": fake_module}):
            result = (backend or TesseractBackend()).recognize(image, "eng")
        return result, captured

    def test_large_capture_is_downscaled_and_child_closed(self):
        image = _FakeImage((10_000, 10_000))
        result, captured = self._run(image)
        self.assertEqual(result, "text")
        self.assertEqual(len(image.children), 1)
        child = image.children[0]
        self.assertLessEqual(child.size[0] * child.size[1], MAX_OCR_PIXELS)
        self.assertTrue(child.closed)
        self.assertFalse(image.closed)

    def test_capture_within_budget_is_untouched(self):
        image = _FakeImage((1920, 1080))
        _, captured = self._run(image)
        self.assertEqual(captured["size"], (1920, 1080))
        self.assertEqual(image.children, [])
        self.assertEqual(captured["lang"], "eng")
        self.assertGreater(captured["timeout"], 0)

    def test_resize_failure_falls_back_to_original(self):
        image = _FakeImage((10_000, 10_000), fail_resize=True)
        _, captured = self._run(image)
        self.assertEqual(captured["size"], (10_000, 10_000))

    def test_invalid_size_falls_back(self):
        image = _FakeImage(("bad", "size"))
        _, captured = self._run(image)
        self.assertEqual(captured["size"], ("bad", "size"))

    def test_custom_budget_is_honoured(self):
        image = _FakeImage((4000, 4000))
        _, captured = self._run(image, backend=TesseractBackend(max_pixels=4_000_000))
        self.assertLessEqual(captured["size"][0] * captured["size"][1], 4_000_000)


if __name__ == "__main__":
    unittest.main()
