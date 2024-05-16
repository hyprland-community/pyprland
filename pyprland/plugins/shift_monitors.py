"""Shift workspaces across monitors."""

from typing import cast

from .interface import Plugin


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    """Shift workspaces across monitors."""

    monitors: list[str] = []

    async def init(self) -> None:
        """Initialize the plugin."""
        self.monitors: list[str] = [mon["name"] for mon in cast(list[dict], await self.hyprctl_json("monitors"))]

    async def run_shift_monitors(self, arg: str) -> None:
        """<+1/-1> Swaps monitors' workspaces in the given direction."""
        direction: int = int(arg)
        mon_list = self.monitors[:-1] if direction > 0 else list(reversed(self.monitors[1:]))

        for i, mon in enumerate(mon_list):
            await self.hyprctl(f"swapactiveworkspaces {mon} {self.monitors[i + direction]}")

    async def event_monitoradded(self, monitor) -> None:
        """Keep track of monitors."""
        self.monitors.append(monitor)

    async def event_monitorremoved(self, monitor) -> None:
        """Keep track of monitors."""
        self.monitors.remove(monitor)
