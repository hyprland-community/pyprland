"""Fallback backend base class for limited functionality environments."""

import asyncio
from abc import abstractmethod
from collections.abc import Callable
from logging import Logger
from typing import Any

from ..constants import DEFAULT_NOTIFICATION_DURATION_MS, DEFAULT_REFRESH_RATE_HZ
from ..models import ClientInfo, MonitorInfo
from .backend import EnvironmentBackend


def make_monitor_info(  # noqa: PLR0913  # pylint: disable=too-many-arguments,too-many-positional-arguments
    index: int,
    name: str,
    width: int,
    height: int,
    pos_x: int = 0,
    pos_y: int = 0,
    scale: float = 1.0,
    transform: int = 0,
    refresh_rate: float = DEFAULT_REFRESH_RATE_HZ,
    enabled: bool = True,
    description: str = "",
) -> MonitorInfo:
    """Create a MonitorInfo dict with default values for fallback backends.

    Args:
        index: Monitor index
        name: Monitor name (e.g., "DP-1")
        width: Monitor width in pixels
        height: Monitor height in pixels
        pos_x: X position
        pos_y: Y position
        scale: Scale factor
        transform: Transform value (0-7)
        refresh_rate: Refresh rate in Hz
        enabled: Whether the monitor is enabled
        description: Monitor description

    Returns:
        MonitorInfo dict with all required fields
    """
    return MonitorInfo(
        id=index,
        name=name,
        description=description or name,
        make="",
        model="",
        serial="",
        width=width,
        height=height,
        refreshRate=refresh_rate,
        x=pos_x,
        y=pos_y,
        activeWorkspace={"id": 0, "name": ""},
        specialWorkspace={"id": 0, "name": ""},
        reserved=[0, 0, 0, 0],
        scale=scale,
        transform=transform,
        focused=index == 0,
        dpmsStatus=enabled,
        vrr=False,
        activelyTearing=False,
        disabled=not enabled,
        currentFormat="",
        availableModes=[],
        to_disable=False,
    )


class FallbackBackend(EnvironmentBackend):
    """Base class for fallback backends (X11, generic Wayland).

    Provides minimal functionality - only get_monitors() is implemented
    by subclasses. Other methods are stubs that log warnings or no-op.

    These backends provide monitor information for plugins like wallpapers
    but do not support compositor-specific features like window management
    or event handling.
    """

    async def get_clients(
        self,
        mapped: bool = True,
        workspace: str | None = None,
        workspace_bl: str | None = None,
        *,
        log: Logger,
    ) -> list[ClientInfo]:
        """Not supported in fallback mode.

        Args:
            mapped: Ignored
            workspace: Ignored
            workspace_bl: Ignored
            log: Logger to use for this operation

        Returns:
            Empty list
        """
        log.debug("get_clients() not supported in fallback backend")
        return []

    def parse_event(self, raw_data: str, *, log: Logger) -> tuple[str, Any] | None:
        """No event support in fallback mode.

        Args:
            raw_data: Ignored
            log: Logger to use for this operation

        Returns:
            None (no events)
        """
        return None

    async def execute(self, command: str | list | dict, *, log: Logger, **kwargs: Any) -> bool:
        """Not supported in fallback mode.

        Args:
            command: Ignored
            log: Logger to use for this operation
            **kwargs: Ignored

        Returns:
            False (command not executed)
        """
        log.debug("execute() not supported in fallback backend")
        return False

    async def execute_batch(self, commands: list[str], *, log: Logger) -> None:
        """Not supported in fallback mode.

        Args:
            commands: Ignored
            log: Logger to use for this operation
        """
        log.debug("execute_batch() not supported in fallback backend")

    async def execute_json(self, command: str, *, log: Logger, **kwargs: Any) -> Any:
        """Not supported in fallback mode.

        Args:
            command: Ignored
            log: Logger to use for this operation
            **kwargs: Ignored

        Returns:
            Empty dict
        """
        log.debug("execute_json() not supported in fallback backend")
        return {}

    async def notify(
        self,
        message: str,
        duration: int = DEFAULT_NOTIFICATION_DURATION_MS,
        color: str = "ff0000",
        *,
        log: Logger,
    ) -> None:
        """Send notification via notify-send.

        Args:
            message: The notification message
            duration: Duration in milliseconds
            color: Ignored (notify-send doesn't support colors)
            log: Logger to use for this operation
        """
        log.info("Notification: %s", message)
        try:
            # Convert duration from ms to ms (notify-send uses ms)
            proc = await asyncio.create_subprocess_shell(
                f'notify-send -t {duration} "Pyprland" "{message}"',
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            await proc.wait()
        except OSError as e:
            log.debug("notify-send failed: %s", e)

    @classmethod
    @abstractmethod
    async def is_available(cls) -> bool:
        """Check if this backend's required tool is available.

        Subclasses must implement this to check for their required
        tool (e.g., xrandr, wlr-randr).

        Returns:
            True if the backend can be used
        """

    @classmethod
    async def _check_command(cls, command: str) -> bool:
        """Check if a command is available and works.

        Args:
            command: The command to test

        Returns:
            True if command executed successfully
        """
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.DEVNULL,
                stderr=asyncio.subprocess.DEVNULL,
            )
            return await proc.wait() == 0
        except OSError:
            return False

    async def _run_monitor_command(
        self,
        command: str,
        tool_name: str,
        parser: Callable[[str, bool, Logger], list[MonitorInfo]],
        *,
        include_disabled: bool,
        log: Logger,
    ) -> list[MonitorInfo]:
        """Run a command and parse its output for monitor information.

        This is a shared helper for wayland/xorg backends to reduce duplication.

        Args:
            command: Shell command to execute
            tool_name: Name of the tool for error messages
            parser: Function to parse the command output
            include_disabled: Whether to include disabled monitors
            log: Logger instance

        Returns:
            List of MonitorInfo dicts, empty on failure
        """
        try:
            proc = await asyncio.create_subprocess_shell(
                command,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )
            stdout, stderr = await proc.communicate()

            if proc.returncode != 0:
                log.error("%s failed: %s", tool_name, stderr.decode())
                return []

            return parser(stdout.decode(), include_disabled, log)

        except OSError as e:
            log.warning("Failed to get monitors from %s: %s", tool_name, e)
            return []
