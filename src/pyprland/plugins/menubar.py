"""Run a bar."""

import contextlib
from pathlib import Path
from time import time
from typing import TYPE_CHECKING, cast

from ..aioops import TaskManager
from ..common import apply_variables
from ..models import Environment, ReloadReason
from ..process import ManagedProcess
from ..validation import ConfigField, ConfigItems
from .interface import Plugin

if TYPE_CHECKING:
    from ..adapters.proxy import BackendProxy

CRASH_COOLDOWN = 120  # seconds - crashes within this trigger backoff
MAX_BACKOFF_DELAY = 60  # cap at 60 seconds
BASE_DELAY = 2  # base for exponential calculation
IDLE_LOOP_INTERVAL = 10


def get_pid_from_layers_hyprland(layers: dict) -> bool | int:
    """Get the PID of the bar from Hyprland layers.

    Args:
        layers: The layers dictionary from hyprctl

    Returns:
        PID if bar found with valid PID, False otherwise
    """
    for screen in layers:
        for layer in layers[screen]["levels"].values():
            for instance in layer:
                if instance["namespace"].startswith("bar-"):
                    pid = instance.get("pid", 0)
                    return pid if pid > 0 else False
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
    backend: "BackendProxy",
    environment: str,
) -> int | bool:
    """Check if the bar is running.

    Args:
        pid: The process ID
        backend: The environment backend
        environment: Current environment ("hyprland" or "niri")
    """
    # First check /proc - works for any spawned process
    is_running = Path(f"/proc/{pid}").exists()
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


class Extension(Plugin, environments=[Environment.HYPRLAND, Environment.NIRI]):
    """Improves multi-monitor handling of the status bar and restarts it on crashes."""

    config_schema = ConfigItems(
        ConfigField(
            "command",
            str,
            default="uwsm app -- ashell",
            description="Command to run the bar (supports [monitor] variable)",
            required=True,
            category="basic",
        ),
        ConfigField("monitors", list, default=[], description="Preferred monitors list in order of priority", category="basic"),
    )

    monitors: set[str]
    proc: ManagedProcess | None = None
    cur_monitor: str | None = ""
    _tasks: TaskManager
    _consecutive_quick_crashes: int = 0

    def __init__(self, name: str) -> None:
        """Initialize the plugin."""
        super().__init__(name)
        self._tasks = TaskManager()

    async def on_reload(self, reason: ReloadReason = ReloadReason.RELOAD) -> None:
        """Start the process."""
        _ = reason  # unused
        await self.stop()
        self._consecutive_quick_crashes = 0
        self._run_program()

    def _run_program(self) -> None:
        """Create ongoing task restarting gbar in case of crash."""
        self._tasks.start()

        async def _run_loop() -> None:
            pid: int | bool = 0
            while self._tasks.running:
                if pid:
                    pid = await is_bar_alive(pid if isinstance(pid, int) else 0, self.backend, self.state.environment)
                    if pid:
                        if await self._tasks.sleep(IDLE_LOOP_INTERVAL):
                            break
                        continue

                await self.set_best_monitor()
                command = self.get_config_str("command")
                cmd = apply_variables(
                    command,
                    {"monitor": self.cur_monitor or ""},
                )
                start_time = time()
                self.proc = ManagedProcess()
                await self.proc.start(cmd)
                pid = self.proc.pid or 0
                await self.proc.wait()

                now = time()
                elapsed_time = now - start_time

                if elapsed_time >= CRASH_COOLDOWN:
                    # Stable run (2+ min) - reset counter, restart immediately
                    self._consecutive_quick_crashes = 0
                    delay = 0
                else:
                    # Crash within 2 min - apply backoff
                    self._consecutive_quick_crashes += 1
                    if self._consecutive_quick_crashes == 1:
                        delay = 0  # first crash: immediate
                    else:
                        # 2nd: 2s, 3rd: 4s, 4th: 8s, 5th: 16s, 6th: 32s, 7th+: 60s
                        delay = min(BASE_DELAY * (2 ** (self._consecutive_quick_crashes - 2)), MAX_BACKOFF_DELAY)

                text = f"Menu Bar crashed, restarting in {delay}s." if delay > 0 else "Menu Bar crashed, restarting immediately."
                self.log.warning(text)
                if delay:
                    await self.backend.notify_info(text)
                if await self._tasks.sleep(delay or 0.1):
                    break

        self._tasks.create(_run_loop())

    def is_running(self) -> bool:
        """Check if the bar is currently running."""
        return self.proc is not None and self._tasks.running

    async def run_bar(self, args: str) -> None:
        """[restart|stop|toggle] Start (default), restart, stop or toggle the menu bar.

        Args:
            args: The action to perform
                - (empty): Start the bar
                - restart: Stop and restart the bar
                - stop: Stop the bar
                - toggle: Toggle the bar on/off
        """
        if args.startswith("toggle"):
            if self.is_running():
                await self.stop()
            else:
                await self.on_reload()
            return

        await self.stop()
        if not args.startswith("stop"):
            await self.on_reload()

    async def set_best_monitor(self) -> None:
        """Set the best monitor to use in `cur_monitor`."""
        self.cur_monitor = await self.get_best_monitor()
        if not self.cur_monitor:
            if not self.state.active_monitors:
                self.log.error("No monitors available for bar")
                return
            self.cur_monitor = self.state.active_monitors[0]
            await self.backend.notify_info(f"menubar: No preferred monitor found, using {self.cur_monitor}")

    async def get_best_monitor(self) -> str:
        """Get best monitor according to preferred list."""
        preferred_monitors = self.get_config_list("monitors")

        if self.state.environment == Environment.NIRI:
            # Niri: outputs is a dict, enabled outputs have current_mode set
            outputs = await self.backend.execute_json("outputs")
            names = [name for name, data in outputs.items() if data.get("current_mode") is not None]
        else:
            # Hyprland
            monitors = await self.backend.get_monitors()
            names = [m["name"] for m in monitors if m.get("currentFormat") != "Invalid"]

        for monitor in preferred_monitors:
            if monitor in names:
                return cast("str", monitor)
        return ""

    async def event_monitoradded(self, monitor: str) -> None:
        """Switch bar in case the monitor is preferred.

        Args:
            monitor: The monitor name
        """
        if self.cur_monitor:
            preferred = self.get_config_list("monitors")
            cur_idx = preferred.index(self.cur_monitor) if self.cur_monitor else 999
            if monitor not in preferred:
                return
            new_idx = preferred.index(monitor)
            if 0 <= new_idx < cur_idx:
                await self.stop()
                await self.on_reload()

    async def niri_outputschanged(self, _data: dict) -> None:
        """Handle Niri output changes.

        Args:
            _data: Event data from Niri (unused)
        """
        if not self.cur_monitor:
            return

        preferred = self.get_config_list("monitors")
        cur_idx = preferred.index(self.cur_monitor) if self.cur_monitor in preferred else 999

        # Check if a more preferred monitor appeared
        try:
            outputs = await self.backend.execute_json("outputs")
            for name in outputs:
                if name in preferred:
                    new_idx = preferred.index(name)
                    if 0 <= new_idx < cur_idx:
                        # A more preferred monitor appeared
                        await self.stop()
                        await self.on_reload()
                        return
        except (OSError, RuntimeError) as e:
            self.log.warning("Error checking outputs: %s", e)

    async def exit(self) -> None:
        """Stop the process."""
        await self.stop()

    async def stop(self) -> None:
        """Stop the process and supervision task."""
        await self._tasks.stop()
        if self.proc:
            await self.proc.stop()
            self.proc = None
