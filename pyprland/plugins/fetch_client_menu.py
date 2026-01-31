"""Select a client window and move it to the active workspace."""

from typing import ClassVar

from ..adapters.menus import MenuMixin
from ..models import Environment, ReloadReason
from ..validation import ConfigField, ConfigItems
from .interface import Plugin


class Extension(MenuMixin, Plugin):
    """Shows a menu to select and fetch a window to your active workspace."""

    environments: ClassVar[list[Environment]] = [Environment.HYPRLAND]

    config_schema = ConfigItems(
        *MenuMixin.menu_config_schema,
        ConfigField("separator", str, default="|", description="Separator between window number and title", category="appearance"),
    )

    _windows_origins: dict[str, str]

    async def on_reload(self, reason: ReloadReason = ReloadReason.RELOAD) -> None:
        """Initialize windows origins dict on reload."""
        _ = reason  # unused
        self._windows_origins = {}

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
