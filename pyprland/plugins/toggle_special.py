"""toggle_special allows having an "expose" like selection of windows in a special group."""

from typing import ClassVar, cast

from ..models import Environment
from ..validation import ConfigField, ConfigItems
from .interface import Plugin


class Extension(Plugin):
    """Toggle switching the focused window to a special workspace."""

    environments: ClassVar[list[Environment]] = [Environment.HYPRLAND]

    config_schema = ConfigItems(
        ConfigField("name", str, default="minimized", description="Default special workspace name", category="basic"),
    )

    async def run_toggle_special(self, special_workspace: str = "minimized") -> None:
        """[name] Toggles switching the focused window to the special workspace "name" (default: minimized).

        Args:
            special_workspace: The special workspace name
        """
        aw = cast("dict", await self.backend.execute_json("activewindow"))
        wid = aw["workspace"]["id"]
        assert isinstance(wid, int)
        if wid < 1:  # special workspace
            await self.backend.execute(
                [
                    f"togglespecialworkspace {special_workspace}",
                    f"movetoworkspacesilent {self.state.active_workspace},address:{aw['address']}",
                    f"focuswindow address:{aw['address']}",
                ]
            )
        else:
            await self.backend.move_window_to_workspace(aw["address"], f"special:{special_workspace}")
