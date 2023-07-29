from .interface import Plugin

from ..ipc import hyprctlJSON, hyprctl


class Extension(Plugin):
    monitors: list[str] = []

    async def init(self):
        self.monitors = [mon["name"] for mon in await hyprctlJSON("monitors")]

    async def run_shift_monitors(self, arg: str):
        """Swaps monitors' workspaces in the given direction"""
        direction: int = int(arg)
        if direction > 0:
            mon_list = self.monitors[:-1]
        else:
            mon_list = reversed(self.monitors[1:])

        for i, mon in enumerate(mon_list):
            await hyprctl(f"swapactiveworkspaces {mon} {self.monitors[i+direction]}")

    async def event_monitoradded(self, monitor):
        self.monitors.append(monitor.strip())

    async def event_monitorremoved(self, monitor):
        self.monitors.remove(monitor.strip())
