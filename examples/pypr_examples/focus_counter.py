""" Sample plugin
Exposes a "dummy" command: `pypr dummy` showing a notification
- listen to `æctivewindowv2` Hyprland event to count focus changes
- uses `color` configuration item with a default value
"""

from pyprland.plugins.interface import Plugin
from pyprland.ipc import notify_info


class Extension(Plugin):
    "Dummy plugin example"
    focus_changes = 0

    async def run_dummy(self):
        "Show the number of focus switches and monitors"
        # The doc string above is used in `pypr help`

        monitor_list = await self.hyprctlJSON("monitors")
        color = self.config.get("color", "3333BB")
        await notify_info(
            f"Focus changed {self.focus_changes} times on {len(monitor_list)} monitor(s)",
            color=color,
            logger=self.log,
        )

    async def event_activewindowv2(self, _addr) -> None:
        "Handle event `activewindowv2` and track the count"
        self.focus_changes += 1
        self.log.info("Focus changed, count = %d", self.focus_changes)
