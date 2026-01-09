"""Conversion functions for units used in Pyprland & plugins."""

from ..common import is_rotated
from ..models import MonitorInfo


def convert_monitor_dimension(size: int | str, ref_value: int, monitor: MonitorInfo) -> int:
    """Convert `size` into pixels (given a reference value applied to a `monitor`).

    if size is an integer, assumed pixels & return it
    if size is a string, expects a "%" or "px" suffix
    else throws an error

    Args:
        size: The size to convert (int or string with unit)
        ref_value: Reference value for percentage calculations
        monitor: Monitor information
    """
    if isinstance(size, int):
        return size

    if isinstance(size, str):
        if size.endswith("%"):
            p = int(size[:-1])
            return int(ref_value / monitor["scale"] * p / 100)
        if size.endswith("px"):
            return int(size[:-2])

    msg = f"Unsupported format: {size} (applied to {ref_value})"
    raise ValueError(msg)


def convert_coords(coords: str, monitor: MonitorInfo) -> list[int]:
    """Convert a string like "X Y" to coordinates relative to monitor.

    Supported formats for X, Y:
    - Percentage: "V%". V in [0; 100]
    - Pixels: "Vpx". V should fit in your screen and not be zero

    Example:
    "10% 20%", monitor 800x600 => 80, 120

    Args:
        coords: Coordinates string "X Y"
        monitor: Monitor information
    """
    return [
        convert_monitor_dimension(name, monitor[ref], monitor)  # type: ignore
        for (name, ref) in zip(
            [coord.strip() for coord in coords.split()],
            (("height", "width") if is_rotated(monitor) else ("width", "height")),
            strict=False,
        )
    ]
