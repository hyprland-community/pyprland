" Toggle monitors on or off "
from typing import Any, cast

from ..ipc import hyprctl, hyprctlJSON
from .interface import Plugin


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    async def run_toggle_dpms(self):
        """toggles dpms on/off for every monitor"""
        monitors = cast(list[dict[str, Any]], await hyprctlJSON("monitors"))
        powered_off = any(m["dpmsStatus"] for m in monitors)
        if not powered_off:
            await hyprctl("dpms on")
        else:
            await hyprctl("dpms off")
