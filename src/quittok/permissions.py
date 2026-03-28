from __future__ import annotations

import subprocess
from typing import Any


def _application_services():
    import ApplicationServices

    return ApplicationServices


def accessibility_trusted(prompt: bool = False) -> bool:
    services = _application_services()
    if hasattr(services, "AXIsProcessTrustedWithOptions"):
        options: dict[str, Any] = {}
        if hasattr(services, "kAXTrustedCheckOptionPrompt"):
            options[services.kAXTrustedCheckOptionPrompt] = bool(prompt)
        return bool(services.AXIsProcessTrustedWithOptions(options))
    if hasattr(services, "AXIsProcessTrusted"):
        return bool(services.AXIsProcessTrusted())
    return False


def open_accessibility_settings() -> None:
    subprocess.run(
        [
            "open",
            "x-apple.systempreferences:com.apple.preference.security?Privacy_Accessibility",
        ],
        check=False,
    )


def request_accessibility() -> bool:
    trusted = accessibility_trusted(prompt=True)
    if not trusted:
        open_accessibility_settings()
    return trusted
