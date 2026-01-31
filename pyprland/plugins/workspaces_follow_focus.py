"""Force workspaces to follow the focus / mouse."""

from typing import ClassVar, cast

from ..validation import ConfigField, ConfigItems
from .interface import Plugin


class Extension(Plugin):
    """Makes non-visible workspaces available on the currently focused screen."""

    environments: ClassVar[list[str]] = ["hyprland"]

    config_schema = ConfigItems(
        ConfigField("max_workspaces", int, default=10, description="Maximum number of workspaces to manage", category="basic"),
    )

    workspace_list: list[int]

    async def on_reload(self) -> None:
        """Rebuild workspaces list."""
        self.workspace_list = list(range(1, self.get_config_int("max_workspaces") + 1))

    async def event_focusedmon(self, screenid_name: str) -> None:
        """Reacts to monitor changes.

        Args:
            screenid_name: The screen ID and name
        """
        monitor_id, workspace_name = screenid_name.split(",")
        # move every free workspace to the currently focused desktop
        busy_workspaces = {mon["activeWorkspace"]["name"] for mon in await self.backend.get_monitors() if mon["name"] != monitor_id}
        workspaces = [w["name"] for w in cast("list[dict]", await self.backend.execute_json("workspaces")) if w["id"] > 0]

        batch: list[str] = []
        for n in workspaces:
            if n in busy_workspaces or n == workspace_name:
                continue
            batch.append(f"moveworkspacetomonitor name:{n} {monitor_id}")
        await self.backend.execute(batch)

    async def run_change_workspace(self, direction: str) -> None:
        """<direction> Switch workspaces of current monitor, avoiding displayed workspaces.

        Args:
            direction: Integer offset to move (e.g., +1 for next, -1 for previous)
        """
        increment = int(direction)
        # get focused screen info
        monitors = await self.backend.get_monitors()
        monitor = await self.get_focused_monitor_or_warn()
        if monitor is None:
            return
        busy_workspaces = {m["activeWorkspace"]["id"] for m in monitors if m["id"] != monitor["id"]}
        cur_workspace = monitor["activeWorkspace"]["id"]
        available_workspaces = [i for i in self.workspace_list if i not in busy_workspaces]
        try:
            idx = available_workspaces.index(cur_workspace)
        except ValueError:
            next_workspace = available_workspaces[0 if increment > 0 else -1]
        else:
            next_workspace = available_workspaces[(idx + increment) % len(available_workspaces)]

        await self.backend.execute(
            [
                f"moveworkspacetomonitor name:{next_workspace} {monitor['name']}",
                f"workspace {next_workspace}",
            ],
            weak=True,
        )
