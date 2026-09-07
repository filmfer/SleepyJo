"""Lightweight Tkinter "About me" window (Step 5).

Bulletproof rendering: the ENTIRE visual (BMC logo + text) is composited
into a single PIL image and displayed as one PhotoImage. macOS Aqua ignores
tk.Label/tk.Canvas text colors and font styling in some themes, which made
window content invisible — PIL-rendered pixels cannot be ignored. The only
Tk text-free interactive element is an invisible clickable region over the
URL. Logo is embedded as base64 (zero network at runtime).
"""

from __future__ import annotations

import base64
import io
import logging
import os
import webbrowser

from PIL import Image, ImageDraw, ImageFont

from .icons import is_dark_theme

log = logging.getLogger(__name__)

BMC_URL = "https://buymeacoffee.com/filmfer"
# Injected by tools/embed_logo.py (PNG, 545x153).
BMC_LOGO_B64 = "iVBORw0KGgoAAAANSUhEUgAAAiEAAACZCAMAAADOzxqEAAAAGXRFWHRTb2Z0d2FyZQBBZG9iZSBJbWFnZVJlYWR5ccllPAAAAIRQTFRFw6kJSkAahnUS8NACHBkhpI8N4cME/+ZAhnUROjMcKyYfaFoW0rYHlYIPs5wLWU0Yd2cUHBkg//e/aFoVd2cTKyYe0rYG/98Q/+6AWU0X//vf//3v/+Eg//CP/+Mw//Sv/+pg//nP/+xw//Kf/+hQ/+5///a/DQwiDQwj/////90A////A0MgiAAAACx0Uk5T/////////////////////////////////////////////////////////wDH1gmMAAARpUlEQVR42uydaWPiOAyGfcQpuUMp04N2em8z8P//3xJiJ5btHJA2pY30ZbctE4z8RJZeK4bsTLt7ePq7RZuhXV+8PG4sHgj8cfNwj56atb29dhFy94QeQrt/bSXk/Rrdg1Yy8p+TkGfMPtCUvWxsQh4xgKA19vfOJOQVnYIGCptnSAgCgtaCSEXIIzoEzcpXNw0hz5iDoDlykYYQrGLQXPauCHlHX6A57bki5A7XGDS3XVSEoNSO1mb/lYRs0A9oHUGE7B7QD2itdrcnBLf70drtZUfu0Ato7fZ3R3CRQetcZghWMmhd9khQT0XrsneCPkDrsickBK3TLpAQNCQEDQlBQ0LQfjohnJB0oZsg5A/6FwnZbv10cUuXHy1Gbxepj26eLyHpav3Rb+uV4OjqGRLCF8uPobZcISOzI+TPcD4OjKTo7XkR4h8HyN6wbJoXISsw+wFdLRYJaUzsyxkKM9g1untWhNB6+ViQjhyDJKtAvRKr33kS8kEXoo0RkiZ/ypS2emGC/p4TIQszE6W0XGmkXe1/koXwVb0krdDfcyKEB0MzVH9f91TBBv09q2qX3x5Rw1T/h/6eFSH7LGO1HBhDZNaC+vvMCNlbekX7ACnzkO0VKiIzJaS0P+liRV2glKlrWpW46eEXC3T4LAmpzdcUM0P78LGYQUK67ZCxLHH7bjaE/FksFuSYxLNahW4xV50HIWTdNAiJ/lYyn4grVfWsMReZASHCykkDSq+qzkO4d7egdgob4FLz2wk5ft/fUf6i/WJCVh8jDZORX07IWEAwiPxyQki1lStIchUcw8U+U0mqpCRAv/9qQpLDLMuu030+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"

WIN_W, WIN_H = 360, 340
LOGO_TARGET_W = 210


def _palette(dark: bool):  # type: ignore[no-untyped-def]
    """Theme-aware palette: white text on dark window, black on light."""
    if dark:
        return (30, 30, 30, 255), (240, 240, 240, 255), (100, 181, 246, 255)
    return (255, 255, 255, 255), (26, 26, 26, 255), (26, 115, 232, 255)

LOGO_TARGET_W = 210


def _font(size: int):  # type: ignore[no-untyped-def]
    """Load a real TrueType font; degrade to PIL's scalable default."""
    candidates = [
        "/System/Library/Fonts/Helvetica.ttc",           # macOS
        "C:/Windows/Fonts/arial.ttf",                    # Windows
        "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
    ]
    for path in candidates:
        try:
            return ImageFont.truetype(path, size)
        except OSError:
            continue
    return ImageFont.load_default(size=size)


