""" expose Brings every client window to screen for selection
toggle_minimized allows having an "expose" like selection of minimized windows
"""
from typing import Any
from .interface import Plugin

from ..ipc import hyprctlJSON, hyprctl


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    exposed = False

    async def run_toggle_minimized(self, special_workspace="minimized"):
        """[name] Toggles switching the focused window to the special workspace "name" (default: minimized)"""
        aw: dict[str, Any] = await hyprctlJSON("activewindow")
        wid = aw["workspace"]["id"]
        assert isinstance(wid, int)
        if wid < 1:  # special workspace: unminimize
            wrk = await hyprctlJSON("activeworkspace")
            await hyprctl(f"togglespecialworkspace {special_workspace}")
            await hyprctl(f"movetoworkspacesilent {wrk['id']},address:{aw['address']}")
            await hyprctl(f"focuswindow address:{aw['address']}")
        else:
            await hyprctl(
                f"movetoworkspacesilent special:{special_workspace},address:{aw['address']}"
            )

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
            aw: dict[str, Any] = await hyprctlJSON("activewindow")
            focused_addr = aw["address"]
            for client in self.exposed_clients:
                await hyprctl(
                    f"movetoworkspacesilent {client['workspace']['id']},address:{client['address']}"
                )
            await hyprctl("togglespecialworkspace exposed")
            await hyprctl(f"focuswindow address:{focused_addr}")
            self.exposed = False
        else:
            self.exposed = await hyprctlJSON("clients")
            for client in self.exposed_clients:
                await hyprctl(
                    f"movetoworkspacesilent special:exposed,address:{client['address']}"
                )
            await hyprctl("togglespecialworkspace exposed")
