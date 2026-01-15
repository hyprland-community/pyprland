"""Select a client window and move it to the active workspace."""

from ..adapters.menus import MenuMixin
from .interface import Plugin


class Extension(MenuMixin, Plugin):
    """Shows a menu with shortcuts."""

    environments = ["hyprland"]

    _windows_origins: dict[str, str] = {}

    # Commands

    async def run_unfetch_client(self) -> None:
        """Return a window back to its origin."""
        addr = self.state.active_window
        try:
            origin = self._windows_origins[addr]
        except KeyError:
            await self.notify_error("unknown window origin")
        else:
            await self.hyprctl(f"movetoworkspacesilent {origin},address:{addr}")

    async def run_fetch_client_menu(self) -> None:
        """Select a client window and move it to the active workspace."""
        await self.ensure_menu_configured()

        clients = await self.get_clients(workspace_bl=self.state.active_workspace)

        separator = self.config.get("separator", "|")

        choice = await self.menu.run([f"{i + 1} {separator} {c['title']}" for i, c in enumerate(clients)])

        if choice:
            num = int(choice.split(None, 1)[0]) - 1
            addr = clients[num]["address"]
            self._windows_origins[addr] = clients[num]["workspace"]["name"]
            await self.hyprctl(f"movetoworkspace {self.state.active_workspace},address:{addr}")
