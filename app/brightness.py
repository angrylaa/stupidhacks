"""
Controls built-in display brightness via private macOS APIs loaded at runtime.
Tries DisplayServices (macOS 12+, Apple Silicon) then CoreDisplay as fallback.
"""
import ctypes
from typing import Optional


class BrightnessController:
    def __init__(self):
        self._set_fn   = None
        self._get_fn   = None
        self._display  = self._main_display_id()
        self._original: float = 0.5
        self._load_api()
        b = self.current
        if b is not None:
            self._original = b

    @property
    def is_available(self) -> bool:
        return self._set_fn is not None

    @property
    def current(self) -> Optional[float]:
        if not self._get_fn:
            return None
        val = ctypes.c_float(0.0)
        if self._get_fn(self._display, ctypes.byref(val)) == 0:
            return float(val.value)
        return None

    def set(self, level: float) -> bool:
        if not self._set_fn:
            return False
        level = max(0.0, min(1.0, level))
        return self._set_fn(self._display, ctypes.c_float(level)) == 0

    def restore(self):
        self.set(self._original)

    # ── Private ────────────────────────────────────────────────────────────────

    def _load_api(self):
        candidates = [
            (
                "/System/Library/PrivateFrameworks/DisplayServices.framework/DisplayServices",
                "DisplayServicesSetBrightness",
                "DisplayServicesGetBrightness",
            ),
            (
                "/System/Library/Frameworks/CoreDisplay.framework/CoreDisplay",
                "CoreDisplay_Display_SetUserBrightness",
                "CoreDisplay_Display_GetUserBrightness",
            ),
        ]
        for path, set_name, get_name in candidates:
            try:
                lib    = ctypes.CDLL(path)
                set_fn = getattr(lib, set_name)
                get_fn = getattr(lib, get_name)
                set_fn.argtypes = [ctypes.c_uint32, ctypes.c_float]
                set_fn.restype  = ctypes.c_int32
                get_fn.argtypes = [ctypes.c_uint32, ctypes.POINTER(ctypes.c_float)]
                get_fn.restype  = ctypes.c_int32
                self._set_fn = set_fn
                self._get_fn = get_fn
                return
            except (OSError, AttributeError):
                continue

    @staticmethod
    def _main_display_id() -> int:
        try:
            cg = ctypes.CDLL(
                "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
            )
            cg.CGMainDisplayID.restype  = ctypes.c_uint32
            cg.CGMainDisplayID.argtypes = []
            return int(cg.CGMainDisplayID())
        except OSError:
            return 0
