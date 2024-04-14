" Run gbar on the first available display from a list of displays"

import asyncio

from .interface import Plugin
from ..common import state


class Extension(Plugin):
    "Manage gBar application"
    monitors: set[str]
    proc = None
    cur_monitor = ""

    async def run_gbar(self, args):
        "Starts gBar on the first available monitor"
        if args.startswith("re"):
            self.kill()
            await self.on_reload()

    async def on_reload(self):
        "Initializes if not done"
        if not self.proc:
            self.cur_monitor = await self.get_best_monitor()
            if not self.cur_monitor:
                first_mon = next(iter(state.monitors))
                await self.notify_info(
                    f"gBar: No preferred monitor found, using {first_mon}"
                )
                cmd = f"gBar bar {first_mon}"
            else:
                cmd = f"gBar bar {self.cur_monitor}"
            self.log.info("starting gBar: %s", cmd)
            self.proc = await asyncio.create_subprocess_shell(cmd)

    async def get_best_monitor(self):
        "get best monitor according to preferred list"
        preferred = self.config.get("monitors", [])
        for monitor in preferred:
            if monitor in state.monitors:
                return monitor

    async def event_monitoradded(self, monitor):
        "Switch bar in case the monitor is preferred"
        if self.cur_monitor:
            preferred = self.config.get("monitors", [])
            cur_idx = preferred.index(self.cur_monitor) if self.cur_monitor else 999
            new_idx = preferred.index(monitor)
            if 0 <= new_idx < cur_idx:
                self.kill()
                await self.on_reload()

    def kill(self):
        "Kill the process"
        if self.proc:
            self.proc.kill()
            self.proc = None
