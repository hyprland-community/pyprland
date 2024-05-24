"""Placement for absolute window positioning."""

__all__ = ["Placement"]

import enum
from typing import cast

from ...adapters.units import convert_monitor_dimension
from ...types import ClientInfo, MonitorInfo
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
        """Get destination coordinate for the provided animation type."""
        return cast(tuple[int, int], getattr(Placement, animation_type)(monitor, client, margin))

    # animation types
    @staticmethod
    def fromtop(monitor: MonitorInfo, client: ClientInfo, margin: int) -> tuple[int, int]:
        """Slide from/to top."""
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width, mon_height = get_size(monitor)

        client_width = client["size"][0]
        margin_x = int((mon_width - client_width) / 2) + mon_x

        corrected_margin = convert_monitor_dimension(margin, mon_height, monitor)

        return (margin_x, mon_y + corrected_margin)

    @staticmethod
    def frombottom(monitor: MonitorInfo, client: ClientInfo, margin: int) -> tuple[int, int]:
        """Slide from/to bottom."""
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
        """Slide from/to left."""
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width, mon_height = get_size(monitor)

        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y

        corrected_margin = convert_monitor_dimension(margin, mon_width, monitor)

        return (corrected_margin + mon_x, margin_y)

    @staticmethod
    def fromright(monitor: MonitorInfo, client: ClientInfo, margin: int) -> tuple[int, int]:
        """Slide from/to right."""
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width, mon_height = get_size(monitor)

        client_width = client["size"][0]
        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y

        corrected_margin = convert_monitor_dimension(margin, mon_width, monitor)

        return (mon_width - client_width - corrected_margin + mon_x, margin_y)


# }}}
