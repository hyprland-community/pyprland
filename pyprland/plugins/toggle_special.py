""" toggle_special allows having an "expose" like selection of windows in a special group
"""

from typing import cast

from .interface import Plugin
from ..common import state


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    async def run_toggle_special(self, special_workspace="minimized"):
        """[name] Toggles switching the focused window to the special workspace "name" (default: minimized)"""
        aw = cast(dict, await self.hyprctlJSON("activewindow"))
        wid = aw["workspace"]["id"]
        assert isinstance(wid, int)
        if wid < 1:  # special workspace: unminimize
            await self.hyprctl(
                [
                    f"togglespecialworkspace {special_workspace}",
                    f"movetoworkspacesilent {state.active_workspace},address:{aw['address']}",
                    f"focuswindow address:{aw['address']}",
                ]
            )
        else:
            await self.hyprctl(
                f"movetoworkspacesilent special:{special_workspace},address:{aw['address']}"
            )
