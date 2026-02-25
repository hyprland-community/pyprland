"""Implements a "Centered" layout.

- windows are normally tiled but one
- the active window is floating and centered
- you can cycle the active window, keeping the same layout type
- layout can be toggled any time
"""

from collections import defaultdict
from collections.abc import Callable
from functools import partial
from typing import Any, cast

from ..common import is_rotated
from ..constants import MIN_CLIENTS_FOR_LAYOUT
from ..models import ClientInfo, Environment, ReloadReason
from ..validation import ConfigField, ConfigItems
from .interface import Plugin


class Extension(Plugin, environments=[Environment.HYPRLAND]):
    """A workspace layout where one window is centered and maximized while others are in the background."""

    config_schema = ConfigItems(
        ConfigField("margin", int, default=60, description="Margin around the centered window in pixels", category="basic"),
        ConfigField(
            "offset", (str, list, tuple), default=[0, 0], description="Offset of the centered window as 'X Y' or [X, Y]", category="basic"
        ),
        ConfigField("style", list, default=[], description="Window rules to apply to the centered window", category="basic"),
        ConfigField("captive_focus", bool, default=False, description="Keep focus on the centered window", category="behavior"),
        ConfigField(
            "on_new_client",
            str,
            default="focus",
            choices=["focus", "background", "close"],
            description="Behavior when a new window opens",
            category="behavior",
        ),
        ConfigField("next", str, description="Command to run when 'next' is called and layout is disabled", category="commands"),
        ConfigField("prev", str, description="Command to run when 'prev' is called and layout is disabled", category="commands"),
        ConfigField("next2", str, description="Alternative command for 'next'", category="commands"),
        ConfigField("prev2", str, description="Alternative command for 'prev'", category="commands"),
    )

    workspace_info: dict[str, dict[str, Any]]
    last_index = 0
    command_handlers: dict[str, Callable]

    async def init(self) -> None:
        """Initialize the plugin."""
        self.workspace_info = defaultdict(lambda: {"enabled": False, "addr": ""})
        self.command_handlers = {
            "toggle": self._run_toggle,
            "next": partial(self._run_changefocus, 1, default_override="next"),
            "prev": partial(self._run_changefocus, -1, default_override="prev"),
            "next2": partial(self._run_changefocus, 1, default_override="next2"),
            "prev2": partial(self._run_changefocus, -1, default_override="prev2"),
        }

    # Events

    async def event_openwindow(self, windescr: str) -> None:
        """Re-set focus to main if a window is opened.

        Args:
            windescr: The window description
        """
        if not self.enabled:
            return
        win_addr = "0x" + windescr.split(",", 1)[0]

        behavior = self.get_config_str("on_new_client")
        new_client: ClientInfo | None = None
        clients = await self.get_clients()
        new_client_idx = 0
        for i, cli in enumerate(clients):
            if cli["address"] == win_addr:
                if cli["floating"]:
                    # Ignore floating windows
                    return
                new_client = cli
                new_client_idx = i
                break

        if new_client:
            self.last_index = new_client_idx
            if behavior == "background":
                # focus the main client
                await self.backend.focus_window(self.main_window_addr)
            elif behavior == "close":
                await self._run_toggle()
            else:  # foreground
                # make the new client the main window
                await self.unprepare_window(clients)
                self.main_window_addr = win_addr
                await self.prepare_window(clients)

    async def event_activewindowv2(self, _: str) -> None:
        """Keep track of focused client.

        Args:
            _: The window address (unused)
        """
        captive = self.get_config_bool("captive_focus")
        is_not_active = self.state.active_window != self.main_window_addr
        if captive and self.enabled and is_not_active:
            try:
                next(c for c in await self.get_clients() if c["address"] == self.state.active_window)
            except StopIteration:
                pass
            else:
                await self.backend.focus_window(self.main_window_addr)

    async def event_closewindow(self, addr: str) -> None:
        """Disable when the main window is closed.

        Args:
            addr: The window address
        """
        addr = "0x" + addr
        clients = [c for c in await self.get_clients() if c["address"] != addr]
        if self.enabled and await self._sanity_check(clients):
            closed_main = self.main_window_addr == addr
            if self.enabled and closed_main:
                self.log.debug("main window closed, focusing next")
                await self._run_changefocus(1)

    # Command

    async def run_layout_center(self, what: str) -> None:
        """<toggle|next|prev|next2|prev2> turn on/off or change the active window.

        Args:
            what: The action to perform
                - toggle: Enable/disable the centered layout
                - next/prev: Focus the next/previous window in the stack
                - next2/prev2: Alternative focus commands (configurable)
        """
        fn = self.command_handlers.get(what)
        if fn:
            await fn()
        else:
            await self.backend.notify_error(f"unknown layout_center command: {what}")

    async def on_reload(self, reason: ReloadReason = ReloadReason.RELOAD) -> None:
        """Loads the configuration and apply the tag style."""
        _ = reason  # unused
        if not self.get_config_list("style"):
            return
        await self.backend.execute("windowrule tag -layout_center", base_command="keyword")
        commands = [f"windowrule {rule}, match:tag layout_center" for rule in self.get_config_list("style")]
        if commands:
            await self.backend.execute(commands, base_command="keyword")

    # Utils

    async def get_clients(
        self,
        mapped: bool = True,
        workspace: str | None = None,
        workspace_bl: str | None = None,
    ) -> list[ClientInfo]:
        """Return the client list in the currently active workspace."""
        _ = workspace
        clients = await super().get_clients(mapped=mapped, workspace=self.state.active_workspace, workspace_bl=workspace_bl)
        clients.sort(key=lambda c: c["address"])
        return clients

    async def unprepare_window(self, clients: list[ClientInfo] | None = None) -> None:
        """Set the window as normal.

        Args:
            clients: The list of clients
        """
        if not clients:
            clients = await self.get_clients()
        addr = self.main_window_addr
        for cli in clients:
            if cli["address"] == addr and cli["floating"]:
                await self.backend.toggle_floating(addr)
                if self.get_config_list("style"):
                    await self.backend.execute(f"tagwindow -layout_center address:{addr}")
                break

    async def prepare_window(self, clients: list[ClientInfo] | None = None) -> None:
        """Set the window as centered.

        Args:
            clients: The list of clients
        """
        if not clients:
            clients = await self.get_clients()
        addr = self.main_window_addr
        for cli in clients:
            if cli["address"] == addr and not cli["floating"]:
                await self.backend.toggle_floating(addr)
                if self.get_config_list("style"):
                    await self.backend.execute(f"tagwindow +layout_center address:{addr}")
                break

        geometry = await self._calculate_centered_geometry(self.margin, self.offset)
        if geometry is None:
            return
        x, y, width, height = geometry

        await self.backend.resize_window(addr, width, height)
        await self.backend.move_window(addr, x, y)

    async def _calculate_centered_geometry(
        self, margin_conf: int | tuple[int, int], offset_conf: tuple[int, int]
    ) -> tuple[int, int, int, int] | None:
        """Calculate the geometry (x, y, width, height) for the centered window.

        Args:
            margin_conf: The margin configuration
            offset_conf: The offset configuration

        Returns:
            Tuple of (x, y, width, height) or None if no focused monitor found.
        """
        x, y = offset_conf
        margin: tuple[int, int] = (margin_conf, margin_conf) if isinstance(margin_conf, int) else margin_conf

        monitor = await self.get_focused_monitor_or_warn("centered geometry calculation")
        if monitor is None:
            return None

        scale = monitor["scale"]
        width = monitor["width"] - (2 * margin[0])
        height = monitor["height"] - (2 * margin[1])
        if is_rotated(monitor):
            width, height = height, width
        final_x = x + monitor["x"] + (margin[0] / scale)
        final_y = y + monitor["y"] + (margin[1] / scale)
        return int(final_x), int(final_y), int(width / scale), int(height / scale)

    # Subcommands

    async def _sanity_check(self, clients: list[ClientInfo] | None = None) -> bool:
        """Auto-disable if needed & return enabled status.

        Args:
            clients: The list of clients
        """
        clients = clients or await self.get_clients()
        if len(clients) < MIN_CLIENTS_FOR_LAYOUT:
            # If < 2 clients, disable the layout & stop
            self.log.info("disabling (clients starvation)")
            await self.unprepare_window()
            self.enabled = False
        return self.enabled

    async def _run_changefocus(self, direction: int, default_override: str | None = None) -> None:
        """Change the focus in the given direction (-1 or 1).

        Args:
            direction: The direction to change focus
            default_override: The default override command
        """
        if self.enabled:
            clients = [cli for cli in await self.get_clients() if not cli.get("floating") or cli["address"] == self.main_window_addr]
            if await self._sanity_check(clients):
                addresses = [c["address"] for c in clients]
                try:
                    idx = addresses.index(self.main_window_addr)
                except ValueError:
                    idx = self.last_index

                # Use modulo arithmetic for cyclic focus
                index = (idx + direction) % len(clients)

                new_client = clients[index]
                await self.unprepare_window(clients)
                self.main_window_addr = new_client["address"]
                await self.backend.focus_window(self.main_window_addr)
                self.last_index = index
                await self.prepare_window(clients)
        elif default_override:
            command = self.get_config(default_override)
            if command:
                await self.backend.execute(str(command))

    async def _run_toggle(self) -> None:
        """Toggle the center layout."""
        disabled = not self.enabled
        if disabled:
            self.main_window_addr = self.state.active_window
            await self.prepare_window()
        else:
            await self.unprepare_window()

        self.enabled = disabled

    # Properties

    @property
    def offset(self) -> tuple[int, int]:
        """Returns the centered window offset."""
        offset = self.get_config("offset")
        if isinstance(offset, str):
            x, y = (int(i) for i in offset.split() if i.strip())
            return (x, y)
        return cast("tuple[int, int]", offset)

    @property
    def margin(self) -> int:
        """Returns the margin of the centered window."""
        return self.get_config_int("margin")

    # enabled
    @property
    def enabled(self) -> bool:
        """Is center layout enabled on the active workspace ?."""
        return cast("bool", self.workspace_info[self.state.active_workspace]["enabled"])

    @enabled.setter
    def enabled(self, value: bool) -> None:
        """Set if center layout enabled on the active workspace."""
        self.workspace_info[self.state.active_workspace]["enabled"] = value

    # main_window_addr

    @property
    def main_window_addr(self) -> str:
        """Get active workspace's centered window address."""
        return cast("str", self.workspace_info[self.state.active_workspace]["addr"])

    @main_window_addr.setter
    def main_window_addr(self, value: str) -> None:
        """Set active workspace's centered window address."""
        self.workspace_info[self.state.active_workspace]["addr"] = value
