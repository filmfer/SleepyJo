#!/usr/bin/env python3
"""Generate app icons (icns/ico/png) from the SleepyJo icon factory.

Split-eye design: left half = open eye, right half = closed eye.
Renders at 2x supersampling for smooth downscale.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw  # noqa: E402

from sleepyjo.icons import _eye  # noqa: E402


def split_eye_icon(size: int = 256) -> Image.Image:
    """App icon: dark rounded square, left=open eye, right=closed eye."""
    ss = size * 2  # 2x supersampling
    img = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)

    # Dark rounded-rectangle background (macOS app icon style).
    pad = size // 12
    d.rounded_rectangle(
        (pad, pad, ss - pad, ss - pad),
        radius=size * 22 // 100, fill=(29, 29, 31, 255))

    lw = max(3, ss // 18)
    eye_w, eye_h = ss * 0.34, ss * 0.42
    cy = ss * 0.52

    # --- Left half: open eye (pupil + upper lashes) ---
    open_layer = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    open_draw = ImageDraw.Draw(open_layer)
    _eye(open_draw, ss * 0.27, cy, eye_w, eye_h,
         (255, 255, 255, 255), lw, closed=False)
    # Clip to left half (with a small overlap at the center).
    mask = Image.new("L", (ss, ss), 0)
    ImageDraw.Draw(mask).rectangle((0, 0, ss * 0.52, ss), fill=255)
    img.paste(open_layer, (0, 0), mask)

    # --- Right half: closed eye (lower lashes) ---
    closed_layer = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    closed_draw = ImageDraw.Draw(closed_layer)
    _eye(closed_draw, ss * 0.73, cy, eye_w, eye_h,
         (255, 255, 255, 255), lw, closed=True)
    # Clip to right half.
    mask = Image.new("L", (ss, ss), 0)
    ImageDraw.Draw(mask).rectangle((ss * 0.48, 0, ss, ss), fill=255)
    img.paste(closed_layer, (0, 0), mask)

    # Subtle vertical divider.
    div_x = ss // 2
    d.line((div_x, ss * 0.22, div_x, ss * 0.78),
           fill=(255, 255, 255, 25), width=1)

    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    dist = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist")
    dist.mkdir(exist_ok=True)
    icon = split_eye_icon(256)
    icon.save(dist / "icon.png")
    icon.save(dist / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32),
                                        (48, 48), (64, 64), (128, 128),
                                        (256, 256)])
    icon.save(dist / "icon.icns")
    print(f"Icons written to {dist}/ (png, ico, icns)")


if __name__ == "__main__":
    main()
