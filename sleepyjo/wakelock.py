"""OS wake-lock abstraction.

Platform dispatch (resolved at create()):
- macOS: IOPMAssertion via ctypes on IOKit (Intel & Apple Silicon),
  with a `caffeinate` subprocess fallback.
- Windows: SetThreadExecutionState via ctypes (x64 & ARM64).
- Linux: D-Bus ScreenSaver.Inhibit + SimulateUserActivity heartbeat
  (Wayland/X11 safe, unprivileged).

All subprocess resources are released via context managers.
"""

from __future__ import annotations

import ctypes
import logging
import platform
import shutil
import subprocess
import threading
from typing import Optional, Protocol

log = logging.getLogger(__name__)

_OS = platform.system()


class WakeLock(Protocol):
    def acquire(self) -> None: ...
    def release(self) -> None: ...


class _BaseWakeLock:
    def __enter__(self) -> "_BaseWakeLock":
        self.acquire()
        return self

    def __exit__(self, *_exc: object) -> None:
        self.release()


# --- macOS -----------------------------------------------------------------
class MacOSWakeLock(_BaseWakeLock):
    _AVOID_SLEEP = b"PreventUserIdleSystemSleep"
    _NO_DISPLAY_SLEEP = b"NoDisplaySleepAssertion"
    _CF_STRING_ENCODING = 0x08000100

    def __init__(self) -> None:
        self._iokit = ctypes.CDLL("/System/Library/Frameworks/IOKit.framework/IOKit")
        self._cf = ctypes.CDLL(
            "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"
        )
        self._cf.CFStringCreateWithCString.restype = ctypes.c_void_p
        self._cf.CFStringCreateWithCString.argtypes = [
            ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32,
        ]
        self._cf.CFRelease.argtypes = [ctypes.c_void_p]
        self._iokit.IOPMAssertionCreateWithName.restype = ctypes.c_int
        self._iokit.IOPMAssertionCreateWithName.argtypes = [
            ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p,
            ctypes.POINTER(ctypes.c_uint32),
        ]
        self._iokit.IOPMAssertionRelease.restype = ctypes.c_int
        self._iokit.IOPMAssertionRelease.argtypes = [ctypes.c_uint32]
        self._assertions: list[int] = []
        self._delegate: Optional[CaffeinateWakeLock] = None

    def _create_assertion(self, atype: bytes) -> Optional[int]:
        cf_type = self._cf.CFStringCreateWithCString(
            None, atype, self._CF_STRING_ENCODING)
        cf_reason = self._cf.CFStringCreateWithCString(
            None, b"SleepyJo is keeping this Mac awake", self._CF_STRING_ENCODING)
        if not cf_type or not cf_reason:
            return None
        aid = ctypes.c_uint32(0)
        rc = self._iokit.IOPMAssertionCreateWithName(
            cf_type, 255, cf_reason, ctypes.byref(aid))
        self._cf.CFRelease(cf_type)
        self._cf.CFRelease(cf_reason)
        if rc != 0:
            log.error("IOPMAssertionCreateWithName(%s) failed rc=%d", atype, rc)
            return None
        return int(aid.value)

    def acquire(self) -> None:
        if self._assertions or self._delegate is not None:
            return
        aids: list[int] = []
        for atype in (self._AVOID_SLEEP, self._NO_DISPLAY_SLEEP):
            aid = self._create_assertion(atype)
            if aid is None:
                log.warning("IOPMAssertion unavailable; falling back to caffeinate")
                self._release_assertions(aids)
                caffeinate = CaffeinateWakeLock()
                caffeinate.acquire()
                if caffeinate._proc is None:
                    log.error("caffeinate fallback also unavailable")
                    return
                self._delegate = caffeinate
                return
            aids.append(aid)
        self._assertions = aids

    def _release_assertions(self, aids: list[int]) -> None:
        for aid in aids:
            self._iokit.IOPMAssertionRelease(aid)

    def release(self) -> None:
        if self._delegate is not None:
            self._delegate.release()
            self._delegate = None
        self._release_assertions(self._assertions)
        self._assertions = []


class CaffeinateWakeLock(_BaseWakeLock):
    """Fallback: `caffeinate -d -i -s` subprocess (macOS)."""

    def __init__(self) -> None:
        self._proc: Optional[subprocess.Popen] = None

    def acquire(self) -> None:
        if self._proc is None and shutil.which("caffeinate"):
            self._proc = subprocess.Popen(
                ["caffeinate", "-d", "-i", "-s"],
                stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
            )

    def release(self) -> None:
        if self._proc is not None:
            self._proc.terminate()
            try:
                self._proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                self._proc.kill()
            self._proc = None


