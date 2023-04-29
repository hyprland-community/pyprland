from .interface import Plugin

from ..ipc import hyprctlJSON, hyprctl


class Extension(Plugin):
    async def run_toggle_dpms(self):
        monitors = await hyprctlJSON("monitors")
        poweredOff = any(m["dpmsStatus"] for m in monitors)
        if not poweredOff:
            await hyprctl("dpms on")
        else:
            await hyprctl("dpms off")
