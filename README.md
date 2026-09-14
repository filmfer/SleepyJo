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

The DMG is ad-hoc signed but not notarized (requires a paid Apple
Developer account). If macOS reports the app as broken/damaged:

```bash
sudo xattr -rd com.apple.quarantine /Applications/SleepyJo.app
```
