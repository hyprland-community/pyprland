"""Abstract base class defining the compositor backend interface.

EnvironmentBackend defines the contract for all compositor backends:
- Window operations (get_clients, focus, move, resize, close)
- Monitor queries (get_monitors, get_monitor_props)
- Command execution (execute, execute_batch, execute_json)
- Event parsing (parse_event)

Notifications are handled separately by the Notifier abstraction
(see adapters/notifier.py). Each backend provides its preferred
notifier via get_default_notifier().

All methods accept a 'log' parameter for traceability via BackendProxy.
"""

from abc import ABC, abstractmethod
from collections.abc import Callable, Iterable
from logging import Logger
from typing import Any

from ..common import MINIMUM_ADDR_LEN, SharedState
from ..models import ClientInfo, MonitorInfo
from .notifier import Notifier


class EnvironmentBackend(ABC):
    """Abstract base class for environment backends (Hyprland, Niri, etc).

    All methods that perform logging require a `log` parameter to be passed.
    This allows the calling code (via BackendProxy) to inject the appropriate
    logger for traceability.
    """

    address_prefix: str = "0x"
    """Prefix the compositor uses for window addresses.

    Hyprland omits it in its event stream, so plugins convert between the
    two forms; backends with unprefixed ids (Niri) set this to "".
    """

    minimum_address_length: int = MINIMUM_ADDR_LEN
    """Shortest plausible address, used to reject empty or truncated ones."""

    scratch_workspace_prefix: str = "special:S-"
    """Prefix for the workspaces scratchpads are parked on while hidden.

    Hyprland uses dedicated "special" workspaces; backends without that
    concept park windows on an ordinary workspace with this prefix.
    """

    scratch_workspaces_are_implicit: bool = True
    """Whether the compositor creates the parking workspace on demand.

    Niri only knows workspaces declared in its config and silently ignores
    moves to any other name, so those must be declared ahead of time.
    """

    supports_window_rules: bool = True
    """Whether rules can be declared at runtime for windows that don't exist yet.

    Niri has no runtime config mutation, so callers must apply the state
    reactively once the window appears, accepting a brief flash.
    """

    supports_offscreen_placement: bool = True
    """Whether a window can be parked outside the monitor's bounds.

    Niri clamps floating windows back onto the screen, so backends that
    clamp set this to False and place the window at its final position.
    """

    def scratch_workspace(self, uid: str) -> str:
        """Return the workspace name a scratchpad is parked on while hidden."""
        escaped = uid.replace(":", "_").replace("/", "_").replace(" ", "_")
        return f"{self.scratch_workspace_prefix}{escaped}"

    def is_hidden_workspace(self, name: str) -> bool:
        """Whether a workspace is one the user never sees directly.

        On Hyprland that covers every special workspace, not just the ones
        Pyprland owns. Used to avoid restoring focus onto it.
        """
        return name.startswith("special")

    def is_scratch_workspace(self, name: str) -> bool:
        """Whether a workspace is one Pyprland parks scratchpads on.

        Narrower than `is_hidden_workspace`: only Pyprland's own workspaces.
        """
        return name.startswith(self.scratch_workspace_prefix)

    async def missing_scratch_workspaces(self, uids: Iterable[str], *, log: Logger) -> list[str]:
        """Return the parking workspaces the compositor doesn't know about.

        Compositors that create them on demand never have any missing.
        """
        _ = uids, log
        return []

    def __init__(self, state: SharedState) -> None:
        """Initialize the backend.

        Args:
            state: Shared state object
        """
        self.state = state

    def short_address(self, address: str) -> str:
        """Return the address in its unprefixed form, as used by registry keys."""
        return address.removeprefix(self.address_prefix)

    def full_address(self, address: str) -> str:
        """Return the address in its prefixed form, as used by commands.

        Returns "" if the address is empty or implausibly short.
        """
        if not address or len(self.short_address(address)) < self.minimum_address_length:
            return ""
        return address if address.startswith(self.address_prefix) else self.address_prefix + address

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

    def parse_events(self, raw_data: str, *, log: Logger) -> list[tuple[str, Any]]:
        """Parse a raw event string into zero or more events.

        Most compositors emit one logical event per line, so the default
        wraps `parse_event`; backends that synthesise events (see
        NiriBackend) override this to emit several at once.
        """
        event = self.parse_event(raw_data, log=log)
        return [event] if event else []

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
    async def execute(self, command: str | list | dict, *, log: Logger, **kwargs: Any) -> bool:
        """Execute a command (or list of commands).

        Args:
            command: The command to execute
            log: Logger to use for this operation
            **kwargs: Additional arguments (base_command, weak, etc.)
        """

    @abstractmethod
    async def execute_json(self, command: str, *, log: Logger, **kwargs: Any) -> Any:
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
    def get_default_notifier(self) -> Notifier:
        """Return the default notifier for this backend.

        Each backend provides its preferred notification mechanism
        (e.g. Hyprland uses native IPC, Niri uses notify-send).
        This can be overridden by user config at the manager level.
        """

    async def get_client_props(
        self,
        match_fn: Callable[[Any, Any], bool] | None = None,
        clients: list[ClientInfo] | None = None,
        *,
        log: Logger,
        **kw: Any,
    ) -> ClientInfo | None:
        """Return the properties of a client matching the given criteria.

        Args:
            match_fn: Custom match function (defaults to equality)
            clients: Optional pre-fetched client list
            log: Logger to use for this operation
            **kw: Property to match (addr, cls, etc.)
        """
        if match_fn is None:

            def default_match_fn(value1: Any, value2: Any) -> bool:
                return bool(value1 == value2)

            match_fn = default_match_fn

        assert kw

        addr = kw.get("addr")
        klass = kw.get("cls")

        if addr:
            assert len(addr) >= self.minimum_address_length, "Client address is invalid"
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

    async def close_window(self, address: str, *, silent: bool = True, log: Logger) -> bool:
        """Close a window.

        Args:
            address: Window address (without 'address:' prefix)
            silent: Accepted for API consistency (currently unused for close)
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

    async def set_window_floating(self, address: str, floating: bool, *, log: Logger) -> bool:
        """Put a window in the floating or the tiled layout.

        Unlike `toggle_floating` this is idempotent, so callers that need a
        window to end up in a known state don't have to query it first.

        Args:
            address: Window address (without 'address:' prefix)
            floating: True to float the window, False to tile it
            log: Logger to use for this operation

        Returns:
            True if command succeeded
        """
        command = "setfloating" if floating else "settiled"
        return await self.execute(f"{command} address:{address}", log=log)

    async def set_keyword(self, keyword_command: str, *, log: Logger) -> bool:
        """Execute a keyword/config command.

        Args:
            keyword_command: The keyword command string (e.g., "general:gaps_out 10")
            log: Logger to use for this operation

        Returns:
            True if command succeeded
        """
        return await self.execute(keyword_command, log=log, base_command="keyword")

    # ─── Batch Window Operations ──────────────────────────────────────────────
    #
    # Scratchpad transitions move, stack and re-parent several windows at once.
    # Hyprland accepts these as batched command strings; other backends may need
    # one request per window, or may not support the operation at all.

    async def move_windows(self, placements: Iterable[tuple[str, int, int]], *, log: Logger) -> bool:
        """Move several windows to exact positions.

        Args:
            placements: (address, x, y) triples
            log: Logger to use for this operation

        Returns:
            True if the commands succeeded
        """
        return await self.execute([f"movewindowpixel exact {x} {y},address:{addr}" for addr, x, y in placements], log=log)

    async def move_windows_to_workspace(
        self,
        addresses: Iterable[str],
        workspace: str,
        *,
        silent: bool = True,
        log: Logger,
    ) -> bool:
        """Move several windows to a workspace.

        Args:
            addresses: Window addresses
            workspace: Target workspace name or ID
            silent: If True, don't follow the windows
            log: Logger to use for this operation

        Returns:
            True if the commands succeeded
        """
        cmd = "movetoworkspacesilent" if silent else "movetoworkspace"
        return await self.execute([f"{cmd} {workspace},address:{addr}" for addr in addresses], log=log)

    async def raise_windows(self, addresses: Iterable[str], *, log: Logger) -> bool:
        """Bring several windows to the top of the stacking order.

        Args:
            addresses: Window addresses
            log: Logger to use for this operation

        Returns:
            True if the commands succeeded
        """
        return await self.execute([f"alterzorder top,address:{addr}" for addr in addresses], log=log)

    async def set_window_animations(self, addresses: Iterable[str], enabled: bool, *, log: Logger) -> bool:
        """Enable or suppress the compositor's own animations for some windows.

        Used to hide the jump when a window is pre-positioned offscreen before
        a scratchpad slides it in.
        """
        sign = "-" if enabled else "+"
        return await self.execute([f"tagwindow {sign}pypr_noanim address:{addr}" for addr in addresses], log=log)

    async def move_workspace_to_monitor(self, workspace: str, monitor: str, *, log: Logger) -> bool:
        """Move a whole workspace to another monitor.

        Args:
            workspace: Workspace name or ID
            monitor: Target monitor name
            log: Logger to use for this operation

        Returns:
            True if command succeeded
        """
        return await self.execute(f"moveworkspacetomonitor {workspace} {monitor}", log=log)
