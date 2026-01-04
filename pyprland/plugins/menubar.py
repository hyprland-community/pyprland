"""Run a bar."""

import asyncio
import contextlib
import os
from collections.abc import Callable
from time import time
from typing import Any, cast

from ..common import apply_variables, state
from .interface import Plugin

COOLDOWN_TIME = 60
IDLE_LOOP_INTERVAL = 10


def get_pid_from_layers(layers: dict) -> bool | int:
    """Get the PID of the bar from the layers."""
    for screen in layers:
        for layer in layers[screen]["levels"].values():
            for instance in layer:
                if instance["namespace"].startswith("bar-"):
                    return instance["pid"] > 0 and cast("int", instance["pid"])
    return False


async def is_bar_alive(pid: int, hyprctl_json: Callable[..., Any]) -> int | bool:
    """Check if the bar is running."""
    is_running = os.path.exists(f"/proc/{pid}")
    if is_running:
        print("found running", pid)
        return pid
    layers = await hyprctl_json("layers")
    pid = get_pid_from_layers(layers)
    if pid:
        print("found layer", pid)
        return pid
    return False


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
            pid = 0
            while True:
                if pid:
                    pid = await is_bar_alive(pid, self.hyprctl_json)
                    if pid:
                        await asyncio.sleep(IDLE_LOOP_INTERVAL)
                        continue

                await self.set_best_monitor()
                cmd = apply_variables(
                    self.config.get("command", "gBar bar [monitor]"),
                    {"monitor": self.cur_monitor if self.cur_monitor else ""},
                )
                start_time = time()
                self.proc = await asyncio.create_subprocess_shell(cmd)
                pid = self.proc.pid
                await self.proc.wait()

                now = time()

                elapsed_time = now - start_time
                delay = 0 if elapsed_time >= COOLDOWN_TIME else int((COOLDOWN_TIME - elapsed_time) / 2)
                text = f"Menu Bar crashed, restarting in {delay}s." if delay > 0 else "Menu Bar crashed, restarting immediately."
                self.log.warning(text)
                if delay:
                    await self.notify_info(text)
                await asyncio.sleep(delay or 0.1)

        self.ongoing_task = asyncio.create_task(_run_loop())

    async def run_bar(self, args: str) -> None:
        """<restart|stop> Start (default), restart or stop gBar."""
        self.kill()
        if not args.startswith("stop"):
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
