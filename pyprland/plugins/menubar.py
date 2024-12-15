"""Run a bar."""

import asyncio
import contextlib
from time import time

from ..common import apply_variables, state
from .interface import Plugin


class Extension(Plugin):
    """Manage desktop bars application."""

    monitors: set[str]
    proc = None
    cur_monitor: str | None = ""

    ongoing_task: asyncio.Task | None = None

    async def on_reload(self) -> None:
        """Start the process."""
        self.kill()
        self._run_program()

    def _run_program(self) -> None:
        """Create ongoing task restarting gbar in case of crash."""
        if self.ongoing_task:
            self.ongoing_task.cancel()

        async def _run_loop() -> None:
            prev_time = time()
            while True:
                await self.set_best_monitor()
                cmd = apply_variables(self.config.get("command", "gBar bar [monitor]"), {"monitor": self.cur_monitor})
                now = time()
                self.proc = await asyncio.create_subprocess_shell(cmd)
                await self.proc.wait()
                delay = 60 - (now - prev_time)
                text = f"Menu Bar crashed, restarting in {delay // 2}s." if delay > 0 else "Menu Bar crashed, restarting."
                await self.notify_error(text)
                prev_time = now
                if delay > 0:
                    await asyncio.sleep(delay / 2)

        self.ongoing_task = asyncio.create_task(_run_loop())

    async def run_bar(self, args: str) -> None:
        """Start gBar on the first available monitor."""
        if args.startswith("re"):
            self.kill()
            await self.on_reload()

    async def set_best_monitor(self) -> None:
        """Set the best monitor to use in `cur_monitor`."""
        self.cur_monitor = await self.get_best_monitor()
        if not self.cur_monitor:
            self.cur_monitor = next(iter(state.monitors))
            await self.notify_info(f"gBar: No preferred monitor found, using {self.cur_monitor}")

    async def get_best_monitor(self) -> str:
        """Get best monitor according to preferred list."""
        preferred: list[str] = self.config.get("monitors", [])
        monitors = [m for m in await self.hyprctl_json("monitors") if m.get("currentFormat") != "Invalid"]
        names = [m["name"] for m in monitors]
        for monitor in preferred:
            if monitor in names:
                return monitor
        return ""

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
