"""Hyprpaper integration for the wallpapers plugin."""

import asyncio
from typing import TYPE_CHECKING

from ...aioops import ailistdir, aiopen

if TYPE_CHECKING:
    import logging

    from ...adapters.proxy import BackendProxy

__all__ = ["HyprpaperManager"]


async def _is_hyprpaper_running() -> bool:
    """Check if hyprpaper process is running via /proc filesystem."""
    for pid in await ailistdir("/proc"):
        if pid.isdigit():
            try:
                async with aiopen(f"/proc/{pid}/comm") as f:
                    if (await f.read()).strip() == "hyprpaper":
                        return True
            except OSError:
                pass  # Process may have exited
    return False


class HyprpaperManager:
    """Manages hyprpaper lifecycle and command execution."""

    def __init__(self, log: "logging.Logger") -> None:
        """Initialize the manager.

        Args:
            log: Logger instance for logging messages.
        """
        self.log = log

    async def ensure_running(self) -> bool:
        """Ensure hyprpaper is running, starting it if necessary.

        Returns:
            True if hyprpaper is available, False if it couldn't be started.
        """
        if await _is_hyprpaper_running():
            return True

        self.log.info("Hyprpaper not running, starting it...")
        await asyncio.create_subprocess_exec(
            "hyprpaper",
            stdout=asyncio.subprocess.DEVNULL,
            stderr=asyncio.subprocess.DEVNULL,
        )

        # Wait for hyprpaper to start (up to 3 seconds)
        for _ in range(30):
            await asyncio.sleep(0.1)
            if await _is_hyprpaper_running():
                self.log.info("Hyprpaper started successfully")
                return True

        self.log.warning("Hyprpaper failed to start")
        return False

    async def set_wallpaper(self, commands: list[str], backend: "BackendProxy") -> bool:
        """Send wallpaper commands to hyprpaper via Hyprland.

        Args:
            commands: List of hyprpaper commands (e.g., ["wallpaper DP-1, /path/to/img"])
            backend: The environment backend for executing commands.

        Returns:
            True if successful, False otherwise.
        """
        if not await self.ensure_running():
            return False

        for cmd in commands:
            await backend.execute(["execr hyprctl hyprpaper " + cmd])

        return True

    async def stop(self) -> None:
        """Stop hyprpaper process."""
        proc = await asyncio.create_subprocess_shell("pkill hyprpaper")
        await proc.wait()
