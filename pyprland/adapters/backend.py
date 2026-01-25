"""Backend adapter interface."""

from abc import ABC, abstractmethod
from collections.abc import Callable
from logging import Logger
from typing import Any

from ..common import MINIMUM_ADDR_LEN, SharedState
from ..models import ClientInfo, MonitorInfo


class EnvironmentBackend(ABC):
    """Abstract base class for environment backends (Hyprland, Niri, etc).

    All methods that perform logging require a `log` parameter to be passed.
    This allows the calling code (via BackendProxy) to inject the appropriate
    logger for traceability.
    """

    def __init__(self, state: SharedState) -> None:
        """Initialize the backend.

        Args:
            state: Shared state object
        """
        self.state = state

    @abstractmethod
    async def get_clients(
        self,
        mapped: bool = True,
        workspace: str | None = None,
        workspace_bl: str | None = None,
        *,
        log: Logger,
    ) -> list[ClientInfo]:
        """Return the list of clients, optionally filtered.

        Args:
            mapped: If True, only return mapped clients
            workspace: Filter to this workspace name
            workspace_bl: Blacklist this workspace name
            log: Logger to use for this operation
        """

    @abstractmethod
    async def get_monitors(self, *, log: Logger, include_disabled: bool = False) -> list[MonitorInfo]:
        """Return the list of monitors.

        Args:
            log: Logger to use for this operation
            include_disabled: If True, include disabled monitors (Hyprland only)
        """

    @abstractmethod
    def parse_event(self, raw_data: str, *, log: Logger) -> tuple[str, Any] | None:
        """Parse a raw event string into (event_name, event_data).

        Args:
            raw_data: Raw event string from the compositor
            log: Logger to use for this operation
        """

    async def get_monitor_props(
        self,
        name: str | None = None,
        include_disabled: bool = False,
        *,
        log: Logger,
    ) -> MonitorInfo:
        """Return focused monitor data if `name` is not defined, else use monitor's name.

        Args:
            name: Monitor name to look for, or None for focused monitor
            include_disabled: If True, include disabled monitors in search
            log: Logger to use for this operation
        """
        monitors = await self.get_monitors(log=log, include_disabled=include_disabled)
        if name:
            for mon in monitors:
                if mon["name"] == name:
                    return mon
        else:
            for mon in monitors:
                if mon.get("focused"):
                    return mon
        msg = "no focused monitor"
        raise RuntimeError(msg)

    @abstractmethod
    async def execute(self, command: str | list | dict, *, log: Logger, **kwargs: Any) -> bool:  # noqa: ANN401
        """Execute a command (or list of commands).

        Args:
            command: The command to execute
            log: Logger to use for this operation
            **kwargs: Additional arguments (base_command, weak, etc.)
        """

    @abstractmethod
    async def execute_json(self, command: str, *, log: Logger, **kwargs: Any) -> Any:  # noqa: ANN401
        """Execute a command and return the JSON result.

        Args:
            command: The command to execute
            log: Logger to use for this operation
            **kwargs: Additional arguments
        """

    @abstractmethod
    async def execute_batch(self, commands: list[str], *, log: Logger) -> None:
        """Execute a batch of commands.

        Args:
            commands: List of commands to execute
            log: Logger to use for this operation
        """

    @abstractmethod
    async def notify(self, message: str, duration: int, color: str, *, log: Logger) -> None:
        """Send a notification.

        Args:
            message: The notification message
            duration: Duration in milliseconds
            color: Hex color code
            log: Logger to use for this operation
        """

    async def notify_info(self, message: str, duration: int = 5000, *, log: Logger) -> None:
        """Send an info notification (default: blue color).

        Args:
            message: The notification message
            duration: Duration in milliseconds
            log: Logger to use for this operation
        """
        await self.notify(message, duration, "0000ff", log=log)

    async def notify_error(self, message: str, duration: int = 5000, *, log: Logger) -> None:
        """Send an error notification (default: red color).

        Args:
            message: The notification message
            duration: Duration in milliseconds
            log: Logger to use for this operation
        """
        await self.notify(message, duration, "ff0000", log=log)

    async def get_client_props(
        self,
        match_fn: Callable[[Any, Any], bool] | None = None,
        clients: list[ClientInfo] | None = None,
        *,
        log: Logger,
        **kw: Any,  # noqa: ANN401
    ) -> ClientInfo | None:
        """Return the properties of a client matching the given criteria.

        Args:
            match_fn: Custom match function (defaults to equality)
            clients: Optional pre-fetched client list
            log: Logger to use for this operation
            **kw: Property to match (addr, cls, etc.)
        """
        if match_fn is None:

            def default_match_fn(value1: Any, value2: Any) -> bool:  # noqa: ANN401
                return bool(value1 == value2)

            match_fn = default_match_fn

        assert kw

        addr = kw.get("addr")
        klass = kw.get("cls")

        if addr:
            assert len(addr) > MINIMUM_ADDR_LEN, "Client address is invalid"
            prop_name = "address"
            prop_value = addr
        elif klass:
            prop_name = "class"
            prop_value = klass
        else:
            prop_name, prop_value = next(iter(kw.items()))

        clients_list = clients or await self.get_clients(mapped=False, log=log)

        for client in clients_list:
            assert isinstance(client, dict)
            val = client.get(prop_name)
            if match_fn(val, prop_value):
                return client
        return None

    # ─── Window Operation Helpers ─────────────────────────────────────────────

    async def focus_window(self, address: str, *, log: Logger) -> bool:
        """Focus a window by address.

        Args:
            address: Window address (without 'address:' prefix)
            log: Logger to use for this operation

        Returns:
            True if command succeeded
        """
        return await self.execute(f"focuswindow address:{address}", log=log)

    async def move_window_to_workspace(
        self,
        address: str,
        workspace: str,
        *,
        silent: bool = True,
        log: Logger,
    ) -> bool:
        """Move a window to a workspace.

        Args:
            address: Window address (without 'address:' prefix)
            workspace: Target workspace name or ID
            silent: If True, don't follow the window (default: True)
            log: Logger to use for this operation

        Returns:
            True if command succeeded
        """
        cmd = "movetoworkspacesilent" if silent else "movetoworkspace"
        return await self.execute(f"{cmd} {workspace},address:{address}", log=log)

    async def pin_window(self, address: str, *, log: Logger) -> bool:
        """Toggle pin state of a window.

        Args:
            address: Window address (without 'address:' prefix)
            log: Logger to use for this operation

        Returns:
            True if command succeeded
        """
        return await self.execute(f"pin address:{address}", log=log)

    async def close_window(self, address: str, *, log: Logger) -> bool:
        """Close a window.

        Args:
            address: Window address (without 'address:' prefix)
            log: Logger to use for this operation

        Returns:
            True if command succeeded
        """
        return await self.execute(f"closewindow address:{address}", log=log)

    async def resize_window(self, address: str, width: int, height: int, *, log: Logger) -> bool:
        """Resize a window to exact pixel dimensions.

        Args:
            address: Window address (without 'address:' prefix)
            width: Target width in pixels
            height: Target height in pixels
            log: Logger to use for this operation

        Returns:
            True if command succeeded
        """
        return await self.execute(f"resizewindowpixel exact {width} {height},address:{address}", log=log)

    async def move_window(self, address: str, x: int, y: int, *, log: Logger) -> bool:  # pylint: disable=invalid-name
        """Move a window to exact pixel position.

        Args:
            address: Window address (without 'address:' prefix)
            x: Target x position in pixels
            y: Target y position in pixels
            log: Logger to use for this operation

        Returns:
            True if command succeeded
        """
        return await self.execute(f"movewindowpixel exact {x} {y},address:{address}", log=log)

    async def toggle_floating(self, address: str, *, log: Logger) -> bool:
        """Toggle floating state of a window.

        Args:
            address: Window address (without 'address:' prefix)
            log: Logger to use for this operation

        Returns:
            True if command succeeded
        """
        return await self.execute(f"togglefloating address:{address}", log=log)

    async def set_keyword(self, keyword_command: str, *, log: Logger) -> bool:
        """Execute a keyword/config command.

        Args:
            keyword_command: The keyword command string (e.g., "general:gaps_out 10")
            log: Logger to use for this operation

        Returns:
            True if command succeeded
        """
        return await self.execute(keyword_command, log=log, base_command="keyword")
