"""toggle_special allows having an "expose" like selection of windows in a special group."""

from typing import cast

from ..common import state
from .interface import Plugin


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    """Toggle switching the focused window to a special workspace."""

    async def run_toggle_special(self, special_workspace="minimized") -> None:
        """[name] Toggles switching the focused window to the special workspace "name" (default: minimized)."""
        aw = cast(dict, await self.hyprctl_json("activewindow"))
        wid = aw["workspace"]["id"]
        assert isinstance(wid, int)
        if wid < 1:  # special workspace
            await self.hyprctl(
                [
                    f"togglespecialworkspace {special_workspace}",
                    f"movetoworkspacesilent {state.active_workspace},address:{aw['address']}",
                    f"focuswindow address:{aw['address']}",
                ]
            )
        else:
            await self.hyprctl(f"movetoworkspacesilent special:{special_workspace},address:{aw['address']}")
