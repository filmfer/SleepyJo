# SleepyJo

Lightweight cross-platform system tray wake-lock utility (Caffeine-like).

- **Wake-lock:** macOS (IOPMAssertion / `caffeinate`), Windows (`SetThreadExecutionState`), Linux (D-Bus ScreenSaver inhibit + activity heartbeat). Works on Intel, AMD, Apple Silicon (M Series) and ARM.
- **Tray icons:** SVG-based moon icon rendered dynamically for the OS tray, optimized for macOS/Linux (white/black) and Windows (colored).
- **Battery-aware:** durations capped by remaining battery, 10% toast warning, auto-disable at 5%.
- **Timers:** 1 h default; 1/2/4/8 h presets limited by battery headroom.
- **i18n:** Portuguese (default), English, French, Italian, German, Spanish.
- **About me:** embedded modern HTML page opened in the native browser.

## Run

```bash
python3 -m venv .venv
. .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
python -m sleepyjo
```

## Build

Tag a release (`git tag v0.1.0 && git push --tags`) — the GitHub Actions
workflow builds standalone executables for macOS (Intel + M Series), Linux
(Debian/Ubuntu/Fedora compatible binaries, x86_64 + ARM64), and Windows
(x64 + ARM64) and publishes them to a GitHub Release.

## Author

J. Filipe Fernandes — filmfer@gmail.com — <https://buymeacoffee.com/filmfer>

## macOS first launch (unsigned build)

The DMG is ad-hoc signed but **not notarized** (notarization requires a
paid Apple Developer account). When you open the app for the first time,
macOS Gatekeeper will warn that it "cannot verify the app" because it
was downloaded from the internet. This is expected — the app is safe,
it just isn't signed with a paid Apple certificate.

**Option 1 — Right-click open (simplest, try this first):**

1. Open the DMG and drag SleepyJo to Applications.
2. In Finder, **right-click (or Control-click) SleepyJo.app → Open**.
3. Click **Open** again in the confirmation dialog.
4. The app launches and macOS will remember your choice — no warning
   on future launches.

> Note: on macOS Sequoia (15) and later, the dialog has no "Open"
> button — use Option 2 instead.

**Option 2 — System Settings override (macOS Sequoia+):**

1. Try to launch the app once (it will be blocked).
2. Go to **System Settings → Privacy & Security**.
3. Scroll to the Security section and click **Open Anyway** next to
   the SleepyJo message, then confirm with **Open**.

**Option 3 — Terminal (removes the quarantine flag entirely):**

```bash
sudo xattr -rd com.apple.quarantine /Applications/SleepyJo.app
```

This clears the download quarantine attribute, after which the app
opens normally without any prompt.
