from .interface import Plugin

from ..ipc import hyprctlJSON, hyprctl


def contains(monitor, window):
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


class Extension(Plugin):
    async def run_attract_lost(self, *args):
        """Brings lost floating windows to the current workspace"""
        monitors = await hyprctlJSON("monitors")
        windows = await hyprctlJSON("clients")
        lost = [
            win
            for win in windows
            if win["floating"] and not any(contains(mon, win) for mon in monitors)
        ]
        focused = [mon for mon in monitors if mon["focused"]][0]
        interval = focused["width"] / (1 + len(lost))
        intervalY = focused["height"] / (1 + len(lost))
        batch = []
        workspace: int = focused["activeWorkspace"]["id"]
        margin = interval // 2
        marginY = intervalY // 2
        for i, window in enumerate(lost):
            batch.append(f'movetoworkspacesilent {workspace},pid:{window["pid"]}')
            batch.append(
                f'movewindowpixel exact {int(margin + focused["x"] + i*interval)} {int(marginY + focused["y"] + i*intervalY)},pid:{window["pid"]}'
            )
        await hyprctl(batch)
