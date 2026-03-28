from __future__ import annotations

import sys


def _ensure_pyobjc() -> None:
    try:
        import AppKit  # noqa: F401
        import AVFoundation  # noqa: F401
        import Quartz  # noqa: F401
        import objc  # noqa: F401
    except ModuleNotFoundError as exc:
        missing = exc.name or "pyobjc"
        raise SystemExit(
            f"Missing dependency: {missing}. Install project dependencies first with `pip install -e .`."
        ) from exc


def main() -> None:
    _ensure_pyobjc()
    import AppKit

    from .app import QuitTokApp

    app = AppKit.NSApplication.sharedApplication()
    delegate = QuitTokApp.alloc().init()
    app.setDelegate_(delegate)
    app.run()


if __name__ == "__main__":
    main()
