" Run gbar on the first available display from a list of displays"

import asyncio

from .interface import Plugin
from ..common import state


class Extension(Plugin):
    "Manage gBar application"
    monitors: set[str]
    proc = None

    async def init(self):
        self.proc = None

    async def get_best_monitor(self):
        "get best monitor according to preferred list"
        preferred = self.config.get("monitors", [])
        for monitor in preferred:
            if monitor in state.monitors:
                return monitor
        first_mon = next(iter(state.monitors))
        await self.notify_info(f"gBar: No preferred monitor found, using {first_mon}")
        return first_mon

    async def on_reload(self):
        if not self.proc:
            cmd = f"gBar bar {await self.get_best_monitor()}"
            self.log.info("starting gBar: %s", cmd)
            self.proc = await asyncio.create_subprocess_shell(cmd)
