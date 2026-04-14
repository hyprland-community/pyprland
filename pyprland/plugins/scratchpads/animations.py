"""Placement for absolute window positioning."""

__all__ = ["Placement"]

import enum
from collections.abc import Callable

from ...adapters.units import convert_monitor_dimension
from ...models import ClientInfo, MonitorInfo
from .helpers import get_size


class AnimationTarget(enum.Enum):
    """Animation type (selects between main window and satellite windows)."""

    MAIN = "main"
    EXTRA = "extra"
    ALL = "all"


# ---------------------------------------------------------------------------
# X-position strategies
# ---------------------------------------------------------------------------


def _x_center(mon_x: int, mon_w: int, client_w: int, _margin_w: int) -> int:
    """Center horizontally on the monitor."""
    return (mon_w - client_w) // 2 + mon_x


def _x_left(mon_x: int, _mon_w: int, _client_w: int, margin_w: int) -> int:
    """Align to left edge with margin."""
    return margin_w + mon_x


def _x_right(mon_x: int, mon_w: int, client_w: int, margin_w: int) -> int:
    """Align to right edge with margin."""
    return mon_w - client_w - margin_w + mon_x


# ---------------------------------------------------------------------------
# Y-position strategies
# ---------------------------------------------------------------------------


def _y_center(mon_y: int, mon_h: int, client_h: int, _margin_h: int) -> int:
    """Center vertically on the monitor."""
    return (mon_h - client_h) // 2 + mon_y


def _y_top(mon_y: int, _mon_h: int, _client_h: int, margin_h: int) -> int:
    """Align to top edge with margin."""
    return margin_h + mon_y


def _y_bottom(mon_y: int, mon_h: int, client_h: int, margin_h: int) -> int:
    """Align to bottom edge with margin."""
    return mon_h - client_h - margin_h + mon_y


# ---------------------------------------------------------------------------
# Direction -> (x_strategy, y_strategy) mapping
# ---------------------------------------------------------------------------

_PosFn = Callable[[int, int, int, int], int]

_DIRECTION_MAP: dict[str, tuple[_PosFn, _PosFn]] = {
    "fromtop": (_x_center, _y_top),
    "frombottom": (_x_center, _y_bottom),
    "fromleft": (_x_left, _y_center),
    "fromright": (_x_right, _y_center),
    "fromtopleft": (_x_left, _y_top),
    "fromtopright": (_x_right, _y_top),
    "frombottomleft": (_x_left, _y_bottom),
    "frombottomright": (_x_right, _y_bottom),
}


class Placement:
    """Compute on-screen and off-screen window positions for each animation direction."""

    @staticmethod
    def get(animation_type: str, monitor: MonitorInfo, client: ClientInfo, margin: int) -> tuple[int, int]:
        """Get destination coordinate for the provided animation type.

        Args:
            animation_type: Type of animation (fromtop, frombottom, etc.)
            monitor: Monitor information
            client: Client window information
            margin: Margin to apply
        """
        x_fn, y_fn = _DIRECTION_MAP[animation_type]
        mon_x, mon_y = monitor["x"], monitor["y"]
        mon_w, mon_h = get_size(monitor)
        client_w, client_h = client["size"]
        margin_w = convert_monitor_dimension(margin, mon_w, monitor)
        margin_h = convert_monitor_dimension(margin, mon_h, monitor)
        return (
            x_fn(mon_x, mon_w, client_w, margin_w),
            y_fn(mon_y, mon_h, client_h, margin_h),
        )

    @staticmethod
    def get_offscreen(animation_type: str, monitor: MonitorInfo, client: ClientInfo, margin: int) -> tuple[int, int]:
        """Get off-screen position for the given animation type.

        Computes the final on-screen position via ``get()``, then pushes the
        window far off-screen along the animation axis.  An extra monitor
        dimension is subtracted/added so the window doesn't appear on an
        adjacent monitor in multi-monitor setups.

        For each axis the direction operates on (left/right or top/bottom),
        the coordinate is pushed far offscreen.  For the centered axis
        (if any), the on-screen coordinate is preserved.

        Args:
            animation_type: Type of animation (fromtop, frombottom, etc.)
            monitor: Monitor information
            client: Client window information
            margin: Margin to apply
        """
        fx, fy = Placement.get(animation_type, monitor, client, margin)
        mon_x, mon_y = monitor["x"], monitor["y"]
        mon_w, mon_h = get_size(monitor)
        client_w, client_h = client["size"]

        x_fn, y_fn = _DIRECTION_MAP[animation_type]

        # For each axis: push far offscreen if direction uses that edge, otherwise keep on-screen position
        if x_fn is _x_left:
            off_x = mon_x - client_w - mon_w
        elif x_fn is _x_right:
            off_x = mon_x + mon_w + mon_w
        else:
            off_x = fx

        if y_fn is _y_top:
            off_y = mon_y - client_h - mon_h
        elif y_fn is _y_bottom:
            off_y = mon_y + mon_h + mon_h
        else:
            off_y = fy

        return (off_x, off_y)
