"""Run gbar on the first available display from a list of displays."""

import asyncio
import contextlib

from ..common import state
from .interface import Plugin


class Extension(Plugin):
    """Manage gBar application."""

    monitors: set[str]
    proc = None
    cur_monitor = ""

    ongoing_task: asyncio.Task | None = None

    def _run_gbar(self, cmd: str) -> None:
        """Create ongoing task restarting gbar in case of crash."""

        async def _run_loop() -> None:
            while True:
                self.proc = await asyncio.create_subprocess_shell(cmd)
                await self.proc.wait()
                self.notify_error("gBar crashed, restarting")

        if self.ongoing_task:
            self.ongoing_task.cancel()
        self.ongoing_task = asyncio.create_task(_run_loop())

    async def run_gbar(self, args: str) -> None:
        """Start gBar on the first available monitor."""
        if args.startswith("re"):
            self.kill()
            await self.on_reload()

    async def on_reload(self) -> None:
        """Initialize if not done."""
        if not self.proc:
            self.cur_monitor = await self.get_best_monitor()
            if not self.cur_monitor:
                first_mon = next(iter(state.monitors))
                await self.notify_info(f"gBar: No preferred monitor found, using {first_mon}")
                cmd = f"gBar bar {first_mon}"
            else:
                cmd = f"gBar bar {self.cur_monitor}"
            self.log.info("starting gBar: %s", cmd)
            self._run_gbar(cmd)

    async def get_best_monitor(self) -> str | None:
        """Get best monitor according to preferred list."""
        preferred = self.config.get("monitors", [])
        for monitor in preferred:
            if monitor in state.monitors:
                return monitor

    async def event_monitoradded(self, monitor: str) -> None:
        """Switch bar in case the monitor is preferred."""
        if self.cur_monitor:
            preferred = self.config.get("monitors", [])
            cur_idx = preferred.index(self.cur_monitor) if self.cur_monitor else 999
            new_idx = preferred.index(monitor)
            if 0 <= new_idx < cur_idx:
                self.kill()
                await self.on_reload()

    async def exit(self) -> None:
        """Kill the process."""
        self.kill()

    def kill(self) -> None:
        """Kill the process."""
        if self.proc:
            if self.ongoing_task:
                self.ongoing_task.cancel()
                self.ongoing_task = None
            with contextlib.suppress(ProcessLookupError):
                self.proc.kill()
            self.proc = None
