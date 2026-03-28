from __future__ import annotations

import AppKit


class StatusMenu:
    def __init__(self, controller) -> None:
        self.controller = controller
        self.status_item = None
        self.menu = None
        self.enabled_item = None
        self.safe_mode_item = None
        self.kill_count_item = None
        self.accessibility_item = None
        self.keyboard_hook_item = None

    def install(self) -> None:
        self.status_item = AppKit.NSStatusBar.systemStatusBar().statusItemWithLength_(
            AppKit.NSVariableStatusItemLength
        )
        button = self.status_item.button()
        if button is not None:
            button.setTitle_("2016")

        self.menu = AppKit.NSMenu.alloc().initWithTitle_("QuitTok 2016")
        self.enabled_item = self._item("Enabled", "toggleEnabled:")
        self.safe_mode_item = self._item("Safe Demo Mode", "toggleSafeDemoMode:")
        self.menu.addItem_(self.enabled_item)
        self.menu.addItem_(self.safe_mode_item)
        self.menu.addItem_(AppKit.NSMenuItem.separatorItem())
        self.menu.addItem_(self._item("Trigger Meme Now", "manualTrigger:"))
        self.menu.addItem_(AppKit.NSMenuItem.separatorItem())
        self.kill_count_item = self._item("Closures prevented: 0", None, enabled=False)
        self.accessibility_item = self._item("Accessibility: unknown", None, enabled=False)
        self.keyboard_hook_item = self._item("Keyboard hook: offline", None, enabled=False)
        self.menu.addItem_(self.kill_count_item)
        self.menu.addItem_(self.accessibility_item)
        self.menu.addItem_(self.keyboard_hook_item)
        self.menu.addItem_(self._item("Prompt for Accessibility", "requestAccessibility:"))
        self.menu.addItem_(AppKit.NSMenuItem.separatorItem())
        self.menu.addItem_(self._item("Quit QuitTok 2016", "quitApp:"))
        self.status_item.setMenu_(self.menu)

    def _item(self, title: str, action: str | None, enabled: bool = True):
        item = AppKit.NSMenuItem.alloc().initWithTitle_action_keyEquivalent_(
            title,
            action,
            "",
        )
        item.setTarget_(self.controller if action else None)
        item.setEnabled_(enabled)
        return item

    def refresh(self, *, enabled: bool, safe_demo_mode: bool, kill_count: int, accessibility: bool, keyboard_hook_live: bool) -> None:
        if self.enabled_item is None:
            return
        self.enabled_item.setState_(
            AppKit.NSControlStateValueOn if enabled else AppKit.NSControlStateValueOff
        )
        self.safe_mode_item.setState_(
            AppKit.NSControlStateValueOn if safe_demo_mode else AppKit.NSControlStateValueOff
        )
        self.kill_count_item.setTitle_(f"Closures prevented: {kill_count}")
        self.accessibility_item.setTitle_(
            f"Accessibility: {'granted' if accessibility else 'missing'}"
        )
        self.keyboard_hook_item.setTitle_(
            f"Keyboard hook: {'live' if keyboard_hook_live else 'offline'}"
        )
