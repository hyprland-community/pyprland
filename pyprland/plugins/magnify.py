" Toggles workspace zooming "
from .interface import Plugin

from ..ipc import hyprctl


class Extension(Plugin):  # pylint: disable=missing-class-docstring
    zoomed = False

    async def run_zoom(self, *args):
        """[factor] zooms to "factor" or toggles zoom level ommited"""
        if args:
            value = int(args[0])
            await hyprctl(f"misc:cursor_zoom_factor {value}", "keyword")
            self.zoomed = value != 1
        else:  # toggle
            if self.zoomed:
                await hyprctl("misc:cursor_zoom_factor 1", "keyword")
            else:
                fact = int(self.config.get("factor", 2))
                await hyprctl(f"misc:cursor_zoom_factor {fact}", "keyword")
            self.zoomed = not self.zoomed
