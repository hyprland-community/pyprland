" Moves unreachable client windows to the currently focused workspace"
from typing import Any, cast

from .interface import Plugin


def contains(monitor, window):
    "Tell if a window is visible in a monitor"
    if not (
        window["at"][0] > monitor["x"]
        and window["at"][0] < monitor["x"] + monitor["width"]
    ):
        return False
    if not (
        window["at"][1] > monitor["y"]
        and window["at"][1] < monitor["y"] + monitor["height"]
    ):
        return False
    return True


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    async def run_attract_lost(self):
        """Brings lost floating windows to the current workspace"""
        monitors = cast(list, await self.hyprctlJSON("monitors"))
        windows = cast(list, await self.hyprctlJSON("clients"))
        lost = [
            win
            for win in windows
            if win["floating"] and not any(contains(mon, win) for mon in monitors)
        ]
        focused: dict[str, Any] = [mon for mon in monitors if mon["focused"]][0]
        interval = focused["width"] / (1 + len(lost))
        interval_y = focused["height"] / (1 + len(lost))
        batch = []
        workspace: int = focused["activeWorkspace"]["id"]
        margin = interval // 2
        margin_y = interval_y // 2
        for i, window in enumerate(lost):
            pos_x = int(margin + focused["x"] + i * interval)
            pos_y = {int(margin_y + focused["y"] + i * interval_y)}
            batch.append(f'movetoworkspacesilent {workspace},pid:{window["pid"]}')
            batch.append(f'movewindowpixel exact {pos_x} {pos_y},pid:{window["pid"]}')
        await self.hyprctl(batch)
