"""Battery-aware timer monitor (Step 3).

Single daemon thread using Event.wait() — no busy polling.
- Countdown of the active wake period.
- Battery capacity cap for selectable durations.
- One-shot 10% toast warning; auto-disable at 5%.
- Pre-sleep blink trigger (T-minus <= 60s while deactivated).
"""

from __future__ import annotations

import logging
import platform
import re
import shutil
import subprocess
import threading
import time
from typing import Callable, Dict, Optional

import psutil

log = logging.getLogger(__name__)

POLL_INTERVAL = 15.0


def battery_percent() -> Optional[float]:
    try:
        bat = psutil.sensors_battery()
        return float(bat.percent) if bat else None
    except Exception as exc:  # noqa: BLE001
        log.debug("battery query failed: %s", exc)
        return None


def battery_secsleft() -> Optional[int]:
    try:
        bat = psutil.sensors_battery()
        if bat and bat.secsleft and bat.secsleft != psutil.POWER_TIME_UNLIMITED:
            return int(bat.secsleft)
    except Exception as exc:  # noqa: BLE001
        log.debug("battery secsleft query failed: %s", exc)
    return None


def max_awake_hours() -> Optional[float]:
    """Highest selectable duration allowed, conservatively derated to 80%."""
    secs = battery_secsleft()
    if secs is None:
        return None  # desktop / unknown -> no cap
    return max(0.25, round(secs * 0.8 / 3600.0, 2))


def notify(title: str, message: str) -> None:
    """Fire an OS-native toast (best-effort, non-blocking, never raises)."""
    try:
        system = platform.system()
        if system == "Darwin":
            script = 'display notification "%s" with title "%s"' % (message, title)
            subprocess.Popen(["osascript", "-e", script],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif system == "Linux" and shutil.which("notify-send"):
            subprocess.Popen(["notify-send", title, message],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        elif system == "Windows":
            _windows_toast(title, message)
    except Exception as exc:  # noqa: BLE001
        log.error("notification failed: %s", exc)


def _windows_toast(title: str, message: str) -> None:
    """PowerShell toast via Windows Runtime; falls back to MessageBoxW."""
    ps_script = (
        "[Windows.UI.Notifications.ToastNotificationManager, "
        "Windows.UI.Notifications, ContentType=WindowsRuntime] > $null; "
        "$t=[Windows.UI.Notifications.ToastNotificationManager]::GetTemplateContent("
        "[Windows.UI.Notifications.ToastTemplateType]::ToastText02);"
        "$els=$t.GetElementsByTagName('text');"
        "$els.Item(0).AppendChild($t.CreateTextNode('" + title + "'))> $null;"
        "$els.Item(1).AppendChild($t.CreateTextNode('" + message + "'))> $null;"
        "$n=[Windows.UI.Notifications.ToastNotification]::new($t);"
        "[Windows.UI.Notifications.ToastNotificationManager]::CreateToastNotifier("
        "'SleepyJo').Show($n)"
    )
    try:
        subprocess.Popen(
            ["powershell", "-NoProfile", "-NonInteractive", "-Command", ps_script],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except OSError as exc:
        log.error("PowerShell toast failed: %s", exc)
        import ctypes
        ctypes.windll.user32.MessageBoxW(0, message, title, 0x40)


class BatteryMonitor(threading.Thread):
    """Countdown + battery-threshold watcher (daemon)."""

    def __init__(self,
                 on_expire: Callable[[], None],
                 on_battery_10: Callable[[], None],
                 on_battery_5: Callable[[], None],
                 on_presleep: Callable[[], None],
                 is_active: Callable[[], bool]) -> None:
        super().__init__(daemon=True, name="sleepyjo-monitor")
        self._on_expire = on_expire
        self._on_battery_10 = on_battery_10
        self._on_battery_5 = on_battery_5
        self._on_presleep = on_presleep
        self._is_active = is_active
        self._stop = threading.Event()
        self._deadline: Optional[float] = None
        self._fired: Dict[str, bool] = {}

    def start_timer(self, hours: float) -> None:
        self._deadline = time.monotonic() + hours * 3600.0
        self._fired = {}

    def cancel_timer(self) -> None:
        self._deadline = None

    def remaining_secs(self) -> Optional[float]:
        if self._deadline is None:
            return None
        return max(0.0, self._deadline - time.monotonic())

    def stop(self) -> None:
        self._stop.set()

    def run(self) -> None:
        while not self._stop.wait(POLL_INTERVAL):
            try:
                self._tick()
            except Exception as exc:  # noqa: BLE001
                log.exception("monitor tick failed: %s", exc)

    def _tick(self) -> None:
        rem = self.remaining_secs()
        if rem is not None and rem <= 0:
            self._deadline = None
            log.info("timer expired; deactivating")
            self._on_expire()

        pct = battery_percent()
        if pct is not None:
            if pct <= 10.0 and not self._fired.get("warn10"):
                self._fired["warn10"] = True
                self._on_battery_10()
            if pct <= 5.0 and not self._fired.get("warn5"):
                self._fired["warn5"] = True
                self._on_battery_5()
            if pct > 10.0:
                self._fired["warn10"] = False
            if pct > 5.0:
                self._fired["warn5"] = False

        # Pre-sleep blink: only while deactivated, and only when the OS
        # exposes its scheduled display-sleep time.
        if not self._is_active():
            secs = self._seconds_until_os_sleep()
            if secs is not None and secs <= 60.0:
                self._on_presleep()

    @staticmethod
    def _seconds_until_os_sleep() -> Optional[float]:
        """Best-effort scheduled display-sleep query; None if unsupported."""
        if platform.system() != "Darwin":
            return None
        try:
            out = subprocess.run(
                ["pmset", "-g", "custom"], capture_output=True, text=True,
                timeout=3, check=True).stdout
            match = re.search(r"^ *displaysleep\s+(\d+)", out, re.MULTILINE)
            if not match:
                return None
            minutes = int(match.group(1))
            return None if minutes == 0 else minutes * 60.0
        except Exception as exc:  # noqa: BLE001
            log.debug("pmset query failed: %s", exc)
            return None

