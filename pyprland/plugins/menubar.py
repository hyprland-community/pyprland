"""Run a bar."""

import asyncio
import contextlib
import os
from time import time
from typing import TYPE_CHECKING, cast

from ..common import apply_variables
from .interface import Plugin

if TYPE_CHECKING:
    from ..adapters.backend import EnvironmentBackend

COOLDOWN_TIME = 60
IDLE_LOOP_INTERVAL = 10


def get_pid_from_layers_hyprland(layers: dict) -> bool | int:
    """Get the PID of the bar from Hyprland layers.

    Args:
        layers: The layers dictionary from hyprctl
    """
    for screen in layers:
        for layer in layers[screen]["levels"].values():
            for instance in layer:
                if instance["namespace"].startswith("bar-"):
                    return instance["pid"] > 0 and cast("int", instance["pid"])
    return False


def is_bar_in_layers_niri(layers: list) -> bool:
    """Check if a bar exists in Niri layers.

    Args:
        layers: List of LayerSurface from Niri

    Note: Niri's LayerSurface doesn't include PID, so we can only
    detect presence, not recover the PID.
    """
    return any(layer.get("namespace", "").startswith("bar-") for layer in layers)


async def is_bar_alive(
    pid: int,
    backend: "EnvironmentBackend",
    environment: str,
) -> int | bool:
    """Check if the bar is running.

    Args:
        pid: The process ID
        backend: The environment backend
        environment: Current environment ("hyprland" or "niri")
    """
    # First check /proc - works for any spawned process
    is_running = os.path.exists(f"/proc/{pid}")
    if is_running:
        return pid

    # Try to detect via layers query
    if environment == "niri":
        with contextlib.suppress(OSError, AssertionError, KeyError):
            layers = await backend.execute_json("Layers")
            if is_bar_in_layers_niri(layers):
                # Bar exists but we lost PID tracking
                # Return True to prevent respawn
                return True
    else:
        # Hyprland
        with contextlib.suppress(OSError, AssertionError, KeyError):
            layers = await backend.execute_json("layers")
            found_pid = get_pid_from_layers_hyprland(layers)
            if found_pid:
                return found_pid

    return False


class Extension(Plugin):
    """Manage desktop bars application."""

    environments = ["hyprland", "niri"]

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
                    pid = await is_bar_alive(pid, self.backend, self.state.environment)
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

    def is_running(self) -> bool:
        """Check if the bar is currently running."""
        return self.proc is not None and self.ongoing_task is not None

    async def run_bar(self, args: str) -> None:
        """<restart|stop|toggle> Start (default), restart, stop or toggle gBar.

        Args:
            args: The command arguments
        """
        if args.startswith("toggle"):
            if self.is_running():
                self.kill()
            else:
                await self.on_reload()
            return

        self.kill()
        if not args.startswith("stop"):
            await self.on_reload()

    async def set_best_monitor(self) -> None:
        """Set the best monitor to use in `cur_monitor`."""
        self.cur_monitor = await self.get_best_monitor()
        if not self.cur_monitor:
            self.cur_monitor = next(iter(self.state.monitors))
            await self.notify_info(f"gBar: No preferred monitor found, using {self.cur_monitor}")

    async def get_best_monitor(self) -> str:
        """Get best monitor according to preferred list."""
        preferred: list[str] = self.config.get("monitors", [])

        if self.state.environment == "niri":
            # Niri: outputs is a dict, enabled outputs have current_mode set
            outputs = await self.backend.execute_json("outputs")
            names = [name for name, data in outputs.items() if data.get("current_mode") is not None]
        else:
            # Hyprland
            monitors = await self.backend.execute_json("monitors")
            names = [m["name"] for m in monitors if m.get("currentFormat") != "Invalid"]

        for monitor in preferred:
            if monitor in names:
                return monitor
        return ""

    async def event_monitoradded(self, monitor: str) -> None:
        """Switch bar in case the monitor is preferred.

        Args:
            monitor: The monitor name
        """
        if self.cur_monitor:
            preferred = self.config.get("monitors", [])
            cur_idx = preferred.index(self.cur_monitor) if self.cur_monitor else 999
            if monitor not in preferred:
                return
            new_idx = preferred.index(monitor)
            if 0 <= new_idx < cur_idx:
                self.kill()
                await self.on_reload()

    async def niri_outputschanged(self, _data: dict) -> None:
        """Handle Niri output changes.

        Args:
            _data: Event data from Niri (unused)
        """
        if not self.cur_monitor:
            return

        preferred = self.config.get("monitors", [])
        cur_idx = preferred.index(self.cur_monitor) if self.cur_monitor in preferred else 999

        # Check if a more preferred monitor appeared
        try:
            outputs = await self.backend.execute_json("outputs")
            for name in outputs:
                if name in preferred:
                    new_idx = preferred.index(name)
                    if 0 <= new_idx < cur_idx:
                        # A more preferred monitor appeared
                        self.kill()
                        await self.on_reload()
                        return
        except Exception:  # pylint: disable=broad-exception-caught
            self.log.exception("Error checking outputs")

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
