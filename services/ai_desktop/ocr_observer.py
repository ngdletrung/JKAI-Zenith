# -*- coding: utf-8 -*-
"""
services/ai_desktop/ocr_observer.py
[READ-ONLY OCR OBSERVATION - L1]

Captures one window's pixels in memory and recognizes visible text with
Tesseract. This is observation only:

  * no input injection, no focus change, no HWND messages, no lease/nonce;
  * captured images never touch disk and are discarded after recognition;
  * nothing here can reach the mutation path.

The backend is lazy: hosts without `pytesseract` or the Tesseract binary report
an honest `available: false` instead of crashing. Callers must treat OCR output
as untrusted text (it may contain secrets shown on screen), which is why the
host agent keeps the whole feature behind `JKAI_OCR_ENABLED=1` plus an explicit
`include_ocr` request flag.

License posture: pytesseract, Tesseract and tessdata are Apache-2.0; Pillow is
HPND. Pixel-budget geometry is adapted from UI-TARS (Apache-2.0, see
`services/ai_desktop/image_geometry.py`). All are recorded in
`config/security/third_party_manifest.json` and verified by
`scripts/verify_third_party_licenses.py`.
"""

from __future__ import annotations

import importlib.util
import re
import time
from dataclasses import dataclass, asdict
from typing import Any, Dict, Optional, Protocol, Tuple

import win32gui

MAX_OCR_CHARS = 8000
DEFAULT_LANGUAGE = "eng"
MIN_REGION_PX = 8
_MAX_CAPTURE_PX = 8000
# Keep recognition inside a predictable memory budget. 4K captures stay
# untouched; only 5K/8K regions are downscaled by a single ratio.
MAX_OCR_PIXELS = 12_000_000
_LANGUAGE_RE = re.compile(r"^[a-z]{3}(?:\+[a-z]{3}){0,3}$")


class OCRObserverError(RuntimeError):
    """Typed fail-closed error; `code` is stable for receipts and tests."""

    def __init__(self, code: str, detail: str = "") -> None:
        super().__init__(f"{code}: {detail}" if detail else code)
        self.code = code
        self.detail = detail


@dataclass(frozen=True)
class OCRResult:
    hwnd: int
    text: str
    line_count: int
    char_count: int
    truncated: bool
    region: Tuple[int, int, int, int]
    width: int
    height: int
    language: str
    engine: str
    duration_ms: int

    def as_dict(self) -> Dict[str, Any]:
        payload = asdict(self)
        payload["region"] = list(self.region)
        return payload


class OCRBackend(Protocol):
    def availability(self) -> Tuple[bool, str]: ...

    def capture(self, region: Tuple[int, int, int, int]) -> Any: ...

    def recognize(self, image: Any, language: str) -> str: ...


class TesseractBackend:
    """Default backend: Pillow capture + pytesseract/Tesseract recognition."""

    engine_name = "tesseract"

    def __init__(self, timeout_seconds: float = 15.0, max_pixels: int = MAX_OCR_PIXELS) -> None:
        self.timeout_seconds = float(timeout_seconds)
        self.max_pixels = max(1, int(max_pixels))

    def availability(self) -> Tuple[bool, str]:
        if importlib.util.find_spec("pytesseract") is None:
            return False, "PYTESSERACT_NOT_INSTALLED"
        if importlib.util.find_spec("PIL") is None:
            return False, "PILLOW_NOT_INSTALLED"
        try:
            import pytesseract

            version = pytesseract.get_tesseract_version()
        except Exception as exc:
            return False, f"TESSERACT_UNAVAILABLE: {type(exc).__name__}"
        return True, str(version)

    def capture(self, region: Tuple[int, int, int, int]) -> Any:
        from PIL import ImageGrab

        return ImageGrab.grab(bbox=region, all_screens=True)

    def recognize(self, image: Any, language: str) -> str:
        import pytesseract

        bounded, resized = self._bound_pixels(image)
        try:
            return pytesseract.image_to_string(bounded, lang=language, timeout=self.timeout_seconds)
        finally:
            if resized:
                try:
                    bounded.close()
                except Exception:
                    pass

    def _bound_pixels(self, image: Any) -> Tuple[Any, bool]:
        """Downscale oversized captures; failures keep the original image."""
        try:
            width, height = image.size
            width, height = int(width), int(height)
            if width <= 0 or height <= 0 or width * height <= self.max_pixels:
                return image, False
            from .image_geometry import linear_resize

            new_height, new_width = linear_resize(height, width, max_pixels=self.max_pixels)
            from PIL import Image

            return image.resize((new_width, new_height), Image.LANCZOS), True
        except Exception:
            return image, False


