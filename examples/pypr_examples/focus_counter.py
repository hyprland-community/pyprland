""" Sample plugin
Exposes a "dummy" command: `pypr dummy` showing a notification
- listen to `æctivewindowv2` Hyprland event to count focus changes
- uses `color` configuration item with a default value
"""

from pyprland.plugins.interface import Plugin
from pyprland.ipc import hyprctlJSON, notify_info


class Extension(Plugin):
    "Dummy plugin example"
    focus_switch = 0

    async def run_dummy(self):
        "Show the number of focus switches and monitors"

        monitor_list = await hyprctlJSON("monitors")
        color = self.config.get("color", "3333BB")
        await notify_info(
            f"You switched windows {self.focus_switch}x on {len(monitor_list)} monitor(s)",
            color=color,
        )

    async def event_activewindowv2(self, _addr) -> None:
        "Handle event `activewindowv2`"
        self.focus_switch += 1
