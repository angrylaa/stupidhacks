from __future__ import annotations

import AppKit
import ApplicationServices
import Foundation
import Quartz
import objc

from . import permissions


class TriggerMonitor(AppKit.NSObject):
    def initWithController_(self, controller):
        self = objc.super(TriggerMonitor, self).init()
        if self is None:
            return None
        self.controller = controller
        self.notification_center = AppKit.NSWorkspace.sharedWorkspace().notificationCenter()
        self.event_tap = None
        self.run_loop_source = None
        self.event_callback = None
        self.system_wide_element = ApplicationServices.AXUIElementCreateSystemWide()
        return self

    @objc.python_method
    def start(self) -> None:
        self.notification_center.addObserver_selector_name_object_(
            self,
            "workspaceDidTerminateApplication:",
            AppKit.NSWorkspaceDidTerminateApplicationNotification,
            None,
        )
        self.refresh_accessibility()

    @objc.python_method
    def stop(self) -> None:
        self.notification_center.removeObserver_(self)
        self.stop_event_tap()

    @objc.python_method
    def keyboard_hook_live(self) -> bool:
        return self.event_tap is not None

    @objc.python_method
    def refresh_accessibility(self) -> bool:
        trusted = permissions.accessibility_trusted(prompt=False)
        if trusted and self.event_tap is None:
            self.start_event_tap()
        elif not trusted and self.event_tap is not None:
            self.stop_event_tap()
        return trusted

    @objc.python_method
    def stop_event_tap(self) -> None:
        if self.run_loop_source is not None:
            Foundation.CFRunLoopRemoveSource(
                Foundation.CFRunLoopGetCurrent(),
                self.run_loop_source,
                Foundation.kCFRunLoopCommonModes,
            )
            self.run_loop_source = None
        if self.event_tap is not None:
            Quartz.CFMachPortInvalidate(self.event_tap)
            self.event_tap = None

    @objc.python_method
    def start_event_tap(self) -> None:
        if self.event_tap is not None:
            return

        def callback(proxy, event_type, event, refcon):
            return self._event_callback(proxy, event_type, event, refcon)

        event_types = (
            Quartz.kCGEventKeyDown,
            Quartz.kCGEventMouseMoved,
            Quartz.kCGEventLeftMouseDown,
            Quartz.kCGEventLeftMouseUp,
            Quartz.kCGEventLeftMouseDragged,
            Quartz.kCGEventRightMouseDown,
            Quartz.kCGEventRightMouseUp,
            Quartz.kCGEventRightMouseDragged,
            Quartz.kCGEventOtherMouseDown,
            Quartz.kCGEventOtherMouseUp,
            Quartz.kCGEventOtherMouseDragged,
            Quartz.kCGEventScrollWheel,
        )
        mask = 0
        for event_type in event_types:
            mask |= Quartz.CGEventMaskBit(event_type)
        self.event_callback = callback
        self.event_tap = Quartz.CGEventTapCreate(
            Quartz.kCGSessionEventTap,
            Quartz.kCGHeadInsertEventTap,
            Quartz.kCGEventTapOptionDefault,
            mask,
            self.event_callback,
            None,
        )
        if self.event_tap is None:
            return
        self.run_loop_source = Quartz.CFMachPortCreateRunLoopSource(None, self.event_tap, 0)
        Foundation.CFRunLoopAddSource(
            Foundation.CFRunLoopGetCurrent(),
            self.run_loop_source,
            Foundation.kCFRunLoopCommonModes,
        )
        Quartz.CGEventTapEnable(self.event_tap, True)

    @objc.python_method
    def _event_callback(self, proxy, event_type, event, refcon):
        if event_type in (Quartz.kCGEventTapDisabledByTimeout, Quartz.kCGEventTapDisabledByUserInput):
            if self.event_tap is not None:
                Quartz.CGEventTapEnable(self.event_tap, True)
            return event

        if self.controller.overlay_is_visible():
            if event_type in (
                Quartz.kCGEventMouseMoved,
                Quartz.kCGEventLeftMouseDown,
                Quartz.kCGEventLeftMouseUp,
                Quartz.kCGEventLeftMouseDragged,
                Quartz.kCGEventRightMouseDown,
                Quartz.kCGEventRightMouseUp,
                Quartz.kCGEventRightMouseDragged,
                Quartz.kCGEventOtherMouseDown,
                Quartz.kCGEventOtherMouseUp,
                Quartz.kCGEventOtherMouseDragged,
                Quartz.kCGEventScrollWheel,
            ):
                return None

        if (
            event_type == Quartz.kCGEventLeftMouseDown
            and self.controller.should_handle_automatic_triggers()
        ):
            button_kind = self._window_button_kind_for_event(event)
            if button_kind is not None:
                self.controller.handle_window_button_trigger(button_kind)
                return event

        keycode = Quartz.CGEventGetIntegerValueField(event, Quartz.kCGKeyboardEventKeycode)
        flags = Quartz.CGEventGetFlags(event)
        command_down = bool(flags & Quartz.kCGEventFlagMaskCommand)

        if self.controller.overlay_is_visible():
            if keycode in (12, 13, 53):
                return None
            return event

        if not self.controller.should_handle_automatic_triggers():
            return event

        if command_down and keycode in (12, 13):
            self.controller.handle_hotkey_trigger(int(keycode))
            return event

        return event

    def workspaceDidTerminateApplication_(self, notification):
        app = notification.userInfo().get(AppKit.NSWorkspaceApplicationKey)
        if app is None:
            return None
        bundle_id = app.bundleIdentifier()
        localized_name = app.localizedName()
        self.controller.handle_workspace_termination(bundle_id, localized_name)
        return None

    @objc.python_method
    def _window_button_kind_for_event(self, event) -> str | None:
        location = Quartz.CGEventGetLocation(event)
        error, element = ApplicationServices.AXUIElementCopyElementAtPosition(
            self.system_wide_element,
            location.x,
            location.y,
            None,
        )
        if error != 0 or element is None:
            return None

        role = self._ax_attribute(element, ApplicationServices.kAXRoleAttribute)
        subrole = self._ax_attribute(element, ApplicationServices.kAXSubroleAttribute)
        identifier = self._ax_attribute(element, ApplicationServices.kAXIdentifierAttribute)
        description = self._ax_attribute(element, ApplicationServices.kAXDescriptionAttribute)
        title = self._ax_attribute(element, ApplicationServices.kAXTitleAttribute)

        values = {
            str(value).lower()
            for value in (role, subrole, identifier, description, title)
            if value
        }
        if "axbutton" not in values and role != "AXButton":
            return None

        if any("close" in value for value in values) or subrole == "AXCloseButton":
            return "close-button"
        if any("minimize" in value for value in values) or subrole == "AXMinimizeButton":
            return "minimize-button"
        return None

    @objc.python_method
    def _ax_attribute(self, element, attribute: str):
        error, value = ApplicationServices.AXUIElementCopyAttributeValue(
            element,
            attribute,
            None,
        )
        if error != 0:
            return None
        return value
