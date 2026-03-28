"""
Lid angle → brightness policy.
Pure logic, no side effects — easy to unit test.
"""
from dataclasses import dataclass, field
from enum import Enum, auto
from typing import Optional


class Mode(Enum):
    CONTINUOUS = auto()   # real angle in degrees 0–180
    BINARY     = auto()   # only open (True) or closed (False)


class Action(Enum):
    DIM     = auto()   # set to 5%
    BRIGHTEN = auto()  # set to 100%
    RESTORE = auto()   # restore saved brightness


@dataclass
class LidAnglePolicy:
    # Thresholds in degrees
    open_threshold:  float = 145.0   # past this → dim
    close_threshold: float = 60.0    # below this → bright
    hysteresis:      float = 5.0     # dead-band to prevent flicker

    DIM_LEVEL:    float = field(default=0.05, init=False)   # 5%
    BRIGHT_LEVEL: float = field(default=1.0,  init=False)   # 100%

    # Brightness before we touched it; restored when entering the middle band
    saved_brightness: float = 0.5

    _state: str = field(default="middle", init=False, repr=False)

    def evaluate(self, angle: float, mode: Mode) -> Optional[Action]:
        if mode == Mode.BINARY:
            return self._eval_binary(angle > 90)
        return self._eval_continuous(angle)

    # ------------------------------------------------------------------

    def _eval_binary(self, is_open: bool) -> Optional[Action]:
        target = "fully_open" if is_open else "closing"
        if target == self._state:
            return None
        self._state = target
        return Action.DIM if is_open else Action.BRIGHTEN

    def _eval_continuous(self, angle: float) -> Optional[Action]:
        new = self._next_state(angle)
        if new == self._state:
            return None
        self._state = new
        return {
            "fully_open": Action.DIM,
            "closing":    Action.BRIGHTEN,
            "middle":     Action.RESTORE,
        }[new]

    def _next_state(self, angle: float) -> str:
        if self._state == "fully_open":
            if angle < self.open_threshold - self.hysteresis:
                return "closing" if angle < self.close_threshold else "middle"
            return "fully_open"

        if self._state == "closing":
            if angle > self.close_threshold + self.hysteresis:
                return "fully_open" if angle > self.open_threshold else "middle"
            return "closing"

        # middle
        if angle >= self.open_threshold:
            return "fully_open"
        if angle <= self.close_threshold:
            return "closing"
        return "middle"
