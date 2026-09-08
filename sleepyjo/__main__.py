import sys


def _run() -> int:
    from sleepyjo.app import main
    return main()


if __name__ == "__main__":
    raise SystemExit(_run())
