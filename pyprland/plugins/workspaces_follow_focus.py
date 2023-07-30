""" Force workspaces to follow the focus / mouse """
from .interface import Plugin

from ..ipc import hyprctlJSON, hyprctl


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    workspace_list: list[int] = []

    async def load_config(self, config):
        "loads the config"
        await super().load_config(config)
        self.workspace_list = list(range(1, self.config.get("max_workspaces", 10) + 1))

    async def event_focusedmon(self, screenid_index):
        "reacts to monitor changes"
        monitor_id, workspace_id = screenid_index.split(",")
        workspace_id = int(workspace_id)
        # move every free workspace to the currently focused desktop
        busy_workspaces = set(
            mon["activeWorkspace"]["id"]
            for mon in await hyprctlJSON("monitors")
            if mon["name"] != monitor_id
        )
        workspaces = [w["id"] for w in await hyprctlJSON("workspaces") if w["id"] > 0]

        batch: list[str | list[str]] = []
        for n in workspaces:
            if n in busy_workspaces or n == workspace_id:
                continue
            batch.append(f"moveworkspacetomonitor {n} {monitor_id}")
        await hyprctl(batch)

    async def run_change_workspace(self, direction: str):
        """<+1/-1> Switch workspaces of current monitor, avoiding displayed workspaces"""
        increment = int(direction)
        # get focused screen info
        monitors = await hyprctlJSON("monitors")
        assert isinstance(monitors, list)
        for monitor in monitors:
            if monitor["focused"]:
                break
        else:
            self.log.error("Can not find a focused monitor")
            return
        assert isinstance(monitor, dict)
        busy_workspaces = set(
            m["activeWorkspace"]["id"] for m in monitors if m["id"] != monitor["id"]
        )
        cur_workspace = monitor["activeWorkspace"]["id"]
        available_workspaces = [
            i for i in self.workspace_list if i not in busy_workspaces
        ]
        try:
            idx = available_workspaces.index(cur_workspace)
        except ValueError:
            next_workspace = available_workspaces[0 if increment > 0 else -1]
        else:
            next_workspace = available_workspaces[
                (idx + increment) % len(available_workspaces)
            ]
        await hyprctl(f"moveworkspacetomonitor {next_workspace},{monitor['name']}")
        await hyprctl(f"workspace {next_workspace}")
