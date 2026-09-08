#!/usr/bin/env python3
"""Generate app icons (icns/ico/png) from the SleepyJo icon factory."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from PIL import Image, ImageDraw  # noqa: E402

from sleepyjo.icons import SS, _eye  # noqa: E402


def app_icon(size: int = 256) -> Image.Image:
    """macOS-style app icon: dark rounded square + white open eye."""
    ss = size * 2
    img = Image.new("RGBA", (ss, ss), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    d.rounded_rectangle(
        (size // 16, size // 16, ss - size // 16, ss - size // 16),
        radius=size * 22 // 100, fill=(29, 29, 31, 255))
    lw = max(2, ss // 16)
    _eye(d, ss / 2, ss / 2 + size * 0.02, ss * 0.46, ss * 0.29,
         (255, 255, 255, 255), lw, closed=False)
    return img.resize((size, size), Image.LANCZOS)


def main() -> None:
    dist = Path(sys.argv[1]) if len(sys.argv) > 1 else Path("dist")
    dist.mkdir(exist_ok=True)
    icon = app_icon(256)
    icon.save(dist / "icon.png")
    icon.save(dist / "icon.ico", sizes=[(16, 16), (24, 24), (32, 32),
                                        (48, 48), (64, 64), (128, 128),
                                        (256, 256)])
    icon.save(dist / "icon.icns")
    print(f"Icons written to {dist}/ (png, ico, icns)")


if __name__ == "__main__":
    main()
