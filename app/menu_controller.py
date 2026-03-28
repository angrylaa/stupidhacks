"""
Menu bar app built with rumps.
Shows ☀ in the menu bar; lets the user enable/disable and set launch-at-login.
"""
import rumps

from .brightness import BrightnessController
from .lid_monitor import LidMonitor
from .policy import Action, LidAnglePolicy, Mode


class LidLightApp(rumps.App):
    def __init__(self):
        super().__init__("☀", quit_button="Quit LidLight")

        self._enabled  = True
        self._policy   = LidAnglePolicy()
        self._bright   = BrightnessController()
        self._monitor  = LidMonitor(
            on_angle  = self._on_angle,
            on_binary = self._on_binary,
        )

        if not self._bright.is_available:
            rumps.alert(
                title="LidLight",
                message="Display brightness API unavailable.\n"
                        "Brightness control will be disabled.",
            )

        self._policy.saved_brightness = self._bright.current or 0.5

        # Build menu
        self._enabled_item = rumps.MenuItem("LidLight: Enabled",  callback=self._toggle_enabled)
        self._login_item   = rumps.MenuItem("Launch at Login",     callback=self._toggle_login)
        self._enabled_item.state = True
        self._login_item.state   = self._login_enabled()

        self.menu = [self._enabled_item, None, self._login_item]

        self._monitor.start()

    # ── rumps timer: keeps the run loop alive for the SMC poll thread ──────────
    # (The actual polling is done on a background thread in LidMonitor;
    #  this 60 s timer just ensures rumps doesn't consider the app idle.)
    @rumps.timer(60)
    def _keepalive(self, _):
        pass

    # ── Menu callbacks ─────────────────────────────────────────────────────────

    def _toggle_enabled(self, sender):
        self._enabled = not self._enabled
        sender.state  = self._enabled
        sender.title  = "LidLight: Enabled" if self._enabled else "LidLight: Disabled"
        if not self._enabled:
            self._bright.restore()

    def _toggle_login(self, sender):
        import subprocess, sys, os
        app_path = self._app_bundle_path()
        if app_path is None:
            rumps.alert("Launch at Login", "Run LidLight as a .app bundle to enable this feature.")
            return

        enable = not self._login_enabled()
        if enable:
            subprocess.run(["osascript", "-e",
                f'tell application "System Events" to make login item at end '
                f'with properties {{path:"{app_path}", hidden:false}}'], check=False)
        else:
            subprocess.run(["osascript", "-e",
                'tell application "System Events" to delete '
                '(every login item whose name is "LidLight")'], check=False)

        sender.state = enable

    # ── Lid events ─────────────────────────────────────────────────────────────

    def _on_angle(self, angle: float):
        self._apply(self._policy.evaluate(angle, Mode.CONTINUOUS))

    def _on_binary(self, is_open: bool):
        self._apply(self._policy.evaluate(180.0 if is_open else 0.0, Mode.BINARY))

    def _apply(self, action):
        if not self._enabled or action is None:
            return
        if action == Action.DIM:
            self._bright.set(self._policy.DIM_LEVEL)
        elif action == Action.BRIGHTEN:
            self._bright.set(self._policy.BRIGHT_LEVEL)
        elif action == Action.RESTORE:
            self._bright.set(self._policy.saved_brightness)

    # ── Helpers ────────────────────────────────────────────────────────────────

    @staticmethod
    def _login_enabled() -> bool:
        import subprocess
        result = subprocess.run(
            ["osascript", "-e",
             'tell application "System Events" to get name of every login item'],
            capture_output=True, text=True
        )
        return "LidLight" in result.stdout

    @staticmethod
    def _app_bundle_path():
        import sys, os
        exe = sys.executable
        # When running as .app bundle, executable is inside *.app/Contents/MacOS/
        parts = exe.split(os.sep)
        try:
            idx = next(i for i, p in enumerate(parts) if p.endswith(".app"))
            return os.sep + os.path.join(*parts[:idx + 1])
        except StopIteration:
            return None
