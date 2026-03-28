"""
Orchestrates lid state detection.

Primary:   SMC key MSLD polled every 0.5 s (may give angle or binary).
Fallback:  NSWorkspace screen-sleep / screen-wake notifications (reliable binary).

All callbacks are invoked on the main thread.
"""
import threading
from typing import Callable, Optional

from .smc import SMCLidReader


class LidMonitor:
    def __init__(
        self,
        on_angle:  Optional[Callable[[float], None]] = None,
        on_binary: Optional[Callable[[bool],  None]] = None,
    ):
        self.on_angle  = on_angle   # called with degrees when SMC gives continuous data
        self.on_binary = on_binary  # called with True=open / False=closing

        self._smc           = SMCLidReader()
        self._smc_ok        = False
        self._timer: Optional[threading.Timer] = None
        self._last_binary: Optional[bool]      = None
        self._observers: list = []   # keep strong refs to PyObjC observers

    # ── Lifecycle ──────────────────────────────────────────────────────────────

    def start(self):
        self._smc_ok = self._smc.connect()
        self._register_power_notifications()
        self._schedule_poll()

    def stop(self):
        if self._timer:
            self._timer.cancel()
            self._timer = None
        self._smc.disconnect()
        self._unregister_power_notifications()

    # ── SMC polling ───────────────────────────────────────────────────────────

    def _schedule_poll(self):
        self._timer = threading.Timer(0.5, self._poll)
        self._timer.daemon = True
        self._timer.start()

    def _poll(self):
        try:
            if self._smc_ok:
                reading = self._smc.read_lid_state()
                if reading.kind == "angle":
                    self._fire_angle(float(reading.value))
                elif reading.kind == "binary":
                    self._fire_binary(bool(reading.value))
        finally:
            self._schedule_poll()   # always reschedule

    # ── NSWorkspace notifications (binary fallback) ────────────────────────────

    def _register_power_notifications(self):
        try:
            from AppKit import NSWorkspace
            from Foundation import NSOperationQueue

            nc = NSWorkspace.sharedWorkspace().notificationCenter()

            def on_sleep(_note):
                self._fire_binary(False)   # lid closing

            def on_wake(_note):
                self._fire_binary(True)    # lid opened

            for name, cb in (
                ("NSWorkspaceScreensDidSleepNotification", on_sleep),
                ("NSWorkspaceScreensDidWakeNotification",  on_wake),
            ):
                token = nc.addObserverForName_object_queue_usingBlock_(
                    name, None, NSOperationQueue.mainQueue(), cb
                )
                self._observers.append(token)
        except Exception:
            pass   # PyObjC unavailable — SMC polling is the only path

    def _unregister_power_notifications(self):
        try:
            from AppKit import NSWorkspace
            nc = NSWorkspace.sharedWorkspace().notificationCenter()
            for token in self._observers:
                nc.removeObserver_(token)
        except Exception:
            pass
        self._observers.clear()

    # ── Dispatch helpers ───────────────────────────────────────────────────────

    def _fire_angle(self, angle: float):
        if self.on_angle:
            self.on_angle(angle)

    def _fire_binary(self, is_open: bool):
        if is_open == self._last_binary:
            return   # deduplicate
        self._last_binary = is_open
        if self.on_binary:
            self.on_binary(is_open)
