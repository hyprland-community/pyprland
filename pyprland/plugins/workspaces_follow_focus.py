"""Force workspaces to follow the focus / mouse."""

from typing import cast

from .interface import Plugin


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    """Force workspaces to follow the focus / mouse."""

    workspace_list: list[int] = []

    async def on_reload(self) -> None:
        """Rebuild workspaces list."""
        self.workspace_list = list(range(1, self.config.get("max_workspaces", 10) + 1))

    async def event_focusedmon(self, screenid_name: str) -> None:
        """Reacts to monitor changes."""
        monitor_id, workspace_name = screenid_name.split(",")
        # move every free workspace to the currently focused desktop
        busy_workspaces = {
            mon["activeWorkspace"]["name"] for mon in cast(list[dict], await self.hyprctl_json("monitors")) if mon["name"] != monitor_id
        }
        workspaces = [w["name"] for w in cast(list[dict], await self.hyprctl_json("workspaces")) if w["id"] > 0]

        batch: list[str] = []
        for n in workspaces:
            if n in busy_workspaces or n == workspace_name:
                continue
            batch.append(f"moveworkspacetomonitor name:{n} {monitor_id}")
        await self.hyprctl(batch)

    async def run_change_workspace(self, direction: str) -> None:
        """<+1/-1> Switch workspaces of current monitor, avoiding displayed workspaces."""
        increment = int(direction)
        # get focused screen info
        monitors = await self.hyprctl_json("monitors")
        assert isinstance(monitors, list)
        for monitor in monitors:
            if monitor["focused"]:
                break
        else:
            self.log.error("Can not find a focused monitor")
            return
        assert isinstance(monitor, dict)
        busy_workspaces = {m["activeWorkspace"]["id"] for m in monitors if m["id"] != monitor["id"]}
        cur_workspace = monitor["activeWorkspace"]["id"]
        available_workspaces = [i for i in self.workspace_list if i not in busy_workspaces]
        try:
            idx = available_workspaces.index(cur_workspace)
        except ValueError:
            next_workspace = available_workspaces[0 if increment > 0 else -1]
        else:
            next_workspace = available_workspaces[(idx + increment) % len(available_workspaces)]

        await self.hyprctl(
            [
                f"moveworkspacetomonitor {next_workspace} {monitor['name']}",
                f"workspace {next_workspace}",
            ]
        )
