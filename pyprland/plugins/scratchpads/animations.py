" Animations for absolute window positioning "

__all__ = ["Animations"]

from ...adapters.units import convert_monitor_dimension
from ...common import MonitorInfo, ClientInfo, is_rotated


def get_size(monitor: MonitorInfo):
    "Get the (width, height) size of the monitor"
    s = monitor["scale"]
    h, w = int(monitor["height"] / s), int(monitor["width"] / s)
    if is_rotated(monitor):
        return (h, w)
    return (w, h)


class Animations:  # {{{
    "Animation store"

    @staticmethod
    def fromtop(monitor: MonitorInfo, client: ClientInfo, client_uid: str, margin: int):
        "Slide from/to top"
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width, mon_height = get_size(monitor)

        client_width = client["size"][0]
        margin_x = int((mon_width - client_width) / 2) + mon_x

        corrected_margin = convert_monitor_dimension(margin, mon_height, monitor)

        return (
            f"movewindowpixel exact {margin_x} {mon_y + corrected_margin},{client_uid}"
        )

    @staticmethod
    def frombottom(
        monitor: MonitorInfo, client: ClientInfo, client_uid: str, margin: int
    ):
        "Slide from/to bottom"
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width, mon_height = get_size(monitor)

        client_width = client["size"][0]
        client_height = client["size"][1]
        margin_x = int((mon_width - client_width) / 2) + mon_x

        corrected_margin = convert_monitor_dimension(margin, mon_height, monitor)

        return f"movewindowpixel exact {margin_x} {mon_y + mon_height - client_height - corrected_margin},{client_uid}"

    @staticmethod
    def fromleft(
        monitor: MonitorInfo, client: ClientInfo, client_uid: str, margin: int
    ):
        "Slide from/to left"
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width, mon_height = get_size(monitor)

        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y

        corrected_margin = convert_monitor_dimension(margin, mon_width, monitor)

        return (
            f"movewindowpixel exact {corrected_margin + mon_x} {margin_y},{client_uid}"
        )

    @staticmethod
    def fromright(
        monitor: MonitorInfo, client: ClientInfo, client_uid: str, margin: int
    ):
        "Slide from/to right"
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width, mon_height = get_size(monitor)

        client_width = client["size"][0]
        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y

        corrected_margin = convert_monitor_dimension(margin, mon_width, monitor)

        return f"movewindowpixel exact {mon_width - client_width - corrected_margin + mon_x } {margin_y},{client_uid}"


# }}}
