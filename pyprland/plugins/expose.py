"""expose Brings every client window to screen for selection."""

from ..models import ClientInfo, Environment, ReloadReason
from ..validation import ConfigField, ConfigItems
from .interface import Plugin


class Extension(Plugin, environments=[Environment.HYPRLAND]):
    """Exposes all windows for a quick 'jump to' feature."""

    config_schema = ConfigItems(
        ConfigField("include_special", bool, default=False, description="Include windows from special workspaces", category="basic"),
    )

    exposed: list[ClientInfo]

    async def on_reload(self, reason: ReloadReason = ReloadReason.RELOAD) -> None:
        """Initialize exposed list on reload."""
        _ = reason  # unused
        self.exposed = []

    @property
    def exposed_clients(self) -> list[ClientInfo]:
        """Returns the list of clients currently using exposed mode."""
        if self.get_config_bool("include_special"):
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
            await self.backend.execute(commands)
            self.exposed = []
        else:
            self.exposed = await self.get_clients(workspace_bl=self.state.active_workspace)
            commands = []
            for client in self.exposed_clients:
                commands.append(f"movetoworkspacesilent special:exposed,address:{client['address']}")
            commands.append("togglespecialworkspace exposed")
            await self.backend.execute(commands)
