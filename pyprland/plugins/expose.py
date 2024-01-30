""" expose Brings every client window to screen for selection
"""
from typing import Any, cast

from .interface import Plugin


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
            aw: dict[str, Any] = cast(dict, await self.hyprctlJSON("activewindow"))
            focused_addr = aw["address"]
            commands = []
            for client in self.exposed_clients:
                commands.append(
                    f"movetoworkspacesilent {client['workspace']['id']},address:{client['address']}"
                )
            commands.extend(
                [
                    "togglespecialworkspace exposed",
                    f"focuswindow address:{focused_addr}",
                ]
            )
            await self.hyprctl(commands)
            self.exposed = []
        else:
            self.exposed = cast(list, await self.hyprctlJSON("clients"))
            commands = []
            for client in self.exposed_clients:
                commands.append(
                    f"movetoworkspacesilent special:exposed,address:{client['address']}"
                )
            commands.append("togglespecialworkspace exposed")
            await self.hyprctl(commands)