# --- Windows ---------------------------------------------------------------
class WindowsWakeLock(_BaseWakeLock):
    ES_CONTINUOUS = 0x80000000
    ES_SYSTEM_REQUIRED = 0x00000001
    ES_DISPLAY_REQUIRED = 0x00000002

    def __init__(self) -> None:
        self._acquired = False

    def acquire(self) -> None:
        if self._acquired:
            return
        flags = self.ES_CONTINUOUS | self.ES_SYSTEM_REQUIRED | self.ES_DISPLAY_REQUIRED
        if ctypes.windll.kernel32.SetThreadExecutionState(ctypes.c_uint(flags)) == 0:
            log.error("SetThreadExecutionState failed")
            return
        self._acquired = True

    def release(self) -> None:
        if not self._acquired:
            return
        ctypes.windll.kernel32.SetThreadExecutionState(
            ctypes.c_uint(self.ES_CONTINUOUS))
        self._acquired = False


# --- Linux -----------------------------------------------------------------
class LinuxWakeLock(_BaseWakeLock):
    """D-Bus ScreenSaver inhibit + 60s SimulateUserActivity heartbeat."""

    _HEARTBEAT_SECS = 60.0

    def __init__(self) -> None:
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._bus = None
        self._cookie: Optional[int] = None

    def _get_bus(self):  # type: ignore[no-untyped-def]
        if self._bus is not None:
            return self._bus
        try:
            import gi  # type: ignore[import-not-found]
            gi.require_version("Gio", "2.0")
            from gi.repository import Gio  # type: ignore[import-not-found]
            self._bus = Gio.bus_get_sync(Gio.BusType.SESSION, None)
        except Exception as exc:  # noqa: BLE001
            log.error("D-Bus session unavailable: %s", exc)
            return None
        return self._bus

    def _call(self, service: str, path: str, iface: str, method: str,
              params: object = None, reply_type: object = None):  # type: ignore[no-untyped-def]
        from gi.repository import Gio  # type: ignore[import-not-found]
        bus = self._get_bus()
        if bus is None:
            return None
        try:
            return bus.call_sync(
                service, path, iface, method,
                params, reply_type, Gio.DBusCallFlags.NONE, -1, None,
            )
        except Exception as exc:  # noqa: BLE001
            log.debug("D-Bus %s.%s failed: %s", iface, method, exc)
            return None

    def _inhibit(self) -> Optional[int]:
        from gi.repository import GLib  # type: ignore[import-not-found]
        params = GLib.Variant("(ss)", ("SleepyJo", "Keeping system awake"))
        u_type = GLib.VariantType("(u)")
        for service, path, iface in (
            ("org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver",
             "org.freedesktop.ScreenSaver"),
            ("org.freedesktop.PowerManagement",
             "/org/freedesktop/PowerManagement/Inhibit",
             "org.freedesktop.PowerManagement.Inhibit"),
        ):
            result = self._call(service, path, iface, "Inhibit", params, u_type)
            if result is not None:
                return int(result.unpack()[0])
        return None

    def acquire(self) -> None:
        if self._thread is not None:
            return
        self._cookie = self._inhibit()
        self._stop.clear()
        self._thread = threading.Thread(
            target=self._heartbeat, daemon=True, name="sleepyjo-heartbeat")
        self._thread.start()

    def _heartbeat(self) -> None:
        while not self._stop.wait(self._HEARTBEAT_SECS):
            self._call("org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver",
                       "org.freedesktop.ScreenSaver", "SimulateUserActivity")

    def release(self) -> None:
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=5)
            self._thread = None
        if self._cookie is not None:
            from gi.repository import GLib  # type: ignore[import-not-found]
            self._call("org.freedesktop.ScreenSaver", "/org/freedesktop/ScreenSaver",
                       "org.freedesktop.ScreenSaver", "UnInhibit",
                       GLib.Variant("(u)", (self._cookie,)))
            self._cookie = None


# --- Dispatch ---------------------------------------------------------------
def create() -> WakeLock:
    if _OS == "Darwin":
        return MacOSWakeLock()
    if _OS == "Windows":
        return WindowsWakeLock()
    if _OS == "Linux":
        return LinuxWakeLock()
    raise NotImplementedError(f"Unsupported platform: {_OS}")

