"""Common types for scratchpads."""

from dataclasses import dataclass
from enum import Flag, auto


class HideFlavors(Flag):
    """Flags for different hide behavior."""

    NONE = auto()
    FORCED = auto()
    TRIGGERED_BY_AUTOHIDE = auto()
    IGNORE_TILED = auto()


@dataclass
class FocusTracker:
    """Focus tracking object."""

    prev_focused_window: str
    prev_focused_window_wrkspc: str

    def clear(self) -> None:
        """Clear the tracking."""
        self.prev_focused_window = ""
        self.prev_focused_window_wrkspc = ""
