" Not a real Plugin - provides some core features and some caching of commonly requested structures "
from .interface import Plugin
from ..common import state


class Extension(Plugin):
    "Internal built-in plugin allowing caching states and implementing special commands"

    async def init(self):
        "initializes the plugin"
        state.active_window = ""
        state.active_workspace = (await self.hyprctlJSON("activeworkspace"))["name"]
        state.active_monitor = next(
            mon["name"]
            for mon in (await self.hyprctlJSON("monitors"))
            if mon["focused"]
        )

    async def event_activewindowv2(self, addr):
        "keep track of focused client"
        state.active_window = "0x" + addr

    async def event_workspace(self, wrkspace):
        "track the active workspace"
        state.active_workspace = wrkspace

    async def event_focusedmon(self, mon):
        "track the active workspace"
        state.active_monitor, state.active_workspace = mon.rsplit(",", 1)

    def set_commands(self, **cmd_map):
        "Set some commands, made available as run_`name` methods"
        for name, fn in cmd_map.items():
            setattr(self, f"run_{name}", fn)
