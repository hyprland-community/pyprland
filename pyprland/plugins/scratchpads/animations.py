" Animations for absolute window positioning "

__all__ = ["Animations"]

from ...adapters.units import convert_monitor_dimension
from ...common import MonitorInfo, ClientInfo


class Animations:  # {{{
    "Animation store"

    @staticmethod
    def fromtop(monitor: MonitorInfo, client: ClientInfo, client_uid: str, margin: int):
        "Slide from/to top"
        scale = float(monitor["scale"])
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width = int(monitor["width"] / scale)

        client_width = client["size"][0]
        margin_x = int((mon_width - client_width) / 2) + mon_x

        corrected_margin = convert_monitor_dimension(margin, monitor["height"], monitor)

        return (
            f"movewindowpixel exact {margin_x} {mon_y + corrected_margin},{client_uid}"
        )

    @staticmethod
    def frombottom(
        monitor: MonitorInfo, client: ClientInfo, client_uid: str, margin: int
    ):
        "Slide from/to bottom"
        scale = float(monitor["scale"])
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width = int(monitor["width"] / scale)
        mon_height = int(monitor["height"] / scale)

        client_width = client["size"][0]
        client_height = client["size"][1]
        margin_x = int((mon_width - client_width) / 2) + mon_x

        corrected_margin = convert_monitor_dimension(margin, monitor["height"], monitor)

        return f"movewindowpixel exact {margin_x} {mon_y + mon_height - client_height - corrected_margin},{client_uid}"

    @staticmethod
    def fromleft(
        monitor: MonitorInfo, client: ClientInfo, client_uid: str, margin: int
    ):
        "Slide from/to left"
        scale = float(monitor["scale"])
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_height = int(monitor["height"] / scale)

        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y

        corrected_margin = convert_monitor_dimension(margin, monitor["width"], monitor)

        return (
            f"movewindowpixel exact {corrected_margin + mon_x} {margin_y},{client_uid}"
        )

    @staticmethod
    def fromright(
        monitor: MonitorInfo, client: ClientInfo, client_uid: str, margin: int
    ):
        "Slide from/to right"
        scale = float(monitor["scale"])
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width = int(monitor["width"] / scale)
        mon_height = int(monitor["height"] / scale)

        client_width = client["size"][0]
        client_height = client["size"][1]
        margin_y = int((mon_height - client_height) / 2) + mon_y

        corrected_margin = convert_monitor_dimension(margin, monitor["width"], monitor)

        return f"movewindowpixel exact {mon_width - client_width - corrected_margin + mon_x } {margin_y},{client_uid}"


# }}}
