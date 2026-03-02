"""Placement for absolute window positioning."""

__all__ = ["Placement"]

import enum
from typing import cast

from ...adapters.units import convert_monitor_dimension
from ...models import ClientInfo, MonitorInfo
from .helpers import get_size


class AnimationTarget(enum.Enum):
    """Animation type (selects between main window and satellite windows)."""

    MAIN = "main"
    EXTRA = "extra"
    ALL = "all"


class Placement:  # {{{
    """Animation store."""

    # main function
    @staticmethod
    def get(animation_type: str, monitor: MonitorInfo, client: ClientInfo, margin: int) -> tuple[int, int]:
        """Get destination coordinate for the provided animation type.

        Args:
            animation_type: Type of animation (fromtop, frombottom, etc.)
            monitor: Monitor information
            client: Client window information
            margin: Margin to apply
        """
        return cast("tuple[int, int]", getattr(Placement, animation_type)(monitor, client, margin))

    @staticmethod
    def get_offscreen(animation_type: str, monitor: MonitorInfo, client: ClientInfo, margin: int) -> tuple[int, int]:
        """Get off-screen position for the given animation type.

        Computes the final on-screen position via `get()`, then pushes the
        window far off-screen along the animation axis.  An extra monitor
        dimension is subtracted/added so the window doesn't appear on an
        adjacent monitor in multi-monitor setups.

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
        offscreen_map = {
            "fromtop": (fx, mon_y - client_h - mon_h),
            "frombottom": (fx, mon_y + mon_h + mon_h),
            "fromleft": (mon_x - client_w - mon_w, fy),
            "fromright": (mon_x + mon_w + mon_w, fy),
        }
        return offscreen_map[animation_type]

    # animation types
    @staticmethod
    def fromtop(monitor: MonitorInfo, client: ClientInfo, margin: int) -> tuple[int, int]:
        """Slide from/to top.

        Args:
            monitor: Monitor information
            client: Client window information
            margin: Margin to apply
        """
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width, mon_height = get_size(monitor)

        client_width = client["size"][0]
        margin_x = int((mon_width - client_width) / 2) + mon_x

        corrected_margin = convert_monitor_dimension(margin, mon_height, monitor)

        return (margin_x, mon_y + corrected_margin)

    @staticmethod
    def frombottom(monitor: MonitorInfo, client: ClientInfo, margin: int) -> tuple[int, int]:
        """Slide from/to bottom.

        Args:
            monitor: Monitor information
            client: Client window information
            margin: Margin to apply
        """
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width, mon_height = get_size(monitor)

        client_width = client["size"][0]
        client_height = client["size"][1]
        margin_x = int((mon_width - client_width) / 2) + mon_x

        corrected_margin = convert_monitor_dimension(margin, mon_height, monitor)

        return (margin_x, mon_y + mon_height - client_height - corrected_margin)

    @staticmethod
    def fromleft(monitor: MonitorInfo, client: ClientInfo, margin: int) -> tuple[int, int]:
        """Slide from/to left.

        Args:
            monitor: Monitor information
            client: Client window information
            margin: Margin to apply
        """
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width, mon_height = get_size(monitor)

        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y

        corrected_margin = convert_monitor_dimension(margin, mon_width, monitor)

        return (corrected_margin + mon_x, margin_y)

    @staticmethod
    def fromright(monitor: MonitorInfo, client: ClientInfo, margin: int) -> tuple[int, int]:
        """Slide from/to right.

        Args:
            monitor: Monitor information
            client: Client window information
            margin: Margin to apply
        """
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width, mon_height = get_size(monitor)

        client_width = client["size"][0]
        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y

        corrected_margin = convert_monitor_dimension(margin, mon_width, monitor)

        return (mon_width - client_width - corrected_margin + mon_x, margin_y)


# }}}
