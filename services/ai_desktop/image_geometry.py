# -*- coding: utf-8 -*-
"""
services/ai_desktop/image_geometry.py
[IMAGE GEOMETRY HELPERS - ADAPTED FROM UI-TARS]

Portions adapted from ByteDance/UI-TARS
(https://github.com/bytedance/UI-TARS), `codes/ui_tars/action_parser.py`
(Apache-2.0, Copyright (c) 2025 Bytedance Ltd. and/or its affiliates).
See NOTICE.md, CREDITS.md and LICENSES/Apache-2.0.txt.

UI-TARS uses these helpers to bound screenshot pixels before model input.
JKAI uses them only to keep Tesseract captures inside a safe pixel budget;
coordinates are never injected into the desktop, so no UI-TARS action or
pyautogui code path is imported.
"""

from __future__ import annotations

import math
from typing import Tuple

IMAGE_FACTOR = 28
MIN_PIXELS = 100 * 28 * 28
MAX_PIXELS = 16384 * 28 * 28
MAX_RATIO = 200


def _positive_int(value: int, name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        raise ValueError(f"{name} must be a positive int, got {value!r}")
    return value


def _positive_number(value: float, name: str) -> float:
    if isinstance(value, bool) or not isinstance(value, (int, float)):
        raise ValueError(f"{name} must be a positive number, got {value!r}")
    if not math.isfinite(value) or value <= 0:
        raise ValueError(f"{name} must be a positive number, got {value!r}")
    return value


def _pixel_budget(min_pixels: int, max_pixels: int) -> Tuple[int, int]:
    low = _positive_int(min_pixels, "min_pixels")
    high = _positive_int(max_pixels, "max_pixels")
    if low > high:
        raise ValueError("min_pixels must not exceed max_pixels")
    return low, high


def round_by_factor(number: int, factor: int) -> int:
    factor = _positive_int(factor, "factor")
    return int(round(_positive_number(number, "number") / factor) * factor)


def ceil_by_factor(number: int, factor: int) -> int:
    factor = _positive_int(factor, "factor")
    return int(math.ceil(_positive_number(number, "number") / factor) * factor)


def floor_by_factor(number: int, factor: int) -> int:
    factor = _positive_int(factor, "factor")
    return int(math.floor(_positive_number(number, "number") / factor) * factor)


def linear_resize(
    height: int,
    width: int,
    factor: int = IMAGE_FACTOR,
    min_pixels: int = MIN_PIXELS,
    max_pixels: int = MAX_PIXELS,
) -> Tuple[int, int]:
    """Scale by a single ratio so the pixel count lands in the budget."""
    height = _positive_int(height, "height")
    width = _positive_int(width, "width")
    min_pixels, max_pixels = _pixel_budget(min_pixels, max_pixels)

    pixels = width * height
    if pixels > max_pixels:
        ratio = math.sqrt(max_pixels / pixels)
        width = min(width, max(1, int(width * ratio)))
        height = min(height, max(1, int(height * ratio)))
    elif pixels < min_pixels:
        ratio = math.sqrt(min_pixels / pixels)
        width = max(width, math.ceil(width * ratio))
        height = max(height, math.ceil(height * ratio))
    return height, width


def smart_resize(
    height: int,
    width: int,
    factor: int = IMAGE_FACTOR,
    min_pixels: int = MIN_PIXELS,
    max_pixels: int = MAX_PIXELS,
) -> Tuple[int, int]:
    """Resize so both sides are factor-aligned and pixels stay in budget."""
    height = _positive_int(height, "height")
    width = _positive_int(width, "width")
    factor = _positive_int(factor, "factor")
    min_pixels, max_pixels = _pixel_budget(min_pixels, max_pixels)

    if max(height, width) / min(height, width) > MAX_RATIO:
        raise ValueError(
            f"absolute aspect ratio must be smaller than {MAX_RATIO}, "
            f"got {max(height, width) / min(height, width)}"
        )

    h_bar = max(factor, round_by_factor(height, factor))
    w_bar = max(factor, round_by_factor(width, factor))
    if h_bar * w_bar > max_pixels:
        beta = math.sqrt((height * width) / max_pixels)
        h_bar = floor_by_factor(height / beta, factor)
        w_bar = floor_by_factor(width / beta, factor)
        h_bar = max(factor, h_bar)
        w_bar = max(factor, w_bar)
    elif h_bar * w_bar < min_pixels:
        beta = math.sqrt(min_pixels / (height * width))
        h_bar = ceil_by_factor(height * beta, factor)
        w_bar = ceil_by_factor(width * beta, factor)
    return h_bar, w_bar