class OCRObserver:
    """Read-only OCR of one HWND region on a fresh capture."""

    def __init__(self, backend: Optional[OCRBackend] = None, max_chars: int = MAX_OCR_CHARS) -> None:
        self.backend = backend if backend is not None else TesseractBackend()
        self.max_chars = max(1, int(max_chars))

    def availability(self) -> Tuple[bool, str]:
        probe = getattr(self.backend, "availability", None)
        if not callable(probe):
            # Explicitly injected backend: trust the caller, but still degrade
            # safely if its probe itself fails.
            return True, "INJECTED_BACKEND"
        try:
            return probe()
        except Exception as exc:
            return False, f"BACKEND_PROBE_FAILED: {type(exc).__name__}"

    @staticmethod
    def _validate_language(language: str) -> str:
        clean = str(language or DEFAULT_LANGUAGE).strip().lower()
        if not _LANGUAGE_RE.match(clean):
            raise OCRObserverError("OCR_LANGUAGE_INVALID", clean)
        return clean

    @staticmethod
    def _region(hwnd: int, region: Optional[Tuple[int, int, int, int]]) -> Tuple[int, int, int, int]:
        if isinstance(hwnd, bool) or not isinstance(hwnd, int) or hwnd <= 0:
            raise OCRObserverError("OCR_HWND_INVALID", str(hwnd))
        try:
            if not win32gui.IsWindow(hwnd):
                raise OCRObserverError("OCR_HWND_INVALID", str(hwnd))
        except OCRObserverError:
            raise
        except Exception as exc:
            raise OCRObserverError("OCR_HWND_INVALID", str(exc)) from exc

        try:
            if win32gui.IsIconic(hwnd):
                raise OCRObserverError("OCR_WINDOW_MINIMIZED", str(hwnd))
        except OCRObserverError:
            raise
        except Exception:
            pass

        if region is None:
            try:
                rect = win32gui.GetWindowRect(hwnd)
            except Exception as exc:
                raise OCRObserverError("OCR_CAPTURE_FAILED", f"GetWindowRect: {exc}") from exc
            rect = tuple(int(v) for v in rect)
        else:
            if not isinstance(region, (list, tuple)) or len(region) != 4:
                raise OCRObserverError("OCR_REGION_INVALID", str(region))
            if any(isinstance(v, bool) or not isinstance(v, int) for v in region):
                raise OCRObserverError("OCR_REGION_INVALID", str(region))
            rect = tuple(region)

        left, top, right, bottom = rect
        width, height = right - left, bottom - top
        if width < MIN_REGION_PX or height < MIN_REGION_PX:
            raise OCRObserverError("OCR_REGION_TOO_SMALL", f"{width}x{height}")
        if width > _MAX_CAPTURE_PX or height > _MAX_CAPTURE_PX:
            raise OCRObserverError("OCR_REGION_TOO_LARGE", f"{width}x{height}")
        return (left, top, right, bottom)

    def observe(
        self,
        hwnd: int,
        language: str = DEFAULT_LANGUAGE,
        region: Optional[Tuple[int, int, int, int]] = None,
    ) -> OCRResult:
        clean_language = self._validate_language(language)
        rect = self._region(hwnd, region)
        available, detail = self.availability()
        if not available:
            raise OCRObserverError("OCR_ENGINE_UNAVAILABLE", detail)

        started = time.perf_counter()
        try:
            image = self.backend.capture(rect)
        except Exception as exc:
            raise OCRObserverError("OCR_CAPTURE_FAILED", str(exc)) from exc
        if image is None:
            raise OCRObserverError("OCR_CAPTURE_FAILED", "backend returned no image")

        try:
            raw = self.backend.recognize(image, clean_language)
        except Exception as exc:
            raise OCRObserverError("OCR_RECOGNITION_FAILED", str(exc)) from exc
        finally:
            close = getattr(image, "close", None)
            if callable(close):
                try:
                    close()
                except Exception:
                    pass
        duration_ms = int((time.perf_counter() - started) * 1000)

        if isinstance(raw, bytes):
            raw = raw.decode("utf-8", errors="replace")
        text = str(raw or "").replace("\x00", "").replace("\x0c", "")
        truncated = len(text) > self.max_chars
        if truncated:
            text = text[: self.max_chars]

        return OCRResult(
            hwnd=hwnd,
            text=text,
            line_count=sum(1 for line in text.splitlines() if line.strip()),
            char_count=len(text),
            truncated=truncated,
            region=rect,
            width=rect[2] - rect[0],
            height=rect[3] - rect[1],
            language=clean_language,
            engine=str(getattr(self.backend, "engine_name", type(self.backend).__name__)),
            duration_ms=duration_ms,
        )
