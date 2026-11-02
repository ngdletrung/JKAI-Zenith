# -*- coding: utf-8 -*-
"""
tests/test_ocr_observer.py
[READ-ONLY OCR OBSERVER + HOST AGENT WIRING TESTS]

The OCR engine is replaced by a strict fake backend, so these tests exercise
real validation, availability gating, capture/recognition error mapping,
truncation, and the agent's opt-in `include_ocr` behaviour without touching a
screen or requiring Tesseract.
"""

import importlib.util
import os
import sys
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, ".")

from services.ai_desktop.ocr_observer import (  # noqa: E402
    OCRObserver,
    OCRObserverError,
    TesseractBackend,
)

ROOT = Path(__file__).resolve().parent.parent


def _load_agent_module():
    spec = importlib.util.spec_from_file_location(
        "jkai_host_desktop_agent_ocr_test", ROOT / "scripts" / "host_desktop_agent.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class _Image:
    def __init__(self):
        self.closed = False

    def close(self):
        self.closed = True


class _Backend:
    engine_name = "fake"

    def __init__(
        self,
        available=True,
        detail="fake-1.0",
        text="hello\nworld\n",
        capture_error=None,
        recognize_error=None,
    ):
        self.available = available
        self.detail = detail
        self.text = text
        self.capture_error = capture_error
        self.recognize_error = recognize_error
        self.calls = []
        self.image = None

    def availability(self):
        return self.available, self.detail

    def capture(self, region):
        self.calls.append(("capture", tuple(region)))
        if self.capture_error:
            raise self.capture_error
        self.image = _Image()
        return self.image

    def recognize(self, image, language):
        self.calls.append(("recognize", language))
        if self.recognize_error:
            raise self.recognize_error
        return self.text


def _patch_window(rect=(0, 0, 200, 100), iconic=False, is_window=True):
    return [
        patch("services.ai_desktop.ocr_observer.win32gui.IsWindow", return_value=is_window),
        patch("services.ai_desktop.ocr_observer.win32gui.IsIconic", return_value=iconic),
        patch("services.ai_desktop.ocr_observer.win32gui.GetWindowRect", return_value=rect),
    ]


class TestOCRObserver(unittest.TestCase):
    def _run(self, observer, **kwargs):
        patches = _patch_window()
        for item in patches:
            item.start()
        try:
            return observer.observe(**kwargs)
        finally:
            for item in patches:
                item.stop()

    def test_01_observe_returns_text_metadata(self):
        backend = _Backend()
        observer = OCRObserver(backend=backend)
        result = self._run(observer, hwnd=1234)
        self.assertEqual(result.text, "hello\nworld\n")
        self.assertEqual(result.line_count, 2)
        self.assertEqual(result.char_count, len("hello\nworld\n"))
        self.assertFalse(result.truncated)
        self.assertEqual(result.region, (0, 0, 200, 100))
        self.assertEqual(result.engine, "fake")
        self.assertTrue(backend.image.closed)

    def test_02_explicit_region_is_used(self):
        backend = _Backend()
        result = self._run(
            OCRObserver(backend=backend), hwnd=1234, region=(10, 20, 110, 120)
        )
        self.assertEqual(result.region, (10, 20, 110, 120))
        self.assertEqual(backend.calls[0], ("capture", (10, 20, 110, 120)))

    def test_03_unavailable_engine_fails_closed(self):
        observer = OCRObserver(backend=_Backend(available=False, detail="PYTESSERACT_NOT_INSTALLED"))
        with self.assertRaises(OCRObserverError) as ctx:
            self._run(observer, hwnd=1234)
        self.assertEqual(ctx.exception.code, "OCR_ENGINE_UNAVAILABLE")
        self.assertIn("PYTESSERACT", ctx.exception.detail)

    def test_04_invalid_language_rejected_before_backend(self):
        backend = _Backend()
        with self.assertRaises(OCRObserverError) as ctx:
            self._run(OCRObserver(backend=backend), hwnd=1234, language="en; rm -rf")
        self.assertEqual(ctx.exception.code, "OCR_LANGUAGE_INVALID")
        self.assertEqual(backend.calls, [])

    def test_05_invalid_hwnd_fails(self):
        with self.assertRaises(OCRObserverError) as ctx:
            self._run(OCRObserver(backend=_Backend()), hwnd=0)
        self.assertEqual(ctx.exception.code, "OCR_HWND_INVALID")

    def test_06_minimized_window_fails(self):
        observer = OCRObserver(backend=_Backend())
        patches = _patch_window(iconic=True)
        for item in patches:
            item.start()
        try:
            with self.assertRaises(OCRObserverError) as ctx:
                observer.observe(hwnd=1234)
        finally:
            for item in patches:
                item.stop()
        self.assertEqual(ctx.exception.code, "OCR_WINDOW_MINIMIZED")

    def test_07_region_too_small_fails(self):
        with self.assertRaises(OCRObserverError) as ctx:
            self._run(OCRObserver(backend=_Backend()), hwnd=1234, region=(0, 0, 4, 4))
        self.assertEqual(ctx.exception.code, "OCR_REGION_TOO_SMALL")

    def test_08_capture_error_mapped(self):
        observer = OCRObserver(backend=_Backend(capture_error=RuntimeError("grab failed")))
        with self.assertRaises(OCRObserverError) as ctx:
            self._run(observer, hwnd=1234)
        self.assertEqual(ctx.exception.code, "OCR_CAPTURE_FAILED")

    def test_09_recognition_error_mapped_and_image_closed(self):
        backend = _Backend(recognize_error=RuntimeError("tesseract died"))
        observer = OCRObserver(backend=backend)
        with self.assertRaises(OCRObserverError) as ctx:
            self._run(observer, hwnd=1234)
        self.assertEqual(ctx.exception.code, "OCR_RECOGNITION_FAILED")
        self.assertTrue(backend.image.closed)

    def test_10_truncates_to_max_chars(self):
        observer = OCRObserver(backend=_Backend(text="x" * 50), max_chars=10)
        result = self._run(observer, hwnd=1234)
        self.assertTrue(result.truncated)
        self.assertEqual(result.char_count, 10)

    def test_11_strips_form_feed_and_nul(self):
        observer = OCRObserver(backend=_Backend(text="a\x00b\x0cc\n"))
        result = self._run(observer, hwnd=1234)
        self.assertEqual(result.text, "abc\n")

    def test_12_availability_reports_missing_pytesseract(self):
        with patch("services.ai_desktop.ocr_observer.importlib.util.find_spec", return_value=None):
            available, detail = TesseractBackend().availability()
        self.assertFalse(available)
        self.assertEqual(detail, "PYTESSERACT_NOT_INSTALLED")

    def test_13_injected_backend_without_probe_is_treated_as_available(self):
        class _ProbeLess:
            engine_name = "probe-less"

            def capture(self, region):
                return _Image()

            def recognize(self, image, language):
                return "ok"

        result = self._run(OCRObserver(backend=_ProbeLess()), hwnd=1234)
        self.assertEqual(result.text, "ok")


class TestAgentOCRBranch(unittest.TestCase):
    def setUp(self):
        self.agent = _load_agent_module()
        self.handler = self.agent.DesktopRequestHandler.__new__(self.agent.DesktopRequestHandler)

    def test_14_disabled_by_default(self):
        with patch.dict(os.environ, {}, clear=False):
            os.environ.pop("JKAI_OCR_ENABLED", None)
            result = self.handler._observe_ocr({}, {"hwnd": 42})
        self.assertEqual(result["status"], "DISABLED")
        self.assertEqual(result["reason"], "JKAI_OCR_ENABLED_NOT_SET")

    def test_15_missing_hwnd_is_typed_error(self):
        with patch.dict(os.environ, {"JKAI_OCR_ENABLED": "1"}):
            result = self.handler._observe_ocr({}, {})
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["code"], "OCR_HWND_INVALID")

    def test_16_unavailable_engine_reported_honestly(self):
        class _Unavailable:
            def __init__(self):
                pass

            def availability(self):
                return False, "TESSERACT_UNAVAILABLE"

            def observe(self, *args, **kwargs):
                raise AssertionError("must not observe when unavailable")

        with patch.dict(os.environ, {"JKAI_OCR_ENABLED": "1"}), patch(
            "services.ai_desktop.ocr_observer.OCRObserver", _Unavailable
        ):
            result = self.handler._observe_ocr({}, {"hwnd": 42})
        self.assertEqual(result["status"], "UNAVAILABLE")
        self.assertEqual(result["reason"], "TESSERACT_UNAVAILABLE")

    def test_17_success_marks_sensitive_and_hashes_text(self):
        class _Result:
            def as_dict(self):
                return {"hwnd": 42, "text": "secret text", "char_count": 11}

        class _Available:
            def __init__(self):
                pass

            def availability(self):
                return True, "5.0"

            def observe(self, hwnd, language="eng", region=None):
                return _Result()

        with patch.dict(os.environ, {"JKAI_OCR_ENABLED": "1"}), patch(
            "services.ai_desktop.ocr_observer.OCRObserver", _Available
        ):
            result = self.handler._observe_ocr({}, {"hwnd": 42})
        self.assertEqual(result["status"], "OK")
        self.assertTrue(result["sensitive"])
        self.assertEqual(len(result["text_sha256"]), 64)

    def test_18_observer_error_is_reported_with_code(self):
        class _Failing:
            def __init__(self):
                pass

            def availability(self):
                return True, "5.0"

            def observe(self, *args, **kwargs):
                raise OCRObserverError("OCR_WINDOW_MINIMIZED", "42")

        with patch.dict(os.environ, {"JKAI_OCR_ENABLED": "1"}), patch(
            "services.ai_desktop.ocr_observer.OCRObserver", _Failing
        ):
            result = self.handler._observe_ocr({}, {"hwnd": 42})
        self.assertEqual(result["status"], "ERROR")
        self.assertEqual(result["code"], "OCR_WINDOW_MINIMIZED")


if __name__ == "__main__":
    unittest.main()
