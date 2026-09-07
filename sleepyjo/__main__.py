from .app import main
import sys


def _run() -> int:
    # Frozen (PyInstaller) About window: the packaged exe re-invokes itself
    # with --about, giving Tk its own process/main thread (macOS-safe).
    if "--about" in sys.argv:
        import argparse
        from .about import AboutWindow
        from .i18n import I18n

        parser = argparse.ArgumentParser()
        parser.add_argument("--lang", default="")
        args, _ = parser.parse_known_args()
        AboutWindow(I18n(args.lang)).show()
        return 0
    return main()


if __name__ == "__main__":
    raise SystemExit(_run())
