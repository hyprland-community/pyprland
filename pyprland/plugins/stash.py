"""stash allows stashing and showing windows in named groups."""

from typing import cast

from ..models import Environment
from .interface import Plugin

STASH_PREFIX = "stash-"


class Extension(Plugin, environments=[Environment.HYPRLAND]):
    """Stash and show windows in named groups using special workspaces."""

    async def run_stash(self, name: str = "default") -> None:
        """[name] Toggle stashing the focused window (default stash: "default").

        Args:
            name: The stash group name
        """
        aw = cast("dict", await self.backend.execute_json("activewindow"))
        addr = aw.get("address", "")
        if not addr:
            return

        ws_name = aw["workspace"]["name"]

        if ws_name.startswith(f"special:{STASH_PREFIX}"):
            # Window is stashed → unstash it to current workspace
            stash_name = ws_name.removeprefix("special:")
            await self.backend.execute(
                [
                    f"togglespecialworkspace {stash_name}",
                    f"movetoworkspacesilent {self.state.active_workspace},address:{addr}",
                    f"focuswindow address:{addr}",
                ]
            )
        else:
            # Window is not stashed → stash it
            await self.backend.move_window_to_workspace(addr, f"special:{STASH_PREFIX}{name}")

    async def run_stash_show(self, name: str = "default") -> None:
        """[name] Toggle visibility of stash "name" (default: "default").

        Args:
            name: The stash group name
        """
        await self.backend.execute(f"togglespecialworkspace {STASH_PREFIX}{name}")
