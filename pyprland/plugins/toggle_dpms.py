from .interface import Plugin

from ..ipc import hyprctlJSON, hyprctl


class Extension(Plugin):
    async def run_toggle_dpms(self):
        """toggles dpms on/off for every monitor"""
        monitors = await hyprctlJSON("monitors")
        powered_off = any(m["dpmsStatus"] for m in monitors)
        if not powered_off:
            await hyprctl("dpms on")
        else:
            await hyprctl("dpms off")