class AboutWindow:
    """Builds and shows the centered About dialog on the Tk main thread."""

    def __init__(self, i18n) -> None:  # noqa: ANN001 - avoids circular import
        import os
        import tempfile
        import tkinter as tk

        self._tk = tk
        self._i18n = i18n

        self._root = tk.Tk()
        self._root.title(i18n.t("about_title"))
        self._root.resizable(False, False)
        self._root.attributes("-topmost", True)

        composite, url_box = self._render_composite()

        # System Python on macOS ships Tcl/Tk 8.5 where Pillow's ImageTk
        # renders unreliably (window shows empty). Tk's NATIVE PhotoImage
        # reads PPM in every version — bypass Pillow for display entirely.
        self._ppm_path = os.path.join(tempfile.gettempdir(), "sleepyjo_about.ppm")
        composite.save(self._ppm_path)
        self._photo = tk.PhotoImage(file=self._ppm_path)
        log.info("PhotoImage loaded native: %dx%d",
                 self._photo.width(), self._photo.height())

        self._canvas = tk.Canvas(self._root, width=WIN_W, height=WIN_H,
                                 highlightthickness=0, bd=0)
        self._canvas.pack(fill="both", expand=True)
        self._canvas.create_image(0, 0, image=self._photo, anchor="nw")

        # Invisible clickable region over the URL inside the composite image.
        tag = "link"
        self._canvas.create_rectangle(url_box, outline="", fill="",
                                      tags=(tag,))
        self._canvas.tag_bind(tag, "<Button-1>",
                              lambda _e: webbrowser.open(BMC_URL))
        self._canvas.tag_bind(tag, "<Enter>",
                              lambda _e: self._canvas.config(cursor="hand2"))
        self._canvas.tag_bind(tag, "<Leave>",
                              lambda _e: self._canvas.config(cursor=""))

        self._center()
        self._root.protocol("WM_DELETE_WINDOW", self._root.destroy)

    # -- composite rendering (all pixels drawn by PIL) -------------------------
    def _render_composite(self):  # type: ignore[no-untyped-def]
        t = self._i18n.t
        dark = is_dark_theme()
        bg, fg, link = _palette(dark)
        log.info("About window: dark=%s", dark)
        img = Image.new("RGBA", (WIN_W, WIN_H), bg)
        draw = ImageDraw.Draw(img)
        cx = WIN_W // 2

        y = 20
        try:
            logo = Image.open(io.BytesIO(base64.b64decode(BMC_LOGO_B64)))
            scale = min(1.0, LOGO_TARGET_W / logo.width)
            logo = logo.convert("RGBA").resize(
                (int(logo.width * scale), int(logo.height * scale)),
                Image.LANCZOS)
            img.paste(logo, (cx - logo.width // 2, y), logo)
            y += logo.height + 20
        except Exception as exc:  # noqa: BLE001
            log.error("BMC logo decode failed: %s", exc)

        f_body = _font(13)
        f_url = _font(13)
        url_box = (0, 0, 0, 0)
        lines = [t("about_author"), t("about_email"), t("about_coffee")]
        for line in lines:
            w = draw.textlength(line, font=f_body)
            draw.text((cx - w / 2, y), line, font=f_body, fill=fg)
            y += 28

        uw = draw.textlength(BMC_URL, font=f_url)
        ux, uy = cx - uw / 2, y + 6
        draw.text((ux, uy), BMC_URL, font=f_url, fill=link)
        draw.line((ux, uy + 17, ux + uw, uy + 17), fill=link, width=1)
        url_box = (ux - 4, uy - 2, ux + uw + 4, uy + 22)
        log.info("About composite rendered: lines=%d url_box=%s",
                 len(lines), url_box)
        return img.convert("RGB"), url_box

    def _center(self) -> None:
        self._root.update_idletasks()
        x = (self._root.winfo_screenwidth() - WIN_W) // 2
        y = (self._root.winfo_screenheight() - WIN_H) // 2
        self._root.geometry(f"{WIN_W}x{WIN_H}+{x}+{y}")

    def show(self) -> None:
        self._root.mainloop()


def _main() -> int:
    """Standalone About window entry: python -m sleepyjo.about [--lang xx]"""
    import argparse
    import tempfile

    logging.basicConfig(
        level=logging.INFO,
        filename=os.path.join(tempfile.gettempdir(), "sleepyjo_about.log"),
        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    parser = argparse.ArgumentParser(description="SleepyJo About window")
    parser.add_argument("--lang", default="")
    args = parser.parse_args()
    from .i18n import I18n

    log.info("About subprocess starting (lang=%s)", args.lang)
    AboutWindow(I18n(args.lang)).show()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
