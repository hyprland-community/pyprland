"""Select a client window and move it to the active workspace."""

from ..adapters.menus import MenuMixin
from ..common import is_rotated
from ..models import Environment, ReloadReason
from ..validation import ConfigField, ConfigItems
from .interface import Plugin


class Extension(MenuMixin, Plugin, environments=[Environment.HYPRLAND]):
    """Shows a menu to select and fetch a window to your active workspace."""

    config_schema = ConfigItems(
        *MenuMixin.menu_config_schema,
        ConfigField("separator", str, default="|", description="Separator between window number and title", category="appearance"),
        ConfigField(
            "center_on_fetch", bool, default=True, description="Center the fetched window on the focused monitor", category="behavior"
        ),
        ConfigField(
            "margin", int, default=60, description="Margin from monitor edges in pixels when centering/resizing", category="behavior"
        ),
    )

    _windows_origins: dict[str, str]

    async def on_reload(self, reason: ReloadReason = ReloadReason.RELOAD) -> None:
        """Initialize windows origins dict on reload."""
        _ = reason  # unused
        self._windows_origins = {}

    async def _center_window_on_monitor(self, address: str) -> None:
        """Center a window on the focused monitor, resizing if needed.

        Forces the window to float, resizes if it exceeds monitor bounds
        (accounting for margin), and centers it on the focused monitor.
        Handles rotated monitors by swapping width/height.

        Args:
            address: The window address to center.
        """
        monitor = await self.get_focused_monitor_or_warn()
        if monitor is None:
            return

        # Get window properties
        client = await self.backend.get_client_props(addr=address)
        if client is None:
            self.log.warning("Could not get client properties for %s", address)
            return

        # Force float if not already floating
        if not client.get("floating", False):
            await self.backend.toggle_floating(address)
            # Re-fetch client props after floating (size might change)
            client = await self.backend.get_client_props(addr=address)
            if client is None:
                return

        margin = self.get_config_int("margin")

        # Get monitor dimensions, handling rotation
        mon_x = monitor["x"]
        mon_y = monitor["y"]
        mon_width = monitor["width"]
        mon_height = monitor["height"]
        scale = monitor.get("scale", 1.0)

        if is_rotated(monitor):
            mon_width, mon_height = mon_height, mon_width

        # Calculate available space (accounting for margin and scale)
        available_width = int(mon_width / scale) - 2 * margin
        available_height = int(mon_height / scale) - 2 * margin

        # Get window size
        win_size = client.get("size", [0, 0])
        win_width = win_size[0]
        win_height = win_size[1]

        # Resize if window is too large
        needs_resize = False
        new_width = win_width
        new_height = win_height

        if win_width > available_width:
            new_width = available_width
            needs_resize = True
        if win_height > available_height:
            new_height = available_height
            needs_resize = True

        if needs_resize:
            await self.backend.resize_window(address, new_width, new_height)
            win_width = new_width
            win_height = new_height

        # Calculate centered position
        center_x = int(mon_x / scale) + (int(mon_width / scale) - win_width) // 2
        center_y = int(mon_y / scale) + (int(mon_height / scale) - win_height) // 2

        await self.backend.move_window(address, center_x, center_y)

    # Commands

    async def run_unfetch_client(self) -> None:
        """Return a window back to its origin."""
        addr = self.state.active_window
        try:
            origin = self._windows_origins[addr]
        except KeyError:
            await self.backend.notify_error("unknown window origin")
        else:
            await self.backend.move_window_to_workspace(addr, origin)

    async def run_fetch_client_menu(self) -> None:
        """Select a client window and move it to the active workspace."""
        await self.ensure_menu_configured()

        clients = await self.get_clients(workspace_bl=self.state.active_workspace)

        separator = self.get_config_str("separator")

        choice = await self.menu.run([f"{i + 1} {separator} {c['title']}" for i, c in enumerate(clients)])

        if choice:
            num = int(choice.split(None, 1)[0]) - 1
            addr = clients[num]["address"]
            self._windows_origins[addr] = clients[num]["workspace"]["name"]
            await self.backend.move_window_to_workspace(addr, self.state.active_workspace, silent=False)

            # Center the window on the focused monitor if configured
            if self.get_config_bool("center_on_fetch"):
                await self._center_window_on_monitor(addr)
