from __future__ import annotations

import AppKit
import time
import objc

from .config import AppConfig
from .overlay import OverlayController
from .policy import PunishmentPolicy
from .status_menu import StatusMenu
from .trigger_monitor import TriggerMonitor
from .volume import VolumeController
from . import permissions


class QuitTokApp(AppKit.NSObject):
    def init(self):
        self = objc.super(QuitTokApp, self).init()
        if self is None:
            return None
        self.enabled = True
        self.safe_demo_mode = False
        self.config = AppConfig.load()
        self.policy = PunishmentPolicy(self.config)
        self.volume = VolumeController()
        self.status_menu = StatusMenu(self)
        self.overlay = OverlayController.alloc().initWithController_(self)
        self.trigger_monitor = TriggerMonitor.alloc().initWithController_(self)
        self.last_trigger_at = 0.0
        self.last_trigger_bundle_id = None
        self.last_trigger_source = None
        return self

    def applicationDidFinishLaunching_(self, notification):
        AppKit.NSApp.setActivationPolicy_(AppKit.NSApplicationActivationPolicyAccessory)
        self.status_menu.install()
        permissions.request_accessibility()
        self.trigger_monitor.start()
        self.refresh_status_menu()
        return None

    def applicationWillTerminate_(self, notification):
        self.trigger_monitor.stop()
        self.volume.restore()
        return None

    @objc.python_method
    def refresh_status_menu(self) -> None:
        ax_trusted = self.trigger_monitor.refresh_accessibility()
        self.status_menu.refresh(
            enabled=self.enabled,
            safe_demo_mode=self.safe_demo_mode,
            kill_count=self.policy.kill_count,
            accessibility=ax_trusted,
            keyboard_hook_live=self.trigger_monitor.keyboard_hook_live(),
        )

    @objc.python_method
    def should_handle_automatic_triggers(self) -> bool:
        return self.enabled and not self.safe_demo_mode

    @objc.python_method
    def overlay_is_visible(self) -> bool:
        return self.overlay.is_visible()

    @objc.python_method
    def _frontmost_application(self):
        app = AppKit.NSWorkspace.sharedWorkspace().frontmostApplication()
        bundle_id = app.bundleIdentifier() if app else None
        name = app.localizedName() if app else None
        return bundle_id, name

    @objc.python_method
    def _trigger(self, source: str, bundle_id: str | None, app_name: str | None) -> bool:
        now = time.monotonic()
        if self._should_ignore_trigger(source, bundle_id, now):
            return False
        event = self.policy.build_event(source, bundle_id=bundle_id, app_name=app_name)
        self.last_trigger_at = now
        self.last_trigger_bundle_id = bundle_id
        self.last_trigger_source = source
        self.volume.max_out()
        self.overlay.present(event)
        self.refresh_status_menu()
        return True

    @objc.python_method
    def _should_ignore_trigger(self, source: str, bundle_id: str | None, now: float) -> bool:
        if bundle_id is None or self.last_trigger_bundle_id != bundle_id:
            return False
        elapsed = now - self.last_trigger_at
        if source == self.last_trigger_source and elapsed < 0.35:
            return True
        if source == "app-quit" and elapsed < 1.0:
            return True
        return False

    @objc.python_method
    def _schedule_trigger(self, source: str, bundle_id: str | None, app_name: str | None, delay: float = 0.08) -> bool:
        if not self.should_handle_automatic_triggers():
            return False
        payload = {
            "source": source,
            "bundle_id": bundle_id,
            "app_name": app_name,
        }
        AppKit.NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
            delay,
            self,
            "fireScheduledTrigger:",
            payload,
            False,
        )
        return True

    @objc.python_method
    def handle_hotkey_trigger(self, keycode: int) -> bool:
        if not self.should_handle_automatic_triggers():
            return False
        bundle_id, name = self._frontmost_application()
        source = "cmd+w" if keycode == 13 else "cmd+q"
        return self._schedule_trigger(source, bundle_id, name)

    @objc.python_method
    def handle_window_button_trigger(self, button_kind: str) -> bool:
        if not self.should_handle_automatic_triggers():
            return False
        bundle_id, name = self._frontmost_application()
        return self._schedule_trigger(button_kind, bundle_id, name)

    @objc.python_method
    def handle_workspace_termination(self, bundle_id: str | None, app_name: str | None) -> bool:
        if not self.should_handle_automatic_triggers():
            return False
        if bundle_id == AppKit.NSBundle.mainBundle().bundleIdentifier():
            return False
        return self._trigger("app-quit", bundle_id, app_name)

    @objc.python_method
    def overlay_did_dismiss(self) -> None:
        self.volume.restore()
        self.refresh_status_menu()

    def fireScheduledTrigger_(self, timer):
        payload = timer.userInfo() or {}
        source = payload.get("source", "scheduled")
        bundle_id = payload.get("bundle_id")
        app_name = payload.get("app_name")
        self._trigger(source, bundle_id, app_name)
        return None

    def toggleEnabled_(self, sender):
        self.enabled = not self.enabled
        self.refresh_status_menu()
        return None

    def toggleSafeDemoMode_(self, sender):
        self.safe_demo_mode = not self.safe_demo_mode
        self.refresh_status_menu()
        return None

    def manualTrigger_(self, sender):
        self._trigger("manual-test", "manual.trigger", "Manual Test")
        return None

    def requestAccessibility_(self, sender):
        permissions.request_accessibility()
        self.refresh_status_menu()
        return None

    def quitApp_(self, sender):
        self.trigger_monitor.stop()
        AppKit.NSApp.terminate_(None)
        return None
