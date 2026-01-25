"""Sample plugin demonstrating pyprland plugin development.

Exposes a "counter" command: `pypr counter` showing focus change statistics.
- Listens to `activewindowv2` Hyprland event to count focus changes
- Uses configuration schema with typed accessors
"""

from pyprland.plugins.interface import Plugin
from pyprland.validation import ConfigField, ConfigItems


class Extension(Plugin):
    """Count and display window focus changes."""

    environments = ["hyprland"]

    focus_changes = 0

    config_schema = ConfigItems(
        ConfigField("multiplier", int, default=1, description="Multiplier for focus count"),
    )

    async def run_counter(self, args: str = "") -> None:
        """Show the number of focus switches and monitors.

        This command displays a notification with focus change statistics.
        """
        monitor_list = await self.backend.execute_json("monitors")
        await self.backend.notify_info(
            f"Focus changed {self.focus_changes} times on {len(monitor_list)} monitor(s)",
        )

    async def event_activewindowv2(self, _addr: str) -> None:
        """Handle window focus change events."""
        self.focus_changes += self.get_config_int("multiplier")
        self.log.info("Focus changed, count = %d", self.focus_changes)
