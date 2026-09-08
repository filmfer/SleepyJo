"""System tray controller (Step 4): pystray menu + icon state machine.

States: deactivated=closed eye; active(<1h)=open; active(>1h)=tired
(toothpick); pre-sleep blink animation (3 blinks) while deactivated.
Timer entries exceeding battery headroom are disabled.
"""

from __future__ import annotations

import logging
import threading
import time
from typing import Callable, Optional

import pystray

from . import battery, icons
from .i18n import I18n

log = logging.getLogger(__name__)

TIRED_THRESHOLD_SECS = 3600.0


class TrayController:
    """Owns the pystray Icon and delegates actions to callbacks."""

    def __init__(self,
                 i18n: I18n,
                 on_activate: Callable[[float], None],
                 on_deactivate: Callable[[], None],
                 on_about: Callable[[], None],
                 on_quit: Callable[[], None],
                 on_language: Callable[[str], None]) -> None:
        self._i18n = i18n
        self._on_activate = on_activate
        self._on_deactivate = on_deactivate
        self._on_about = on_about
        self._on_quit = on_quit
        self._on_language = on_language
        self._active = False
        self._active_since: Optional[float] = None
        self._dark = icons.is_dark_theme()
        self._blink_stop = threading.Event()
        self._icon = pystray.Icon(
            "SleepyJo",
            icon=icons.render("closed", dark=self._dark),
            title=i18n.t("app_name"),
            menu=self._build_menu(),
        )

    def _build_menu(self) -> pystray.Menu:
        t = self._i18n.t
        cap = battery.max_awake_hours()
        items = [
            pystray.MenuItem(
                lambda item: t("menu_activate") if not self._active
                else t("menu_deactivate"),
                self._toggle, default=True),
            pystray.Menu.SEPARATOR,
        ]
        for hours in (1, 2, 4, 8):
            items.append(pystray.MenuItem(
                t("menu_custom_hours", hours=hours),
                self._make_timer_handler(hours),
                enabled=lambda item, h=hours: (
                    not self._active and (cap is None or h <= cap)),
            ))
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem(t("menu_about"), self._about))
        items.append(pystray.Menu.SEPARATOR)
        flags = t("menu_flags")
        lang_items = [
            pystray.MenuItem(
                f"{flags.get(lang, '')} {label}",
                self._make_lang_handler(lang),
                radio=True,
                checked=lambda item, l=lang: self._i18n.lang == l)
            for lang, label in (
                ("pt", "Português"), ("en", "English"), ("fr", "Français"),
                ("it", "Italiano"), ("de", "Deutsch"), ("es", "Español"))
        ]
        items.append(pystray.MenuItem(
            t("menu_language"), pystray.Menu(*lang_items)))
        items.append(pystray.Menu.SEPARATOR)
        items.append(pystray.MenuItem(t("menu_quit"), self._quit))
        return pystray.Menu(*items)

    def _toggle(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        if self._active:
            self._on_deactivate()
        else:
            self._on_activate(1.0)  # default: 1 hour

    def _make_timer_handler(self, hours: float) -> Callable[[pystray.Icon, pystray.MenuItem], None]:
        def handler(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:
            self._on_activate(hours)
        return handler

    def _make_lang_handler(self, lang: str) -> Callable[[pystray.Icon, pystray.MenuItem], None]:
        def handler(_icon: pystray.Icon, _item: pystray.MenuItem) -> None:
            self._i18n.set_language(lang)
            self._on_language(lang)
        return handler

    def _about(self, _icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._on_about()

    def _quit(self, icon: pystray.Icon, _item: pystray.MenuItem) -> None:
        self._blink_stop.set()
        self._on_quit()
        icon.stop()


    # -- state updates ---------------------------------------------------------
    def set_active(self, active: bool) -> None:
        self._active = active
        self._active_since = time.monotonic() if active else None
        self._update_icon()

    def refresh_theme(self) -> None:
        self._dark = icons.is_dark_theme()
        self._update_icon()

    def _update_icon(self) -> None:
        try:
            self._icon.icon = icons.render(self._current_kind(), dark=self._dark)
        except Exception as exc:  # noqa: BLE001
            log.error("icon update failed: %s", exc)

    def _current_kind(self) -> str:
        if not self._active:
            return "closed"
        elapsed = time.monotonic() - (self._active_since or time.monotonic())
        return "tired" if elapsed > TIRED_THRESHOLD_SECS else "open"

    def run_blink(self, interval: float = 0.35, cycles: int = 3) -> None:
        """Blink the icon 3x (pre-sleep animation) on a worker thread."""
        self._blink_stop.set()
        self._blink_stop = threading.Event()

        def animate() -> None:
            try:
                stop = self._blink_stop
                for _ in range(cycles):
                    for frame in ("blink_closed", "open"):
                        if stop.is_set():
                            return
                        self._icon.icon = icons.render(frame, dark=self._dark)
                        stop.wait(interval)
                self._update_icon()
            except Exception as exc:  # noqa: BLE001
                log.error("blink animation failed: %s", exc)

        threading.Thread(target=animate, daemon=True,
                         name="sleepyjo-blink").start()

    def notify_tray(self, message: str) -> None:
        self._icon.notify(message, self._i18n.t("app_name"))

    def run(self) -> None:
        self._icon.run()
