import sys


def _run() -> int:
    # Frozen (PyInstaller) About window: the packaged exe re-invokes itself
    # with --about, giving Tk its own process/main thread (macOS-safe).
    # NOTE: absolute imports — PyInstaller executes this file as __main__
    # with no package context, so relative imports fail in the frozen app.
    if "--about" in sys.argv:
        import argparse
        from sleepyjo.about import AboutWindow
        from sleepyjo.i18n import I18n

        parser = argparse.ArgumentParser()
        parser.add_argument("--lang", default="")
        args, _ = parser.parse_known_args()
        AboutWindow(I18n(args.lang)).show()
        return 0
    from sleepyjo.app import main
    return main()


if __name__ == "__main__":
    raise SystemExit(_run())
