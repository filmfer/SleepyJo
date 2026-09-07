"""Lightweight Tkinter "About me" window (Step 5).

Centered, minimal, animated GIF via Pillow's frame sequencer with after()
scheduling (never blocks the Tk main loop). GIF is fetched once and cached;
network failure degrades gracefully to text-only.
"""

from __future__ import annotations

import logging
import tempfile
import threading
import urllib.request
from pathlib import Path
from typing import Optional

GIF_URL = "https://media.giphy.com/media/o7RZbs4KAA6tvM4H6j/giphy.gif"
GIF_MAX_W = 200

log = logging.getLogger(__name__)


def _cached_gif_path() -> Optional[Path]:
    cache = Path(tempfile.gettempdir()) / "sleepyjo_about.gif"
    if cache.exists() and cache.stat().st_size > 0:
        return cache
    try:
        req = urllib.request.Request(
            GIF_URL, headers={"User-Agent": "SleepyJo/0.1"})
        with urllib.request.urlopen(req, timeout=10) as resp:  # noqa: S310
            data = resp.read(2 * 1024 * 1024)  # hard cap 2 MiB
        cache.write_bytes(data)
        return cache
    except Exception as exc:  # noqa: BLE001
        log.error("GIF download failed: %s", exc)
        return None


class AboutWindow:
    """Builds and shows the centered About dialog on the Tk main thread."""

    def __init__(self, i18n) -> None:  # noqa: ANN001 - avoids circular import
        import tkinter as tk
        from PIL import Image, ImageTk

        self._tk = tk
        self._Image = Image
        self._ImageTk = ImageTk
        self._i18n = i18n
        self._job: Optional[str] = None
        self._frames: list = []
        self._idx = 0
        self._durations: list = []

        self._root = tk.Tk()
        self._root.title(i18n.t("about_title"))
        self._root.resizable(False, False)
        self._root.attributes("-topmost", True)
        self._build_ui()
        self._center()
        self._root.protocol("WM_DELETE_WINDOW", self._root.destroy)

    def _build_ui(self) -> None:
        import webbrowser
        t = self._i18n.t
        root = self._root
        root.configure(padx=16, pady=12)

        gif_path = _cached_gif_path()
        if gif_path is not None:
            try:
                gif = self._Image.open(gif_path)
                scale = min(1.0, GIF_MAX_W / gif.width)
                target = (int(gif.width * scale), int(gif.height * scale))
                self._load_frames(gif, target)
            except Exception as exc:  # noqa: BLE001
                log.error("GIF decode failed: %s", exc)

        if self._frames:
            self._label = self._tk.Label(root, image=self._frames[0], bg="white")
            self._label.image = self._frames[0]
            self._label.pack(pady=(0, 8))
            self._animate()

        for key in ("about_author", "about_email", "about_coffee"):
            self._tk.Label(root, text=t(key), font=("TkDefaultFont", 10)).pack(pady=1)

        link = self._tk.Label(
            root, text="https://buymeacoffee.com/filmfer",
            fg="#1a73e8", cursor="hand2")
        link.pack(pady=(2, 4))
        link.bind("<Button-1>",
                  lambda _e: webbrowser.open("https://buymeacoffee.com/filmfer"))

    def _load_frames(self, gif, target) -> None:  # noqa: ANN001
        try:
            while True:
                frame = gif.convert("RGBA")
                frame.thumbnail(target, self._Image.LANCZOS)
                self._frames.append(self._ImageTk.PhotoImage(frame))
                self._durations.append(max(50, gif.info.get("duration", 80)))
                gif.seek(len(self._frames))
        except EOFError:
            pass

    def _animate(self) -> None:
        if not self._frames:
            return
        self._idx = (self._idx + 1) % len(self._frames)
        self._label.configure(image=self._frames[self._idx])
        self._label.image = self._frames[self._idx]
        self._job = self._root.after(self._durations[self._idx], self._animate)

    def _center(self) -> None:
        self._root.update_idletasks()
        w, h = self._root.winfo_width(), self._root.winfo_height()
        x = (self._root.winfo_screenwidth() - w) // 2
        y = (self._root.winfo_screenheight() - h) // 2
        self._root.geometry(f"+{x}+{y}")

    def show(self) -> None:
        self._root.mainloop()


def _main() -> int:
    """Standalone About window entry: python -m sleepyjo.about [--lang xx]"""
    import argparse

    parser = argparse.ArgumentParser(description="SleepyJo About window")
    parser.add_argument("--lang", default="")
    args = parser.parse_args()
    from .i18n import I18n

    AboutWindow(I18n(args.lang)).show()
    return 0


if __name__ == "__main__":
    raise SystemExit(_main())
