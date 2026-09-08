"""SleepyJo application orchestrator: wires tray, wake-lock, and monitor."""

from __future__ import annotations

import logging
import threading

from . import battery, wakelock
from .i18n import I18n
from .tray import TrayController

log = logging.getLogger(__name__)


class SleepyJoApp:
    def __init__(self) -> None:
        self._i18n = I18n()
        self._lock = wakelock.create()
        self._active = threading.Event()

        self._monitor = battery.BatteryMonitor(
            on_expire=self.deactivate,
            on_battery_10=self._warn_10,
            on_battery_5=self._critical_5,
            on_presleep=self._presleep_blink,
            is_active=self._active.is_set,
        )
        self._monitor.start()

        self._tray = TrayController(
            i18n=self._i18n,
            on_activate=self.activate,
            on_deactivate=self.deactivate,
            on_about=self.show_about,
            on_quit=self._quit,
            on_language=lambda _lang: None,
        )

    # -- activation -----------------------------------------------------------
    def activate(self, hours: float) -> None:
        cap = battery.max_awake_hours()
        if cap is not None and hours > cap:
            log.warning("Requested %.1fh exceeds battery headroom (%.1fh); clamping",
                        hours, cap)
            hours = cap
        self._lock.acquire()
        self._active.set()
        self._monitor.start_timer(hours)
        self._tray.set_active(True)
        battery.notify(self._i18n.t("app_name"),
                       self._i18n.t("notif_activated", hours=g(hours)))

    def deactivate(self) -> None:
        if not self._active.is_set():
            return
        self._active.clear()
        self._monitor.cancel_timer()
        self._lock.release()
        self._tray.set_active(False)
        battery.notify(self._i18n.t("app_name"), self._i18n.t("notif_deactivated"))

    # -- battery callbacks ------------------------------------------------------
    def _warn_10(self) -> None:
        battery.notify(self._i18n.t("app_name"), self._i18n.t("notif_battery_10"))

    def _critical_5(self) -> None:
        self.deactivate()
        battery.notify(self._i18n.t("app_name"), self._i18n.t("notif_battery_5"))

    def _presleep_blink(self) -> None:
        self._tray.run_blink()

    # -- about ------------------------------------------------------------------
    def show_about(self) -> None:
        """Open the About page (HTML) in the native browser.

        No GUI toolkit: the page is styled for macOS/Windows/Linux themes
        via prefers-color-scheme and opened with the platform browser.
        """
        from .about import open_about
        open_about(self._i18n)


    # -- lifecycle ---------------------------------------------------------------
    def _quit(self) -> None:
        self._active.clear()
        self._monitor.stop()
        self._lock.release()

    def run(self) -> None:
        self._tray.run()


def g(hours: float) -> int:
    return max(1, round(hours))


def main() -> int:
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s %(name)s %(levelname)s %(message)s")
    app = SleepyJoApp()
    app.run()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
