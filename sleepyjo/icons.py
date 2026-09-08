"""Programmatic icon factory (Pillow). No shipped image assets.

Draws outline eyes with 4x supersampling (LANCZOS downscale) for smooth,
detailed rendering at tiny tray sizes. Foreground color follows the OS
Light/Dark theme. Icons cached per (kind, dark, size) — O(1) lookups.
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
SS = 6  # supersample factor
FORE_LIGHT = (0, 0, 0, 255)
FORE_DARK = (255, 255, 255, 255)


def is_dark_theme() -> bool:
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


def _tray_size() -> int:
    system = platform.system()
    if system == "Darwin":
        return 22
    if system == "Windows":
        return 16
    return 24


def _almond(draw: ImageDraw.ImageDraw, cx: float, cy: float, w: float,
            h: float, color, lw: int) -> None:
    """Almond silhouette: upper lid arc + shallower lower lid arc."""
    draw.arc((cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2),
             start=195, end=345, fill=color, width=lw)
    draw.arc((cx - w / 2, cy - h * 0.30, cx + w / 2, cy + h * 0.62),
             start=25, end=155, fill=color, width=lw)


def _eye(draw: ImageDraw.ImageDraw, cx: float, cy: float, w: float,
         h: float, color, lw: int, closed: bool) -> None:
    """Almond eye. Open: solid pupil + 3 lashes on the upper lid.
    Closed: same almond, empty, with 3 lashes hanging from the lower lid."""
    _almond(draw, cx, cy, w, h, color, lw)
    lash_len = h * 0.30
    if closed:
        # Lashes from the lower arc, hanging down/outward.
        lrx, lry = w / 2 * 0.92, h * 0.42
        lcy = cy + h * 0.14
        for phi in (65.0, 90.0, 115.0):
            a = math.radians(phi)
            bx = cx + lrx * math.cos(a)
            by = lcy + lry * math.sin(a)
            dx, dy = math.cos(a), math.sin(a)
            draw.line((bx, by, bx + dx * lash_len, by + dy * lash_len),
                      fill=color, width=max(1, lw - 1))
        return
    # Solid pupil (single filled circle — reads cleanly at tray size).
    r = h * 0.30
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    # Lashes from the upper arc, radiating up/outward.
    urx, ury = w / 2 * 0.94, h / 2 * 0.94
    for phi in (45.0, 90.0, 135.0):
        a = math.radians(phi)
        bx = cx + urx * math.cos(a)
        by = cy - ury * math.sin(a)
        dx, dy = math.cos(a), -math.sin(a)
        draw.line((bx, by, bx + dx * lash_len, by + dy * lash_len),
                  fill=color, width=max(1, lw - 1))


def _tired(draw: ImageDraw.ImageDraw, cx: float, cy: float, w: float,
           h: float, color, lw: int) -> None:
    """Open eye with a toothpick propping the droopy upper eyelid."""
    _almond(draw, cx, cy, w, h, color, lw)
    # Solid pupil.
    r = h * 0.30
    draw.ellipse((cx - r, cy - r, cx + r, cy + r), fill=color)
    # Droopy upper lid sagging into the eye.
    draw.arc((cx - w * 0.42, cy - h * 0.75, cx + w * 0.42, cy + h * 0.35),
             start=215, end=325, fill=color, width=max(1, lw - 1))
    # Toothpick anchored on the lid, extending up-right.
    x0, y0 = cx - w * 0.22, cy - h * 0.52
    x1, y1 = cx + w * 0.55, cy - h * 1.15
    draw.line((x0, y0, x1, y1), fill=color, width=max(1, lw))
    # Match head.
    mr = w * 0.10
    draw.ellipse((x1 - mr, y1 - mr, x1 + mr, y1 + mr), outline=color,
                 width=max(1, lw - 1))


def render(kind: IconKind, dark: Optional[bool] = None,
           size: Optional[int] = None) -> "Image.Image":
    if dark is None:
        dark = is_dark_theme()
    if size is None:
        size = _tray_size()
    key = (kind, dark, size)
    if key in _cache:
        return _cache[key]

    color = FORE_DARK if dark else FORE_LIGHT
    ss = size * SS
    img = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)
    cx, cy = ss / 2, ss / 2
    w, h = ss * 0.82, ss * 0.52
    lw = max(2, ss // 11)

    if kind == "closed":
        _eye(draw, cx, cy, w, h, color, lw, closed=True)
    elif kind == "open":
        _eye(draw, cx, cy, w, h, color, lw, closed=False)
    elif kind == "tired":
        _tired(draw, cx, cy, w, h, color, lw)
    elif kind == "blink_closed":
        # Slightly angled lid to read as a blink frame.
        draw.arc((ss * 0.08, cy - ss * 0.18, ss * 0.92, cy + ss * 0.28),
                 start=30, end=150, fill=color, width=lw)
    else:
        raise ValueError(f"unknown icon kind: {kind}")

    out = img.resize((size, size), Image.LANCZOS)
    _cache[key] = out
    return out


def blink_sequence() -> tuple:
    return ("open", "blink_closed", "open", "blink_closed",
            "open", "blink_closed", "open")


def clear_cache() -> None:
    _cache.clear()
