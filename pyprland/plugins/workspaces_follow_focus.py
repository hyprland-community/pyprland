"""Force workspaces to follow the focus / mouse."""

import asyncio
from typing import cast

from ..models import Environment
from .interface import Plugin


class Extension(Plugin, environments=[Environment.HYPRLAND]):
    """Makes non-visible workspaces available on the currently focused screen."""

    _pending_task: asyncio.Task | None = None

    async def event_focusedmon(self, screenid_name: str) -> None:
        """Reacts to monitor changes (debounced).

        Args:
            screenid_name: The screen ID and name
        """
        if self._pending_task and not self._pending_task.done():
            self._pending_task.cancel()
        self._pending_task = asyncio.create_task(self._handle_focusedmon(screenid_name))

    async def busy_workspaces(self, focused_monitor: dict | None = None) -> set[int]:
        """Returns a set of workspaces that are currently in use on other monitors.

        Args:
            focused_monitor: The focused monitor dict to exclude from the result.
        """
        return {
            mon["activeWorkspace"]["id"]
            for mon in await self.backend.get_monitors()
            if focused_monitor is None or mon["id"] != focused_monitor["id"]
        }

    async def _handle_focusedmon(self, screenid_name: str) -> None:
        """Moves free workspaces to the focused monitor.

        Args:
            screenid_name: The screen ID and name
        """
        monitor_id, workspace_name = screenid_name.split(",")
        await asyncio.sleep(0.1)
        # move every free workspace to the currently focused desktop
        busy_workspaces = await self.busy_workspaces()
        workspaces = [
            w["id"]
            for w in cast("list[dict]", await self.backend.execute_json("workspaces"))
            if w.get("id") is not None and w.get("id") > 0
        ]

        batch: list[str] = []
        for n in workspaces:
            if n in busy_workspaces or n == workspace_name:
                continue
            batch.append(f"moveworkspacetomonitor {n} {monitor_id}")
        if batch:
            await self.backend.execute(batch)

    async def run_change_workspace(self, direction: str) -> None:
        """<direction> Switch workspaces of current monitor, avoiding displayed workspaces.

        Args:
            direction: Integer offset to move (e.g., +1 for next, -1 for previous)
        """
        increment = int(direction)
        # get focused screen info
        monitor = await self.get_focused_monitor_or_warn()
        if monitor is None:
            return
        busy_workspaces = await self.busy_workspaces(focused_monitor=monitor)
        cur_workspace = monitor["activeWorkspace"].get("id")
        workspaces = [
            w["id"]
            for w in cast("list[dict]", await self.backend.execute_json("workspaces"))
            if w.get("id") is not None and w.get("id") > 0
        ]
        available_workspaces = [i for i in workspaces if i not in busy_workspaces]

        if not available_workspaces:
            await self.logger.warning("No available workspaces to switch to.")
            return

        try:
            idx = available_workspaces.index(cur_workspace)
        except ValueError:
            next_workspace = available_workspaces[0 if increment > 0 else -1]
        else:
            next_workspace = available_workspaces[(idx + increment) % len(available_workspaces)]

        await self.backend.execute(
            [
                f"moveworkspacetomonitor {next_workspace} {monitor['name']}",
                f"workspace {next_workspace}",
            ],
            weak=True,
        )
