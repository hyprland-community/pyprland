"""Command building for Hyprland and Niri backends."""

from typing import Any

from ...models import MonitorInfo

NIRI_TRANSFORM_NAMES = [
    "Normal",
    "90",
    "180",
    "270",
    "Flipped",
    "Flipped90",
    "Flipped180",
    "Flipped270",
]


def build_hyprland_command(monitor: MonitorInfo, config: dict[str, Any]) -> str:
    """Build Hyprland monitor command string.

    Args:
        monitor: Monitor information (must have x, y set)
        config: Monitor-specific configuration

    Returns:
        Command string like "monitor DP-1,1920x1080@60,0x0,1.0,transform,0"
    """
    name = monitor["name"]
    rate = config.get("rate", monitor["refreshRate"])
    res = config.get("resolution", f"{monitor['width']}x{monitor['height']}")
    if isinstance(res, list):
        res = f"{res[0]}x{res[1]}"
    scale = config.get("scale", monitor["scale"])
    position = f"{monitor['x']}x{monitor['y']}"
    transform = config.get("transform", monitor["transform"])
    return f"monitor {name},{res}@{rate},{position},{scale},transform,{transform}"


def build_niri_position_action(name: str, x_pos: int, y_pos: int) -> dict:
    """Build Niri position action.

    Args:
        name: Output name
        x_pos: X coordinate
        y_pos: Y coordinate

    Returns:
        Niri action dict for setting position
    """
    return {"Output": {"output": name, "action": {"Position": {"Specific": {"x": x_pos, "y": y_pos}}}}}


def build_niri_scale_action(name: str, scale: float) -> dict:
    """Build Niri scale action.

    Args:
        name: Output name
        scale: Scale factor

    Returns:
        Niri action dict for setting scale
    """
    return {"Output": {"output": name, "action": {"Scale": {"Specific": float(scale)}}}}


def build_niri_transform_action(name: str, transform: int | str) -> dict:
    """Build Niri transform action.

    Args:
        name: Output name
        transform: Transform value (int 0-7 or string)

    Returns:
        Niri action dict for setting transform
    """
    if isinstance(transform, int) and 0 <= transform < len(NIRI_TRANSFORM_NAMES):
        transform_str = NIRI_TRANSFORM_NAMES[transform]
    else:
        transform_str = str(transform)
    return {"Output": {"output": name, "action": {"Transform": {"transform": transform_str}}}}


def build_niri_disable_action(name: str) -> dict:
    """Build Niri disable action.

    Args:
        name: Output name

    Returns:
        Niri action dict for disabling output
    """
    return {"Output": {"output": name, "action": "Off"}}
