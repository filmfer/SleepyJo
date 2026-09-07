"""Programmatic icon factory (Pillow). No shipped image assets.

Draws outline eyes; foreground color follows OS Light/Dark theme.
Icons are cached per (state, dark, size) tuple in an O(1) dict.
"""

from __future__ import annotations

import logging
import math
import platform
import subprocess
from typing import Dict, Optional, Tuple

from PIL import Image, ImageDraw

log = logging.getLogger(__name__)

IconKind = str  # "closed" | "open" | "tired" | "blink_closed"
_cache: Dict[Tuple[str, bool, int], "Image.Image"] = {}
FORE_COLOR_LIGHT_THEME = (0, 0, 0, 255)   # black outline on light theme
FORE_COLOR_DARK_THEME = (255, 255, 255, 255)  # white outline on dark theme


# --- Theme detection ---------------------------------------------------------
def is_dark_theme() -> bool:
    """Best-effort OS theme detection; defaults to dark (white outline)."""
    system = platform.system()
    try:
        if system == "Darwin":
            out = subprocess.run(
                ["defaults", "read", "-g", "AppleInterfaceStyle"],
                capture_output=True, text=True, timeout=2)
            return out.returncode == 0 and "Dark" in out.stdout
        if system == "Windows":
            import winreg  # type: ignore[import-not-found]
            with winreg.OpenKey(
                winreg.HKEY_CURRENT_USER,
                r"Software\Microsoft\Windows\CurrentVersion\Themes\PersonalTheme",
            ) as key:
                val, _ = winreg.QueryValueEx(key, "SystemUsesLightTheme")
                return not bool(val)
        if system == "Linux":
            out = subprocess.run(
                ["gsettings", "get", "org.gnome.desktop.interface", "color-scheme"],
                capture_output=True, text=True, timeout=2)
            return "dark" in out.stdout.lower()
    except Exception as exc:  # noqa: BLE001
        log.debug("theme detection failed: %s", exc)
    return True


# --- Renderers ---------------------------------------------------------------
def _tray_size() -> int:
    """Native tray icon size per platform."""
    system = platform.system()
    if system == "Darwin":
        return 22
    if system == "Windows":
        return 16
    return 24


def _draw_eye(draw: ImageDraw.ImageDraw, cx: float, cy: float, w: float,
              h: float, color: Tuple[int, int, int, int], width: int,
              closed: bool) -> None:
    """Outline eye: almond (open) or straight lid (closed)."""
    box = (cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2)
    if closed:
        draw.line((box[0], cy, box[2], cy), fill=color, width=width)
        return
    draw.arc(box, start=200, end=340, fill=color, width=width)   # upper lid
    draw.arc(box, start=20, end=160, fill=color, width=width)    # lower lid
    r = h * 0.22
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), outline=color, width=width)


def _draw_tired(draw: ImageDraw.ImageDraw, cx: float, cy: float, w: float,
                h: float, color: Tuple[int, int, int, int], width: int) -> None:
    """Open eye with a toothpick propping the upper eyelid."""
    _draw_eye(draw, cx, cy, w, h, color, width, closed=False)
    # Toothpick: diagonal stick under the upper lid, left to right.
    x0, y0 = cx - w * 0.55, cy - h * 0.05
    x1, y1 = cx + w * 0.65, cy - h * 0.85
    draw.line((x0, y0, x1, y1), fill=color, width=max(1, width))
    # Small match-head.
    r = w * 0.08
    draw.ellipse((x1 - r, y1 - r, x1 + r, y1 + r), outline=color, width=max(1, width))


def render(kind: IconKind, dark: Optional[bool] = None,
           size: Optional[int] = None) -> "Image.Image":
    """Render (and cache) a tray icon. O(1) via dict memoization."""
    if dark is None:
        dark = is_dark_theme()
    if size is None:
        size = _tray_size()
    key = (kind, dark, size)
    if key in _cache:
        return _cache[key]

    color = FORE_COLOR_DARK_THEME if dark else FORE_COLOR_LIGHT_THEME
    img = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = size / 2, size / 2
    w, h = size * 0.8, size * 0.5
    width = max(1, size // 12)

    if kind == "closed":
        _draw_eye(draw, cx, cy, w, h, color, width, closed=True)
    elif kind == "open":
        _draw_eye(draw, cx, cy, w, h, color, width, closed=False)
    elif kind == "tired":
        _draw_tired(draw, cx, cy, w, h, color, width)
    elif kind == "blink_closed":
        # Blink frame: slightly angled closed lid to feel animated.
        draw.line((cx - w / 2, cy + 1, cx + w / 2, cy - 1), fill=color, width=width)
    else:
        raise ValueError(f"unknown icon kind: {kind}")

    _cache[key] = img
    return img


def blink_sequence() -> tuple:
    """Frames for the pre-sleep animation: 3 blinks (open/closed pairs)."""
    return ("open", "blink_closed", "open", "blink_closed",
            "open", "blink_closed", "open")


def tired_after_secs(hours: float = 1.0, secs: Optional[float] = None) -> bool:
    """Whether the 'tired' icon should show (awake longer than `hours`)."""
    return (secs if secs is not None else 0) >= math.ceil(hours * 3600)


def clear_cache() -> None:
    _cache.clear()
