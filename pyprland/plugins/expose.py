"""expose Brings every client window to screen for selection."""

from ..models import ClientInfo
from .interface import Plugin


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    """Expose all clients on the active workspace."""

    environments = ["hyprland"]

    exposed: list[ClientInfo] = []

    @property
    def exposed_clients(self) -> list[ClientInfo]:
        """Returns the list of clients currently using exposed mode."""
        if self.config.get_bool("include_special", False):
            return self.exposed
        return [c for c in self.exposed if c["workspace"]["id"] > 0]

    async def run_expose(self) -> None:
        """Expose every client on the active workspace.

        If expose is active restores everything and move to the focused window
        """
        if self.exposed:
            commands = [
                f"movetoworkspacesilent {client['workspace']['name']},address:{client['address']}" for client in self.exposed_clients
            ]
            commands.extend(
                (
                    "togglespecialworkspace exposed",
                    f"focuswindow address:{self.state.active_window}",
                )
            )
            await self.hyprctl(commands)
            self.exposed = []
        else:
            self.exposed = await self.get_clients(workspace_bl=self.state.active_workspace)
            commands = []
            for client in self.exposed_clients:
                commands.append(f"movetoworkspacesilent special:exposed,address:{client['address']}")
            commands.append("togglespecialworkspace exposed")
            await self.hyprctl(commands)
