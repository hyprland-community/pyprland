" shift workspaces across monitors "
from typing import cast

from ..ipc import hyprctl, hyprctlJSON
from .interface import Plugin


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    monitors: list[str] = []

    async def init(self):
        self.monitors: list[str] = [
            mon["name"] for mon in cast(list[dict], await hyprctlJSON("monitors"))
        ]

    async def run_shift_monitors(self, arg: str):
        """<+1/-1> Swaps monitors' workspaces in the given direction"""
        direction: int = int(arg)
        if direction > 0:
            mon_list = self.monitors[:-1]
        else:
            mon_list = list(reversed(self.monitors[1:]))

        for i, mon in enumerate(mon_list):
            await hyprctl(f"swapactiveworkspaces {mon} {self.monitors[i+direction]}")

    async def event_monitoradded(self, monitor):
        "keep track of monitors"
        self.monitors.append(monitor)

    async def event_monitorremoved(self, monitor):
        "keep track of monitors"
        self.monitors.remove(monitor)
