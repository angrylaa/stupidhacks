from __future__ import annotations

import time

import AppKit
import AVFoundation
import Foundation
import Quartz
import objc

from .player import MemePlayer
from .policy import PunishmentEvent


HOTKEY_KEYCODES = {12, 13, 53}


class MemePanel(AppKit.NSPanel):
    controller = objc.ivar()

    def canBecomeKeyWindow(self):
        return True

    def canBecomeMainWindow(self):
        return True

    def performKeyEquivalent_(self, event):
        if self.controller and self.controller.should_swallow_event(event):
            return True
        return False

    def keyDown_(self, event):
        if self.controller and self.controller.should_swallow_event(event):
            return None
        return objc.super(MemePanel, self).keyDown_(event)

    def cancelOperation_(self, sender):
        if self.controller and self.controller.is_visible():
            return None
        return objc.super(MemePanel, self).cancelOperation_(sender)

    def performClose_(self, sender):
        if self.controller and self.controller.is_visible():
            return None
        return objc.super(MemePanel, self).performClose_(sender)


class OverlayController(AppKit.NSObject):
    def initWithController_(self, controller):
        self = objc.super(OverlayController, self).init()
        if self is None:
            return None
        self.controller = controller
        self.window = None
        self.player = None
        self.timer = None
        self.unlock_at = 0.0
        self.auto_close_at = 0.0
        self.current_event = None
        self.playback_finished = False
        self.observed_item = None
        self.previous_presentation_options = AppKit.NSApplicationPresentationDefault
        self.presentation_locked = False
        self._build_window()
        return self

    @objc.python_method
    def _build_window(self) -> None:
        screen = AppKit.NSScreen.mainScreen()
        frame = screen.frame() if screen is not None else AppKit.NSMakeRect(0, 0, 1440, 900)
        style = AppKit.NSWindowStyleMaskBorderless
        window = MemePanel.alloc().initWithContentRect_styleMask_backing_defer_(
            frame,
            style,
            AppKit.NSBackingStoreBuffered,
            False,
        )
        window.controller = self
        window.setLevel_(Quartz.CGShieldingWindowLevel())
        window.setOpaque_(True)
        window.setBackgroundColor_(AppKit.NSColor.blackColor())
        window.setReleasedWhenClosed_(False)
        window.setCollectionBehavior_(
            AppKit.NSWindowCollectionBehaviorCanJoinAllSpaces
            | AppKit.NSWindowCollectionBehaviorFullScreenAuxiliary
            | AppKit.NSWindowCollectionBehaviorStationary
        )
        window.setHidesOnDeactivate_(False)
        window.setMovable_(False)
        window.setMovableByWindowBackground_(False)

        root = AppKit.NSView.alloc().initWithFrame_(frame)
        root.setAutoresizingMask_(
            AppKit.NSViewWidthSizable | AppKit.NSViewHeightSizable
        )

        self.player = MemePlayer(frame)
        root.addSubview_(self.player.view)

        window.setContentView_(root)
        self.window = window

    @objc.python_method
    def is_visible(self) -> bool:
        return bool(self.window and self.window.isVisible())

    @objc.python_method
    def should_swallow_event(self, event) -> bool:
        keycode = event.keyCode() if hasattr(event, "keyCode") else None
        if keycode not in HOTKEY_KEYCODES:
            return False
        return self.is_visible()

    @objc.python_method
    def present(self, event: PunishmentEvent) -> None:
        now = time.monotonic()
        self.current_event = event
        self.unlock_at = max(self.unlock_at, now + event.lock_seconds)

        self._remove_playback_observer()
        player_item, clip_duration = self.player.play_clip(event.clip_path)
        clip_exists = player_item is not None
        self.playback_finished = not clip_exists
        duration_buffer = 0.0
        if clip_exists and clip_duration and clip_duration > 0:
            self.auto_close_at = max(self.unlock_at, now + clip_duration + duration_buffer)
        else:
            self.auto_close_at = self.unlock_at
        if player_item is not None:
            Foundation.NSNotificationCenter.defaultCenter().addObserver_selector_name_object_(
                self,
                "playerItemDidFinish:",
                AVFoundation.AVPlayerItemDidPlayToEndTimeNotification,
                player_item,
            )
            self.observed_item = player_item
        self._enable_kiosk_presentation()

        self.window.orderFrontRegardless()
        self.window.makeKeyAndOrderFront_(None)
        AppKit.NSApp.activateIgnoringOtherApps_(True)

        if self.timer is None:
            self.timer = Foundation.NSTimer.scheduledTimerWithTimeInterval_target_selector_userInfo_repeats_(
                0.05,
                self,
                "tick:",
                None,
                True,
            )
        self._tick_labels()

    @objc.python_method
    def _tick_labels(self) -> None:
        return None

    def tick_(self, timer):
        self._tick_labels()
        if time.monotonic() >= self.auto_close_at:
            self.dismissOverlay_(None)

    def playerItemDidFinish_(self, notification):
        self.playback_finished = True
        if time.monotonic() >= self.auto_close_at:
            self.dismissOverlay_(None)
        return None

    @objc.python_method
    def _remove_playback_observer(self) -> None:
        if self.observed_item is None:
            return
        Foundation.NSNotificationCenter.defaultCenter().removeObserver_name_object_(
            self,
            AVFoundation.AVPlayerItemDidPlayToEndTimeNotification,
            self.observed_item,
        )
        self.observed_item = None

    def dismissOverlay_(self, sender):
        if time.monotonic() < self.auto_close_at:
            return None
        if self.timer is not None:
            self.timer.invalidate()
            self.timer = None
        self._remove_playback_observer()
        self.player.stop()
        self._disable_kiosk_presentation()
        self.window.orderOut_(None)
        self.unlock_at = 0.0
        self.auto_close_at = 0.0
        self.current_event = None
        self.playback_finished = False
        self.controller.overlay_did_dismiss()
        return None

    @objc.python_method
    def _enable_kiosk_presentation(self) -> None:
        if self.presentation_locked:
            return
        self.previous_presentation_options = AppKit.NSApp.presentationOptions()
        options = (
            AppKit.NSApplicationPresentationHideDock
            | AppKit.NSApplicationPresentationHideMenuBar
            | AppKit.NSApplicationPresentationDisableProcessSwitching
            | AppKit.NSApplicationPresentationDisableHideApplication
            | AppKit.NSApplicationPresentationDisableForceQuit
        )
        AppKit.NSApp.setPresentationOptions_(options)
        self.presentation_locked = True

    @objc.python_method
    def _disable_kiosk_presentation(self) -> None:
        if not self.presentation_locked:
            return
        AppKit.NSApp.setPresentationOptions_(self.previous_presentation_options)
        self.presentation_locked = False
