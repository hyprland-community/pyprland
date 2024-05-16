"""Not a real Plugin - provides some core features and some caching of commonly requested structures."""

import json

from ..common import MINIMUM_ADDR_LEN, state
from ..types import VersionInfo
from .interface import Plugin


class Extension(Plugin):
    """Internal built-in plugin allowing caching states and implementing special commands."""

    async def init(self) -> None:
        """Initialize the plugin."""
        state.active_window = ""
        try:
            version_info = await self.hyprctl_json("version")
        except json.JSONDecodeError as e:
            self.log.error("Fail to parse hyprctl version: %s", e)
            await self.notify_error("Error: 'hyprctl version': incorrect JSON data")
            version = "v0.0.0"
        else:
            if version_info.get("tag"):
                version = version_info["tag"].split("-", 1)[0]
            else:
                version = "v9.9.9"
                self.log.warning("No tag available, assuming a recent git version.")

        try:
            state.hyprland_version = VersionInfo(*(int(i) for i in version[1:].split(".")[:3]))
        except Exception as e:  # pylint: disable=broad-except
            self.log.error('Fail to parse version tag "%s": %s', version, e)
            await self.notify_error(f"Failed to parse hyprctl version tag: {version}")
            state.hyprland_version = VersionInfo(0, 0, 0)

        state.active_workspace = (await self.hyprctl_json("activeworkspace"))["name"]
        monitors = await self.hyprctl_json("monitors")
        state.monitors = [mon["name"] for mon in monitors]
        state.active_monitor = next(mon["name"] for mon in monitors if mon["focused"])

    async def event_monitoradded(self, name) -> None:
        """Track monitor."""
        state.monitors.append(name)

    async def event_monitorremoved(self, name) -> None:
        """Track monitor."""
        state.monitors.remove(name)

    async def on_reload(self) -> None:
        """Reload the plugin."""
        state.variables = self.config.get("variables", {})

    async def event_activewindowv2(self, addr) -> None:
        """Keep track of the focused client."""
        if not addr or len(addr) < MINIMUM_ADDR_LEN:
            self.log.warning("Active window is incorrect: %s.", addr)
            state.active_window = ""
        else:
            state.active_window = "0x" + addr
            self.log.debug("active_window = %s", state.active_window)

    async def event_workspace(self, wrkspace) -> None:
        """Track the active workspace."""
        state.active_workspace = wrkspace
        self.log.debug("active_workspace = %s", state.active_workspace)

    async def event_focusedmon(self, mon) -> None:
        """Track the active workspace."""
        state.active_monitor, state.active_workspace = mon.rsplit(",", 1)
        self.log.debug("active_monitor = %s", state.active_monitor)

    def set_commands(self, **cmd_map) -> None:
        """Set some commands, made available as run_`name` methods."""
        for name, fn in cmd_map.items():
            setattr(self, f"run_{name}", fn)
