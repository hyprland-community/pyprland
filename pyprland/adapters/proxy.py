"""Backend proxy that injects plugin logger into all calls.

This module provides a BackendProxy class that wraps an EnvironmentBackend
and automatically passes the plugin's logger to all backend method calls.
This allows backend operations to be logged under the calling plugin's
logger for better traceability.
"""

from collections.abc import Callable
from logging import Logger
from typing import TYPE_CHECKING, Any

from ..models import ClientInfo, MonitorInfo

if TYPE_CHECKING:
    from .backend import EnvironmentBackend


class BackendProxy:
    """Proxy that injects the plugin logger into all backend calls.

    This allows backend operations to be logged under the calling plugin's
    logger for better traceability. Each plugin gets its own BackendProxy
    instance with its own logger, while sharing the underlying backend.

    Attributes:
        log: The logger to use for all backend operations
        state: Reference to the shared state (from the underlying backend)
    """

    def __init__(self, backend: "EnvironmentBackend", log: Logger) -> None:
        """Initialize the proxy.

        Args:
            backend: The underlying backend to delegate calls to
            log: The logger to inject into all backend calls
        """
        self._backend = backend
        self.log = log
        self.state = backend.state

    # === Core execution methods ===

    async def execute(self, command: str | list | dict, **kwargs: Any) -> bool:  # noqa: ANN401
        """Execute a command (or list of commands).

        Args:
            command: The command to execute
            **kwargs: Additional arguments (base_command, weak, etc.)

        Returns:
            True if command succeeded
        """
        return await self._backend.execute(command, log=self.log, **kwargs)

    async def execute_json(self, command: str, **kwargs: Any) -> Any:  # noqa: ANN401
        """Execute a command and return the JSON result.

        Args:
            command: The command to execute
            **kwargs: Additional arguments

        Returns:
            The JSON response
        """
        return await self._backend.execute_json(command, log=self.log, **kwargs)

    async def execute_batch(self, commands: list[str]) -> None:
        """Execute a batch of commands.

        Args:
            commands: List of commands to execute
        """
        return await self._backend.execute_batch(commands, log=self.log)

    # === Query methods ===

    async def get_clients(
        self,
        mapped: bool = True,
        workspace: str | None = None,
        workspace_bl: str | None = None,
    ) -> list[ClientInfo]:
        """Return the list of clients, optionally filtered.

        Args:
            mapped: If True, only return mapped clients
            workspace: Filter to this workspace name
            workspace_bl: Blacklist this workspace name

        Returns:
            List of matching clients
        """
        return await self._backend.get_clients(mapped, workspace, workspace_bl, log=self.log)

    async def get_monitors(self, include_disabled: bool = False) -> list[MonitorInfo]:
        """Return the list of monitors.

        Args:
            include_disabled: If True, include disabled monitors

        Returns:
            List of monitors
        """
        return await self._backend.get_monitors(log=self.log, include_disabled=include_disabled)

    async def get_monitor_props(
        self,
        name: str | None = None,
        include_disabled: bool = False,
    ) -> MonitorInfo:
        """Return focused monitor data if name is not defined, else use monitor's name.

        Args:
            name: Monitor name to look for, or None for focused monitor
            include_disabled: If True, include disabled monitors in search

        Returns:
            Monitor info dict
        """
        return await self._backend.get_monitor_props(name, include_disabled, log=self.log)

    async def get_client_props(
        self,
        match_fn: Callable[[Any, Any], bool] | None = None,
        clients: list[ClientInfo] | None = None,
        **kw: Any,  # noqa: ANN401
    ) -> ClientInfo | None:
        """Return the properties of a client matching the given criteria.

        Args:
            match_fn: Custom match function (defaults to equality)
            clients: Optional pre-fetched client list
            **kw: Property to match (addr, cls, etc.)

        Returns:
            Matching client info or None
        """
        return await self._backend.get_client_props(match_fn, clients, log=self.log, **kw)

    # === Notification methods ===

    async def notify(self, message: str, duration: int = 5000, color: str = "ff0000") -> None:
        """Send a notification.

        Args:
            message: The notification message
            duration: Duration in milliseconds
            color: Hex color code
        """
        return await self._backend.notify(message, duration, color, log=self.log)

    async def notify_info(self, message: str, duration: int = 5000) -> None:
        """Send an info notification (blue color).

        Args:
            message: The notification message
            duration: Duration in milliseconds
        """
        return await self._backend.notify_info(message, duration, log=self.log)

    async def notify_error(self, message: str, duration: int = 5000) -> None:
        """Send an error notification (red color).

        Args:
            message: The notification message
            duration: Duration in milliseconds
        """
        return await self._backend.notify_error(message, duration, log=self.log)

    # === Window operation helpers ===

    async def focus_window(self, address: str) -> bool:
        """Focus a window by address.

        Args:
            address: Window address (without 'address:' prefix)

        Returns:
            True if command succeeded
        """
        return await self._backend.focus_window(address, log=self.log)

    async def move_window_to_workspace(
        self,
        address: str,
        workspace: str,
        *,
        silent: bool = True,
    ) -> bool:
        """Move a window to a workspace.

        Args:
            address: Window address (without 'address:' prefix)
            workspace: Target workspace name or ID
            silent: If True, don't follow the window

        Returns:
            True if command succeeded
        """
        return await self._backend.move_window_to_workspace(address, workspace, silent=silent, log=self.log)

    async def pin_window(self, address: str) -> bool:
        """Toggle pin state of a window.

        Args:
            address: Window address (without 'address:' prefix)

        Returns:
            True if command succeeded
        """
        return await self._backend.pin_window(address, log=self.log)

    async def close_window(self, address: str) -> bool:
        """Close a window.

        Args:
            address: Window address (without 'address:' prefix)

        Returns:
            True if command succeeded
        """
        return await self._backend.close_window(address, log=self.log)

    async def resize_window(self, address: str, width: int, height: int) -> bool:
        """Resize a window to exact pixel dimensions.

        Args:
            address: Window address (without 'address:' prefix)
            width: Target width in pixels
            height: Target height in pixels

        Returns:
            True if command succeeded
        """
        return await self._backend.resize_window(address, width, height, log=self.log)

    async def move_window(self, address: str, x: int, y: int) -> bool:  # pylint: disable=invalid-name
        """Move a window to exact pixel position.

        Args:
            address: Window address (without 'address:' prefix)
            x: Target x position in pixels
            y: Target y position in pixels

        Returns:
            True if command succeeded
        """
        return await self._backend.move_window(address, x, y, log=self.log)

    async def toggle_floating(self, address: str) -> bool:
        """Toggle floating state of a window.

        Args:
            address: Window address (without 'address:' prefix)

        Returns:
            True if command succeeded
        """
        return await self._backend.toggle_floating(address, log=self.log)

    async def set_keyword(self, keyword_command: str) -> bool:
        """Execute a keyword/config command.

        Args:
            keyword_command: The keyword command string

        Returns:
            True if command succeeded
        """
        return await self._backend.set_keyword(keyword_command, log=self.log)

    # === Event parsing ===

    def parse_event(self, raw_data: str) -> tuple[str, Any] | None:
        """Parse a raw event string into (event_name, event_data).

        Args:
            raw_data: Raw event string from the compositor

        Returns:
            Tuple of (event_name, event_data) or None if parsing failed
        """
        return self._backend.parse_event(raw_data, log=self.log)
