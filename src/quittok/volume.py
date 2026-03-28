from __future__ import annotations

import subprocess


class VolumeController:
    def __init__(self) -> None:
        self._saved_volume: int | None = None

    def _run_osascript(self, script: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            ["osascript", "-e", script],
            check=False,
            text=True,
            capture_output=True,
        )

    def current_volume(self) -> int | None:
        result = self._run_osascript("output volume of (get volume settings)")
        if result.returncode != 0:
            return None
        try:
            return int(result.stdout.strip())
        except ValueError:
            return None

    def max_out(self) -> None:
        if self._saved_volume is None:
            self._saved_volume = self.current_volume()
        self._run_osascript("set volume output volume 100")

    def restore(self) -> None:
        if self._saved_volume is None:
            return
        self._run_osascript(f"set volume output volume {self._saved_volume}")
        self._saved_volume = None

