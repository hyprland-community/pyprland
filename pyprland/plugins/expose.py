""" expose Brings every client window to screen for selection
"""

from .interface import Plugin
from ..common import state, CastBoolMixin


class Extension(CastBoolMixin, Plugin):  # pylint: disable=missing-class-docstring
    exposed_clients_list: list[dict] = []

    @property
    def exposed_clients(self):
        "Returns the list of clients currently using exposed mode"
        if self.cast_bool(self.config.get("include_special"), False):
            return self.exposed_clients_list
        return [c for c in self.exposed_clients_list if c["workspace"]["id"] > 0]

    async def move_clients_to_workspace(self, workspace, clients):
        """Move clients to a workspace"""
        return [
            f"movetoworkspacesilent {workspace},address:{client['address']}"
            for client in clients
        ]

    async def run_expose(self):
        """Expose every client on the active workspace.
        If expose is active restores everything and move to the focused window"""
        if self.exposed_clients_list:
            commands = self.move_clients_to_workspace(
                state.active_workspace, self.exposed_clients
            )
            commands.extend(
                [
                    "togglespecialworkspace exposed",
                    f"focuswindow address:{state.active_window}",
                ]
            )
            await self.hyprctl(commands)
            self.exposed_clients_list = []
        else:
            self.exposed_clients_list = await self.get_clients(
                workspace_bl=state.active_workspace
            )
            commands = self.move_clients_to_workspace(
                "special:exposed", self.exposed_clients
            )
            commands.append("togglespecialworkspace exposed")
            await self.hyprctl(commands)
