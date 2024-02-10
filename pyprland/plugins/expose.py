""" expose Brings every client window to screen for selection
"""

from .interface import Plugin
from ..common import state


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    exposed: list[dict] = []

    @property
    def exposed_clients(self):
        "Returns the list of clients currently using exposed mode"
        if self.config.get("include_special", False):
            return self.exposed
        return [c for c in self.exposed if c["workspace"]["id"] > 0]

    async def run_expose(self):
        """Expose every client on the active workspace.
        If expose is active restores everything and move to the focused window"""
        if self.exposed:
            commands = []
            for client in self.exposed_clients:
                commands.append(
                    f"movetoworkspacesilent {client['workspace']['id']},address:{client['address']}"
                )
            commands.extend(
                [
                    "togglespecialworkspace exposed",
                    f"focuswindow address:{state.active_window}",
                ]
            )
            await self.hyprctl(commands)
            self.exposed = []
        else:
            self.exposed = await self.get_clients(workspace_bl=state.active_workspace)
            commands = []
            for client in self.exposed_clients:
                commands.append(
                    f"movetoworkspacesilent special:exposed,address:{client['address']}"
                )
            commands.append("togglespecialworkspace exposed")
            await self.hyprctl(commands)
