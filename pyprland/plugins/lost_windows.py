"""Moves unreachable client windows to the currently focused workspace."""

from ..models import ClientInfo, Environment, MonitorInfo
from .interface import Plugin


def contains(monitor: MonitorInfo, window: ClientInfo) -> bool:
    """Tell if a window is visible in a monitor.

    Args:
        monitor: The monitor info
        window: The window info
    """
    if not (window["at"][0] >= monitor["x"] and window["at"][0] < monitor["x"] + monitor["width"]):
        return False
    return bool(window["at"][1] >= monitor["y"] and window["at"][1] < monitor["y"] + monitor["height"])


class Extension(Plugin, environments=[Environment.HYPRLAND]):
    """Brings lost floating windows (which are out of reach) to the current workspace."""

    async def run_attract_lost(self) -> None:
        """Brings lost floating windows to the current workspace."""
        monitors = await self.backend.get_monitors()
        windows = await self.get_clients()
        lost = [win for win in windows if win["floating"] and not any(contains(mon, win) for mon in monitors)]
        focused = await self.get_focused_monitor_or_warn()
        if focused is None:
            return
        interval = focused["width"] / (1 + len(lost))
        interval_y = focused["height"] / (1 + len(lost))
        batch = []
        workspace: int = focused["activeWorkspace"]["id"]
        margin = interval // 2
        margin_y = interval_y // 2
        for i, window in enumerate(lost):
            pos_x = int(margin + focused["x"] + i * interval)
            pos_y = int(margin_y + focused["y"] + i * interval_y)
            batch.append(f"movetoworkspacesilent {workspace},pid:{window['pid']}")
            batch.append(f"movewindowpixel exact {pos_x} {pos_y},pid:{window['pid']}")
        await self.backend.execute(batch)
