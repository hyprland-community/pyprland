" Not a real Plugin - provides some core features and some caching of commonly requested structures "
import json
from .interface import Plugin
from ..common import state, VersionInfo


class Extension(Plugin):
    "Internal built-in plugin allowing caching states and implementing special commands"

    async def init(self):
        "initializes the plugin"
        state.active_window = ""
        try:
            version = (await self.hyprctlJSON("version"))["tag"].split("-", 1)[0]
        except json.JSONDecodeError as e:
            self.log.error("Fail to parse hyprctl version: %s", e)
            await self.notify_error("Error: 'hyprctl version': incorrect JSON data")
            version = "v0.0.0"

        try:
            state.hyprland_version = VersionInfo(
                *(int(i) for i in version[1:].split(".")[:3])
            )
        except Exception as e:  # pylint: disable=broad-except
            self.log.error('Fail to parse hyprctl version "%s": %s', version, e)
            await self.notify_error("Failed to parse hyprctl version")
            state.hyprland_version = VersionInfo(0, 0, 0)

        state.active_workspace = (await self.hyprctlJSON("activeworkspace"))["name"]
        monitors = await self.hyprctlJSON("monitors")
        state.monitors = [mon["name"] for mon in monitors]
        state.active_monitor = next(mon["name"] for mon in monitors if mon["focused"])

    async def event_monitoradded(self, name):
        "track monitor"
        state.monitors.append(name)

    async def event_monitorremoved(self, name):
        "track monitor"
        state.monitors.remove(name)

    async def on_reload(self):
        state.variables = self.config.get("variables", {})

    async def event_activewindowv2(self, addr):
        "keep track of focused client"
        if not addr:
            self.log.warning("Active window is not defined")
            return
        state.active_window = "0x" + addr
        self.log.debug("active_window = %s", state.active_window)

    async def event_workspace(self, wrkspace):
        "track the active workspace"
        state.active_workspace = wrkspace
        self.log.debug("active_workspace = %s", state.active_workspace)

    async def event_focusedmon(self, mon):
        "track the active workspace"
        state.active_monitor, state.active_workspace = mon.rsplit(",", 1)
        self.log.debug("active_monitor = %s", state.active_monitor)

    def set_commands(self, **cmd_map):
        "Set some commands, made available as run_`name` methods"
        for name, fn in cmd_map.items():
            setattr(self, f"run_{name}", fn)
